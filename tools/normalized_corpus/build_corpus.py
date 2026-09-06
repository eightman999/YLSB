#!/usr/bin/env python3
"""Build the YLSB v0.3 UME normalized corpus from the frozen baseline.

The frozen tree is input-only.  Generated records deliberately keep observations,
metadata, policy verdicts, and reuse decisions in separate datasets.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
BASELINE_ID = "ume-first-wave-20260906"
FROZEN_ROOT = ROOT / "results/v0.3/frozen" / BASELINE_ID
RAW_ROOT = FROZEN_ROOT / "original"
REPORTS = RAW_ROOT / "complete_reports"
NORMALIZED = ROOT / "results/v0.3/normalized"
DERIVED = ROOT / "results/v0.3/derived"
SCHEMA_VERSION = "normalized-corpus-v0.1"
PROVENANCE_KINDS = {"reported", "derived", "registry", "inferred", "unknown"}
REUSE_CLASSES = {"reusable_as_is", "regradable", "requires_rerun", "invalid"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def source(path: Path, pointer: str | None = None, kind: str = "reported") -> dict[str, Any]:
    item: dict[str, Any] = {"kind": kind, "source_path": rel(path)}
    if pointer:
        item["source_pointer"] = pointer
    return item


def unknown(reason: str) -> dict[str, str]:
    return {"kind": "unknown", "reason": reason}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def dump_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode() for row in rows
    )


def model_dirs() -> list[Path]:
    return sorted(path for path in REPORTS.iterdir() if path.is_dir() and (path / "summary.json").exists())


def fixture_constraint_audit() -> dict[str, dict[str, Any]]:
    """Independently enumerate the four five-symbol constraint fixtures."""
    positions = list(itertools.permutations("ABCDE"))
    predicates = {
        "CORE-CONSTRAINT-001": lambda p: (
            p.index("A") < p.index("D")
            and abs(p.index("A") - p.index("D")) != 1
            and p.index("B") < p.index("C")
            and abs(p.index("B") - p.index("D")) != 1
            and p.index("B") not in (0, 4)
            and p.index("E") not in (0, 4)
            and p.index("B") == p.index("A") + 1
            and p.index("E") == p.index("B") + 1
            and p.index("D") not in (0, 4)
        ),
        "CORE-CONSTRAINT-002": lambda p: (
            abs(p.index("C") - p.index("E")) != 1
            and p.index("D") not in (0, 4)
            and p[4] == "B"
            and p.index("C") not in (0, 4)
            and p.index("D") < p.index("C")
            and abs(p.index("A") - p.index("E")) != 1
            and abs(p.index("C") - p.index("D")) != 1
        ),
        "CORE-CONSTRAINT-003": lambda p: (
            p.index("C") < p.index("B")
            and p.index("A") == p.index("B") + 1
            and p.index("D") < p.index("C")
            and p.index("A") < p.index("E")
        ),
        "CORE-CONSTRAINT-004": lambda p: (
            p.index("C") == p.index("A") + 1
            and p.index("E") not in (0, 4)
            and abs(p.index("D") - p.index("E")) != 1
            and p.index("D") < p.index("A")
            and abs(p.index("B") - p.index("D")) != 1
        ),
    }
    fixture = {row["id"]: row for row in read_jsonl(ROOT / "ume/tests/core_ume_28.jsonl")}
    result = {}
    for task_id, predicate in predicates.items():
        solutions = ["".join(item) for item in positions if predicate(item)]
        reported_gold = fixture[task_id]["gold"]
        result[task_id] = {
            "reported_gold": reported_gold,
            "enumerated_solutions": solutions,
            "unique": len(solutions) == 1,
            "gold_valid": reported_gold in solutions,
        }
    return result


def build_manifest() -> dict[str, Any]:
    archive = Path("/Users/eightman/Downloads/ylsb_ume_v0.3_complete_reports.zip")
    files = []
    for path in sorted(item for item in RAW_ROOT.rglob("*") if item.is_file()):
        files.append({"path": path.relative_to(RAW_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    top_duplicates = []
    for name in ("env_fingerprint.json", "hardware_model_card.json"):
        left, right = RAW_ROOT / name, REPORTS / name
        top_duplicates.append({
            "path_a": left.relative_to(RAW_ROOT).as_posix(),
            "path_b": right.relative_to(RAW_ROOT).as_posix(),
            "byte_identical": left.read_bytes() == right.read_bytes(),
        })
    return {
        "baseline_id": BASELINE_ID,
        "dataset_status": "frozen",
        "policy": "Files under original/ are immutable source observations.",
        "source_archive": {
            "reported_path": str(archive),
            "filename": archive.name,
            "bytes": archive.stat().st_size,
            "sha256": sha256(archive),
        },
        "file_count": len(files),
        "files": files,
        "known_duplicate_files": top_duplicates,
    }


def quality_reuse(model: str, row: dict[str, Any], fixture_audit: dict[str, Any]) -> tuple[str, str]:
    if row["id"] in fixture_audit and not fixture_audit[row["id"]]["gold_valid"]:
        return "invalid", "Fixture gold contradicts the unique solution obtained by exhaustive enumeration."
    if model == "gpt-oss-20b" and not row.get("non_empty"):
        return "requires_rerun", "Empty response clusters by section despite HTTP success; runtime/template/protocol compatibility is unresolved."
    return "regradable", "Raw model output and expected answer are preserved independently of the v0.3 verdict."


def build() -> tuple[dict[str, bytes], dict[str, Any]]:
    env_path = REPORTS / "env_fingerprint.json"
    hw_path = REPORTS / "hardware_model_card.json"
    env = read_json(env_path)
    hw_card = read_json(hw_path)
    dirs = model_dirs()
    fixture_audit = fixture_constraint_audit()

    submissions: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    task_results: list[dict[str, Any]] = []
    performance: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []

    runtime_id = "runtime-llama-cpp-5ea1b124e7df"
    machine_id = "machine-master-rtx3060-p100-01"
    hardware_ids = ["gpu-master-0-rtx3060", "gpu-master-1-p100"]
    runtime = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "runtime",
        "runtime_id": runtime_id,
        "name": "llama-server",
        "family": "llama.cpp",
        "fork": "upstream (ggml-org/llama.cpp), not a custom fork",
        "version": env["runtime"]["version_string"],
        "commit": env["runtime"]["llama_cpp_commit"],
        "backend": "CUDA",
        "features": {"flash_attention": "auto_unresolved", "tensor_split": False, "mtp": False, "speculative": False},
        "provenance": {
            "default": source(env_path, "/runtime"),
            "/fork": source(hw_path, "/hardware/runtime_fork/fork"),
            "/backend": {"kind": "inferred", "reason": "CUDA environment and NVIDIA devices are reported; backend name is not explicit."},
            "/features/flash_attention": source(env_path, "/runtime_cli_defaults_not_overridden/flash_attn"),
            "/features/tensor_split": source(dirs[0] / "summary.json", "/lane"),
        },
    }

    hardware = []
    for index, (gpu, details, hardware_id) in enumerate(zip(env["gpu"], hw_card["hardware"]["gpus"], hardware_ids)):
        hardware.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "hardware",
            "hardware_id": hardware_id,
            "hardware_type": "gpu",
            "reported_name": gpu["name"],
            "canonical_name": gpu["name"],
            "vendor": "NVIDIA",
            "architecture": details.get("generation"),
            "architecture_code": details.get("arch_code"),
            "count": 1,
            "vram_each_gb": gpu["vram_mib"] / 1024,
            "memory_type": details.get("vram_type"),
            "memory_bandwidth_gbps": details.get("memory_bandwidth_GBps"),
            "compute_capability": None,
            "pcie": details.get("pcie"),
            "provenance": {
                "default": source(env_path, f"/gpu/{index}"),
                "/canonical_name": {"kind": "registry", "source_path": rel(hw_path), "source_pointer": f"/hardware/gpus/{index}/name", "rule": "exact reported-name registry entry"},
                "/architecture": source(hw_path, f"/hardware/gpus/{index}/generation"),
                "/architecture_code": source(hw_path, f"/hardware/gpus/{index}/arch_code"),
                "/memory_type": source(hw_path, f"/hardware/gpus/{index}/vram_type"),
                "/memory_bandwidth_gbps": source(hw_path, f"/hardware/gpus/{index}/memory_bandwidth_GBps"),
                "/compute_capability": unknown("Not reported in the frozen bundle."),
            },
        })

    machine = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "machine",
        "machine_id": machine_id,
        "cpu": {
            "reported_name": None, "canonical_name": None, "vendor": None, "architecture": None,
            "cores": None, "threads": None, "memory_channels": None, "pcie_generation": None, "pcie_lanes": None,
        },
        "ram": {"total_gb": env["ram"]["memtotal_giB_approx"], "memtotal_kb": env["ram"]["memtotal_kb"], "swap_gb": env["ram"]["swap_giB"]},
        "gpu_ids": hardware_ids,
        "aggregate": {"gpu_count": env["gpu_count"], "total_vram_gb": sum(item["vram_mib"] for item in env["gpu"]) / 1024},
        "os": env["os"],
        "driver": env["driver_version"],
        "cuda": env["cuda_toolkit"],
        "rocm": None,
        "provenance": {
            "default": source(env_path),
            "/cpu": unknown("CPU identity and topology are absent from the frozen bundle."),
            "/aggregate/total_vram_gb": {"kind": "derived", "inputs": [f"hardware:{item}" for item in hardware_ids], "formula": "sum(vram_mib)/1024"},
            "/rocm": unknown("ROCm is not reported and is not assumed to be installed."),
        },
    }

    for directory in dirs:
        alias = directory.name
        summary_path = directory / "summary.json"
        model_card_path = directory / "model_card.json"
        summary = read_json(summary_path)
        card = read_json(model_card_path)["model"]
        run_id = f"run-v03-ume-{alias}"
        submission_id = f"submission-v03-ume-{alias}"
        model_id = f"model-{alias}"
        submissions.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "submission",
            "submission_id": submission_id,
            "benchmark": {"name": "YLSB", "version": "0.3", "course": "UME"},
            "timestamp": {"started": summary["started_jst"], "finished": summary["finished_jst"]},
            "author": None,
            "source_path": rel(directory),
            "dataset_status": "frozen",
            "provenance": {"default": source(summary_path), "/author": unknown("No author field is present in the report bundle.")},
        })
        kind = str(card.get("kind") or "").lower()
        architecture_type = "moe" if "moe" in kind else "dense" if kind else "unknown"
        models.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "model",
            "model_id": model_id,
            "reported_name": card["name"],
            "canonical_name": card["name"],
            "provider_or_family": card.get("architecture"),
            "architecture": {
                "type": architecture_type,
                "implementation": card.get("architecture"),
                "total_params_b": card.get("total_params_nominal") / 1e9 if card.get("total_params_nominal") is not None else None,
                "active_params_b": card.get("active_params_nominal") / 1e9 if card.get("active_params_nominal") is not None else None,
                "experts": card.get("expert_count"),
                "active_experts": card.get("expert_used_count"),
                "note": card.get("params_note"),
            },
            "quant": card["quant"],
            "format": "GGUF",
            "file_type": card.get("file_type_name"),
            "source_repo": None,
            "artifact_path_reported": card["path"],
            "sha256": card["sha256"],
            "file_size_bytes": card["filesize_bytes"],
            "parameter_metadata_candidates": [
                {
                    "source": rel(model_card_path),
                    "total_params_b": card.get("total_params_nominal") / 1e9 if card.get("total_params_nominal") is not None else None,
                    "active_params_b": card.get("active_params_nominal") / 1e9 if card.get("active_params_nominal") is not None else None,
                },
                {
                    "source": rel(hw_path),
                    "total_params_b": hw_card["models"][alias].get("total_params") / 1e9 if hw_card["models"][alias].get("total_params") is not None else None,
                    "active_params_b": hw_card["models"][alias].get("active_params") / 1e9 if hw_card["models"][alias].get("active_params") is not None else None,
                },
            ],
            "provenance": {
                "default": source(model_card_path, "/model"),
                "/canonical_name": {"kind": "registry", "source_path": rel(model_card_path), "source_pointer": "/model/name", "rule": "exact first-wave alias registry; no fuzzy merge"},
                "/format": {"kind": "inferred", "reason": "The reported artifact extension and GGUF file_type identify the container."},
                "/source_repo": unknown("Upstream model repository is not reported in the frozen bundle."),
            },
        })
        settings = summary["runtime_settings"]
        chat = summary["chat_template"]
        env_meta = summary.get("env_meta", {})
        template_candidates = [
            {"identifier": "runtime_props", "sha256": chat.get("sha256"), "length": chat.get("len"), "source": chat.get("source")},
        ]
        if env_meta.get("chat_template_sha256"):
            template_candidates.append({"identifier": "gguf_metadata", "sha256": env_meta["chat_template_sha256"], "length": env_meta.get("chat_template_len"), "source": env_meta.get("chat_template_source")})
        template_conflict = len({item["sha256"] for item in template_candidates}) > 1
        config = {
            "ctx": settings["ctx_size"], "batch": settings["batch_size"], "ubatch": settings["ubatch_size"],
            "split_mode": settings["split-mode"], "tensor_split": None,
            "kv_type": {"k": settings["cache_type_k"], "v": settings["cache_type_v"], "offload": settings["kv_offload"]},
            "flash_attention": settings["flash_attn"], "mtp": False, "speculative": False,
            "seed": {"request": settings["seed_in_request_body"], "server_default": settings["seed_server_default"], "effective": None, "note": settings["seed_note"]},
            "max_tokens": settings["max_tokens_by_section"], "cold_or_warm": "mixed_by_section",
            "n_gpu_layers": settings["n-gpu-layers"], "parallel": settings["parallel"], "jinja": settings["jinja"],
            "fit": settings["fit"], "temperature": settings["temperature"], "lane": summary["lane"],
            "thinking": settings["thinking"],
            "chat_template_candidates": template_candidates,
        }
        missing = ["effective_seed", "flash_attention_boolean", "tensor_split_values", "original_pp_tg_vram"]
        if template_conflict:
            missing.append("unambiguous_chat_template_hash")
        runs.append({
            "schema_version": SCHEMA_VERSION, "record_type": "run", "run_id": run_id,
            "submission_id": submission_id, "machine_id": machine_id, "model_id": model_id, "runtime_id": runtime_id,
            "config": config,
            "artifacts": {"model_sha256": summary["model_sha256"], "fixtures_sha256": summary["fixtures_sha256"], "grader_sha256": summary["grader_sha256"]},
            "formal_record_compliance": {"compliant": False, "missing_or_ambiguous_required_fields": missing},
            "provenance": {
                "default": source(summary_path),
                "/config/tensor_split": unknown("Lane says non-tensor, but explicit tensor-split values are absent."),
                "/config/seed/effective": unknown("Request omitted seed and server used random default; realized integer seed is not reported."),
                "/config/flash_attention": source(summary_path, "/runtime_settings/flash_attn"),
            },
        })

        raw_path = directory / "raw.jsonl"
        for ordinal, row in enumerate(read_jsonl(raw_path), start=1):
            section = row.get("section")
            if section in {"core", "sentinel", "api_smoke"}:
                reuse, reason = quality_reuse(alias, row, fixture_audit)
                failure_class = row.get("taxonomy")
                if reuse == "invalid":
                    failure_class = "FIXTURE_INVALID"
                elif reuse == "requires_rerun":
                    failure_class = "PROTOCOL"
                task_results.append({
                    "schema_version": SCHEMA_VERSION, "record_type": "task_result",
                    "task_result_id": f"{run_id}-task-{row['id']}", "run_id": run_id,
                    "task_id": row["id"], "section": section, "category": row["category"], "prompt_variant": row.get("mode"),
                    "model_output": row.get("raw_content"), "normalized_answer": row.get("answer"), "expected_answer": row.get("gold"),
                    "score": 1 if row.get("passed") else 0, "status": "pass" if row.get("passed") else "fail",
                    "format_ok": row.get("format_ok"), "non_empty": row.get("non_empty"), "http_status": row.get("http_status"),
                    "failure_class_reported": row.get("taxonomy"), "failure_class_audited": failure_class,
                    "grader": row.get("grader"), "grader_note": row.get("note"), "timings": row.get("timings"),
                    "reuse": {"classification": reuse, "reason": reason},
                    "source": {"path": rel(raw_path), "line": ordinal},
                    "provenance": {"default": source(raw_path, f"line:{ordinal}"), "/failure_class_audited": {"kind": "derived", "method": "deterministic semantic audit rules"}, "/reuse": {"kind": "derived", "method": "reuse classification policy v0.1"}},
                })
            elif section in {"pp", "tg", "depth", "cold_load"}:
                target = row.get("pp_tokens_target") if section == "pp" else row.get("tg_tokens_target")
                performance.append({
                    "schema_version": SCHEMA_VERSION, "record_type": "performance",
                    "measurement_id": f"{run_id}-original-{section}-{row.get('depth') if section == 'depth' else (target or 'load')}-r{row.get('rep', 1)}",
                    "run_id": run_id, "measurement_phase": "original_run", "metric": section,
                    "value": row.get("tokens_per_sec", row.get("predicted_per_second", row.get("cold_wall_ms"))),
                    "unit": "tokens/s" if section != "cold_load" else "ms",
                    "prompt_tokens": row.get("pp_tokens_actual"), "generated_tokens": row.get("tg_tokens_actual", row.get("completion_tokens")),
                    "target_tokens": target, "depth": row.get("depth"), "repeat": row.get("rep"),
                    "wall_ms": row.get("wall_ms", row.get("cold_wall_ms")), "timings_cache_n": (row.get("timings") or {}).get("cache_n", row.get("cache_n")),
                    "vram": None, "measurement_source": "raw_original_run",
                    "reuse": {"classification": "reusable_as_is", "reason": "Original raw measurement is preserved; missing VRAM limits formal comparability but does not alter the observation."},
                    "source": {"path": rel(raw_path), "line": ordinal},
                    "provenance": {"default": source(raw_path, f"line:{ordinal}"), "/vram": unknown("Original PP/TG run did not sample VRAM."), "/reuse": {"kind": "derived", "method": "reuse classification policy v0.1"}},
                })

        posthoc_path = directory / "pp_tg_vram.jsonl"
        for ordinal, row in enumerate(read_jsonl(posthoc_path), start=1):
            metric = row["kind"]
            performance.append({
                "schema_version": SCHEMA_VERSION, "record_type": "performance",
                "measurement_id": f"{run_id}-posthoc-{metric}-{row['target']}-r{row['rep']}",
                "run_id": run_id, "measurement_phase": "posthoc_vram_remeasurement", "metric": metric,
                "value": row.get("tps"), "unit": "tokens/s", "prompt_tokens": row.get("prompt_n"),
                "generated_tokens": row.get("tg_tokens_actual", 1 if metric == "pp" else row.get("target")),
                "target_tokens": row["target"], "depth": None, "repeat": row["rep"], "wall_ms": row.get("wall_ms"),
                "timings_cache_n": row.get("cache_n"),
                "vram": {"before": row.get("vram_before"), "during": row.get("vram_during"), "after": row.get("vram_after")},
                "measurement_source": "posthoc_remeasurement_not_original_run",
                "reuse": {"classification": "reusable_as_is", "reason": "Raw repeat is reusable only as a separately identified post-hoc remeasurement."},
                "source": {"path": rel(posthoc_path), "line": ordinal},
                "provenance": {"default": source(posthoc_path, f"line:{ordinal}"), "/reuse": {"kind": "derived", "method": "reuse classification policy v0.1"}},
            })

        sentinel = [item for item in task_results if item["run_id"] == run_id and item["section"] == "sentinel"]
        verdicts.append({
            "schema_version": SCHEMA_VERSION, "record_type": "verdict", "run_id": run_id,
            "policy_version": "YLSB-v0.3", "gates": summary["gates"],
            "hard_sentinel_observation": {"correct": sum(item["score"] for item in sentinel), "attempts": len(sentinel)},
            "source": rel(summary_path),
            "provenance": {"/gates": source(summary_path, "/gates"), "/hard_sentinel_observation": {"kind": "derived", "inputs": [item["task_result_id"] for item in sentinel]}},
        })

    # Attach recomputable sample statistics without replacing any raw repeat.
    perf_groups: dict[tuple[str, str, str, Any], list[dict[str, Any]]] = defaultdict(list)
    for item in performance:
        if item["metric"] in {"pp", "tg"}:
            perf_groups[(item["run_id"], item["measurement_phase"], item["metric"], item["target_tokens"])].append(item)
    for items in perf_groups.values():
        values = [item["value"] for item in items]
        stats = {
            "repeat_count": len(values),
            "mean": round(statistics.mean(values), 6),
            "stdev": round(statistics.stdev(values), 6) if len(values) > 1 else None,
            "stdev_kind": "sample" if len(values) > 1 else None,
        }
        for item in items:
            item["group_statistics"] = stats
            item["provenance"]["/group_statistics"] = {
                "kind": "derived", "inputs": [member["measurement_id"] for member in items],
                "formula": "arithmetic mean and sample standard deviation over raw repeat values",
            }

    # Deterministic calibration aggregates.
    by_category: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in task_results:
        by_category[(item["section"], item["category"])].append(item)
        by_task[item["task_id"]].append(item)
    category_rows = []
    for (section, category), items in sorted(by_category.items()):
        per_model = Counter(item["run_id"] for item in items if item["score"])
        models_attempted = len({item["run_id"] for item in items})
        category_rows.append({"section": section, "category": category, "attempts": len(items), "correct": sum(item["score"] for item in items), "accuracy": round(sum(item["score"] for item in items) / len(items), 6), "models_attempted": models_attempted, "models_zero_correct": models_attempted - len(per_model)})
    task_rows = []
    for task_id, items in sorted(by_task.items()):
        task_rows.append({"task_id": task_id, "section": items[0]["section"], "category": items[0]["category"], "attempts": len(items), "correct": sum(item["score"] for item in items), "success_rate": round(sum(item["score"] for item in items) / len(items), 6), "failure_modes_reported": dict(sorted(Counter(item["failure_class_reported"] for item in items if item["score"] == 0).items())), "audit_status": "fixture_invalid" if any(item["reuse"]["classification"] == "invalid" for item in items) else "observed"})

    # Required-record coverage is run-level and intentionally strict.
    coverage_checks = {
        "runtime_commit": lambda r: bool(runtime["commit"]),
        "gpu_model": lambda r: all(item["reported_name"] for item in hardware),
        "gpu_count": lambda r: machine["aggregate"]["gpu_count"] is not None,
        "vram": lambda r: all(item["vram_each_gb"] is not None for item in hardware),
        "ram": lambda r: machine["ram"]["total_gb"] is not None,
        "ctx": lambda r: r["config"]["ctx"] is not None,
        "kv_cache": lambda r: all(r["config"]["kv_type"].values()),
        "effective_seed": lambda r: r["config"]["seed"]["effective"] is not None,
        "max_tokens": lambda r: bool(r["config"]["max_tokens"]),
        "batch_ubatch": lambda r: r["config"]["batch"] is not None and r["config"]["ubatch"] is not None,
        "flash_attention_boolean": lambda r: isinstance(r["config"]["flash_attention"], bool),
        "environment_versions": lambda r: all([machine["os"].get("version_id"), machine["driver"], machine["cuda"].get("nvcc")]),
        "model_sha256": lambda r: bool(r["artifacts"]["model_sha256"]),
        "fixture_sha256": lambda r: bool(r["artifacts"]["fixtures_sha256"]),
        "grader_sha256": lambda r: bool(r["artifacts"]["grader_sha256"]),
        "unambiguous_chat_template_hash": lambda r: len({x["sha256"] for x in r["config"]["chat_template_candidates"]}) == 1,
        "original_pp_tg_vram": lambda r: any(p["run_id"] == r["run_id"] and p["measurement_phase"] == "original_run" and p["metric"] in {"pp", "tg"} and p["vram"] is not None for p in performance),
        "pp_tg_stdev": lambda r: all(p.get("group_statistics", {}).get("stdev_kind") == "sample" for p in performance if p["run_id"] == r["run_id"] and p["metric"] in {"pp", "tg"}),
        "repeat_raw_values": lambda r: all(any(p["run_id"] == r["run_id"] and p["measurement_phase"] == "original_run" and p["metric"] == metric for p in performance) for metric in ("pp", "tg")),
        "timings_cache_n": lambda r: all(p["timings_cache_n"] is not None for p in performance if p["run_id"] == r["run_id"] and p["metric"] in {"pp", "tg"}),
    }
    coverage = {name: {"covered_runs": sum(check(run) for run in runs), "total_runs": len(runs), "percent": round(100 * sum(check(run) for run in runs) / len(runs), 1)} for name, check in coverage_checks.items()}

    counts = {
        "submissions": len(submissions), "machines": 1, "gpu_configurations": 1, "cpu_configurations": 0,
        "hardware_records": len(hardware), "models": len(models), "dense_models": sum(m["architecture"]["type"] == "dense" for m in models),
        "moe_models": sum(m["architecture"]["type"] == "moe" for m in models), "runtimes": 1, "runs": len(runs),
        "quality_task_results": len(task_results), "core_results": sum(x["section"] == "core" for x in task_results),
        "sentinel_results": sum(x["section"] == "sentinel" for x in task_results), "api_smoke_results": sum(x["section"] == "api_smoke" for x in task_results),
        "performance_records": len(performance), "original_pp": sum(x["metric"] == "pp" and x["measurement_phase"] == "original_run" for x in performance),
        "original_tg": sum(x["metric"] == "tg" and x["measurement_phase"] == "original_run" for x in performance),
        "posthoc_pp_tg": sum(x["measurement_phase"] == "posthoc_vram_remeasurement" for x in performance),
        "depth": sum(x["metric"] == "depth" for x in performance), "cold_load": sum(x["metric"] == "cold_load" for x in performance),
    }
    reuse_counts = Counter(item["reuse"]["classification"] for item in task_results + performance)
    gpt_empty = [item for item in task_results if item["run_id"].endswith("gpt-oss-20b") and not item["non_empty"]]

    calibration_md = render_calibration(counts, category_rows, task_rows, fixture_audit, verdicts, gpt_empty)
    health_md = render_health(counts, coverage, reuse_counts)
    planner = {
        "schema_version": SCHEMA_VERSION,
        "usage": {
            "historical_comparison": {"allowed": True, "conditions": ["Keep original and post-hoc measurement phases separate.", "Apply fixture/protocol audit flags."]},
            "performance_corpus": {"allowed": True, "conditions": ["Use raw repeats; original-run VRAM is unavailable."]},
            "hardware_model_analysis": {"allowed": True, "conditions": ["Treat CPU fields and unreported hardware properties as unknown."]},
            "candidate_planner_retrieval": {"allowed": True, "conditions": ["Retrieve observations and provenance, not only verdicts."]},
            "candidate_planner_training_on_raw_measurements": {"allowed": True, "conditions": ["Exclude invalid fixtures and isolate requires_rerun records."]},
            "candidate_planner_training_on_v0_3_gate_labels": False,
        },
        "reason": "The first-wave data reveals fixture, protocol/template, and gate-calibration confounders. v0.3 labels are retained for history, not treated as ground truth.",
        "provenance": {"kind": "derived", "inputs": ["normalized/task_results.jsonl", "normalized/performance.jsonl", "derived/v0.3_verdicts.jsonl"]},
    }

    files = {
        str(FROZEN_ROOT / "manifest.json"): dump_json(build_manifest()),
        str(NORMALIZED / "submissions.jsonl"): dump_jsonl(submissions),
        str(NORMALIZED / "machines.jsonl"): dump_jsonl([machine]),
        str(NORMALIZED / "hardware.jsonl"): dump_jsonl(hardware),
        str(NORMALIZED / "models.jsonl"): dump_jsonl(models),
        str(NORMALIZED / "runtimes.jsonl"): dump_jsonl([runtime]),
        str(NORMALIZED / "runs.jsonl"): dump_jsonl(runs),
        str(NORMALIZED / "task_results.jsonl"): dump_jsonl(task_results),
        str(NORMALIZED / "performance.jsonl"): dump_jsonl(performance),
        str(DERIVED / "v0.3_verdicts.jsonl"): dump_jsonl(verdicts),
        str(DERIVED / "candidate_planner_usage.json"): dump_json(planner),
        str(DERIVED / "calibration_data.json"): dump_json({"schema_version": SCHEMA_VERSION, "categories": category_rows, "tasks": task_rows, "constraint_fixture_audit": fixture_audit}),
        str(DERIVED / "calibration_report.md"): calibration_md.encode(),
        str(DERIVED / "corpus_health.md"): health_md.encode(),
    }
    context = {"counts": counts, "coverage": coverage, "reuse_counts": dict(reuse_counts), "fixture_audit": fixture_audit}
    return files, context


def render_calibration(counts: dict[str, int], categories: list[dict[str, Any]], tasks: list[dict[str, Any]], audit: dict[str, Any], verdicts: list[dict[str, Any]], gpt_empty: list[dict[str, Any]]) -> str:
    model_rows = []
    for item in verdicts:
        alias = item["run_id"].removeprefix("run-v03-ume-")
        gates = item["gates"]
        model_rows.append(f"| {alias} | {gates['smallest_meaningful']['pass']} | {gates['fastest_useful']['pass']} | {item['hard_sentinel_observation']['correct']}/4 | {gates['ume_full_clear']['pass']} |")
    cat_rows = [f"| {x['section']} | {x['category']} | {x['attempts']} | {x['correct']} | {100*x['accuracy']:.1f}% | {x['models_attempted']} | {x['models_zero_correct']} |" for x in categories]
    task_table = [f"| {x['task_id']} | {x['category']} | {x['correct']}/{x['attempts']} | {100*x['success_rate']:.1f}% | {', '.join(f'{k}:{v}' for k,v in x['failure_modes_reported'].items()) or '-'} | {x['audit_status']} |" for x in tasks]
    invalid = audit["CORE-CONSTRAINT-003"]
    return f"""# YLSB v0.3 UME 第一陣 calibration report

