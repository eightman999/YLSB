#!/usr/bin/env python3
"""Deterministically regenerate the v0.4 release-candidate evidence.

The v0.3 normalized corpus and frozen observations are inputs.  This command
never edits them.  It builds a complete output tree in a temporary directory,
then replaces the requested generated tree atomically.  ``--check`` performs
the same build and compares it with the checked-in tree without modifying it.

The generated manifest records content identities instead of a current commit
or generation timestamp.  Consequently committing the generated tree does not
make the next invocation drift merely because HEAD changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ylsb_v04.fixtures import validate_v04_fixtures
from ylsb_v04.planner import CandidatePlanner, load_candidate_catalog
from ylsb_v04.registry import load_registry
from ylsb_v04.regrade import calibration, regrade
from ylsb_v04.schema import migrate_directory, validate_normalized_record

DEFAULT_OUTPUT = ROOT / "results/v0.4-rc1"
V03_INPUT = ROOT / "results/v0.3/normalized"
POLICY = ROOT / "policies/ylsb-v0.4-rc1.json"
GRADER = ROOT / "common/grader_basic.py"
NORMALIZED_SCHEMA = ROOT / "schema/normalized-corpus-v0.2.schema.json"
RUN_SCHEMA = ROOT / "schema/run-record-v0.2.schema.json"
RUN_SCHEMA_MIRROR = ROOT / "common/run_record.schema.v2.json"

GENERATOR_VERSION = "ylsb-v0.4-regenerator-1"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _tree_sha(path: Path, *, include: Iterable[str] | None = None) -> str:
    """Hash a directory by relative path and bytes, independent of mtime."""
    names = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            rel = item.relative_to(path).as_posix()
            # Bytecode is an interpreter/worktree by-product, never a source
            # identity.  Ignore it so the manifest is stable after test runs.
            if "__pycache__" in item.parts or item.suffix == ".pyc":
                continue
            if include is None or rel in include:
                names.append((rel, item))
    digest = hashlib.sha256()
    for rel, item in names:
        data = item.read_bytes()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _hardware_facts(normalized: Path) -> dict[str, Any]:
    hardware_rows = _jsonl(normalized / "hardware.jsonl")
    machine_rows = _jsonl(normalized / "machines.jsonl")
    groups = []
    for row in hardware_rows:
        groups.append({
            "canonical_id": row.get("canonical_name") or row.get("hardware_id"),
            "reported_name": row.get("reported_name"),
            "count": row.get("count") or 1,
            "vram_gib_each": row.get("vram_each_gb", row.get("vram_gib_each")),
            "architecture": row.get("architecture"),
            "compute_capability": row.get("compute_capability"),
            "memory_bandwidth_gbps": row.get("memory_bandwidth_gbps"),
        })
    machine = machine_rows[0] if machine_rows else {}
    ram = machine.get("ram") if isinstance(machine.get("ram"), dict) else {}
    return {
        "gpu_groups": groups,
        "ram": {"total_gib": ram.get("total_gb", ram.get("total_gib"))},
        "driver": machine.get("driver"),
        "machine_id": machine.get("machine_id"),
    }


def _planner_output(normalized: Path) -> dict[str, Any]:
    hardware = _hardware_facts(normalized)
    models = load_registry("models", ROOT / "registries/models.json").entries
    runtimes = load_registry("runtimes", ROOT / "registries/runtimes.json").entries
    result = CandidatePlanner(
        hardware,
        models,
        runtimes,
        corpus=normalized,
        candidate_catalog=load_candidate_catalog(),
    ).plan()
    result.update({
        "schema_version": "normalized-corpus-v0.2",
        "record_type": "planner",
        "provenance": {
            "kind": "derived",
            "source": "hardware facts + observed normalized corpus + registries + deterministic planner",
        },
        "prediction": {"status": "predicted"},
    })
    return _stable_paths(result)


def _stable_paths(value: Any) -> Any:
    """Make workspace-local provenance paths portable across checkouts."""
    if isinstance(value, str):
        root_text = ROOT.as_posix().rstrip("/") + "/"
        if value.startswith(root_text):
            return value[len(root_text):]
        return value
    if isinstance(value, list):
        return [_stable_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: _stable_paths(item) for key, item in value.items()}
    return value


def _validate_tree(normalized: Path, derived: Path | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    errors: list[str] = []
    paths = sorted(normalized.glob("*.jsonl"))
    if derived is not None:
        # Verdict JSONL is also normalized-corpus data; markdown and manifest
        # are checked through their generated hashes instead.
        paths.extend(sorted(derived.glob("*.jsonl")))
    for path in paths:
        count = 0
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            count += 1
            row = json.loads(line)
            errors.extend(f"{path.name}:{lineno}: {error}" for error in validate_normalized_record(row))
        counts[path.name] = count
    planner = normalized / "planner.json"
    if planner.exists():
        errors.extend(f"planner.json: {error}" for error in validate_normalized_record(_json(planner)))
        counts[planner.name] = 1
    if errors:
        raise RuntimeError("normalized corpus schema validation failed:\n" + "\n".join(errors[:20]))
    return counts


def _write_manifest(output: Path, *, normalized_counts: dict[str, int], fixture_report: dict[str, Any]) -> None:
    generated = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            rel = path.relative_to(output).as_posix()
            generated[rel] = {"sha256": _sha_file(path), "bytes": path.stat().st_size}
            if path.suffix == ".jsonl":
                generated[rel]["records"] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    manifest = {
        "schema_version": "normalized-corpus-v0.2",
        "release": "v0.4-rc1",
        "engine_release": "v0.4-rc2",
        "generator": {
            "version": GENERATOR_VERSION,
            "path": "tools/regenerate_v04.py",
            "sha256": _sha_file(ROOT / "tools/regenerate_v04.py"),
        },
        "evaluation_policy": {
            "name": "YLSB-v0.4-rc1",
            "path": "policies/ylsb-v0.4-rc1.json",
            "sha256": _sha_file(POLICY),
        },
        "immutable_inputs": {
            "v03_normalized": {"path": "results/v0.3/normalized", "tree_sha256": _tree_sha(V03_INPUT)},
            "v04_fixture": {"path": "fixtures/v0.4-rc1", "tree_sha256": _tree_sha(ROOT / "fixtures/v0.4-rc1")},
            "grader": {"path": "common/grader_basic.py", "sha256": _sha_file(GRADER)},
            "normalized_schema": {"path": "schema/normalized-corpus-v0.2.schema.json", "sha256": _sha_file(NORMALIZED_SCHEMA)},
            "run_record_schema": {"path": "schema/run-record-v0.2.schema.json", "sha256": _sha_file(RUN_SCHEMA)},
            "run_record_schema_mirror": {"path": "common/run_record.schema.v2.json", "sha256": _sha_file(RUN_SCHEMA_MIRROR)},
            "planner_sources": {"path": "ylsb_v04/planner", "tree_sha256": _tree_sha(ROOT / "ylsb_v04/planner")},
            "registry_sources": {"path": "registries", "tree_sha256": _tree_sha(ROOT / "registries")},
            "candidate_catalog": {"path": "registries/candidate_models.json", "sha256": _sha_file(ROOT / "registries/candidate_models.json")},
        },
        "fixture_counts": {"core": fixture_report["core_count"], "sentinel": fixture_report["sentinel_count"]},
        "normalized_record_counts": normalized_counts,
        "artifacts": generated,
        "provenance_note": "Current git HEAD and generated_at are intentionally omitted; content identities above are the freshness contract.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_generated_report(output: Path, counts: dict[str, int]) -> None:
    planner = _json(output / "normalized/planner.json")
    total = sum(value for key, value in counts.items() if key.endswith(".jsonl"))
    lines = [
        "# YLSB v0.4-rc2 generated implementation report",
        "",
        "このレポートは `tools/regenerate_v04.py` が生成した。評価 policy は `YLSB-v0.4-rc1`、engine release は `v0.4-rc2` である。",
        "",
        "## Generated checks",
        "",
        f"- normalized JSONL records: {total}",
        f"- planner candidates: {len(planner.get('candidates', []))}",
        f"- observed-registry candidates: {sum(item.get('registry_kind') == 'observed_registry' for item in planner.get('candidates', []))}",
        f"- candidate-catalog predictions: {sum(item.get('registry_kind') == 'candidate' for item in planner.get('candidates', []))}",
        "- normalized corpus, derived verdict, and planner JSON Schema errors: 0",
        "- generated-at/current-HEAD fields: intentionally omitted",
        "",
        "The manifest is the source of truth for artifact hashes, immutable input identities, and per-file record counts.",
    ]
    (output / "derived/v0.4-rc1-implementation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    normalized = output / "normalized"
    derived = output / "derived"
    # migrate_directory is pure with respect to its source tree.
    migrate_directory(V03_INPUT, normalized)
    regrade(V03_INPUT / "task_results.jsonl", "YLSB-v0.4-rc1", derived)
    (derived / "v0.4-rc1-calibration.md").write_text(calibration(V03_INPUT / "task_results.jsonl"), encoding="utf-8")
    (normalized / "planner.json").write_text(json.dumps(_planner_output(normalized), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    schema_dir = output / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(NORMALIZED_SCHEMA, schema_dir / NORMALIZED_SCHEMA.name)
    shutil.copyfile(RUN_SCHEMA, schema_dir / RUN_SCHEMA.name)
    fixture_report = validate_v04_fixtures()
    counts = _validate_tree(normalized, derived)
    _write_generated_report(output, counts)
    _write_manifest(output, normalized_counts=counts, fixture_report=fixture_report)


def _sync_run_schema_mirror(*, write: bool) -> None:
    same = RUN_SCHEMA.read_bytes() == RUN_SCHEMA_MIRROR.read_bytes()
    if same:
        return
    if write:
        shutil.copyfile(RUN_SCHEMA, RUN_SCHEMA_MIRROR)
        return
    raise RuntimeError("schema mirror drift: common/run_record.schema.v2.json differs from schema/run-record-v0.2.schema.json")


def _files_equal(left: Path, right: Path) -> tuple[bool, str]:
    left_files = {p.relative_to(left).as_posix() for p in left.rglob("*") if p.is_file()}
    right_files = {p.relative_to(right).as_posix() for p in right.rglob("*") if p.is_file()}
    if left_files != right_files:
        missing = sorted(left_files - right_files)
        extra = sorted(right_files - left_files)
        return False, f"file set differs (missing={missing[:3]}, extra={extra[:3]})"
    for rel in sorted(left_files):
        if left.joinpath(rel).read_bytes() != right.joinpath(rel).read_bytes():
            return False, f"content differs: {rel}"
    return True, ""


def regenerate(output: Path = DEFAULT_OUTPUT, *, check: bool = False) -> int:
    output = output.resolve()
    protected = {ROOT.resolve(), (ROOT / "results/v0.3").resolve(), V03_INPUT.resolve()}
    if output in protected:
        raise ValueError(f"refusing to replace protected input tree: {output}")
    if output == (ROOT / "results").resolve():
        raise ValueError(f"refusing to replace broad generated parent: {output}")
    if output.exists() and output != DEFAULT_OUTPUT.resolve():
        manifest = output / "manifest.json"
        valid_generated_tree = False
        if manifest.exists():
            try:
                value = json.loads(manifest.read_text(encoding="utf-8"))
                valid_generated_tree = (
                    value.get("generator", {}).get("path") == "tools/regenerate_v04.py"
                    and str(value.get("engine_release", "")).startswith("v0.4-rc")
                )
            except (OSError, ValueError, TypeError):
                valid_generated_tree = False
        if not valid_generated_tree:
            raise ValueError(f"refusing to replace an unrecognized existing tree: {output}")
    try:
        _sync_run_schema_mirror(write=not check)
    except RuntimeError as exc:
        if check:
            print(f"drift: {exc}", file=sys.stderr)
            return 1
        raise
    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=parent) as tmp:
        candidate = Path(tmp) / output.name
        _build(candidate)
        if check:
            if not output.exists():
                print(f"drift: generated output is missing: {output}", file=sys.stderr)
                return 1
            same, reason = _files_equal(candidate, output)
            if not same:
                print(f"drift: {reason}", file=sys.stderr)
                return 1
            print(f"fresh: {output}")
            return 0
        if output.exists():
            generated_files = {path.relative_to(candidate).as_posix() for path in candidate.rglob("*") if path.is_file()}
            existing_files = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
            unexpected = sorted(existing_files - generated_files)
            if unexpected:
                raise ValueError(
                    "refusing to replace generated tree containing unowned files: "
                    + ", ".join(unexpected[:5])
                )
        backup = None
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{output.name}.old.", dir=parent)) / output.name
            output.rename(backup)
        try:
            candidate.rename(output)
        except Exception:
            if backup and backup.exists():
                backup.rename(output)
            raise
        if backup:
            shutil.rmtree(backup.parent)
    print(f"generated: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="regenerate_v04")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true", help="build in a temporary directory and fail on drift")
    args = parser.parse_args(argv)
    return regenerate(Path(args.output_dir), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
