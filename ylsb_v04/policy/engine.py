from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Policy:
    policy_version: str
    data: dict[str, Any]

    @property
    def gates(self) -> dict[str, Any]:
        return self.data.get("gates", {})


def load_policy(policy: str | Path) -> Policy:
    path = Path(policy)
    if not path.exists():
        path = ROOT / "policies" / (policy if str(policy).endswith(".json") else f"{policy}.json")
    if not path.exists():
        aliases = {"v0.3": "ylsb-v0.3.json", "YLSB-v0.3": "ylsb-v0.3.json", "v0.4-rc1": "ylsb-v0.4-rc1.json", "YLSB-v0.4-rc1": "ylsb-v0.4-rc1.json"}
        path = ROOT / "policies" / aliases.get(str(policy), str(policy))
    data = json.loads(path.read_text(encoding="utf-8"))
    return Policy(data["policy_version"], data)


def _pct(n: int, d: int) -> float:
    return n / d if d else 0.0


def _failure_count(rows: list[dict[str, Any]], kind: str) -> int:
    return sum(1 for row in rows if row.get("failure_class_audited") == kind or row.get("failure_class_reported") == kind)


def _base_stats(rows: list[dict[str, Any]], *, historical: bool = False) -> dict[str, Any]:
    def tier(row: dict[str, Any], *, historical: bool = False) -> str:
        if historical:
            return "historical_core" if row.get("section") == "core" else "historical_other"
        if row.get("tier") in {"essential", "practical", "discriminator"}:
            return row["tier"]
        return "unknown"
    core = [r for r in rows if r.get("section") == "core"]
    essential = [r for r in core if tier(r, historical=historical) == "essential"]
    practical = [r for r in core if tier(r, historical=historical) == "practical"]
    discriminator = [r for r in core if tier(r, historical=historical) == "discriminator"]
    sentinel = [r for r in rows if r.get("section") == "sentinel"]
    def score(items: list[dict[str, Any]], *, exclude_invalid: bool = True, exclude_rerun: bool = False) -> dict[str, Any]:
        valid = [r for r in items if (not exclude_invalid or r.get("reuse", {}).get("classification") != "invalid") and (not exclude_rerun or r.get("reuse", {}).get("classification") != "requires_rerun")]
        correct = sum(1 for r in valid if r.get("answer_correct", r.get("score", 0)) == 1 or r.get("answer_correct") is True)
        non_empty = sum(1 for r in valid if r.get("non_empty") is True)
        format_ok = sum(1 for r in valid if r.get("format_correct", r.get("format_ok", False)) is True)
        return {"correct": correct, "attempts": len(valid), "accuracy": _pct(correct, len(valid)), "format": _pct(format_ok, len(valid)), "non_empty": _pct(non_empty, len(valid))}
    api = [r for r in rows if r.get("section") == "api_smoke"]
    quality = core + sentinel + api
    # v0.3 historical compatibility keeps its complete Core denominator.
    # v0.4 capability rates exclude only explicit invalid fixtures and
    # requires_rerun observations; the latter remain visible in health counts.
    exclude_rerun = not historical
    return {"core": score(core, exclude_invalid=False, exclude_rerun=False), "essential": score(essential, exclude_rerun=exclude_rerun), "practical": score(practical, exclude_rerun=exclude_rerun), "discriminator": score(discriminator, exclude_rerun=exclude_rerun), "sentinel": score(sentinel, exclude_rerun=exclude_rerun), "api_smoke": score(api, exclude_rerun=exclude_rerun), "invalid": _failure_count(rows, "FIXTURE_INVALID"), "invalid_sentinel": _failure_count(sentinel, "FIXTURE_INVALID"), "infra": _failure_count(rows, "INFRA"), "protocol": _failure_count(rows, "PROTOCOL"), "protocol_invalid": sum(1 for r in quality if r.get("protocol_valid") is False), "serving_invalid": sum(1 for r in quality if r.get("serving_valid") is False), "quality_non_empty": _pct(sum(1 for r in quality if r.get("non_empty") is True), len(quality)), "metadata_unknown": sum(1 for r in core if tier(r) == "unknown"), "section_counts": {"core": len(core), "sentinel": len(sentinel), "api_smoke": len(api)}, "rows": len(rows)}