本書はv0.4仕様の決定ではなく、凍結したv0.3観測値から得た校正材料である。観測値、監査結果、v0.3 policy verdictを分離している。

## 1. 第一陣の概要

- 6 submissions / 6 models / 1 machine / 1 runtime
- quality {counts['quality_task_results']}件（Core {counts['core_results']}、Hard Sentinel {counts['sentinel_results']}、API smoke {counts['api_smoke_results']}）
- original PP/TG {counts['original_pp'] + counts['original_tg']}件、depth {counts['depth']}件、cold load {counts['cold_load']}件
- VRAM付きpost-hoc PP/TG {counts['posthoc_pp_tg']}件。original runとは別phaseであり、代替値として結合しない。

## 2. モデル別v0.3結果

| model | Smallest Meaningful | Fastest Useful | Hard Sentinel | UME Full Clear |
|---|---:|---:|---:|---:|
{chr(10).join(model_rows)}

## 3. カテゴリ別difficulty

| section | category | attempts | correct | accuracy | models attempted | models zero correct |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(cat_rows)}

## 4. task別difficulty

| task | category | correct | success rate | reported failure modes | audit |
|---|---|---:|---:|---|---|
{chr(10).join(task_table)}

## 5. constraint監査

4問をA–Eの全120順列で独立に列挙した。001、002、004はreported goldが一意解と一致した。一方、`CORE-CONSTRAINT-003` の一意解は `{invalid['enumerated_solutions'][0]}` で、fixtureのgold `{invalid['reported_gold']}` と一致しない。このtaskは `invalid / FIXTURE_INVALID` とし、0/6をモデル能力の根拠に使わない。残る3問も0/6だが、rawは非空でgraderは単純exact、列挙上fixtureは妥当である。難度過剰の有力な校正信号だが、第一陣だけから「問題が悪い」とは確定しない。

