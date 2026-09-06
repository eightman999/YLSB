import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/normalized_corpus/build_corpus.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_corpus", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def tree_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


class NormalizedCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.files, cls.context = cls.builder.build()
        cls.builder.validate_records(cls.files)

    def rows(self, name):
        payload = next(value for path, value in self.files.items() if path.endswith(name))
        return [json.loads(line) for line in payload.decode().splitlines()]

    def test_deterministic_output(self):
        again, _ = self.builder.build()
        self.assertEqual(self.files, again)

    def test_generator_does_not_modify_frozen_raw(self):
        before = tree_hashes(self.builder.RAW_ROOT)
        subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT, check=True, capture_output=True)
        self.assertEqual(before, tree_hashes(self.builder.RAW_ROOT))

    def test_unknowns_are_not_invented(self):
        machine = self.rows("machines.jsonl")[0]
        self.assertIsNone(machine["cpu"]["reported_name"])
        self.assertEqual(machine["provenance"]["/cpu"]["kind"], "unknown")
        for run in self.rows("runs.jsonl"):
            self.assertIsNone(run["config"]["seed"]["effective"])
            self.assertEqual(run["provenance"]["/config/seed/effective"]["kind"], "unknown")

    def test_exact_alias_registry_does_not_merge_distinct_entities(self):
        models = self.rows("models.jsonl")
        hardware = self.rows("hardware.jsonl")
        self.assertEqual(6, len({item["model_id"] for item in models}))
        self.assertEqual(6, len({item["canonical_name"] for item in models}))
        self.assertEqual(2, len({item["hardware_id"] for item in hardware}))

    def test_observations_and_verdicts_are_separate(self):
        for row in self.rows("task_results.jsonl") + self.rows("performance.jsonl"):
            self.assertNotIn("gates", row)
            self.assertNotIn("policy_version", row)
        for row in self.rows("v0.3_verdicts.jsonl"):
            self.assertEqual("YLSB-v0.3", row["policy_version"])

    def test_v03_verdicts_equal_frozen_summaries(self):
        for row in self.rows("v0.3_verdicts.jsonl"):
            alias = row["run_id"].removeprefix("run-v03-ume-")
            source = json.loads((self.builder.REPORTS / alias / "summary.json").read_text())
            self.assertEqual(source["gates"], row["gates"])

    def test_reuse_classification_is_reproducible(self):
        rows = self.rows("task_results.jsonl")
        invalid = [x for x in rows if x["reuse"]["classification"] == "invalid"]
        rerun = [x for x in rows if x["reuse"]["classification"] == "requires_rerun"]
        self.assertEqual(6, len(invalid))
        self.assertEqual({"CORE-CONSTRAINT-003"}, {x["task_id"] for x in invalid})
        self.assertEqual(15, len(rerun))
        self.assertTrue(all(x["run_id"].endswith("gpt-oss-20b") and not x["non_empty"] for x in rerun))

    def test_constraint_fixture_semantic_audit(self):
        audit = self.builder.fixture_constraint_audit()
        self.assertEqual(["DCBAE"], audit["CORE-CONSTRAINT-003"]["enumerated_solutions"])
        self.assertFalse(audit["CORE-CONSTRAINT-003"]["gold_valid"])
        self.assertTrue(all(audit[key]["gold_valid"] for key in audit if key != "CORE-CONSTRAINT-003"))


if __name__ == "__main__":
    unittest.main()
