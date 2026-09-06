"""Deterministic candidate planning for YLSB v0.4.

The planner produces *predictions*.  It never turns a prediction into an S/F/L/D/X
verdict and it deliberately does not read policy verdicts from the corpus.
"""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


_GB = 1024**3
_SUCCESS = {"success", "easy", "barely", "practical", "fit", "pass", "ok", "usable"}
_FAILURE = {"oom", "fail", "failure", "error", "not_practical", "unsupported", "timeout"}


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _gpu_groups(hardware: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    hardware = hardware or {}
    groups = hardware.get("gpu_groups")
    if groups is None:
        groups = hardware.get("gpus")
    if groups is None and hardware.get("gpu"):
        groups = [hardware["gpu"]]
    result: list[dict[str, Any]] = []
    for raw in groups or []:
        if not isinstance(raw, Mapping):
            continue
        item = dict(raw)
        item["count"] = max(1, int(_as_number(item.get("count")) or 1))
        result.append(item)
    return result


def _gpu_total(hardware: Mapping[str, Any] | None) -> tuple[float, list[str]]:
    """Return reported GPU memory and architecture names without inventing values."""
    total = 0.0
    architectures: list[str] = []
    for item in _gpu_groups(hardware):
        vram = item.get("vram_gib_each", item.get("vram_each_gb", item.get("vram_gib")))
        number = _as_number(vram)
        if number is not None:
            total += number * int(item["count"])
        if item.get("architecture") is not None:
            architectures.extend([str(item["architecture"])] * int(item["count"]))
    # A normalized machine may carry an aggregate, but it is only a fallback for
    # reporting.  Fit decisions below still use per-device capacities.
    if not total:
        aggregate = (hardware or {}).get("aggregate", {})
        total = _as_number(aggregate.get("total_vram_gib", aggregate.get("total_vram_gb"))) or 0.0
    return total, architectures


def _driver_version(hardware: Mapping[str, Any]) -> tuple[int, ...] | None:
    raw = hardware.get("driver_version", hardware.get("driver"))
    if raw is None:
        return None
    numbers = []
    for part in str(raw).replace("-", ".").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            numbers.append(int(digits))
    return tuple(numbers) if numbers else None


def _cc(item: Mapping[str, Any]) -> float | None:
    for key in ("compute_capability", "compute_capability_major_minor", "cc"):
        value = item.get(key)
        if value is not None:
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                return float(value[0]) + float(value[1]) / 10
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _model_info(model: Mapping[str, Any]) -> dict[str, Any]:
    arch = model.get("architecture") if isinstance(model.get("architecture"), Mapping) else {}
    total = _as_number(arch.get("total_params_b", model.get("total_params_b")))
    active = _as_number(arch.get("active_params_b", model.get("active_params_b")))
    model_type = str(arch.get("type", model.get("architecture_type", "unknown"))).lower()
    bpw = _as_number(model.get("bpw"))
    if bpw is None:
        quant = str(model.get("quant", "")).upper()
        if "MXFP4" in quant:
            bpw = 4.0
        elif "Q8" in quant:
            bpw = 8.0
        elif "Q6" in quant:
            bpw = 6.5
        elif "Q5" in quant:
            bpw = 5.5
        elif "Q4" in quant:
            bpw = 4.5
    artifact_bytes = None
    for key in ("artifact_bytes", "file_size_bytes", "size_bytes"):
        artifact_bytes = _as_number(model.get(key))
        if artifact_bytes is not None:
            break
    if artifact_bytes is None and isinstance(model.get("artifacts"), Mapping):
        for key in ("file_size_bytes", "artifact_bytes", "bytes"):
            artifact_bytes = _as_number(model["artifacts"].get(key))
            if artifact_bytes is not None:
                break
    return {
        "total_params_b": total,
        "active_params_b": active,
        "bpw": bpw,
        "type": model_type,
        "artifact_bytes": artifact_bytes,
        "format": model.get("format"),
    }


def _model_params(model: Mapping[str, Any]) -> tuple[float | None, float | None, str]:
    """Backward-compatible compact model metadata helper."""
    info = _model_info(model)
    return info["total_params_b"], info["bpw"], info["type"]


def _ram_gib(hardware: Mapping[str, Any]) -> float:
    ram = hardware.get("ram") if isinstance(hardware.get("ram"), Mapping) else {}
    return _as_number(ram.get("total_gib", ram.get("total_gb"))) or 0.0


def estimate_model_fit(
    hardware: dict[str, Any],
    model: dict[str, Any],
    *,
    context_tokens: int = 8192,
    cpu_offload: bool = False,
) -> dict[str, Any]:
    """Estimate memory/compute pressure and expose placement conditions.

    A multi-GPU aggregate is never treated as a sufficient placement proof.  The
    ``fits`` result is true only when a per-device or explicit layer-split layout
    has enough capacity; CPU offload is a separate opt-in condition.
    """
    groups = _gpu_groups(hardware)
    total_vram, architectures = _gpu_total(hardware)
    capacities: list[float] = []
    for item in groups:
        value = _as_number(item.get("vram_gib_each", item.get("vram_each_gb", item.get("vram_gib"))))
        if value is not None:
            capacities.extend([value] * int(item["count"]))
    info = _model_info(model)
    if info["artifact_bytes"] is not None:
        weight = info["artifact_bytes"] / _GB
        weight_source = "known_artifact_bytes"
    elif info["total_params_b"] is not None and info["bpw"] is not None:
        weight = info["total_params_b"] * 1_000_000_000 * info["bpw"] / 8 / _GB * 1.08
        weight_source = "parameter_and_bpw_estimate"
    else:
        weight = None
        weight_source = "unknown"

    if weight is None or not capacities:
        return {
            "fits": None,
            "status": "unknown",
            "weight_gib": round(weight, 3) if weight is not None else None,
            "weight_source": weight_source,
            "available_vram_gib": round(total_vram, 3),
            "per_device_vram_gib": capacities,
            "allocation": {"per_device": None, "layer_split": None, "cpu_offload": False},
            "conditions": ["reported per-device VRAM and model footprint are required"],
            "confidence": "low",
            "memory_pressure": "unknown",
            "compute_pressure": "unknown" if info["active_params_b"] is None else "active_params_unknown_runtime",
            "memory_params_b": info["total_params_b"],
            "compute_active_params_b": info["active_params_b"],
            "model_architecture": info["type"],
            "hardware_architectures": architectures,
            "reason": "insufficient reported facts; no values were inferred",
        }

    # Known artifact bytes are the weight footprint. KV/workspace/safety are
    # explicit estimates and must be validated by an observed benchmark.
    kv = max(0.25, context_tokens / 8192 * (0.45 if info["type"] == "moe" else 0.65))
    workspace = max(0.5, weight * 0.08)
    safety = max(1.0, (weight + kv + workspace) * 0.15)
    required = weight + kv + workspace + safety
    min_capacity = min(capacities)
    max_capacity = max(capacities)
    aggregate_fit = required <= total_vram
    per_device_fit = required <= max_capacity if len(capacities) == 1 else False
    # Layer split needs enough aggregate memory and enough room on the smallest
    # participating device for a conservative balanced allocation.
    per_device_layer = required / len(capacities)
    layer_split_fit = len(capacities) > 1 and per_device_layer <= min_capacity and aggregate_fit
    ram = _ram_gib(hardware)
    deficit = max(0.0, required - total_vram)
    offload_fit = bool(cpu_offload and ram > 0 and deficit <= ram * 0.75)
    if per_device_fit or layer_split_fit or offload_fit:
        fits: bool | None = True
        status = "estimated"
    elif aggregate_fit:
        fits = False
        status = "aggregate_only"
    else:
        fits = False
        status = "estimated"
    pressure = "high" if required > max_capacity * 0.9 else "moderate" if required > max_capacity * 0.7 else "low"
    active = info["active_params_b"]
    compute_pressure = "unknown" if active is None else ("high" if active > 20 else "moderate" if active > 7 else "low")
    conditions = [
        "fit is a deterministic memory estimate, not an observed run",
        "per-device capacity and layer-split feasibility are reported separately",
    ]
    if offload_fit:
        conditions.append("CPU offload is enabled by the caller and depends on reported host RAM")
    elif not cpu_offload:
        conditions.append("CPU offload was not enabled")
    return {
        "fits": fits,
        "status": status,
        "weight_gib": round(weight, 3),
        "weight_source": weight_source,
        "kv_cache_gib": round(kv, 3),
        "runtime_workspace_gib": round(workspace, 3),
        "safety_margin_gib": round(safety, 3),
        "required_gib": round(required, 3),
        "available_vram_gib": round(total_vram, 3),
        "per_device_vram_gib": [round(x, 3) for x in capacities],
        "aggregate_fit": aggregate_fit,
        "per_device_fit": per_device_fit,
        "layer_split_fit": layer_split_fit,
        "allocation": {
            "per_device": per_device_fit,
            "layer_split": layer_split_fit,
            "cpu_offload": offload_fit,
            "layer_split_required_each_gib": round(per_device_layer, 3),
        },
        "cpu_offload": bool(cpu_offload),
        "cpu_offload_capacity_gib": round(ram * 0.75, 3) if ram else None,
        "deficit_gib": round(deficit, 3),
        "memory_pressure": pressure,
        "compute_pressure": compute_pressure,
        "memory_params_b": info["total_params_b"],
        "compute_active_params_b": active,
        "model_architecture": info["type"],
        "hardware_architectures": architectures,
        "confidence": "medium" if weight_source == "known_artifact_bytes" else "low",
        "conditions": conditions,
        "reason": "heuristic estimate; observed benchmark required for an S/F/L/D/X decision",
    }


def _format_known(model: Mapping[str, Any]) -> str | None:
    value = model.get("format")
    return str(value).lower() if value is not None else None


def _version_at_least(actual: tuple[int, ...] | None, required: Any) -> bool | None:
    if actual is None:
        return None
    required_parts = tuple(int(x) for x in re.findall(r"\d+", str(required)))
    return actual >= required_parts


def _runtime_candidates(
    model: Mapping[str, Any],
    hardware: Mapping[str, Any] | Sequence[str] | None,
    runtimes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    # Accept the old private-call shape (architecture list) for downstream users.
    if isinstance(hardware, Sequence) and not isinstance(hardware, (str, bytes, Mapping)):
        architectures = [str(x) for x in hardware]
        hardware_map: Mapping[str, Any] = {"gpu_groups": [{"architecture": x} for x in architectures]}
    else:
        hardware_map = hardware if isinstance(hardware, Mapping) else {}
        architectures = [str(x.get("architecture")) for x in _gpu_groups(hardware_map) if x.get("architecture") is not None]
    groups = _gpu_groups(hardware_map)
    fmt = _format_known(model)
    driver = _driver_version(hardware_map)
    result: list[dict[str, Any]] = []
    for runtime_raw in runtimes:
        runtime = dict(runtime_raw)
        rid = runtime.get("canonical_id", runtime.get("name"))
        name = str(runtime.get("name", rid or "runtime"))
        hard_reasons: list[str] = []
        unknown_reasons: list[str] = []
        evidence: list[dict[str, Any]] = []
        supported_formats = {str(x).lower() for x in runtime.get("supported_formats", [])}
        experimental_formats = {str(x).lower() for x in runtime.get("experimental_formats", [])}
        supported_arch = {str(x).lower() for x in runtime.get("architectures", [])}
        unknown_gpu = not groups or any(not item.get("architecture") or _cc(item) is None and runtime.get("min_compute_capability") is not None for item in groups)
        if unknown_gpu:
            unknown_reasons.append("GPU identity/compute capability is unknown; compatibility is not established")
        unsupported_arch = [a for a in architectures if supported_arch and a.lower() not in supported_arch]
        if unsupported_arch:
            hard_reasons.append("unsupported GPU architecture: " + ", ".join(sorted(set(unsupported_arch))))
        if fmt is None:
            unknown_reasons.append("model format is unknown")
        elif supported_formats and fmt not in supported_formats and fmt not in experimental_formats:
            hard_reasons.append(f"model format {fmt} is not declared by the runtime")
        min_cc = runtime.get("min_compute_capability")
        if min_cc is not None:
            for item in groups:
                cc = _cc(item)
                if cc is None:
                    continue
                if cc < float(min_cc):
                    hard_reasons.append(f"compute capability {cc:g} is below required {float(min_cc):g}")
                evidence.append({"gpu": item.get("reported_name", item.get("canonical_id")), "compute_capability": cc, "minimum": min_cc})
        min_driver = runtime.get("min_driver_version")
        driver_ok = _version_at_least(driver, min_driver) if min_driver is not None else True
        if driver_ok is False:
            hard_reasons.append(f"driver {'.'.join(map(str, driver or ())) } is below required {min_driver}")
        elif driver_ok is None:
            unknown_reasons.append(f"driver version is unknown; {min_driver} is required")
        for rule in runtime.get("compute_capability_driver_rules", []):
            max_cc = _as_number(rule.get("max_compute_capability"))
            required_driver = rule.get("min_driver_version")
            for item in groups:
                cc = _cc(item)
                if max_cc is not None and cc is not None and cc <= max_cc:
                    ok = _version_at_least(driver, required_driver)
                    if ok is not True:
                        if ok is False:
                            hard_reasons.append(f"CC {cc:g} requires driver {required_driver} under the runtime specification")
                        else:
                            unknown_reasons.append(f"driver version is unknown for CC {cc:g}; {required_driver} is required")
                    evidence.append({"compute_capability": cc, "driver_rule": rule})
        provenance = {
            "source": runtime.get("source"),
            "retrieved_at": runtime.get("retrieved_at"),
            "version_scope": runtime.get("version_scope"),
            "spec_version": runtime.get("spec_version"),
        }
        if hard_reasons:
            compatibility = "reject"
            expected_gain = None
            priority = "none"
            cost = "skip"
            reason = "; ".join(dict.fromkeys(hard_reasons + unknown_reasons))
            validation_status = "rejected"
            confidence = "high"
        elif unknown_reasons:
            # Unknown facts are a measured-validation need, not a known
            # incompatibility. Keep the item visible as an experimental option.
            compatibility = "unknown"
            expected_gain = runtime.get("expected_gain", "unknown")
            priority = "experimental"
            cost = "measure"
            reason = "; ".join(dict.fromkeys(unknown_reasons))
            validation_status = "needs_validation"
            confidence = "low"
        elif fmt in experimental_formats or not supported_arch:
            compatibility = "experimental"
            expected_gain = runtime.get("expected_gain", "unknown")
            priority = "experimental"
            cost = "measure"
            reason = "declared only as experimental; execution must establish compatibility"
            validation_status = "needs_validation"
            confidence = "low"
        else:
            compatibility = "candidate"
            expected_gain = runtime.get("expected_gain", "unknown")
            priority = "baseline" if "llama" in name.lower() else "optional"
            cost = "measure"
            reason = "declared compatible; execution is still required"
            validation_status = "declared_compatible"
            confidence = "low"
        result.append({
            "runtime": rid,
            "name": name,
            "reason": reason,
            "compatibility": compatibility,
            "expected_gain": expected_gain,
            "confidence": confidence,
            "benchmark_cost": cost,
            "priority": priority,
            "validation_status": validation_status,
            "provenance": provenance,
            "compatibility_evidence": evidence,
        })
    return result


class NormalizedCorpusAdapter:
    """Join normalized v0.1/v0.2 records into observation rows.

    Verdict records are intentionally ignored.  The adapter accepts a directory,
    JSONL files, an iterable of records, or already joined observation rows.
    """

    def __init__(self, source: Any):
        self.records = list(_iter_records(source))

    def observations(self) -> list[dict[str, Any]]:
        records = self.records
        joined = []
        raw_records = []
        for row in records:
            if _is_joined_observation(row):
                value = copy.deepcopy(row)
                # A caller may attach a verdict for convenience. Drop that
                # annotation rather than dropping the observed measurement.
                for key in ("gates", "policy_version", "verdict", "original_v0_3_verdict"):
                    value.pop(key, None)
                joined.append(value)
            else:
                raw_records.append(row)
        if joined and not raw_records:
            return joined
        records = raw_records
        by_type: dict[str, list[dict[str, Any]]] = {}
        for row in records:
            if not isinstance(row, Mapping):
                continue
            kind = str(row.get("record_type", "")).lower()
            if kind == "verdict":
                continue
            value = dict(row)
            for key in ("gates", "policy_version", "verdict", "original_v0_3_verdict"):
                value.pop(key, None)
            by_type.setdefault(kind, []).append(value)
        models = {str(r.get("model_id", r.get("canonical_id"))): r for r in by_type.get("model", [])}
        machines = {str(r.get("machine_id", r.get("canonical_id"))): r for r in by_type.get("machine", [])}
        runtimes = {str(r.get("runtime_id", r.get("canonical_id"))): r for r in by_type.get("runtime", [])}
        hardware_by_id = {str(r.get("hardware_id", r.get("canonical_id"))): r for r in by_type.get("hardware", [])}
        performance: dict[str, list[dict[str, Any]]] = {}
        for row in by_type.get("performance", []):
            performance.setdefault(str(row.get("run_id")), []).append(row)
        rows: list[dict[str, Any]] = []
        for run in by_type.get("run", []):
            machine = machines.get(str(run.get("machine_id")), {})
            gpu_ids = machine.get("gpu_ids", []) if isinstance(machine, Mapping) else []
            gpu_groups = [hardware_by_id[key] for key in gpu_ids if key in hardware_by_id]
            hardware = {"gpu_groups": gpu_groups, "driver": machine.get("driver"), "ram": machine.get("ram", {})}
            if machine.get("aggregate"):
                hardware["aggregate"] = machine["aggregate"]
            run_id = str(run.get("run_id"))
            perf_rows = performance.get(run_id) or [None]
            for perf in perf_rows:
                rows.append({
                    "record_type": "observation",
                    "schema_version": "normalized-corpus-v0.2",
                    "run_id": run.get("run_id"),
                    "hardware_id": run.get("machine_id"),
                    "runtime_id": run.get("runtime_id"),
                    "model_id": run.get("model_id"),
                    "hardware": hardware,
                    "machine": machine,
                    "model": models.get(str(run.get("model_id")), {}),
                    "runtime": runtimes.get(str(run.get("runtime_id")), {}),
                    "performance": perf or {},
                    "provenance": _merge_provenance(run, machine, models.get(str(run.get("model_id")), {}), runtimes.get(str(run.get("runtime_id")), {}), perf or {}),
                })
        return joined + rows

    def join(self) -> list[dict[str, Any]]:
        return self.observations()

    @classmethod
    def from_normalized(cls, source: Any) -> "NormalizedCorpusAdapter":
        return cls(source)


def _merge_provenance(*rows: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    namespaces = ("run", "machine", "model", "runtime", "performance")
    for namespace, row in zip(namespaces, rows):
        provenance = row.get("provenance")
        if isinstance(provenance, Mapping):
            output[namespace] = copy.deepcopy(dict(provenance))
    return output


def _is_joined_observation(row: Mapping[str, Any]) -> bool:
    """Identify one joined row without letting one embedded row change the mode."""
    if row.get("record_type") in {"hardware", "machine", "model", "runtime", "run", "performance", "verdict"}:
        return False
    return isinstance(row.get("hardware"), Mapping) and isinstance(row.get("model"), Mapping) and "run_id" in row


def _iter_records(source: Any) -> Iterator[dict[str, Any]]:
    if source is None:
        return
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_dir():
            for item in sorted(path.glob("*.jsonl")):
                yield from _iter_records(item)
        elif path.is_file():
            for line in path.read_text().splitlines():
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, Mapping):
                        yield dict(value)
        return
    if isinstance(source, Mapping):
        if "record_type" in source:
            yield dict(source)
        else:
            for values in source.values():
                if isinstance(values, Mapping):
                    yield dict(values)
                elif isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
                    for row in values:
                        if isinstance(row, Mapping):
                            yield dict(row)
        return
    for item in source:
        if isinstance(item, (str, Path)):
            yield from _iter_records(item)
        elif isinstance(item, Mapping):
            yield dict(item)


def load_normalized_corpus(source: Any) -> list[dict[str, Any]]:
    """Public input adapter API returning joined observation rows."""
    # JSONL loading is intentionally local and deterministic; imports are not
    # allowed to mutate the frozen corpus.
    if isinstance(source, (str, Path)) and Path(source).is_file():
        rows = []
        for line in Path(source).read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return NormalizedCorpusAdapter(rows).observations()
    return NormalizedCorpusAdapter(source).observations()


def adapt_normalized_corpus(source: Any) -> list[dict[str, Any]]:
    return load_normalized_corpus(source)


def _feature(row: Mapping[str, Any]) -> dict[str, Any]:
    hardware = row.get("hardware") if isinstance(row.get("hardware"), Mapping) else {}
    model = row.get("model") if isinstance(row.get("model"), Mapping) else {}
    runtime = row.get("runtime") if isinstance(row.get("runtime"), Mapping) else {}
    model_info = _model_info(model)
    vram, architectures = _gpu_total(hardware)
    return {
        "vram_gib": vram,
        "gpu_count": sum(int(x["count"]) for x in _gpu_groups(hardware)),
        "architectures": tuple(sorted(architectures)),
        "params_b": model_info["total_params_b"],
        "active_params_b": model_info["active_params_b"],
        "model_type": model_info["type"],
        "format": model_info["format"],
        "runtime": str(runtime.get("canonical_id", runtime.get("runtime_id", runtime.get("name", "")))).lower(),
    }


def _distance(actual: Mapping[str, Any], target: Mapping[str, Any]) -> tuple[float, list[str]]:
    distance = 0.0
    basis: list[str] = []
    for key, scale, weight in (("vram_gib", 16.0, 2.0), ("params_b", 35.0, 2.0), ("active_params_b", 10.0, 0.5)):
        a, b = _as_number(actual.get(key)), _as_number(target.get(key))
        if a is not None and b is not None:
            distance += weight * abs(a - b) / max(scale, abs(b), 1.0)
            basis.append(key)
    if actual.get("gpu_count") and target.get("gpu_count"):
        distance += 0.5 * abs(int(actual["gpu_count"]) - int(target["gpu_count"]))
        basis.append("gpu_count")
    if actual.get("architectures") and target.get("architectures"):
        if set(actual["architectures"]) != set(target["architectures"]):
            distance += 1.0
        basis.append("architectures")
    for key in ("model_type", "format", "runtime"):
        if actual.get(key) and target.get(key):
            if actual[key] != target[key]:
                distance += 0.75
            basis.append(key)
    return distance, basis


def _retrieval(
    corpus: Any,
    target_hardware: dict[str, Any] | None = None,
    target_model: dict[str, Any] | None = None,
    target_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = load_normalized_corpus(corpus) if corpus is not None else []
    if not rows:
        return {"used": False, "records": 0, "labels_used": False, "reason": "no observation corpus supplied"}
    target = _feature({"hardware": target_hardware or {}, "model": target_model or {}, "runtime": target_runtime or {}})
    ranked: list[tuple[float, dict[str, Any], list[str]]] = []
    for row in rows:
        if row.get("prediction_status") == "predicted":
            continue
        actual = _feature(row)
        distance, basis = _distance(actual, target)
        ranked.append((distance, row, basis))
    ranked.sort(key=lambda item: (item[0], str(item[1].get("run_id", "")), str(item[1].get("performance", {}).get("measurement_id", ""))))
    nearest = []
    for distance, row, basis in ranked[:5]:
        nearest.append({
            "record_id": row.get("run_id", row.get("record_type")),
            "run_id": row.get("run_id"),
            "model_id": row.get("model_id") or row.get("model", {}).get("canonical_id", row.get("model", {}).get("model_id")),
            "runtime_id": row.get("runtime_id") or row.get("runtime", {}).get("canonical_id", row.get("runtime", {}).get("runtime_id")),
            "distance": round(distance, 6),
            "distance_basis": basis,
            "measurement": copy.deepcopy(row.get("performance", {})),
            "hardware": copy.deepcopy(row.get("hardware", {})),
            "model": copy.deepcopy(row.get("model", {})),
            "runtime": copy.deepcopy(row.get("runtime", {})),
            "provenance": copy.deepcopy(row.get("provenance", {})),
        })
    return {
        "used": bool(nearest),
        "records": len(rows),
        "observed_records": len(ranked),
        "labels_used": False,
        "fields": ["runs", "models", "hardware", "machines", "runtime", "performance", "provenance"],
        "nearest": nearest,
        "reason": "joined observed measurements are contextual evidence only; policy verdict labels are ignored",
    }


def retrieve_nearest_observations(
    corpus: Any,
    hardware: dict[str, Any] | None = None,
    model: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Public retrieval API returning observed rows with provenance."""
    return _retrieval(corpus, hardware, model, runtime)


def _ref(item: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "model": item.get("model"),
        "reported_name": item.get("reported_name"),
        "size_class_b": item.get("size_class_b"),
        "prediction_status": item.get("prediction_status", "predicted"),
        "fit": copy.deepcopy(item.get("fit")),
        "runtime": copy.deepcopy(item.get("runtime")),
        "reason": item.get("reason"),
    }


@dataclass
class CandidatePlanner:
    hardware: dict[str, Any]
    models: list[dict[str, Any]]
    runtimes: list[dict[str, Any]]
    corpus: Any = None

    def plan(self) -> dict[str, Any]:
        available, architectures = _gpu_total(self.hardware)
        all_candidates: list[dict[str, Any]] = []
        for model in sorted(self.models, key=lambda x: str(x.get("canonical_id", x.get("model_id", x.get("reported_name", ""))))):
            info = _model_info(model)
            fit = estimate_model_fit(self.hardware, model)
            runtime = _runtime_candidates(model, self.hardware, self.runtimes)
            usable_runtime = [x for x in runtime if x["compatibility"] in {"candidate", "experimental", "unknown"}]
            model_id = model.get("canonical_id", model.get("model_id", model.get("reported_name")))
            if not usable_runtime:
                candidate_status = "rejected"
                reason = "all runtime candidates rejected: " + "; ".join(x["reason"] for x in runtime) if runtime else "no runtime candidate was supplied"
            else:
                candidate_status = "candidate"
                reason = "hardware facts + model metadata + runtime constraints + deterministic heuristic; no verdict labels used"
            retrieval_runtime = None
            if usable_runtime:
                retrieval_runtime = {"canonical_id": usable_runtime[0].get("runtime"), "name": usable_runtime[0].get("name")}
            all_candidates.append({
                "model": model_id,
                "reported_name": model.get("reported_name", model.get("canonical_name")),
                "model_metadata": copy.deepcopy(model),
                "fit": fit,
                "runtime": runtime,
                "eligible": bool(usable_runtime),
                "candidate_status": "experimental" if any(x["compatibility"] == "unknown" for x in usable_runtime) else candidate_status,
                "objective": "envelope" if usable_runtime else "rejected",
                "prediction_status": "predicted",
                "reason": reason,
                "confidence": fit.get("confidence", "low"),
                "size_class_b": info["total_params_b"],
                "architecture_type": info["type"],
                "memory_params_b": info["total_params_b"],
                "compute_active_params_b": info["active_params_b"],
                "retrieval": _retrieval(self.corpus, self.hardware, model, retrieval_runtime) if self.corpus is not None else {"used": False, "records": 0, "labels_used": False, "reason": "no observation corpus supplied"},
            })
        eligible = [x for x in all_candidates if x["eligible"]]
        by_size = sorted(eligible, key=lambda x: (x.get("size_class_b") is None, x.get("size_class_b") or math.inf, str(x.get("model"))))
        anchor = min(by_size, key=lambda x: abs((x.get("size_class_b") or 0) - 35.0)) if by_size else None
        anchor_result = copy.deepcopy(anchor) if anchor else None
        if anchor_result:
            anchor_result["objective"] = "anchor"
        envelope = [copy.deepcopy(item) for item in by_size]
        for item in envelope:
            item["objective"] = "envelope"
        practical = [x for x in by_size if x["fit"].get("fits") is True]
        # Unknown/false predictions remain useful for X/frontier exploration,
        # but cannot become an S/F/L/D or practical window bound.
        lower = min(practical, key=lambda x: (x.get("size_class_b") is None, x.get("size_class_b") or math.inf)) if practical else None
        largest = max(practical, key=lambda x: x.get("size_class_b") or 0) if practical else None
        sweet = min(practical, key=lambda x: abs((x.get("size_class_b") or 0) - 14.0)) if practical else None
        frontier = max(by_size, key=lambda x: x.get("size_class_b") or 0) if by_size else None
        slots = {"S": _ref(lower), "F": _ref(lower), "L": _ref(largest), "D": _ref(sweet), "X": _ref(frontier)}
        retrieval = _retrieval(self.corpus, self.hardware) if self.corpus is not None else {"used": False, "records": 0, "labels_used": False, "reason": "no observation corpus supplied"}
        return {
            "planner_version": "candidate-planner-v0.1",
            "prediction_status": "predicted",
            "hardware": copy.deepcopy(self.hardware),
            "hardware_vram_gib": available,
            "hardware_architectures": architectures,
            "candidates": all_candidates,
            "anchor": anchor_result,
            "envelope": envelope,
            "slots": slots,
            "experimental_frontier": _ref(frontier),
            "meaningful_window": {"lower_bound": _ref(lower), "practical_lower_bound": _ref(lower), "sweet_spot": _ref(sweet), "practical_upper_bound": _ref(largest), "capacity_frontier": _ref(frontier), "reason": "no practical bound is asserted when no candidate has predicted fits=true" if not practical else "bounds are predictions and require observed benchmark confirmation"},
            "runtime_candidates": {str(item["model"]): item["runtime"] for item in all_candidates},
            "retrieval": retrieval,
            "training_labels_used": False,
            "heuristic_disclaimer": "v0.3 PASS/FAIL verdicts are not used as training truth; predictions require observed benchmark runs",
        }


def _outcome_size(outcome: Mapping[str, Any], by_model: Mapping[str, Mapping[str, Any]]) -> float | None:
    size = _as_number(outcome.get("size_class_b"))
    if size is not None:
        return size
    model_id = outcome.get("model", outcome.get("model_id"))
    return _as_number((by_model.get(str(model_id)) or {}).get("size_class_b"))


def next_benchmark_candidate(plan: dict[str, Any], observed: Iterable[str] | Iterable[dict[str, Any]] = ()) -> dict[str, Any] | None:
    """Select the next useful boundary point from observed outcomes."""
    candidates = [x for x in plan.get("candidates", []) if x.get("eligible", True) and x.get("candidate_status") != "rejected"]
    if not candidates:
        candidates = [x for x in plan.get("envelope", []) if x.get("candidate_status") != "rejected"]
    by_model = {str(x.get("model")): x for x in candidates}
    observed_ids: set[str] = set()
    outcomes: list[dict[str, Any]] = []
    for item in observed or ():
        if isinstance(item, str):
            observed_ids.add(item)
        elif isinstance(item, Mapping):
            model_id = item.get("model", item.get("model_id"))
            if model_id is not None:
                observed_ids.add(str(model_id))
            outcomes.append(dict(item))
    choices = [x for x in candidates if str(x.get("model")) not in observed_ids]
    if not choices:
        return None
    fit_sizes: list[float] = []
    fail_sizes: list[float] = []
    for outcome in outcomes:
        size = _outcome_size(outcome, by_model)
        status = str(outcome.get("status", outcome.get("outcome", ""))).lower()
        if size is None:
            continue
        if status in _SUCCESS:
            fit_sizes.append(size)
        elif status in _FAILURE:
            fail_sizes.append(size)
    sized = [x for x in choices if _as_number(x.get("size_class_b")) is not None]
    if fit_sizes and fail_sizes:
        low, high = max(fit_sizes), min(fail_sizes)
        inside = [x for x in sized if low < float(x["size_class_b"]) < high]
        if inside:
            midpoint = (low + high) / 2
            return min(inside, key=lambda x: (abs(float(x["size_class_b"]) - midpoint), float(x["size_class_b"])))
    if fit_sizes and not fail_sizes:
        above = [x for x in sized if float(x["size_class_b"]) > max(fit_sizes)]
        if above:
            return min(above, key=lambda x: float(x["size_class_b"]))
    if fail_sizes and not fit_sizes:
        below = [x for x in sized if float(x["size_class_b"]) < min(fail_sizes)]
        if below:
            return max(below, key=lambda x: float(x["size_class_b"]))
    if fit_sizes and fail_sizes:
        midpoint = (max(fit_sizes) + min(fail_sizes)) / 2
        return min(sized, key=lambda x: abs(float(x["size_class_b"]) - midpoint)) if sized else choices[0]
    anchor = plan.get("anchor")
    if anchor and str(anchor.get("model")) not in observed_ids and any(str(x.get("model")) == str(anchor.get("model")) for x in choices):
        return next(x for x in choices if str(x.get("model")) == str(anchor.get("model")))
    return min(choices, key=lambda x: (x.get("size_class_b") is None, x.get("size_class_b") or math.inf, str(x.get("model"))))


build_observation_corpus = load_normalized_corpus
join_normalized_corpus = load_normalized_corpus