## 6. Hard Sentinel監査

v0.3採点ではGPT-OSSのみ3/4、他モデルは0/4。GPT-OSSのH03出力 `10:A->C->B->D->E` はreported gold `10:A-C-B-D-E` と意味内容が一致するように見えるが、exact表記差でFAILになっている。rawを再採点可能として保持し、Sentinelは通常合否よりdiscriminator/badgeとして分離する仮説を支持する。0/4 ordinary等の段階名は本データでは決定せず、案としてのみ扱う。

## 7. runtime / protocol問題

GPT-OSSはHTTP/INFRA失敗なしで、Core 6件とAPI smoke 10件が空回答だった（計{len(gpt_empty)}件）。同runでCore 22/28とSentinel 3/4を得ているため、単純な能力低下だけでは説明しにくい。GPT-OSSではruntime `/props` とGGUF metadata由来のchat-template hash候補も競合する。空回答は `PROTOCOL / requires_rerun` とし、template・endpoint・出力抽出の対照runが必要である。

## 8. v0.3 gateの問題点

- Core 80%のFastest Usefulは6モデルすべてFAILで、速度による候補選別に到達しない。第一陣は閾値が目的に対して強すぎる仮説Aを支持するが、母集団6件なので確定はしない。
- constraintは1問がfixture invalid、残る3問も0/6で、Core総率を大きく押し下げる。Essential / Practical / Hardへのtier分離という仮説Bを検討する根拠になる。
- Sentinelは通常のCore能力と異なる識別力を持ち、仮説Cのbadge分離に整合する。
- GPT-OSSの空回答群はModel Quality / Runtime Compatibility / Serving Correctness / Performanceを分ける仮説Dを強く支持する。

