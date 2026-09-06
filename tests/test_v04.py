import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from common.grader_basic import grade_v2
from ylsb_v04.fixtures import fixture_manifest, load_core_v04
from ylsb_v04.importer import SubmissionImporter
from ylsb_v04.planner import CandidatePlanner, estimate_model_fit
from ylsb_v04.policy.engine import Policy, evaluate_run, load_policy
from ylsb_v04.regrade import _adapt_rows
from ylsb_v04.schema import migrate_v03_record, validate_normalized_record, validate_run_record
from tests.test_rc2_schema import synthetic_formal_record

ROOT = Path(__file__).resolve().parents[1]


class V04Tests(unittest.TestCase):
    def test_v03_policy_reproduces_all_frozen_gate_objects(self):
        rows = [json.loads(line) for line in (ROOT / "results/v0.3/normalized/task_results.jsonl").read_text().splitlines() if line]
        policy = load_policy("YLSB-v0.3")
        for run_id in sorted({r["run_id"] for r in rows}):
            actual = evaluate_run([r for r in rows if r["run_id"] == run_id], policy)["gates"]
            alias = run_id.removeprefix("run-v03-ume-")
            expected = json.loads((ROOT / "results/v0.3/frozen/ume-first-wave-20260906/original/complete_reports" / alias / "summary.json").read_text())["gates"]
            self.assertEqual(expected, actual)

    def test_v04_fixture_is_explicit_and_corrected(self):
        cases = load_core_v04()
        self.assertEqual(28, len(cases))
        self.assertEqual("DCBAE", cases[14]["gold"])
        self.assertEqual("discriminator", cases[14]["tier"])
        self.assertIn("unique_solution", cases[14]["tags"])
        self.assertEqual(32, len(fixture_manifest()["fixtures"]))

    def test_grader_separates_semantics_and_format(self):
        case = {"id": "H03", "grader": "exact", "gold": "10:A-C-B-D-E", "format_pattern": r"^[0-9]+:[A-Za-z](?:-[A-Za-z])+$"}
        result = grade_v2(case, "10:A->C->B->D->E")
        self.assertTrue(result["answer_correct"])
        self.assertFalse(result["format_correct"])
        wrong_path = grade_v2({"id": "H03", "grader": "exact", "gold": "10:A-C-B-D-E", "format_pattern": r"^[0-9]+:[A-Za-z](?:-[A-Za-z])+$"}, "10:A-C-B-E")
        self.assertFalse(wrong_path["answer_correct"])
        self.assertTrue(wrong_path["format_correct"])
        ordinary = grade_v2({"id": "X", "grader": "exact", "gold": "A B"}, "AB")
        self.assertFalse(ordinary["answer_correct"])
        self.assertTrue(ordinary["format_correct"])
        choice = grade_v2({"grader": "choice", "gold": "B", "allowed_choices": ["A", "B", "C", "D"]}, "A")
        self.assertFalse(choice["answer_correct"])
        self.assertTrue(choice["format_correct"])

    def test_json_types_are_strict_and_whitespace_is_valid(self):
        case = {"grader": "json_exact", "gold": {"ok": True}}
        self.assertTrue(grade_v2(case, '{ "ok": true }')["answer_correct"])
        self.assertFalse(grade_v2(case, '{"ok": 1}')["answer_correct"])
        self.assertTrue(grade_v2({"grader": "json_exact", "gold": {"ok": 1}}, '{"ok": 2}') ["format_correct"])
        self.assertFalse(grade_v2(case, '{"other": 1}')["format_correct"])

    def test_numeric_decimal_and_serving_taxonomy(self):
        case = {"grader": "numeric_exact", "gold": 9007199254740993}
        self.assertTrue(grade_v2(case, "9007199254740993")["answer_correct"])
        self.assertFalse(grade_v2(case, "9007199254740992")["answer_correct"])
        infra = grade_v2({"grader": "exact", "gold": "A"}, "A", serving_valid=False)
        self.assertEqual("INFRA", infra["status"])
        self.assertTrue(infra["requires_rerun"])
        empty = grade_v2({"grader": "exact", "gold": "A"}, "", serving_valid=True)
        self.assertTrue(empty["serving_valid"])
        self.assertEqual("PROTOCOL", empty["status"])

    def test_empty_is_protocol_rerun(self):
        result = grade_v2({"grader": "exact", "gold": "A"}, "")
        self.assertFalse(result["answer_correct"])
        self.assertEqual("PROTOCOL", result["status"])
        self.assertTrue(result["requires_rerun"])

    def test_sentinel_zero_is_not_a_usefulness_gate(self):
        rows = [{"section": "core", "category": "arithmetic", "tier": "essential", "score": 1, "format_ok": True, "non_empty": True}, {"section": "sentinel", "score": 0, "format_ok": True, "non_empty": True}]
        policy = load_policy("YLSB-v0.4-rc1")
        data = dict(policy.data, gates={name: dict(cfg, fixture_expectations={}) for name, cfg in policy.gates.items()})
        verdict = evaluate_run(rows, Policy(policy.policy_version, data))
        self.assertTrue(verdict["gates"]["smallest_meaningful"]["pass"])

    def test_gpt_sentinel_semantic_four_strict_three_and_identity_split(self):
        raw = []
        for line in (ROOT / "results/v0.3/frozen/ume-first-wave-20260906/original/complete_reports/gpt-oss-20b/raw.jsonl").read_text().splitlines():
            row = json.loads(line)
            if row.get("section") == "sentinel":
                raw.append({"run_id": "gpt", "task_id": row["id"], "section": "sentinel", "fixture_version": "v0.3", "model_output": row.get("raw_content", ""), "non_empty": row.get("non_empty"), "http_status": row.get("http_status")})
        adapted = _adapt_rows(raw)
        self.assertEqual(4, sum(row["answer_correct"] for row in adapted))
        self.assertEqual(3, sum(row["format_correct"] for row in adapted))
        self.assertEqual("v0.3", adapted[0]["fixture"]["fixture_version"])
        self.assertEqual("v0.4-rc1", adapted[0]["fixture_v04"]["fixture_version"])

    def test_v04_input_uses_corrected_fixture_and_preserves_health_flags(self):
        adapted = _adapt_rows([{"run_id": "v04", "task_id": "CORE-CONSTRAINT-003", "section": "core", "fixture_version": "v0.4-rc1", "model_output": "DCBAE", "http_status": 200}])
        self.assertEqual(1, len(adapted))
        self.assertTrue(adapted[0]["answer_correct"])
        self.assertNotEqual("FIXTURE_INVALID", adapted[0]["failure_class_audited"])
        flagged = _adapt_rows([{"run_id": "v04", "task_id": "H01", "section": "sentinel", "fixture_version": "v0.4-rc1", "model_output": "362", "http_status": 200, "protocol_valid": False, "serving_valid": False}])[0]
        self.assertFalse(flagged["protocol_valid"])
        self.assertFalse(flagged["serving_valid"])
        self.assertEqual("INFRA", flagged["failure_class_audited"])

    def test_missing_tier_metadata_cannot_pass_v04_gate(self):
        policy = load_policy("YLSB-v0.4-rc1")
        rows = [{"section": "core", "score": 1, "format_ok": True, "non_empty": True}] * 28 + [{"section": "sentinel", "score": 1, "format_ok": True, "non_empty": True}] * 4 + [{"section": "api_smoke", "score": 1, "format_ok": True, "non_empty": True}] * 10
        verdict = evaluate_run(rows, policy)
        self.assertFalse(verdict["gates"]["smallest_meaningful"]["pass"])
        self.assertGreater(verdict["statistics"]["metadata_unknown"], 0)

    def test_planner_is_deterministic_and_separates_objectives(self):
        hardware = {"gpu_groups": [{"canonical_id": "g", "reported_name": "GPU", "count": 2, "vram_gib_each": 16, "architecture": "Pascal"}]}
        models = [{"canonical_id": "m4", "reported_name": "M4", "format": "GGUF", "quant": "Q4_K_M", "bpw": 4.5, "architecture": {"type": "dense", "total_params_b": 4.0, "active_params_b": 4.0}}]
        runtimes = [{"canonical_id": "r", "name": "llama.cpp", "supported_formats": ["GGUF"], "architectures": ["Pascal"]}]
        first = CandidatePlanner(hardware, models, runtimes).plan()
        second = CandidatePlanner(hardware, models, runtimes).plan()
        self.assertEqual(first, second)
        self.assertEqual("anchor", first["anchor"]["objective"])
        self.assertEqual("envelope", first["envelope"][0]["objective"])
        self.assertFalse(first["training_labels_used"])
        self.assertEqual("predicted", first["meaningful_window"]["sweet_spot"]["prediction_status"])

    def test_import_duplicate_and_absolute_path_independence(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as out_dir:
            source = Path(source_dir) / "submission.jsonl"
            source.write_text('{"record_type":"run","model_id":"m","hardware_id":"h","provenance":{"kind":"reported"}}\n')
            importer = SubmissionImporter(out_dir)
            first = importer.import_submission(source)
            second = importer.import_submission(source)
            self.assertFalse(first.duplicate)
            self.assertTrue(second.duplicate)

    def test_schema_v2_provenance_and_migration(self):
        migrated = migrate_v03_record({"task_id": "X", "answer": "A"})
        self.assertEqual("normalized-corpus-v0.2", migrated["schema_version"])
        self.assertEqual([], validate_normalized_record(migrated))
        # Use the complete formal synthetic record used by the RC2 schema tests.
        valid = synthetic_formal_record()
        self.assertEqual([], validate_run_record(valid))
        self.assertTrue(validate_run_record({"schema_version": 2, "run_id": "r", "hardware": {"cpu": {}, "ram": {}, "gpu_groups": [{"provenance": {}}]}, "runtime": {}, "model": {}}))

    def test_unknown_registry_and_runtime_rejection(self):
        from ylsb_v04.registry import load_registry
        unknown = load_registry("hardware").resolve("unreported GPU")
        self.assertIsNone(unknown["canonical_id"])
        self.assertEqual("unknown", unknown["provenance"]["kind"])
        hardware = {"gpu_groups": [{"reported_name": "NVIDIA GeForce RTX 3060", "count": 1, "vram_gib_each": 12, "architecture": "Ampere"}, {"reported_name": "Tesla P100-PCIE-16GB", "count": 1, "vram_gib_each": 16, "architecture": "Pascal"}]}
        model = {"canonical_id": "m", "reported_name": "m", "format": "GGUF", "bpw": 4, "architecture": {"type": "dense", "total_params_b": 4}}
        planner = CandidatePlanner(hardware, [model], [{"canonical_id": "vllm", "name": "vLLM", "supported_formats": ["GGUF"], "architectures": ["Ampere"]}]).plan()
        self.assertEqual("reject", planner["candidates"][0]["runtime"][0]["compatibility"])

    def test_adaptive_boundary_and_cpu_offload_are_constrained(self):
        hardware = {"gpu_groups": [{"vram_gib_each": 1, "count": 1}], "ram": {"total_gib": 2}}
        model = {"bpw": 8, "architecture": {"type": "dense", "total_params_b": 10}}
        fit = estimate_model_fit(hardware, model, cpu_offload=True)
        self.assertFalse(fit["fits"])
        models = [{"model": "small", "size_class_b": 4}, {"model": "mid", "size_class_b": 8}, {"model": "large", "size_class_b": 12}]
        plan = {"candidates": models, "envelope": models}
        from ylsb_v04.planner import next_benchmark_candidate
        self.assertEqual("mid", next_benchmark_candidate(plan, [{"model": "small", "size_class_b": 4, "status": "fit"}, {"model": "large", "size_class_b": 12, "status": "oom"}])["model"])

    def test_frozen_tree_hash_unchanged_after_v04_operations(self):
        import subprocess, sys
        frozen = ROOT / "results/v0.3/frozen"
        before = {p.relative_to(frozen).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen.rglob("*") if p.is_file()}
        subprocess.run([sys.executable, str(ROOT / "tools/ylsb.py"), "validate-fixtures"], check=True, capture_output=True)
        subprocess.run([sys.executable, str(ROOT / "tools/ylsb.py"), "regrade", "--input", str(ROOT / "results/v0.3/normalized/task_results.jsonl"), "--output-dir", "/tmp/ylsb-v04-test-results"], check=True, capture_output=True)
        after = {p.relative_to(frozen).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_permanent_v03_baseline_hashes(self):
        baseline = json.loads((ROOT / "fixtures/v0.3-baseline-hashes.json").read_text())
        protected = [path for path in baseline if path.startswith("results/v0.3/") or path in {"common/run_record.schema.json", "ume/profile.json", "take/profile.json", "matsu/profile.json"} or "/tests/" in path]
        self.assertGreaterEqual(len(protected), 80)
        for relative in protected:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(baseline[relative], hashlib.sha256(path.read_bytes()).hexdigest(), relative)


if __name__ == "__main__":
    unittest.main()
