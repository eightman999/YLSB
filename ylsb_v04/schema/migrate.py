"""Pure v0.3 -> normalized-corpus-v0.2 adapters.

Migration never edits the input tree and never derives a canonical identity
from a reported name.  Missing facts are represented as ``None`` and marked
unknown with a reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


UNKNOWN = {"kind": "unknown", "reason": "Not present in the v0.3 source record."}


def _provenance(value: Any, source: str) -> Any:
    if isinstance(value, dict) and "kind" in value:
        result = dict(value)
        if result.get("kind") == "unknown":
            result.setdefault("reason", "Unknown in the source record.")
        else:
            result.setdefault("source", source)
        return result
    if isinstance(value, dict) and value:
        result: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, dict) and "kind" in item:
                result[key] = _provenance(item, source)
            else:
                result[key] = item
        return result
    return {"kind": "reported", "source": source}


def _unknown_map(fields: tuple[str, ...]) -> dict[str, Any]:
    return {f"/{field}": dict(UNKNOWN) for field in fields}


def _adapt_hardware(value: Any, source: str) -> dict[str, Any]:
    """Adapt legacy ``gpu``/``ram_gib`` shape without inventing identities."""
    old = value if isinstance(value, dict) else {}
    cpu_old = old.get("cpu") if isinstance(old.get("cpu"), dict) else {}
    cpu = {
        "reported_name": cpu_old.get("reported_name"), "canonical_id": cpu_old.get("canonical_id"),
        "sockets": cpu_old.get("sockets"), "cores": cpu_old.get("cores"), "threads": cpu_old.get("threads"),
        "memory_channels": cpu_old.get("memory_channels"), "pcie_generation": cpu_old.get("pcie_generation"), "pcie_lanes": cpu_old.get("pcie_lanes"),
        "provenance": _provenance(cpu_old.get("provenance"), source) if cpu_old.get("provenance") else dict(UNKNOWN),
    }
    groups: list[dict[str, Any]] = []
    old_groups = old.get("gpu_groups")
    if not isinstance(old_groups, list):
        old_gpu = old.get("gpu")
        old_groups = old_gpu if isinstance(old_gpu, list) else ([old_gpu] if isinstance(old_gpu, dict) else [])
    for group in old_groups:
        if not isinstance(group, dict):
            continue
        groups.append({
            "canonical_id": group.get("canonical_id"), "reported_name": group.get("reported_name", group.get("model")),
            "count": group.get("count"), "vram_gib_each": group.get("vram_gib_each"),
            "bus": group.get("bus"), "numa_node": group.get("numa_node"), "interconnect": group.get("interconnect"),
            "provenance": _provenance(group.get("provenance"), source) if group.get("provenance") else dict(UNKNOWN),
        })
    if not groups:
        groups = [{"canonical_id": None, "reported_name": None, "count": None, "vram_gib_each": None, "provenance": dict(UNKNOWN)}]
    ram = old.get("ram") if isinstance(old.get("ram"), dict) else {}
    total = ram.get("total_gib", old.get("ram_gib"))
    return {
        "cpu": cpu,
        "ram": {"total_gib": total, "provenance": _provenance(ram.get("provenance"), source) if ram.get("provenance") else dict(UNKNOWN)},
        "gpu_groups": groups,
        "topology": old.get("topology"),
        "interconnect": old.get("interconnect"),
    }


def migrate_v03_record(record: dict[str, Any], *, source: str = "v0.3 observation") -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("v0.3 record must be an object")
    result = dict(record)
    result["schema_version"] = "normalized-corpus-v0.2"
    if not result.get("record_type"):
        if "task_id" in result:
            result["record_type"] = "task_result"
        elif "measurement_id" in result:
            result["record_type"] = "performance"
        elif "run_id" in result:
            result["record_type"] = "run"
        else:
            result["record_type"] = "import"
    result["provenance"] = _provenance(result.get("provenance"), source)
    record_type = result["record_type"]
    if record_type == "run" and "hardware" in result:
        result["hardware"] = _adapt_hardware(result.get("hardware"), source)
    if record_type in {"task_result", "performance"}:
        result.setdefault("observation", {"status": "observed"})
    if record_type == "task_result":
        # Keep the historical score as-is; these are observations, not v0.4
        # semantic grades.  A later adapter may add grader-v2 dimensions.
        result.setdefault("task_result_id", f"{result.get('run_id', 'legacy')}-task-{result.get('task_id', 'unknown')}")
        result.setdefault("run_id", None)
        result.setdefault("section", "unknown")
        result.setdefault("score", None)
        result.setdefault("status", "skipped")
        result.setdefault("grader", None)
        result.setdefault("reuse", {"classification": "regradable", "reason": "Migrated observation; no v0.4 verdict inferred."})
        result.setdefault("source", {"path": source})
    elif record_type == "performance":
        result.setdefault("measurement_id", f"{result.get('run_id', 'legacy')}-measurement")
        result.setdefault("run_id", None)
        result.setdefault("measurement_phase", "original_run")
        result.setdefault("metric", None)
        result.setdefault("value", None)
        result.setdefault("unit", None)
        result.setdefault("repeat", None)
        result.setdefault("reuse", {"classification": "regradable", "reason": "Migrated observation; no v0.4 verdict inferred."})
        result.setdefault("source", {"path": source})
    elif record_type == "import":
        result.setdefault("source", {"path": source})
    return result


def migrate_directory(input_dir: str | Path, output_dir: str | Path) -> list[Path]:
    source = Path(input_dir).resolve()
    destination = Path(output_dir).resolve()
    if source == destination or source in destination.parents:
        raise ValueError("migration output must be separate from the v0.3 input tree")
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted(source.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        target = destination / path.name
        payload = "".join(json.dumps(migrate_v03_record(row, source=path.as_posix()), ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
        target.write_text(payload, encoding="utf-8")
        written.append(target)
    return written