## 9. v0.4で変更を検討すべき点

1. Fastest Usefulを固定80%だけで閉じず、妥当性確認済みusefulness floorを満たす構成内のTG比較とする。
2. Core taskへdifficulty tierを付け、invalid fixtureをgateから除外する。
3. Hard SentinelはCore合否から独立した観測/badgeにする。
4. protocol/template/serving検査を能力採点の前段に置き、空回答をCAPABILITYへ直結させない。

## 10. 再ベンチが必要な項目

- GPT-OSSの空回答16件はtemplate/source、endpoint、出力抽出を固定して再実行する。
- 全runのeffective seed、Flash Attentionの実効on/off、明示tensor split、original-run PP/TG VRAMが欠けるため、現行必須記録契約に準拠する正式比較には再実行が必要。
- chat-template hash候補の不一致は、実際に適用されたtemplate bytesを保存して解消する。

## 11. 再採点のみで利用可能な項目

- 非空のquality raw outputは新policy/graderで再採点可能。
- `CORE-CONSTRAINT-003` はfixture修正後に再採点できるが、v0.3得点は上書きしない。
- H03を含む表記正規化はsemantic audit付きで再採点可能。
- PP/TG/depthのraw測定は再利用可能。post-hoc VRAMは別phaseとしてのみ利用する。
"""


def render_health(counts: dict[str, int], coverage: dict[str, Any], reuse: Counter[str]) -> str:
    rows = [f"| {name} | {item['covered_runs']}/{item['total_runs']} | {item['percent']:.1f}% |" for name, item in coverage.items()]
    return f"""# YLSB normalized corpus v0.1 — corpus health

