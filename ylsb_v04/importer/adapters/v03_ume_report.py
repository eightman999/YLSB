from __future__ import annotations

import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RawReportError(f"{path.name}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RawReportError(f"{path.name}: expected a JSON object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [row for _, row in _jsonl_lines(path)]


def _jsonl_lines(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise RawReportError(f"{path.name}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise RawReportError(f"{path.name}:{line_number}: expected an object")
        rows.append((line_number, value))
    return rows


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"


def _unknown(reason: str) -> dict[str, str]:
    return {"kind": "unknown", "reason": reason}


@dataclass(frozen=True)
class AdapterDiagnostic:
    adapter: str
    root: str
    files_found: int
    models_found: tuple[str, ...]
    runs_found: int
    raw_task_rows: int
    performance_rows: int
    missing_required_fields: tuple[str, ...]
    ambiguous_fields: tuple[str, ...]
    unsupported_files: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "root": self.root,
            "files_found": self.files_found,
            "models_found": list(self.models_found),
            "runs_found": self.runs_found,
            "raw_task_rows": self.raw_task_rows,
            "performance_rows": self.performance_rows,
            "missing_required_fields": list(self.missing_required_fields),
            "ambiguous_fields": list(self.ambiguous_fields),
            "unsupported_files": list(self.unsupported_files),
        }


class RawReportError(ValueError):
    """A raw report could not be detected or extracted safely."""

    def __init__(self, message: str, diagnostic: AdapterDiagnostic | None = None):
        super().__init__(message)
        self.diagnostic = diagnostic


@dataclass
class _Source:
    root: Path
    cleanup: tempfile.TemporaryDirectory[str] | None

    def close(self) -> None:
        if self.cleanup is not None:
            self.cleanup.cleanup()


class V03UmeReportAdapter:
    """Extract the historical YLSB v0.3 UME first-wave report layout.

    Extraction is pure: the input tree is read only and every record retains a
    relative source reference. Normalized import and duplicate persistence are
    delegated to :class:`SubmissionImporter` by the public importer facade.
    """

    name = "v03-ume-report"

    def _open(self, source: str | Path) -> _Source:
        path = Path(source).resolve()
        if path.is_dir():
            root = self._find_root(path)
            return _Source(root, None)
        if not path.is_file() or path.suffix.lower() != ".zip":
            raise RawReportError(f"raw source must be a directory or ZIP: {source}")
        temporary = tempfile.TemporaryDirectory(prefix="ylsb-raw-")
        root = Path(temporary.name).resolve()
        try:
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    target = (root / member.filename).resolve()
                    if target != root and root not in target.parents:
                        raise RawReportError(f"ZIP member escapes archive root: {member.filename}")
                archive.extractall(root)
            return _Source(self._find_root(root), temporary)
        except zipfile.BadZipFile as exc:
            temporary.cleanup()
            raise RawReportError(f"{path.name}: corrupt ZIP: {exc}") from exc
        except Exception:
            temporary.cleanup()
            raise

    @staticmethod
    def _find_root(path: Path) -> Path:
        candidates: list[Path] = []
        if path.name == "complete_reports":
            candidates.append(path.parent)
        candidates.append(path)
        candidates.extend(reports.parent for reports in path.rglob("complete_reports") if reports.is_dir())
        if (path / "original").is_dir():
            candidates.insert(0, path / "original")
        for candidate in candidates:
            reports = candidate / "complete_reports"
            model_dirs = [item for item in reports.iterdir() if item.is_dir()] if reports.is_dir() else []
            if model_dirs and all((item / "summary.json").is_file() and V03UmeReportAdapter._is_ume_v03_summary(item / "summary.json") for item in model_dirs):
                return candidate
        diagnostic = AdapterDiagnostic(V03UmeReportAdapter.name, path.as_posix(), sum(p.is_file() for p in path.rglob("*")), (), 0, 0, 0, ("complete_reports/<model>/summary.json with course=ume and version=0.3",), (), ())
        raise RawReportError("unknown or incompatible raw report layout; expected v0.3 UME complete_reports", diagnostic)

    @staticmethod
    def _is_ume_v03_summary(path: Path) -> bool:
        try:
            value = _json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        return str(value.get("course", "")).lower() == "ume" and str(value.get("version", "")) == "0.3"

    @staticmethod
    def _rel(root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    def inventory(self, source: str | Path) -> dict[str, Any]:
        opened = self._open(source)
        try:
            root = opened.root
            reports = root / "complete_reports"
            model_dirs = sorted(item for item in reports.iterdir() if item.is_dir() and (item / "summary.json").is_file())
            files = [path for path in root.rglob("*") if path.is_file()]
            supported = {"summary.json", "model_card.json", "raw.jsonl", "pp_tg_vram.jsonl", "remeasure_pp_tg_vram.json", "pp_remeasure.json", "checkpoint.json", "COMPLETE_REPORT.md", "run.log", "env_fingerprint.json", "hardware_model_card.json", "README.md"}
            unsupported = tuple(self._rel(root, path) for path in files if path.name not in supported and path.suffix.lower() not in {".json", ".jsonl", ".md", ".log"})
            raw_rows = [row for path in model_dirs if (path / "raw.jsonl").is_file() for row in _jsonl(path / "raw.jsonl")]
            raw_count = sum(row.get("section") in {"core", "sentinel", "api_smoke"} for row in raw_rows)
            perf_count = sum(row.get("section") in {"pp", "tg", "depth", "cold_load"} for row in raw_rows) + sum(len(_jsonl(path / "pp_tg_vram.jsonl")) for path in model_dirs if (path / "pp_tg_vram.jsonl").is_file())
            missing: list[str] = []
            for required in ("env_fingerprint.json", "hardware_model_card.json"):
                if not (root / "complete_reports" / required).is_file() and not (root / required).is_file():
                    missing.append(required)
            for model_dir in model_dirs:
                for required in ("summary.json", "model_card.json", "raw.jsonl"):
                    if not (model_dir / required).is_file():
                        missing.append(f"{self._rel(root, model_dir)}/{required}")
            ambiguous = ("effective_seed", "flash_attention_boolean", "tensor_split_values", "chat_template_sha256")
            diagnostic = AdapterDiagnostic(self.name, root.as_posix(), len(files), tuple(path.name for path in model_dirs), len(model_dirs), raw_count, perf_count, tuple(missing), ambiguous, unsupported)
            return diagnostic.as_dict()
        finally:
            opened.close()

    def extract(self, source: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        opened = self._open(source)
        try:
            root = opened.root
            reports = root / "complete_reports"
            model_dirs = sorted(item for item in reports.iterdir() if item.is_dir() and (item / "summary.json").is_file())
            diagnostic = self._inventory_root(root, model_dirs)
            if diagnostic["missing_required_fields"]:
                raise RawReportError("raw bundle is incomplete; see inventory", AdapterDiagnostic(**{k: v if k not in {"models_found", "missing_required_fields", "ambiguous_fields", "unsupported_files"} else tuple(v) for k, v in diagnostic.items()}))
            env_path = root / "env_fingerprint.json"
            if not env_path.is_file():
                env_path = reports / "env_fingerprint.json"
            hw_path = reports / "hardware_model_card.json"
            if not hw_path.is_file():
                hw_path = root / "hardware_model_card.json"
            env = _json(env_path)
            hardware_card = _json(hw_path)
            for name in ("runtime", "ram", "os", "cuda_toolkit", "cpu"):
                if name in env and not isinstance(env[name], dict):
                    raise RawReportError(f"{env_path.name}: /{name} must be an object")
            hardware = hardware_card.get("hardware", {})
            if not isinstance(hardware, dict) or not isinstance(hardware.get("gpus", []), list):
                raise RawReportError(f"{hw_path.name}: /hardware/gpus must be an array")
            if not all(isinstance(gpu, dict) for gpu in hardware.get("gpus", [])):
                raise RawReportError(f"{hw_path.name}: /hardware/gpus entries must be objects")
            source_hashes = {self._rel(root, path): _sha256(path) for path in root.rglob("*") if path.is_file()}
            records: list[dict[str, Any]] = []
            names = [str(g.get("name", "")).lower() for g in hardware_card.get("hardware", {}).get("gpus", [])]
            machine_id = "machine-master-rtx3060-p100-01" if any("rtx 3060" in name for name in names) and any("p100" in name for name in names) else "machine-" + _slug("-".join(names))
            hardware_records = self._hardware_records(root, hw_path, hardware_card, machine_id)
            records.extend(hardware_records)
            records.append(self._machine_record(root, env_path, env, hardware_card, machine_id))
            runtime_record = self._runtime_record(root, env_path, env)
            records.append(runtime_record)
            for model_dir in model_dirs:
                records.extend(self._model_records(root, model_dir, env, hardware_card, machine_card=machine_id, source_hashes=source_hashes))
            diagnostic["source_hashes"] = source_hashes
            return records, diagnostic
        finally:
            opened.close()

    def _prov(self, root: Path, path: Path, kind: str = "reported", pointer: str | None = None, reason: str | None = None) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": kind, "source": self._rel(root, path)}
        if pointer:
            value["source_pointer"] = pointer
        if reason:
            value["reason"] = reason
        if kind == "unknown":
            value.pop("source", None)
        return value

    def _base(self, record_type: str, provenance: dict[str, Any]) -> dict[str, Any]:
        return {"schema_version": "normalized-corpus-v0.2", "record_type": record_type, "provenance": provenance}

    def _hardware_records(self, root: Path, path: Path, card: dict[str, Any], machine_id: str) -> list[dict[str, Any]]:
        output = []
        for gpu in card.get("hardware", {}).get("gpus", []):
            index = gpu.get("index", len(output))
            name_slug = _slug(str(gpu.get("name", "gpu"))).replace("nvidia-", "").replace("tesla-", "").replace("geforce-", "")
            name_slug = re.sub(r"-pcie-?\d+gb$", "", name_slug).replace("-", "")
            hardware_id = f"gpu-master-{index}-{name_slug}"
            row = self._base("hardware", {"default": self._prov(root, path), "/canonical_name": _unknown("registry enrichment is intentionally separate"), "/vendor": _unknown("Vendor is not a separate reported field in the raw hardware card."), "/vram_each_gb": {"kind": "derived", "source": self._rel(root, path), "reason": "Reported vram_mib converted to GiB."}})
            vram = gpu.get("vram_mib")
            row.update({"hardware_id": hardware_id, "hardware_type": "gpu", "reported_name": gpu.get("name"), "canonical_name": None, "vendor": None, "architecture": gpu.get("generation"), "architecture_code": gpu.get("arch_code"), "count": 1, "vram_each_gb": vram / 1024 if isinstance(vram, (int, float)) else None, "memory_type": gpu.get("vram_type"), "memory_bandwidth_gbps": gpu.get("memory_bandwidth_GBps"), "pcie": gpu.get("pcie")})
            output.append(row)
        return output

    def _machine_record(self, root: Path, path: Path, env: dict[str, Any], card: dict[str, Any], machine_id: str) -> dict[str, Any]:
        gpus = card.get("hardware", {}).get("gpus", [])
        row = self._base("machine", {"default": self._prov(root, path), "/cpu": _unknown("CPU identity and topology are absent from the raw bundle."), "/ram": {"kind": "reported", "source": self._rel(root, path), "source_pointer": "/ram"}, "/aggregate/total_vram_gb": {"kind": "derived", "source": self._rel(root, path), "reason": "sum of reported GPU vram_mib converted to GiB"}, "/rocm": _unknown("ROCm is not reported and is not assumed." )})
        gpu_ids = []
        for i, gpu in enumerate(gpus):
            name_slug = _slug(str(gpu.get("name", "gpu"))).replace("nvidia-", "").replace("tesla-", "").replace("geforce-", "")
            name_slug = re.sub(r"-pcie-?\d+gb$", "", name_slug).replace("-", "")
            gpu_ids.append(f"gpu-master-{gpu.get('index', i)}-{name_slug}")
        ram = env.get("ram", {})
        vram_values = [gpu.get("vram_mib") for gpu in gpus]
        total_vram = sum(vram_values) / 1024 if all(isinstance(value, (int, float)) for value in vram_values) else None
        row.update({"machine_id": machine_id, "cpu": env.get("cpu", {}), "ram": {"total_gb": ram.get("memtotal_giB_approx"), "memtotal_kb": ram.get("memtotal_kb"), "swap_gb": ram.get("swap_giB")}, "gpu_ids": gpu_ids, "aggregate": {"gpu_count": len(gpus), "total_vram_gb": total_vram}, "os": env.get("os", {}), "driver": env.get("driver_version"), "cuda": env.get("cuda_toolkit", {}), "rocm": None})
        return row

    def _runtime_record(self, root: Path, path: Path, env: dict[str, Any]) -> dict[str, Any]:
        runtime = env.get("runtime", {})
        row = self._base("runtime", {"default": self._prov(root, path, pointer="/runtime")})
        row.update({"runtime_id": "runtime-llama-cpp-" + str(runtime.get("llama_cpp_commit", "unknown"))[:16], "name": "llama-server", "family": "llama.cpp", "version": runtime.get("version_string"), "commit": runtime.get("llama_cpp_commit"), "backend": None, "features": {"commit": runtime.get("llama_cpp_commit"), "binary": runtime.get("binary")}})
        return row

    def _model_records(self, root: Path, directory: Path, env: dict[str, Any], card: dict[str, Any], machine_card: str, source_hashes: dict[str, str]) -> list[dict[str, Any]]:
        summary_path = directory / "summary.json"
        model_card_path = directory / "model_card.json"
        summary = _json(summary_path)
        model_card = _json(model_card_path) if model_card_path.is_file() else {}
        model_name = directory.name
        model_id = f"model-{model_name}"
        run_id = f"run-v03-ume-{model_name}"
        submission_id = f"submission-v03-ume-{model_name}"
        runtime_id = "runtime-llama-cpp-" + str(env.get("runtime", {}).get("llama_cpp_commit", "unknown"))[:16]
        card = model_card.get("model", {})
        kind = str(card.get("kind") or "").lower()
        architecture = {"type": "moe" if "moe" in kind else "dense" if kind else "unknown", "implementation": card.get("architecture"), "total_params_b": card.get("total_params_nominal") / 1e9 if card.get("total_params_nominal") is not None else None, "active_params_b": card.get("active_params_nominal") / 1e9 if card.get("active_params_nominal") is not None else None, "experts": card.get("expert_count"), "active_experts": card.get("expert_used_count"), "note": card.get("params_note")}
        model = self._base("model", {"default": self._prov(root, model_card_path), "/source_repo": _unknown("Upstream model repository is not reported."), "/format": {"kind": "inferred", "source": self._rel(root, model_card_path), "reason": "Reported artifact path and GGUF file type identify the container."}, "/architecture": {"kind": "derived", "source": self._rel(root, model_card_path), "reason": "Parameter and architecture fields are normalized from the reported model card."}})
        model.update({"model_id": model_id, "reported_name": card.get("name", model_name), "canonical_name": None, "provider_or_family": card.get("architecture"), "architecture": architecture, "quant": card.get("quant", summary.get("quant")), "format": "GGUF", "file_type": card.get("file_type_name"), "artifact_path_reported": card.get("path"), "sha256": card.get("sha256"), "file_size_bytes": card.get("filesize_bytes")})
        submission = self._base("submission", {"default": self._prov(root, summary_path)})
        submission.update({"submission_id": submission_id, "benchmark": {"name": "YLSB", "course": "UME", "version": "0.3"}, "timestamp": {"started": summary.get("started_jst"), "finished": summary.get("finished_jst")}, "dataset_status": "frozen", "source_files": source_hashes})
        run = self._base("run", {"default": self._prov(root, summary_path), "/config/seed/effective": _unknown("Request omitted seed; realized integer seed is not reported."), "/config/flash_attention": _unknown("flash_attn=auto does not establish an effective boolean."), "/config/tensor_split": _unknown("Explicit tensor-split values are absent."), "/config/mtp": _unknown("MTP is not explicitly reported in the v0.3 runtime settings."), "/config/speculative": _unknown("Speculative decoding is not explicitly reported in the v0.3 runtime settings.")})
        settings = summary.get("runtime_settings", {})
        chat = summary.get("chat_template") or {}
        env_meta = summary.get("env_meta") or {}
        candidates = [{"identifier": "runtime_props", "sha256": chat.get("sha256"), "length": chat.get("len"), "source": chat.get("source")}]
        if env_meta.get("chat_template_sha256"):
            candidates.append({"identifier": "gguf_metadata", "sha256": env_meta.get("chat_template_sha256"), "length": env_meta.get("chat_template_len"), "source": env_meta.get("chat_template_source")})
        config = {"ctx": settings.get("ctx_size"), "batch": settings.get("batch_size"), "ubatch": settings.get("ubatch_size"), "split_mode": settings.get("split-mode"), "tensor_split": None, "kv_type": {"k": settings.get("cache_type_k"), "v": settings.get("cache_type_v"), "offload": settings.get("kv_offload")}, "flash_attention": settings.get("flash_attn"), "mtp": None, "speculative": None, "seed": {"request": settings.get("seed_in_request_body"), "server_default": settings.get("seed_server_default"), "effective": None, "note": settings.get("seed_note")}, "max_tokens": settings.get("max_tokens_by_section"), "cold_or_warm": "mixed_by_section", "n_gpu_layers": settings.get("n-gpu-layers"), "parallel": settings.get("parallel"), "jinja": settings.get("jinja"), "fit": settings.get("fit"), "temperature": settings.get("temperature"), "lane": summary.get("lane"), "thinking": settings.get("thinking"), "chat_template_candidates": candidates, "raw_runtime_settings": settings}
        run.update({"run_id": run_id, "submission_id": submission_id, "machine_id": machine_card, "model_id": model_id, "runtime_id": runtime_id, "config": config, "artifacts": {"source_hashes": source_hashes, "model_sha256": summary.get("model_sha256"), "fixtures_sha256": summary.get("fixtures_sha256", {}), "grader_sha256": summary.get("grader_sha256", {})}, "lane": summary.get("lane"), "model_path": summary.get("model_path"), "formal_record_compliance": {"compliant": False, "missing_or_ambiguous_required_fields": ["effective_seed", "flash_attention_boolean", "tensor_split_values", "original_pp_tg_vram"] + (["unambiguous_chat_template_hash"] if len({item.get("sha256") for item in candidates}) > 1 else [])}})
        records = [submission, model, run]
        raw_path = directory / "raw.jsonl"
        if raw_path.is_file():
            records.extend(self._task_records(root, raw_path, run_id))
            records.extend(self._original_performance(root, raw_path, run_id))
        posthoc = directory / "pp_tg_vram.jsonl"
        if posthoc.is_file():
            records.extend(self._posthoc_performance(root, posthoc, run_id))
        records.append(self._verdict(root, summary_path, summary, run_id))
        return records

    def _task_records(self, root: Path, path: Path, run_id: str) -> list[dict[str, Any]]:
        output = []
        for line_number, row in _jsonl_lines(path):
            section = row.get("section")
            if section not in {"core", "sentinel", "api_smoke"} or not row.get("id"):
                continue
            task_id = row["id"]
            output_value = row.get("model_output", row.get("raw_content", ""))
            invalid = task_id == "CORE-CONSTRAINT-003"
            protocol = run_id.endswith("gpt-oss-20b") and (output_value == "" or output_value is None)
            status = "FIXTURE_INVALID" if invalid else "PROTOCOL" if protocol else "pass" if row.get("passed") else "fail"
            score = 1 if row.get("passed") else 0
            record = self._base("task_result", {"default": self._prov(root, path, pointer=f"line:{line_number}"), "/reuse": {"kind": "derived", "source": self._rel(root, path), "reason": "Raw task output remains independently regradable."}})
            record.update({"task_result_id": f"{run_id}-task-{task_id}", "run_id": run_id, "task_id": task_id, "section": section, "category": row.get("category"), "prompt_variant": row.get("mode"), "score": score, "status": status, "grader": row.get("grader"), "grader_note": row.get("note"), "reuse": {"classification": "invalid" if invalid else "requires_rerun" if protocol else "regradable", "reason": "Raw model output and expected answer are preserved."}, "source": {"path": self._rel(root, path), "line": line_number}, "model_output": row.get("raw_content"), "normalized_answer": row.get("answer"), "expected_answer": row.get("gold"), "format_ok": row.get("format_ok"), "non_empty": row.get("non_empty"), "http_status": row.get("http_status"), "timings": row.get("timings"), "fixture_version": "v0.3", "failure_class_reported": row.get("taxonomy"), "failure_class_audited": "FIXTURE_INVALID" if invalid else "PROTOCOL" if protocol else row.get("taxonomy")})
            output.append(record)
        return output

    def _original_performance(self, root: Path, path: Path, run_id: str) -> list[dict[str, Any]]:
        output = []
        for line_number, row in _jsonl_lines(path):
            section = row.get("section")
            if section not in {"pp", "tg", "depth", "cold_load"}:
                continue
            metric = section
            value = row.get("tokens_per_sec", row.get("predicted_per_second", row.get("cold_wall_ms", row.get("wall_ms"))))
            record = self._base("performance", {"default": self._prov(root, path, pointer=f"line:{line_number}"), "/vram": _unknown("Original PP/TG run did not sample VRAM.") if section in {"pp", "tg"} else self._prov(root, path, kind="reported")})
            target = row.get("pp_tokens_target") if section == "pp" else row.get("tg_tokens_target")
            record.update({"measurement_id": f"{run_id}-original-{metric}-{row.get('depth') if section == 'depth' else (target or 'load')}-r{row.get('rep', 1)}", "run_id": run_id, "measurement_phase": "original_run", "measurement_source": "raw_original_run", "metric": metric, "value": value, "unit": "tokens/s" if section != "cold_load" else "ms", "repeat": row.get("rep"), "target_tokens": target, "prompt_tokens": row.get("pp_tokens_actual"), "generated_tokens": row.get("tg_tokens_actual", row.get("completion_tokens")), "depth": row.get("depth"), "wall_ms": row.get("wall_ms", row.get("cold_wall_ms")), "timings_cache_n": row.get("cache_n", (row.get("timings") or {}).get("cache_n")), "vram": None, "reuse": {"classification": "reusable_as_is", "reason": "Original raw measurement is preserved."}, "source": {"path": self._rel(root, path), "line": line_number}})
            output.append(record)
        return output

    def _posthoc_performance(self, root: Path, path: Path, run_id: str) -> list[dict[str, Any]]:
        output = []
        for line_number, row in _jsonl_lines(path):
            metric = row.get("kind")
            if metric not in {"pp", "tg"}:
                continue
            record = self._base("performance", {"default": self._prov(root, path, pointer=f"line:{line_number}"), "/reuse": {"kind": "derived", "source": self._rel(root, path), "reason": "Post-hoc VRAM is retained as a separate phase."}})
            record.update({"measurement_id": f"{run_id}-posthoc-{metric}-{row.get('target')}-r{row.get('rep')}", "run_id": run_id, "measurement_phase": "posthoc_vram_remeasurement", "measurement_source": "posthoc_remeasurement_not_original_run", "metric": metric, "value": row.get("tps"), "unit": "tokens/s", "repeat": row.get("rep"), "target_tokens": row.get("target"), "prompt_tokens": row.get("prompt_n"), "generated_tokens": row.get("tg_tokens_actual", 1 if metric == "pp" else row.get("target")), "timings_cache_n": row.get("cache_n", (row.get("timings") or {}).get("cache_n")), "vram": {"before": row.get("vram_before"), "during": row.get("vram_during"), "after": row.get("vram_after")}, "wall_ms": row.get("wall_ms"), "reuse": {"classification": "reusable_as_is", "reason": "Raw repeat is retained as a separately identified post-hoc remeasurement."}, "source": {"path": self._rel(root, path), "line": line_number}})
            output.append(record)
        return output

    def _verdict(self, root: Path, path: Path, summary: dict[str, Any], run_id: str) -> dict[str, Any]:
        record = self._base("verdict", {"default": self._prov(root, path, pointer="/gates")})
        record.update({"run_id": run_id, "policy_version": "YLSB-v0.3", "gates": summary.get("gates", {}), "source": {"path": self._rel(root, path), "pointer": "/gates"}, "observation_only": True})
        return record

    def _inventory_root(self, root: Path, model_dirs: list[Path]) -> dict[str, Any]:
        reports = root / "complete_reports"
        files = [path for path in root.rglob("*") if path.is_file()]
        supported = {"summary.json", "model_card.json", "raw.jsonl", "pp_tg_vram.jsonl", "remeasure_pp_tg_vram.json", "pp_remeasure.json", "checkpoint.json", "COMPLETE_REPORT.md", "run.log", "env_fingerprint.json", "hardware_model_card.json", "README.md"}
        raw_rows = [row for path in model_dirs if (path / "raw.jsonl").is_file() for row in _jsonl(path / "raw.jsonl")]
        raw_count = sum(row.get("section") in {"core", "sentinel", "api_smoke"} for row in raw_rows)
        perf_count = sum(row.get("section") in {"pp", "tg", "depth", "cold_load"} for row in raw_rows) + sum(len(_jsonl(path / "pp_tg_vram.jsonl")) for path in model_dirs if (path / "pp_tg_vram.jsonl").is_file())
        missing = []
        for required in ("env_fingerprint.json", "hardware_model_card.json"):
            candidate = root / required if (root / required).is_file() else reports / required
            if not candidate.is_file():
                missing.append(required)
        missing.extend(f"{self._rel(root, model_dir)}/{name}" for model_dir in model_dirs for name in ("summary.json", "model_card.json", "raw.jsonl") if not (model_dir / name).is_file())
        return {"adapter": self.name, "root": root.as_posix(), "files_found": len(files), "models_found": [path.name for path in model_dirs], "runs_found": len(model_dirs), "raw_task_rows": raw_count, "performance_rows": perf_count, "missing_required_fields": missing, "ambiguous_fields": ["effective_seed", "flash_attention_boolean", "tensor_split_values", "chat_template_sha256"], "unsupported_files": [self._rel(root, path) for path in files if path.name not in supported and path.suffix.lower() not in {".json", ".jsonl", ".md", ".log"}]}


__all__ = ["AdapterDiagnostic", "RawReportError", "V03UmeReportAdapter"]
