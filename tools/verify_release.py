#!/usr/bin/env python3
"""Run the read-only release verification harness and write evidence.

The harness can live in one checkout while ``--repo`` points at another
checkout (for example, a detached release tag).  The report keeps the
harness and target commit identities separate for that use case.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence
import xml.etree.ElementTree as ET
import re


SCRIPT = Path(__file__).resolve()
HARNESS_DEFAULT = SCRIPT.parents[1]


@dataclass
class CheckResult:
    name: str
    command: list[str]
    returncode: int
    duration_seconds: float
    stdout: str = ""
    stderr: str = ""

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git command failed: {' '.join(args)}")
    return result.stdout.strip()


def _git_sha(repo: Path) -> str | None:
    try:
        return _git(repo, "rev-parse", "HEAD")
    except (OSError, RuntimeError):
        return None


def _status(repo: Path) -> dict[str, Any]:
    try:
        porcelain = _git(repo, "status", "--porcelain=v1")
        unstaged = _git(repo, "diff", "--name-only")
        staged = _git(repo, "diff", "--cached", "--name-only")
        return {
            "porcelain": porcelain.splitlines(),
            "tracked_unstaged": unstaged.splitlines(),
            "tracked_staged": staged.splitlines(),
            "tracked_dirty": bool(unstaged or staged),
            "dirty": bool(porcelain),
        }
    except (OSError, RuntimeError) as exc:
        return {"porcelain": [], "tracked_unstaged": [], "tracked_staged": [], "tracked_dirty": True, "dirty": True, "error": str(exc)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tool_hashes(repo: Path, harness: Path) -> dict[str, Any]:
    target_paths = [
        repo / "tools/regenerate_v04.py",
        repo / "common/grader_basic.py",
        repo / "schema/normalized-corpus-v0.2.schema.json",
        repo / "schema/run-record-v0.2.schema.json",
    ]
    target = {}
    for path in target_paths:
        if path.is_file():
            target[str(path.relative_to(repo))] = _sha256(path)
    harness_path = harness / "tools/verify_release.py"
    return {
        "target": target,
        "harness": {"tools/verify_release.py": _sha256(harness_path)} if harness_path.is_file() else {},
    }


def _dependency_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in ("jsonschema",):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _workflow_context() -> dict[str, str | None]:
    """Record only non-secret GitHub context needed to link evidence."""
    repository = os.environ.get("GITHUB_REPOSITORY")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID")
    return {
        "repository": repository,
        "run_id": run_id,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "run_url": f"{server}/{repository}/actions/runs/{run_id}" if repository and run_id else None,
        "workflow": os.environ.get("GITHUB_WORKFLOW"),
        "ref": os.environ.get("GITHUB_REF"),
        "sha": os.environ.get("GITHUB_SHA"),
    }


def _unit_test_summary(check: CheckResult) -> dict[str, Any]:
    text = f"{check.stdout}\n{check.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", text)
    return {
        "count": int(match.group(1)) if match else None,
        "verbose": "-v" in check.command,
        "passed": check.passed,
        "returncode": check.returncode,
    }


def _protected_baseline_check(repo: Path) -> tuple[bool, list[str], dict[str, str], list[str]]:
    baseline_path = repo / "fixtures/v0.3-baseline-hashes.json"
    if not baseline_path.is_file():
        return False, [f"missing {baseline_path.relative_to(repo)}"], {}, []
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, [f"cannot read baseline: {exc}"], {}, []
    # This is intentionally the same immutable subset used by
    # tests/test_v04.py.  The baseline file also contains mutable documentation
    # and implementation files, which must not block a release verification.
    selected = {
        relative for relative in baseline
        if relative.startswith("results/v0.3/")
        or relative in {"common/run_record.schema.json", "ume/profile.json", "take/profile.json", "matsu/profile.json"}
        or "/tests/" in relative
    }
    excluded = sorted(set(baseline) - selected)
    failures: list[str] = []
    actual: dict[str, str] = {}
    for relative in sorted(selected):
        expected = baseline[relative]
        path = repo / relative
        if not path.is_file():
            failures.append(f"missing protected file: {relative}")
            continue
        value = _sha256(path)
        actual[relative] = value
        if value != expected:
            failures.append(f"hash mismatch: {relative}")
    return not failures, failures, actual, excluded


def _run_command(name: str, command: Sequence[str], repo: Path) -> CheckResult:
    started = time.monotonic()
    try:
        result = subprocess.run(
            list(command),
            cwd=str(repo),
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return CheckResult(name, list(command), result.returncode, time.monotonic() - started, result.stdout, result.stderr)
    except OSError as exc:
        return CheckResult(name, list(command), 127, time.monotonic() - started, "", str(exc))


def _local_check(name: str, passed: bool, detail: str = "") -> CheckResult:
    return CheckResult(name, [name], 0 if passed else 1, 0.0, detail if passed else "", "" if passed else detail)


def _write_junit(path: Path, checks: Sequence[CheckResult]) -> None:
    suite = ET.Element("testsuite", {
        "name": "ylsb-release-verification",
        "tests": str(len(checks)),
        "failures": str(sum(not check.passed for check in checks)),
        "time": f"{sum(check.duration_seconds for check in checks):.6f}",
    })
    for check in checks:
        case = ET.SubElement(suite, "testcase", {
            "name": check.name,
            "time": f"{check.duration_seconds:.6f}",
        })
        if not check.passed:
            failure = ET.SubElement(case, "failure", {"message": f"exit {check.returncode}"})
            failure.text = (check.stderr or check.stdout or "check failed")[-12000:]
        output = ET.SubElement(case, "system-out")
        output.text = check.stdout[-12000:]
        if check.stderr:
            error = ET.SubElement(case, "system-err")
            error.text = check.stderr[-12000:]
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def _write_log(path: Path, checks: Sequence[CheckResult]) -> None:
    chunks = []
    for check in checks:
        chunks.append(f"## {check.name}\n$ {' '.join(check.command)}\n")
        chunks.append(check.stdout)
        if check.stderr:
            chunks.append("\n[stderr]\n" + check.stderr)
        chunks.append(f"\n[exit={check.returncode} duration={check.duration_seconds:.3f}s]\n")
    path.write_text("\n".join(chunks), encoding="utf-8")


def verify(repo: Path, harness: Path, output: Path) -> dict[str, Any]:
    repo = repo.resolve()
    harness = harness.resolve()
    output.mkdir(parents=True, exist_ok=True)
    checks: list[CheckResult] = []

    before_target_status = _status(repo)
    before_harness_status = _status(harness)
    before_ok = not before_target_status.get("dirty", True) and not before_harness_status.get("dirty", True)
    checks.append(_local_check(
        "target and harness clean before checks",
        before_ok,
        json.dumps({"target": before_target_status, "harness": before_harness_status}, ensure_ascii=False),
    ))
    baseline_ok, baseline_failures, baseline_actual, excluded_baseline = _protected_baseline_check(repo)
    checks.append(_local_check("v0.3 protected baseline before checks", baseline_ok, "\n".join(baseline_failures) or f"{len(baseline_actual)} protected hashes verified"))

    python = sys.executable
    unittest_check = _run_command(
        "unittest discover",
        [python, "-m", "unittest", "discover", "-v", "-s", "tests", "-p", "test*.py"],
        repo,
    )
    checks.append(unittest_check)
    checks.append(_run_command(
        "regenerate --check",
        [python, "tools/regenerate_v04.py", "--check"],
        repo,
    ))

    after_target_status = _status(repo)
    after_harness_status = _status(harness)
    after_ok = not after_target_status.get("dirty", True) and not after_harness_status.get("dirty", True)
    checks.append(_local_check(
        "target and harness clean after checks",
        after_ok,
        json.dumps({"target": after_target_status, "harness": after_harness_status}, ensure_ascii=False),
    ))
    baseline_after_ok, baseline_after_failures, baseline_after_actual, _ = _protected_baseline_check(repo)
    checks.append(_local_check("v0.3 protected baseline after checks", baseline_after_ok, "\n".join(baseline_after_failures) or f"{len(baseline_after_actual)} protected hashes verified"))

    target_sha = _git_sha(repo)
    harness_sha = _git_sha(harness)
    summary: dict[str, Any] = {
        "verification": "YLSB release verification",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target": {"repo": str(repo), "sha": target_sha, "status_before": before_target_status, "status": after_target_status},
        "harness": {"repo": str(harness), "sha": harness_sha, "status_before": before_harness_status, "status": after_harness_status},
        "source_sha": {"harness": harness_sha, "target": target_sha},
        "workflow": _workflow_context(),
        "python": {"executable": python, "version": sys.version, "implementation": sys.implementation.name},
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "platform": platform.platform()},
        "dependencies": _dependency_versions(),
        "tool_hashes": _tool_hashes(repo, harness),
        "protected_baseline": {
            "path": "fixtures/v0.3-baseline-hashes.json",
            "files": len(baseline_actual),
            "selected_rule": "results/v0.3/** plus immutable course profiles, common/run_record.schema.json, and */tests/*; same subset as tests/test_v04.py",
            "excluded_files": excluded_baseline,
            "excluded_reason": "baseline entries outside the immutable v0.3 protected subset are mutable documentation or implementation files",
            "before_passed": baseline_ok,
            "after_passed": baseline_after_ok,
            "failures": baseline_failures + baseline_after_failures,
        },
        "checks": [asdict(check) | {"passed": check.passed} for check in checks],
        "unit_tests": _unit_test_summary(unittest_check),
        "passed": all(check.passed for check in checks),
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_log(output / "verification.log", checks)
    (output / "test.log").write_text((output / "verification.log").read_text(encoding="utf-8"), encoding="utf-8")
    _write_junit(output / "junit.xml", checks)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verify_release")
    parser.add_argument("--repo", default=".", help="target checkout to verify")
    parser.add_argument("--harness-repo", default=str(HARNESS_DEFAULT), help="checkout providing this harness; used for source identity")
    parser.add_argument("--output-dir", default=None, help="temporary directory for summary.json, test.log, and junit.xml")
    args = parser.parse_args(argv)
    output = Path(args.output_dir).resolve() if args.output_dir else Path(tempfile.mkdtemp(prefix="ylsb-release-verification-"))
    output.mkdir(parents=True, exist_ok=True)
    try:
        summary = verify(Path(args.repo), Path(args.harness_repo), output)
    except Exception as exc:  # Keep a machine-readable artifact for setup failures too.
        failure = {
            "verification": "YLSB release verification",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        (output / "summary.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "test.log").write_text(failure["error"] + "\n", encoding="utf-8")
        _write_junit(output / "junit.xml", [CheckResult("harness setup", [SCRIPT.name], 2, 0.0, "", failure["error"])])
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 2
    print(f"verification {'passed' if summary['passed'] else 'failed'}: {output}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
