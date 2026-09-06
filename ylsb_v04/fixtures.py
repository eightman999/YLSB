from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _identity(row: dict[str, Any], version: str) -> dict[str, Any]:
    payload_row = {key: value for key, value in row.items() if key != "identity"}
    payload = json.dumps(payload_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"fixture_id": row["id"], "fixture_version": version, "benchmark_version": "0.4-rc1", "sha256": hashlib.sha256(payload).hexdigest()}


def load_core_v04() -> list[dict[str, Any]]:
    """Load the explicit v0.4 fixture; historical v0.3 remains untouched."""
    source = _read_jsonl(ROOT / "fixtures/v0.4-rc1/core_ume_28.jsonl")
    cases = []
    for original in source:
        row = dict(original)
        row["identity"] = _identity(row, "v0.4-rc1")
        row.update(row["identity"])
        cases.append(row)
    return cases


def load_sentinel_v04() -> list[dict[str, Any]]:
    cases = _read_jsonl(ROOT / "fixtures/v0.4-rc1/sentinel_ume_4.jsonl")
    for row in cases:
        row["identity"] = _identity(row, "v0.4-rc1")
        row.update(row["identity"])
    return cases


def fixture_manifest() -> dict[str, Any]:
    return {"benchmark_version": "0.4-rc1", "fixtures": [row["identity"] for row in load_core_v04() + load_sentinel_v04()], "source": "explicit v0.4 fixture files; historical files are immutable"}


def validate_v04_fixtures() -> dict[str, Any]:
    core = load_core_v04()
    sentinel = load_sentinel_v04()
    if len(core) != 28 or len(sentinel) != 4:
        raise ValueError(f"expected 28 core and 4 sentinel fixtures, got {len(core)} and {len(sentinel)}")
    if len({row["id"] for row in core + sentinel}) != 32:
        raise ValueError("fixture IDs are not unique")
    constraints = {row["id"]: row for row in core if row.get("category") == "constraint"}
    predicates = {
        "CORE-CONSTRAINT-001": lambda p: p.index("A") < p.index("D") and abs(p.index("A") - p.index("D")) != 1 and p.index("B") < p.index("C") and abs(p.index("B") - p.index("D")) != 1 and p.index("B") not in (0, 4) and p.index("E") not in (0, 4) and p.index("B") == p.index("A") + 1 and p.index("E") == p.index("B") + 1 and p.index("D") not in (0, 4),
        "CORE-CONSTRAINT-002": lambda p: abs(p.index("C") - p.index("E")) != 1 and p.index("D") not in (0, 4) and p[4] == "B" and p.index("C") not in (0, 4) and p.index("D") < p.index("C") and abs(p.index("A") - p.index("E")) != 1 and abs(p.index("C") - p.index("D")) != 1,
        "CORE-CONSTRAINT-003": lambda p: p.index("C") < p.index("B") and p.index("A") == p.index("B") + 1 and p.index("D") < p.index("C") and p.index("A") < p.index("E"),
        "CORE-CONSTRAINT-004": lambda p: p.index("C") == p.index("A") + 1 and p.index("E") not in (0, 4) and abs(p.index("D") - p.index("E")) != 1 and p.index("D") < p.index("A") and abs(p.index("B") - p.index("D")) != 1,
    }
    audits = {}
    for task_id, predicate in predicates.items():
        solutions = ["".join(p) for p in itertools.permutations("ABCDE") if predicate(p)]
        row = constraints[task_id]
        if row.get("tags", []).count("unique_solution") != 1 or len(solutions) != 1 or row["gold"] not in solutions:
            raise ValueError(f"constraint validation failed for {task_id}: {solutions}")
        audits[task_id] = {"solutions": solutions, "gold": row["gold"], "unique": True, "gold_valid": True}
    for row in core + sentinel:
        if not {"fixture_id", "fixture_version", "benchmark_version", "sha256"}.issubset(row["identity"]):
            raise ValueError(f"missing fixture identity: {row['id']}")
        if row.get("grader") == "numeric_exact":
            float(row["gold"])
        if row.get("grader") == "json_exact" and not isinstance(row["gold"], (dict, list)):
            raise ValueError(f"JSON gold is not structured: {row['id']}")
    return {"core_count": len(core), "sentinel_count": len(sentinel), "constraints": audits, "manifest": fixture_manifest()}