def _gate_detail(name: str, s: dict[str, Any], cfg: dict[str, Any], *, v03: bool = False) -> tuple[bool, str]:
    if v03:
        core = s["core"]
        passed = core["accuracy"] >= cfg.get("core_min", 0) and core["format"] >= cfg.get("format_min", 0) and core["non_empty"] >= cfg.get("non_empty_min", 0) and s["infra"] <= cfg.get("infra_max", 0)
        detail = f"Core>={cfg.get('core_min', 0):.0%}({core['accuracy']:.1%}) format>={cfg.get('format_min', 0):.0%}({core['format']:.1%}) non-empty={cfg.get('non_empty_min', 0):.0%}({core['non_empty']:.1%}) INFRA={cfg.get('infra_max', 0)}({s['infra']})"
        return passed, detail
    essential = s["essential"]
    practical_task = s["practical"]["correct"]
    sentinel_min = cfg.get("sentinel_min", 0)
    sentinel_ok = isinstance(sentinel_min, (int, float)) and sentinel_min > 0 and s["sentinel"]["correct"] >= sentinel_min
    practical_min = cfg.get("practical_task_min", 0)
    practical_ok = practical_task >= practical_min if practical_min > 0 else True
    expected = cfg.get("fixture_expectations", {})
    complete = all(s["section_counts"].get(section) == count for section, count in expected.items())
    passed = complete and s["metadata_unknown"] == 0 and essential["accuracy"] >= cfg.get("essential_min", 0) and essential["format"] >= cfg.get("format_min", 0) and essential["non_empty"] >= cfg.get("non_empty_min", 0) and s["quality_non_empty"] >= cfg.get("quality_non_empty_min", cfg.get("non_empty_min", 0)) and s["protocol"] <= cfg.get("protocol_max", 10**9) and s["protocol_invalid"] == 0 and s["serving_invalid"] == 0 and s["infra"] <= cfg.get("infra_max", 0) and (sentinel_ok or practical_ok)
    detail = f"Essential>={cfg.get('essential_min', 0):.0%}({essential['accuracy']:.1%}) format>={cfg.get('format_min', 0):.0%}({essential['format']:.1%}) non-empty>={cfg.get('non_empty_min', 0):.0%}({essential['non_empty']:.1%}) INFRA<={cfg.get('infra_max', 0)}({s['infra']}) practical_correct>={cfg.get('practical_task_min', 0)}({practical_task})"
    return passed, detail


def evaluate_run(rows: Iterable[dict[str, Any]], policy: Policy) -> dict[str, Any]:
    v03 = policy.policy_version == "YLSB-v0.3"
    rows = list(rows)
    if v03:
        # Historical v0.3 gate semantics deliberately use the complete Core denominator.
        for row in rows:
            row.setdefault("tier", "historical_core" if row.get("section") == "core" else "historical_other")
    stats = _base_stats(rows, historical=v03)
    gates: dict[str, Any] = {}
    for name, cfg in policy.gates.items():
        if name == "ume_full_clear":
            sentinel = stats["sentinel"]
            passed = sentinel["correct"] >= cfg.get("sentinel_min", 0) and stats["invalid_sentinel"] <= cfg.get("invalid_max", 0) and stats["infra"] <= cfg.get("infra_max", 0) and sentinel["non_empty"] >= cfg.get("non_empty_min", 0)
            if not v03:
                expected = cfg.get("fixture_expectations", {})
                passed = passed and stats["metadata_unknown"] == 0 and stats["protocol_invalid"] == 0 and stats["serving_invalid"] == 0 and all(stats["section_counts"].get(section) == count for section, count in expected.items())
            detail = f"Sentinel {sentinel['correct']}/{sentinel['attempts']} INVALID={stats['invalid_sentinel']} INFRA={stats['infra']} non-empty={sum(1 for x in rows if x.get('section') == 'sentinel' and x.get('non_empty'))}/{sentinel['attempts']}"
        else:
            passed, detail = _gate_detail(name, stats, cfg, v03=v03)
        label = {"smallest_meaningful": "Smallest Meaningful候補", "fastest_useful": "Fastest Useful候補", "ume_full_clear": "梅・難問全通過"}.get(name, name)
        gates[name] = {"label": label, "pass": passed, "detail": detail}
    return {"policy_version": policy.policy_version, "gates": gates, "statistics": stats, "hard_sentinel_observation": {"correct": stats["sentinel"]["correct"], "attempts": stats["sentinel"]["attempts"]}}


def threshold_sensitivity(rows: Iterable[dict[str, Any]], policy: Policy | None = None) -> list[dict[str, Any]]:
    policy = policy or load_policy("YLSB-v0.4-rc1")
    values = policy.data.get("threshold_sensitivity", {}).get("essential_min", [0.60, 0.70, 0.80])
    result = []
    for threshold in values:
        data = dict(policy.data)
        data["gates"] = dict(policy.gates)
        data["gates"]["smallest_meaningful"] = dict(data["gates"].get("smallest_meaningful", {}), essential_min=threshold)
        data["gates"]["fastest_useful"] = dict(data["gates"].get("fastest_useful", {}), essential_min=threshold)
        r = evaluate_run(rows, Policy(policy.policy_version, data))
        result.append({"essential_min": threshold, "smallest_meaningful": r["gates"]["smallest_meaningful"], "fastest_useful": r["gates"]["fastest_useful"]})
    return result


def regrade_corpus(path: str | Path, policy: Policy) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["run_id"], []).append(row)
    result = []
    for run_id, items in sorted(grouped.items()):
        verdict = evaluate_run(items, policy)
        result.append({"record_type": "verdict", "run_id": run_id, **verdict, "source_observation": str(path), "regrade": True})
    return result