## Corpus inventory

- Submissions: {counts['submissions']}
- Machines: {counts['machines']}
- GPU configurations: {counts['gpu_configurations']}（heterogeneous RTX 3060 + Tesla P100）
- CPU configurations: {counts['cpu_configurations']}（CPU情報は未報告）
- Models: {counts['models']}（Dense {counts['dense_models']} / MoE {counts['moe_models']}）
- Runtime families: {counts['runtimes']}（llama.cpp）
- Runs: {counts['runs']}
- Quality records: {counts['quality_task_results']}
- Performance records: {counts['performance_records']}

## Mandatory field coverage

Coverageは6 runを分母とする。`unknown`や曖昧な値を充足扱いにしていない。

| field | covered runs | coverage |
|---|---:|---:|
{chr(10).join(rows)}

## Reuse classification

- reusable_as_is: {reuse.get('reusable_as_is', 0)}
- regradable: {reuse.get('regradable', 0)}
- requires_rerun: {reuse.get('requires_rerun', 0)}
- invalid: {reuse.get('invalid', 0)}

`CORE-CONSTRAINT-003`に該当する6件はfixture invalidを優先した。GPT-OSSの同taskも空回答だが、二重計上せずinvalidに含めたため、GPT-OSS空回答16件のうちrequires_rerunは15件である。

