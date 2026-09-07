import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.regenerate_v04 import regenerate
from ylsb_v04.schema import validate_normalized_record


class GeneratedReleaseTests(unittest.TestCase):
    def test_checked_in_release_is_fresh(self):
        root = Path(__file__).parents[1]
        self.assertEqual(0, regenerate(root / "results/v0.4-rc1", check=True))

    def test_generation_and_drift_check_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "rc2"
            self.assertEqual(0, regenerate(output))
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("v0.4-rc3", manifest["engine_release"])
            report = (output / "derived/v0.4-rc1-implementation-report.md").read_text(encoding="utf-8")
            expected_records = sum(value for key, value in manifest["normalized_record_counts"].items() if key.endswith(".jsonl"))
            self.assertIn(f"normalized JSONL records: {expected_records}", report)
            planner = json.loads((output / "normalized/planner.json").read_text(encoding="utf-8"))
            self.assertEqual([], validate_normalized_record(planner))
            self.assertEqual(0, regenerate(output, check=True))
            (output / "normalized/planner.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(1, regenerate(output, check=True))

    def test_existing_non_generated_tree_is_protected(self):
        root = Path(__file__).parents[1]
        with self.assertRaises(ValueError):
            regenerate(root / "fixtures/v0.4-rc1", check=True)

    def test_generated_tree_does_not_delete_imported_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "rc2"
            self.assertEqual(0, regenerate(output))
            imported = output / "normalized/imported/submission.jsonl"
            imported.parent.mkdir(parents=True)
            imported.write_text("user data\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                regenerate(output)
            self.assertTrue(imported.exists())

    def test_generation_check_survives_checkout_relocation(self):
        """Absolute checkout paths must not enter newly generated provenance."""
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            relocated = Path(tmp) / "relocated-checkout"
            shutil.copytree(root, relocated, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            result = subprocess.run(
                [sys.executable, "tools/regenerate_v04.py", "--check"],
                cwd=relocated,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
