import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.verify_release import (
    CheckResult,
    _git_sha,
    _protected_baseline_check,
    _write_junit,
)


ROOT = Path(__file__).parents[1]


class VerifyReleaseTests(unittest.TestCase):
    def test_v03_protected_baseline_is_intact(self):
        passed, failures, actual, excluded = _protected_baseline_check(ROOT)
        self.assertTrue(passed, failures)
        self.assertEqual(91, len(actual))
        self.assertGreaterEqual(len(excluded), 1)

    def test_junit_records_failed_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "junit.xml"
            check = CheckResult("synthetic failure", ["false"], 1, 0.01, "out", "err")
            _write_junit(path, [check])
            xml = path.read_text(encoding="utf-8")
            self.assertIn('failures="1"', xml)
            self.assertIn("synthetic failure", xml)
            self.assertIn("err", xml)

    def test_git_sha_is_available_for_target_checkout(self):
        self.assertRegex(_git_sha(ROOT) or "", r"^[0-9a-f]{40}$")

    def test_harness_and_target_sha_can_be_distinguished(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            repos = []
            for directory, content in ((first, "one"), (second, "two")):
                root = Path(directory)
                subprocess.run(["git", "init", "-q", str(root)], check=True)
                subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
                subprocess.run(["git", "-C", str(root), "config", "user.name", "YLSB test"], check=True)
                (root / "value.txt").write_text(content, encoding="utf-8")
                subprocess.run(["git", "-C", str(root), "add", "value.txt"], check=True)
                subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "test"], check=True)
                repos.append(root)
            self.assertNotEqual(_git_sha(repos[0]), _git_sha(repos[1]))


if __name__ == "__main__":
    unittest.main()