## Known issues

- `CORE-CONSTRAINT-003` のreported goldが全順列監査の一意解と不一致。
- GPT-OSSにHTTP成功下の空回答が16件あり、runtime/template/protocol要因が未分離。
- original PP/TGにはVRAMサンプルがなく、90件のVRAM測定は別のpost-hoc run。
- effective seedは未記録。server default `-1` は乱数指定であり、実際の整数seedではない。
- Flash Attentionは`auto`で実効on/offが不明。
- GPT-OSSでは`/props`とGGUF metadataのchat-template hash候補が一致せず、実適用templateを一意に確定できない。
- GemmaとGPT-OSSには2つのmodel-card間でtotal/active parameter値の差がある。両候補と出典を保持し、無言で統合しない。
- CPU、ROCm、GPU compute capability等は未報告のためnull/unknownのまま保持。

このため6 runすべて、現行の18項目必須記録契約を満たす正式な比較可能結果ではない。観測値は削除せず、用途ごとの制約を付けて再利用する。
"""


def validate_records(files: dict[str, bytes]) -> None:
    schema = read_json(ROOT / "results/v0.3/schema/normalized-corpus-v0.1.schema.json")

    def schema_check(value: Any, rule: dict[str, Any], location: str = "record") -> None:
        if "$ref" in rule:
            prefix = "#/$defs/"
            if not rule["$ref"].startswith(prefix):
                raise ValueError(f"unsupported schema reference: {rule['$ref']}")
            schema_check(value, schema["$defs"][rule["$ref"][len(prefix):]], location)
            return
        if "oneOf" in rule:
            matches = 0
            for candidate in rule["oneOf"]:
                try:
                    schema_check(value, candidate, location)
                    matches += 1
                except (TypeError, ValueError):
                    pass
            if matches != 1:
                raise ValueError(f"{location}: expected exactly one schema match, got {matches}")
        for candidate in rule.get("allOf", []):
            schema_check(value, candidate, location)
        if "const" in rule and value != rule["const"]:
            raise ValueError(f"{location}: expected constant {rule['const']!r}")
        if "enum" in rule and value not in rule["enum"]:
            raise ValueError(f"{location}: {value!r} is not in enum")
        expected_type = rule.get("type")
        type_map = {"object": dict, "array": list, "string": str, "number": (int, float), "integer": int, "boolean": bool, "null": type(None)}
        if expected_type and not isinstance(value, type_map[expected_type]):
            raise TypeError(f"{location}: expected {expected_type}, got {type(value).__name__}")
        if isinstance(value, dict):
            for name in rule.get("required", []):
                if name not in value:
                    raise ValueError(f"{location}: missing required property {name}")
            properties = rule.get("properties", {})
            for name, child in properties.items():
                if name in value:
                    schema_check(value[name], child, f"{location}/{name}")
            extra_rule = rule.get("additionalProperties")
            if isinstance(extra_rule, dict):
                for name in set(value) - set(properties):
                    schema_check(value[name], extra_rule, f"{location}/{name}")
        if isinstance(value, str):
            if "minLength" in rule and len(value) < rule["minLength"]:
                raise ValueError(f"{location}: string is too short")
            if "pattern" in rule and re.search(rule["pattern"], value) is None:
                raise ValueError(f"{location}: string does not match {rule['pattern']}")

    ids: dict[str, set[str]] = defaultdict(set)
    parsed: dict[str, list[dict[str, Any]]] = {}
    for path, payload in files.items():
        if not path.endswith(".jsonl"):
            continue
        rows = [json.loads(line) for line in payload.decode().splitlines()]
        parsed[Path(path).name] = rows
        primary_key = {
            "submission": "submission_id", "machine": "machine_id", "hardware": "hardware_id",
            "model": "model_id", "runtime": "runtime_id", "run": "run_id",
            "task_result": "task_result_id", "performance": "measurement_id",
        }
        for row in rows:
            schema_check(row, schema, f"{Path(path).name}")
            if row.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(f"bad schema version in {path}")
            for prov in row.get("provenance", {}).values():
                if prov.get("kind") not in PROVENANCE_KINDS:
                    raise ValueError(f"bad provenance kind in {path}: {prov}")
            key = primary_key.get(row["record_type"])
            if key:
                if row[key] in ids[key]:
                    raise ValueError(f"duplicate {key}: {row[key]}")
                ids[key].add(row[key])
            reuse = row.get("reuse", {}).get("classification")
            if reuse is not None and reuse not in REUSE_CLASSES:
                raise ValueError(f"bad reuse class: {reuse}")
    for run in parsed["runs.jsonl"]:
        if run["submission_id"] not in ids["submission_id"] or run["machine_id"] not in ids["machine_id"] or run["model_id"] not in ids["model_id"] or run["runtime_id"] not in ids["runtime_id"]:
            raise ValueError(f"broken run reference: {run['run_id']}")
    # Verdicts must remain byte-for-value equivalent to source summary gates.
    for verdict in parsed["v0.3_verdicts.jsonl"]:
        alias = verdict["run_id"].removeprefix("run-v03-ume-")
        if verdict["gates"] != read_json(REPORTS / alias / "summary.json")["gates"]:
            raise ValueError(f"v0.3 verdict drift: {alias}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if checked-in generated output differs")
    args = parser.parse_args()
    before = {path.relative_to(RAW_ROOT).as_posix(): sha256(path) for path in RAW_ROOT.rglob("*") if path.is_file()}
    files, context = build()
    validate_records(files)
    if args.check:
        changed = [path for path, payload in files.items() if not Path(path).exists() or Path(path).read_bytes() != payload]
        if changed:
            raise SystemExit("generated output differs:\n" + "\n".join(changed))
    else:
        for path, payload in files.items():
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    after = {path.relative_to(RAW_ROOT).as_posix(): sha256(path) for path in RAW_ROOT.rglob("*") if path.is_file()}
    if before != after:
        raise SystemExit("frozen raw tree changed during generation")
    print(json.dumps(context, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
