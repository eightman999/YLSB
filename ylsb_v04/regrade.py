from __future__ import annotations

import json
import hashlib
import statistics
from pathlib import Path
from typing import Any

from .policy.engine import Policy, evaluate_run, load_policy, threshold_sensitivity
from common.grader_basic import grade_v2
from .fixtures import load_sentinel_v04, load_core_v04


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle(input_path: Path) -> tuple[Path, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve only the supplied corpus bundle; never fall back to a global corpus."""
    root = input_path if input_path.is_dir() else input_path.parent
    task_path = root / "task_results.jsonl" if input_path.is_dir() else input_path
    supplied = _read(task_path)
    # Import output may be one mixed submission-*.jsonl.  Separate records by
    # type before adapting; records from the same file take precedence over
    # optional sibling performance/runs files.
    task_rows = [row for row in supplied if row.get("record_type") == "task_result" or row.get("task_id")]
    supplied_performance = [row for row in supplied if row.get("record_type") == "performance" or row.get("measurement_id")]
    supplied_runs = [row for row in supplied if row.get("record_type") == "run" and row.get("run_id")]
    rows = task_rows if task_rows else supplied
    perf_path, runs_path = root / "performance.jsonl", root / "runs.jsonl"
    performance = supplied_performance or (_read(perf_path) if perf_path.exists() else [])
    runs = supplied_runs or (_read(runs_path) if runs_path.exists() else [])
    return root, rows, performance, runs


def _fixture_catalog() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    v03 = {}
    for relative in ("ume/tests/core_ume_28.jsonl", "ume/tests/sentinel_ume_4.jsonl", "ume/tests/api_smoke_10.jsonl"):
        path = ROOT / relative
        for row in _read(path):
            row = dict(row)
            row["fixture_identity"] = {"fixture_id": row["id"], "fixture_version": "v0.3", "benchmark_version": "0.3", "sha256": _sha(path)}
            v03[row["id"]] = row
    v04 = {row["id"]: row for row in load_core_v04() + load_sentinel_v04()}
    return v03, v04


def _adapt_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pure v0.3 observation -> v2 grader -> explicit fixture metadata adapter."""
    v03, v04 = _fixture_catalog()
    adapted = []
    for source in rows:
        row = dict(source)
        task_id = row.get("task_id") or row.get("id")
        source_fixture = row.get("fixture") if isinstance(row.get("fixture"), dict) else {}
        declared_version = row.get("fixture_version") or source_fixture.get("fixture_version") or row.get("benchmark_version")
        source_path = str((row.get("source") or {}).get("path", "")) if isinstance(row.get("source"), dict) else ""
        if declared_version and str(declared_version).startswith("v0.4"):
            source_kind = "v04"
        elif (declared_version and str(declared_version).startswith("v0.3")) or "/v0.3/" in source_path or row.get("schema_version") == "normalized-corpus-v0.1":
            source_kind = "v03"
        else:
            source_kind = "unknown"
        case = v04.get(task_id) if source_kind == "v04" else v03.get(task_id) if source_kind == "v03" else None
        if case is None:
            row["metadata_unknown"] = True
            adapted.append(row)
            continue
        case_identity = case.get("fixture_identity") or case.get("identity")
        output = row.get("model_output", row.get("raw_content", ""))
        output = "" if output is None else str(output)
        # HTTP 200 with an empty body is a healthy serving path but a protocol
        # failure.  Keep those dimensions independent for rerun accounting.
        serving_ok = row.get("http_status") in (None, 200, "200")
        protocol_ok = bool(output.strip()) and source.get("protocol_valid") is not False
        serving_ok = serving_ok and source.get("serving_valid") is not False
        grading_case = dict(case)
        if task_id in v04:
            # Output contracts are v0.4 fixture metadata; source v0.3 rows
            # remain the immutable identity used for historical provenance.
            grading_case.update({key: v04[task_id][key] for key in ("format_pattern", "output_pattern", "allowed_choices") if key in v04[task_id]})
        # v0.3's deterministic answer extraction is an observation field; use it
        # only as the semantic candidate. Recheck strict format against raw output.
        semantic_output = row.get("normalized_answer", output)
        graded = grade_v2(grading_case, semantic_output, serving_valid=serving_ok, protocol_valid=protocol_ok)
        strict = grade_v2(grading_case, output, serving_valid=serving_ok, protocol_valid=protocol_ok)
        graded["format_correct"] = strict["format_correct"]
        graded["non_empty"] = strict["non_empty"]
        graded["protocol_valid"] = strict["protocol_valid"]
        graded["serving_valid"] = strict["serving_valid"]
        graded["status"] = "INFRA" if not serving_ok else ("PROTOCOL" if not protocol_ok else ("PASS" if graded["answer_correct"] else "CAPABILITY"))
        graded["requires_rerun"] = not serving_ok or not protocol_ok
        row.update(graded)
        if source_kind == "v04":
            row["fixture"] = source_fixture or case_identity
            row["fixture_v04"] = case["identity"]
            row["tier"] = case.get("tier")
            row["gate_roles"] = case.get("gate_roles", [])
        else:
            row["fixture"] = case_identity
        if source_kind == "v03" and task_id in v04:
            metadata = v04[task_id]
            row["fixture_v04"] = metadata["identity"]
            row["tier"] = metadata.get("tier")
            row["gate_roles"] = metadata.get("gate_roles", [])
        elif row.get("section") == "api_smoke":
            # The API fixture remains v0.3 source data; its v0.4 role is explicit health.
            row["fixture_v04"] = {"fixture_id": task_id, "fixture_version": "v0.4-rc1", "benchmark_version": "0.4-rc1", "sha256": case["fixture_identity"]["sha256"]}
            row["tier"] = "practical"
            row["gate_roles"] = ["serving_health"]
        if source_kind == "v03" and task_id == "CORE-CONSTRAINT-003":
            row["answer_correct"] = False
            row["format_correct"] = False
            row["failure_class_audited"] = "FIXTURE_INVALID"
            row["reuse"] = {"classification": "invalid", "reason": "v0.3 gold contradicts exhaustive solution; v0.4 corrected fixture is separate"}
        elif not serving_ok:
            row["failure_class_audited"] = "INFRA"
            row["reuse"] = {"classification": "requires_rerun", "reason": "serving health failed; capability result is not reusable"}
        elif not graded.get("protocol_valid") or not graded.get("non_empty"):
            row["failure_class_audited"] = "PROTOCOL"
            row["reuse"] = {"classification": "requires_rerun", "reason": "empty output retained as protocol/serving uncertainty"}
        else:
            row["failure_class_audited"] = "PASS" if graded["answer_correct"] else "CAPABILITY"
            row.setdefault("reuse", {"classification": "regradable", "reason": "v2 deterministic regrade"})
        row["observation"] = {"status": "observed", "source_fixture": case_identity}
        adapted.append(row)
    return adapted


def _comparable_performance(performance: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Map supplied original-run measurements to comparable R0 TG128 samples."""
    run_meta = {row.get("run_id"): row for row in runs}
    comparable: dict[str, list[dict[str, Any]]] = {}
    for row in performance:
        if str(row.get("metric", "")).lower() != "tg" or row.get("target_tokens") != 128:
            continue
        if row.get("measurement_phase") != "original_run" or row.get("value") is None:
            continue
        metadata = run_meta.get(row.get("run_id"), {})
        config = metadata.get("config", {})
        lane = config.get("lane") or metadata.get("lane")
        # Context is comparable only when the performance record reports it.
        # Run-level ctx is retained in the run record but is not silently
        # projected onto a measurement that omitted that field.
        context = row.get("context_tokens", row.get("context"))
        if lane != "R0":
            continue
        comparable.setdefault(row["run_id"], []).append({
            "value": row["value"], "repeat": row.get("repeat"), "metric": "TG",
            "target_tokens": 128, "depth_tokens": row.get("depth") if row.get("depth") is not None else 0, "lane": lane,
            "context_tokens": context, "run_context_tokens": config.get("ctx") or config.get("ctx_size"), "measurement_phase": "original_run",
            "source": row.get("source"),
        })
    # A comparison must use one phase/point/lane/context.  If all runs expose
    # a context, keep only contexts common to every run; absent context is an
    # explicit legacy value and is comparable to the same absent value.
    context_sets = [
        {sample.get("context_tokens") for sample in samples}
        for samples in comparable.values() if samples
    ]
    common = set.intersection(*context_sets) if context_sets else set()
    if context_sets and common:
        return {run_id: [sample for sample in samples if sample.get("context_tokens") in common] for run_id, samples in comparable.items()}
    if context_sets and not common:
        return {}
    return comparable


def _legacy_v03_verdict_path(input_path: Path) -> Path:
    """Use historical verdicts only for an input physically under results/v0.3."""
    try:
        input_path.resolve().relative_to((ROOT / "results/v0.3").resolve())
    except ValueError:
        return Path("/dev/null")
    return ROOT / "results/v0.3/derived/v0.3_verdicts.jsonl"


def regrade(input_path: str | Path, policy_name: str = "YLSB-v0.4-rc1", output_dir: str | Path | None = None) -> tuple[Path, Path]:
    input_path = Path(input_path)
    bundle_root, source_rows, performance, runs = _bundle(input_path)
    rows = _adapt_rows(source_rows)
    comparable = _comparable_performance(performance, runs)
    policy = load_policy(policy_name)
    old_path = _legacy_v03_verdict_path(input_path)
    old = {row["run_id"]: row for row in _read(old_path)} if old_path.exists() else {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["run_id"], []).append(row)
    output_dir = Path(output_dir) if output_dir else ROOT / "results/v0.4-rc1/derived"
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir = output_dir.parent / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    grader_identity = {"path": "common/grader_basic.py", "sha256": _sha(ROOT / "common/grader_basic.py"), "version": "v2"}
    for row in rows:
        row["schema_version"] = "normalized-corpus-v0.2"
        row["record_type"] = "task_result"
        row["grader_identity"] = grader_identity
        legacy_provenance = row.get("provenance")
        row["provenance"] = {"kind": "derived", "source": str(input_path), "method": "v0.3 observation + v2 grader + explicit fixture metadata", "legacy": legacy_provenance}
    (normalized_dir / "task_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    result = []
    for run_id in sorted(grouped):
        new = evaluate_run(grouped[run_id], policy)
        previous = old.get(run_id, {})
        changed = []
        for name, gate in new["gates"].items():
            if gate.get("pass") != previous.get("gates", {}).get(name, {}).get("pass"):
                changed.append(name)
        observed = comparable.get(run_id, [])
        mean = statistics.mean([x["value"] for x in observed]) if observed else None
        result.append({"schema_version": "normalized-corpus-v0.2", "record_type": "verdict", "run_id": run_id, "policy_version": policy.policy_version, "gates": new["gates"], "original_v0_3_verdict": previous, "policy_verdict": new, **({"v0_4_rc1_verdict": new} if policy.policy_version == "YLSB-v0.4-rc1" else {}), "changed_reason": changed or ["policy dimensions unchanged"], "observed_comparable_performance": {"metric": "TG", "target_tokens": 128, "depth_tokens": 0, "lane": "R0", "phase": "original_run", "aggregation": "mean", "samples": observed, "mean_tokens_per_second": mean, "sample_count": len(observed), "slot_status": "candidate_only_until_observed_gate_pass", "source_corpus": str(bundle_root)}, "source_observation": str(input_path), "provenance": {"kind": "derived", "method": "v2 grader + explicit fixture metadata + deterministic policy engine", "source": str(input_path)}})
    slug = policy.policy_version.lower().replace("ylsb-", "")
    jsonl = output_dir / f"{slug}-regrade.jsonl"
    lines = [f"# {policy.policy_version} regrade", "", f"Same observations were evaluated with versioned {policy.policy_version}. Raw/frozen inputs and prior verdicts are unchanged.", "", f"| run | prior Smallest | {policy.policy_version} Smallest | prior Fastest | {policy.policy_version} Fastest | change |", "|---|---:|---:|---:|---:|---|"]
    for row in result:
        oldg, newg = row["original_v0_3_verdict"].get("gates", {}), row["policy_verdict"]["gates"]
        lines.append(f"| {row['run_id']} | {oldg.get('smallest_meaningful', {}).get('pass')} | {newg.get('smallest_meaningful', {}).get('pass')} | {oldg.get('fastest_useful', {}).get('pass')} | {newg.get('fastest_useful', {}).get('pass')} | {', '.join(row['changed_reason'])} |")
    eligible = [row for row in result if row["policy_verdict"]["gates"].get("fastest_useful", {}).get("pass") and row["observed_comparable_performance"].get("mean_tokens_per_second") is not None]
    lines += ["", "## Observed Fastest Useful comparison", "", "Selection uses only passing candidates and supplied original R0 TG128 observations; planner predictions are excluded.", "", "| run | gate pass | mean original TG tok/s | measurement phase |", "|---|---:|---:|---|"]
    for row in result:
        perf = row["observed_comparable_performance"]
        lines.append(f"| {row['run_id']} | {row['policy_verdict']['gates'].get('fastest_useful', {}).get('pass')} | {perf.get('mean_tokens_per_second')} | {perf.get('phase')} |")
    if eligible:
        fastest = max(eligible, key=lambda row: row["observed_comparable_performance"]["mean_tokens_per_second"])
        selection = {"run_id": fastest["run_id"], "metric": "TG", "target_tokens": 128, "depth_tokens": 0, "lane": "R0", "phase": "original_run", "aggregation": "mean", "mean_tokens_per_second": fastest["observed_comparable_performance"]["mean_tokens_per_second"]}
        for row in result:
            row["fastest_useful_selection"] = selection
        lines += ["", f"Selected Fastest Useful candidate: `{fastest['run_id']}` at {selection['mean_tokens_per_second']} tok/s (R0 TG128@d0 original_run, mean)."]
    jsonl.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result), encoding="utf-8")
    md = output_dir / f"{slug}-regrade.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jsonl, md


def calibration(input_path: str | Path) -> str:
    input_path = Path(input_path)
    bundle_root, source_rows, performance, runs = _bundle(input_path)
    rows = _adapt_rows(source_rows)
    policy = load_policy("YLSB-v0.4-rc1")
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["run_id"], []).append(row)
    comparable = _comparable_performance(performance, runs)
    run_context = {row.get("run_id"): (row.get("config", {}).get("ctx") or row.get("config", {}).get("ctx_size")) for row in runs}
    old_path = _legacy_v03_verdict_path(input_path)
    old = {row["run_id"]: row for row in _read(old_path)} if old_path.exists() else {}
    verdicts = {run_id: evaluate_run(items, policy) for run_id, items in groups.items()}
    lines = [
        "# YLSB v0.4-rc1 calibration",
        "",
        "これは release candidate の校正結果であり、恒久 threshold の確定ではない。",
        f"入力 bundle: `{bundle_root}`。v0.3 の観測値を v2 grader と明示 fixture metadata で再評価した。",
        "",
        "## 校正で確認する変更点",
        "- Core 28 / Hard Sentinel 4 / API smoke 10 を fixture metadata の tier と gate role で集計する。",
        "- answer correctness、strict format、non-empty、protocol、serving health を別の次元として保持する。",
        "- requires_rerun は capability 分母から除外するが、health と raw flag には残す。",
        "- v0.3 の source fixture identity と v0.4 grader/fixture identity は別フィールドで保持する。",
        "",
        "## Raw protocol flags",
        "",
        "空応答は capability failure に置換せず、invalid fixture と分けて集計する。",
        "",
        "| run | empty quality rows | requires_rerun | empty/invalid overlap | serving invalid |",
        "|---|---:|---:|---:|---:|",
    ]
    for run_id, items in sorted(groups.items()):
        empty = [x for x in items if x.get("non_empty") is False]
        rerun = [x for x in items if x.get("reuse", {}).get("classification") == "requires_rerun"]
        invalid_empty = [x for x in items if x.get("reuse", {}).get("classification") == "invalid" and x.get("non_empty") is False]
        serving_invalid = sum(x.get("serving_valid") is False for x in items)
        lines.append(f"| {run_id} | {len(empty)} | {len(rerun)} | {len(invalid_empty)} | {serving_invalid} |")

    cases = load_core_v04() + load_sentinel_v04()
    tier_counts = {tier: sum(1 for row in cases if row.get("tier") == tier) for tier in ("essential", "practical", "discriminator")}
    lines += [
        "",
        "## Tier distribution",
        "",
        f"Essential {tier_counts['essential']} / Practical {tier_counts['practical']} / Discriminator {tier_counts['discriminator']}。Core 28 と Hard Sentinel 4 の metadata を直接読んだ値である。",
        "",
        "## 6モデルの実測結果",
        "",
        "accuracy は requires_rerun と FIXTURE_INVALID を除いた capability 分母、Sentinel は semantic correct/strict format、TG は入力 performance の同一 phase/point/lane/context の repeat 平均である。",
        "",
        "| model/run | v0.3 Smallest | v0.4 Smallest | v0.3 Fastest | v0.4 Fastest | Essential accuracy | Sentinel semantic | Sentinel strict | empty | rerun | mean TG128 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run_id, items in sorted(groups.items()):
        stats = verdicts[run_id]["statistics"]
        sentinel_rows = [x for x in items if x.get("section") == "sentinel"]
        oldg = old.get(run_id, {}).get("gates", {})
        mean = statistics.mean([x["value"] for x in comparable.get(run_id, [])]) if comparable.get(run_id) else None
        model = run_id.removeprefix("run-v03-ume-")
        lines.append("| {} | {} | {} | {} | {} | {:.1%} ({}/{}) | {}/{} | {}/{} | {} | {} | {} |".format(
            model,
            oldg.get("smallest_meaningful", {}).get("pass", "unknown"),
            verdicts[run_id]["gates"].get("smallest_meaningful", {}).get("pass"),
            oldg.get("fastest_useful", {}).get("pass", "unknown"),
            verdicts[run_id]["gates"].get("fastest_useful", {}).get("pass"),
            stats["essential"]["accuracy"], stats["essential"]["correct"], stats["essential"]["attempts"],
            sum(bool(x.get("answer_correct")) for x in sentinel_rows), len(sentinel_rows),
            sum(bool(x.get("format_correct")) for x in sentinel_rows), len(sentinel_rows),
            sum(x.get("non_empty") is False for x in items),
            sum(x.get("reuse", {}).get("classification") == "requires_rerun" for x in items),
            mean if mean is not None else "unknown",
        ))

    lines += ["", "## H03 semantic / strict audit", "", "以下は入力された6モデルの H03 行から計算した値で、固定文言や手入力の performance 値ではない。", "", "| model/run | semantic correct | strict format |", "|---|---:|---:|"]
    for run_id, items in sorted(groups.items()):
        h03 = [x for x in items if x.get("task_id") == "H03"]
        lines.append(f"| {run_id.removeprefix('run-v03-ume-')} | {sum(bool(x.get('answer_correct')) for x in h03)}/{len(h03)} | {sum(bool(x.get('format_correct')) for x in h03)}/{len(h03)} |")

    lines += ["", "## Threshold sensitivity", "", "| run | " + " | ".join(f"{v['essential_min']:.0%}" for v in threshold_sensitivity(next(iter(groups.values()), []), policy)) + " |", "|---|" + "---:|" * len(policy.data.get("threshold_sensitivity", {}).get("essential_min", []))]
    for run_id, items in sorted(groups.items()):
        sens = threshold_sensitivity(items, policy)
        lines.append(f"| {run_id} | " + " | ".join("Y" if x["smallest_meaningful"]["pass"] else "N" for x in sens) + " |")

    eligible = [(run_id, statistics.mean([x["value"] for x in comparable[run_id]])) for run_id in groups if verdicts[run_id]["gates"].get("fastest_useful", {}).get("pass") and comparable.get(run_id)]
    lines += ["", "## Comparable performance / Fastest Useful", "", "performance row に context がないため、表の context は run.config.ctx の監査表示である。比較キーに未報告値を推測で埋めず、formal slot は同一 context が明記された追加測定で確認する。", "", "| run | observed mean TG128 | samples | phase | lane | context |", "|---|---:|---:|---|---|---|"]
    for run_id, items in sorted(groups.items()):
        samples = comparable.get(run_id, [])
        mean = statistics.mean([x["value"] for x in samples]) if samples else None
        sample = samples[0] if samples else {}
        context = sample.get("context_tokens") if sample.get("context_tokens") is not None else run_context.get(run_id, "unknown")
        lines.append(f"| {run_id} | {mean if mean is not None else 'unknown'} | {len(samples)} | {sample.get('measurement_phase', 'unknown')} | {sample.get('lane', 'unknown')} | {context if context is not None else 'unknown'} |")
    if eligible:
        fastest = max(eligible, key=lambda pair: pair[1])
        lines += ["", f"Fastest Useful 候補は `{fastest[0]}`（実測 mean TG128={fastest[1]}）である。formal slot として確定するには同一条件の追加測定が必要である。"]
    else:
        lines += ["", "Fastest Useful は gate pass と比較可能な実測が揃わないため、今回の入力では候補を選べない。"]

    lines += [
        "",
        "## First-wave interpretation and limits",
        "",
        "v0.3 の gate detail/label は historical policy で再計算し、v0.4 は同じ観測に対する tier/health/regrade の解釈として保存した。invalid fixture、欠損/duplicate の corpus 構造、protocol/serving 不良は正式 gate を通さない。",
        "threshold sensitivity は 60/70/80% の比較用であり恒久値ではない。最終化には別 hardware family、homogeneous multi-GPU、別 runtime、seed/template/VRAM を明記した rerun が必要である。",
    ]
    return "\n".join(lines) + "\n"
