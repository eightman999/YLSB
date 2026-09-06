from __future__ import annotations

import json
import math
import statistics
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
    from jsonschema import FormatChecker

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"{'.'.join(str(x) for x in error.absolute_path) or '<root>'}: {error.message}" for error in validator.iter_errors(instance)]


def validate_normalized_record(record: dict[str, Any]) -> list[str]:
    return _jsonschema_errors(record, _schema("normalized-corpus-v0.2.schema.json"))


def validate_run_record(record: dict[str, Any]) -> list[str]:
    errors = _jsonschema_errors(record, _schema("run-record-v0.2.schema.json"))
    if not errors:
        errors.extend(validate_run_record_semantics(record))
    return errors


_COURSE_PROFILES = {
    "YLSB-UME": ROOT / "ume" / "profile.json",
    "YLSB-TAKE": ROOT / "take" / "profile.json",
    "YLSB-MATSU": ROOT / "matsu" / "profile.json",
}


def course_profile(course_id: str) -> dict[str, Any]:
    """Return the immutable v0.3 course profile used for v2 semantic checks."""
    try:
        path = _COURSE_PROFILES[course_id]
    except KeyError:
        raise ValueError(f"unsupported course_id: {course_id!r}") from None
    return json.loads(path.read_text(encoding="utf-8"))


def expected_performance_slots(course_id: str) -> tuple[tuple[str, int, int], ...]:
    """Return ``(metric, point_tokens, depth_tokens)`` slots required by a course.

    The profiles define a baseline at depth zero for every PP/TG point.  Long
    context probes use the profile's dedicated PP/TG point (``depth_pp`` /
    ``depth_tg``) at each non-zero profile depth.  The zero-depth union is
    deliberately de-duplicated while preserving profile order.
    """
    profile = course_profile(course_id)
    slots: list[tuple[str, int, int]] = []
    for metric, points, depth_key in (
        ("PP", profile["pp"], "depth_pp"),
        ("TG", profile["tg"], "depth_tg"),
    ):
        slots.extend((metric, int(point), 0) for point in points)
        long_point = int(profile[depth_key])
        slots.extend((metric, long_point, int(depth)) for depth in profile["depth"] if int(depth) > 0)
    return tuple(slots)


def _number_close(actual: float, expected: float) -> bool:
    # JSON producers commonly round summaries to six decimals; retain enough
    # tolerance for that representation while rejecting substantive drift.
    return math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)


def validate_run_record_semantics(record: dict[str, Any]) -> list[str]:
    """Check cross-field formal-run invariants that JSON Schema cannot express."""
    if not isinstance(record, dict):
        return ["<root>: formal run record must be an object"]
    course_id = record.get("course_id")
    if course_id not in _COURSE_PROFILES:
        return [f"course_id: unsupported course {course_id!r}"]
    profile = course_profile(course_id)
    repeats = int(profile["repetitions"])
    expected = set(expected_performance_slots(course_id))
    errors: list[str] = []

    summaries = record.get("performance_summary", [])
    samples = record.get("performance_samples", [])
    summary_map: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, summary in enumerate(summaries):
        key = (summary.get("metric"), summary.get("point_tokens"), summary.get("depth_tokens"))
        if key in summary_map:
            errors.append(f"performance_summary[{index}]: duplicate slot {key}")
        summary_map[key] = summary
        if summary.get("repeats_expected") != repeats:
            errors.append(f"performance_summary[{index}].repeats_expected: expected {repeats}")
        if summary.get("repeats_recorded") != repeats:
            errors.append(f"performance_summary[{index}].repeats_recorded: expected {repeats}")

    actual_summary_slots = set(summary_map)
    for key in sorted(expected - actual_summary_slots):
        errors.append(f"performance_summary: missing course slot {key}")
    for key in sorted(actual_summary_slots - expected):
        errors.append(f"performance_summary: unexpected course slot {key}")

    sample_map: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for index, sample in enumerate(samples):
        key = (sample.get("metric"), sample.get("point_tokens"), sample.get("depth_tokens"))
        sample_map.setdefault(key, []).append(sample)
        if sample.get("vram_used_mib") is None:
            errors.append(f"performance_samples[{index}].vram_used_mib: formal value is required")
        if sample.get("timings_cache_n") is None:
            errors.append(f"performance_samples[{index}].timings_cache_n: formal value is required")

    actual_sample_slots = set(sample_map)
    for key in sorted(expected - actual_sample_slots):
        errors.append(f"performance_samples: missing course slot {key}")
    for key in sorted(actual_sample_slots - expected):
        errors.append(f"performance_samples: unexpected course slot {key}")

    for key, slot_samples in sample_map.items():
        indices = sorted(sample.get("repeat_index") for sample in slot_samples)
        if indices != list(range(1, repeats + 1)):
            errors.append(f"performance_samples[{key}].repeat_index: expected 1..{repeats}, got {indices}")
        summary = summary_map.get(key)
        if summary is None or len(slot_samples) != repeats:
            continue
        rates = [sample["tokens_per_second"] for sample in slot_samples]
        mean = statistics.fmean(rates)
        kind = summary.get("standard_deviation_kind")
        deviation = statistics.stdev(rates) if kind == "sample" else statistics.pstdev(rates)
        if not _number_close(summary["mean_tokens_per_second"], mean):
            errors.append(f"performance_summary[{key}].mean_tokens_per_second: does not match samples")
        if not _number_close(summary["standard_deviation_tokens_per_second"], deviation):
            errors.append(f"performance_summary[{key}].standard_deviation_tokens_per_second: does not match samples")
        peak = max(sample["vram_used_mib"] for sample in slot_samples)
        if not _number_close(summary["vram_peak_mib"], peak):
            errors.append(f"performance_summary[{key}].vram_peak_mib: does not match samples")
    return errors


def validate_record(record: dict[str, Any]) -> list[str]:
    if record.get("schema_version") == 2 and record.get("record_type") in {"run", None}:
        return validate_run_record(record)
    return validate_normalized_record(record)


__all__ = [
    "PROVENANCE_KINDS", "RECORD_TYPES", "course_profile", "expected_performance_slots",
    "validate_normalized_record", "validate_run_record", "validate_run_record_semantics", "validate_record",
]
