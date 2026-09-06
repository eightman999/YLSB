#!/usr/bin/env python3
"""YLSB v0.4-rc1 CLI: plan, import, regrade and report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ylsb_v04.fixtures import fixture_manifest, validate_v04_fixtures
from ylsb_v04.importer import RawReportError, RawReportImporter, SubmissionImporter
from ylsb_v04.registry import load_registry
from ylsb_v04.regrade import calibration, regrade
from ylsb_v04.schema import migrate_directory


def _json(path_or_text: str):
    path = Path(path_or_text)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else json.loads(path_or_text)


def _records(path: str | None):
    if not path:
        return []
    value = Path(path)
    if value.suffix == ".jsonl":
        return [json.loads(line) for line in value.read_text(encoding="utf-8").splitlines() if line.strip()]
    loaded = _json(path)
    return loaded if isinstance(loaded, list) else [loaded]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ylsb")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--hardware", required=True)
    plan.add_argument("--models", default=str(ROOT / "registries/models.json"))
    plan.add_argument("--runtimes", default=str(ROOT / "registries/runtimes.json"))
    plan.add_argument("--corpus", help="normalized v0.1/v0.2 corpus for nearest observed retrieval")
    plan.add_argument("--observed", help="JSON/JSONL benchmark outcomes used for adaptive next-candidate selection")
    plan.add_argument("--output")
    imp = sub.add_parser("import")
    imp.add_argument("source")
    imp.add_argument("--destination", default=str(ROOT / "results/v0.4-rc1/normalized/imported"))
    raw = sub.add_parser("import-raw", help="inventory or import a raw benchmark report bundle")
    raw.add_argument("source")
    raw.add_argument("--destination", default=str(ROOT / "results/v0.4-rc1/normalized/imported"))
    raw.add_argument("--adapter", default="v03-ume-report")
    raw.add_argument("--dry-run", action="store_true", help="report adapter inventory without writing records")
    rg = sub.add_parser("regrade")
    rg.add_argument("--input", required=True)
    rg.add_argument("--policy", default="YLSB-v0.4-rc1")
    rg.add_argument("--output-dir")
    report = sub.add_parser("report")
    report.add_argument("--input", default=str(ROOT / "results/v0.3/normalized/task_results.jsonl"))
    report.add_argument("--output", default=str(ROOT / "docs/v0.4-calibration.md"))
    regenerate = sub.add_parser("regenerate", help="deterministically regenerate v0.4 derived artifacts")
    regenerate.add_argument("--output-dir", default=str(ROOT / "results/v0.4-rc1"))
    regenerate.add_argument("--check", action="store_true", help="build temporary output and fail on drift")
    migrate = sub.add_parser("migrate")
    migrate.add_argument("--input-dir", "--input", dest="input_dir", default=str(ROOT / "results/v0.3/normalized"))
    migrate.add_argument("--output-dir", "--output", dest="output_dir", default=str(ROOT / "results/v0.4-rc1/normalized"))
    sub.add_parser("validate-fixtures")
    args = parser.parse_args(argv)
    if args.command == "plan":
        from ylsb_v04.planner import CandidatePlanner, load_candidate_catalog, next_benchmark_candidate
        hardware = _json(args.hardware)
        models = load_registry("models", args.models).entries
        runtimes = load_registry("runtimes", args.runtimes).entries
        result = CandidatePlanner(hardware, models, runtimes, corpus=args.corpus, candidate_catalog=load_candidate_catalog()).plan()
        result.update({"schema_version": "normalized-corpus-v0.2", "record_type": "planner", "provenance": {"kind": "derived", "source": "hardware facts + registry + deterministic planner heuristics"}, "prediction": {"status": "predicted"}})
        if result.get("envelope"):
            result["next_best_benchmark"] = next_benchmark_candidate(result, _records(args.observed))
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output: Path(args.output).write_text(output, encoding="utf-8")
        else: print(output, end="")
    elif args.command == "import":
        result = SubmissionImporter(args.destination).import_submission(args.source)
        print(json.dumps({"fingerprint": result.fingerprint, "duplicate": result.duplicate, "records": len(result.records), "reason": result.reason}, ensure_ascii=False))
    elif args.command == "import-raw":
        try:
            result = RawReportImporter(args.destination, adapter=args.adapter).import_raw(args.source, dry_run=args.dry_run)
        except RawReportError as exc:
            payload = {"error": str(exc)}
            if exc.diagnostic is not None:
                payload["inventory"] = exc.diagnostic.as_dict()
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
            return 2
        if args.dry_run:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            imported, inventory = result
            print(json.dumps({"fingerprint": imported.fingerprint, "duplicate": imported.duplicate, "records": len(imported.records), "reason": imported.reason, "inventory": inventory}, ensure_ascii=False))
    elif args.command == "regrade":
        paths = regrade(args.input, args.policy, args.output_dir)
        print(json.dumps({"jsonl": str(paths[0]), "markdown": str(paths[1])}, ensure_ascii=False))
    elif args.command == "report":
        Path(args.output).write_text(calibration(args.input), encoding="utf-8")
        print(args.output)
    elif args.command == "regenerate":
        from tools.regenerate_v04 import regenerate as regenerate_v04
        return regenerate_v04(Path(args.output_dir), check=args.check)
    elif args.command == "migrate":
        paths = migrate_directory(args.input_dir, args.output_dir)
        print(json.dumps({"schema_version": "normalized-corpus-v0.2", "files": [str(path) for path in paths]}, ensure_ascii=False))
    else:
        report = validate_v04_fixtures()
        print(json.dumps({"valid": True, "fixture_count": report["core_count"] + report["sentinel_count"], "constraint_audit": report["constraints"]}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main() or 0)
