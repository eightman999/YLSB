from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROVENANCE_KINDS = frozenset({"reported", "registry", "derived", "inferred", "unknown"})
RECORD_TYPES = frozenset({"submission", "model", "run", "task_result", "performance", "verdict", "hardware", "machine", "runtime", "planner", "import"})
ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))


def _jsonschema_errors(instance: Any, schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        raise RuntimeError(
            "YLSB v0.4 schema validation requires jsonschema; install with "
            "python3 -m pip install -r requirements-v04.txt"
        ) from None
    validator = Draft202012Validator(schema)
    return [f"{'.'.join(str(x) for x in error.absolute_path) or '<root>'}: {error.message}" for error in validator.iter_errors(instance)]


def validate_normalized_record(record: dict[str, Any]) -> list[str]:
    return _jsonschema_errors(record, _schema("normalized-corpus-v0.2.schema.json"))


def validate_run_record(record: dict[str, Any]) -> list[str]:
    return _jsonschema_errors(record, _schema("run-record-v0.2.schema.json"))


def validate_record(record: dict[str, Any]) -> list[str]:
    if record.get("schema_version") == 2 and record.get("record_type") in {"run", None}:
        return validate_run_record(record)
    return validate_normalized_record(record)


__all__ = ["PROVENANCE_KINDS", "RECORD_TYPES", "validate_normalized_record", "validate_run_record", "validate_record"]
