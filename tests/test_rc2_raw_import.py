import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from ylsb_v04.importer import RawReportError, RawReportImporter


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "results/v0.3/frozen/ume-first-wave-20260906/original"


def tree_hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()}


class RawImportTests(unittest.TestCase):
    def test_inventory_and_semantic_extraction_of_frozen_bundle(self):
        adapter = RawReportImporter().adapter
        inventory = adapter.inventory(FROZEN)
        self.assertEqual("v03-ume-report", inventory["adapter"])
        self.assertEqual(6, inventory["runs_found"])
        self.assertEqual(252, inventory["raw_task_rows"])
        self.assertEqual(198, inventory["performance_rows"])
        records, _ = adapter.extract(FROZEN)
        tasks = [row for row in records if row["record_type"] == "task_result"]
        performance = [row for row in records if row["record_type"] == "performance"]
        self.assertEqual(252, len(tasks))
        self.assertEqual(198, len(performance))
        self.assertTrue(any(row["task_id"] == "CORE-CONSTRAINT-003" and row["status"] == "FIXTURE_INVALID" and row["fixture_version"] == "v0.3" for row in tasks))
        self.assertTrue(any(row["status"] == "PROTOCOL" and not row["non_empty"] for row in tasks))
        self.assertEqual({"original_run", "posthoc_vram_remeasurement"}, {row["measurement_phase"] for row in performance})
        self.assertTrue(any(row["measurement_phase"] == "original_run" and row["metric"] == "pp" and row["vram"] is None for row in performance))
        self.assertTrue(any(row["measurement_phase"] == "posthoc_vram_remeasurement" and row["vram"] for row in performance))
        runs = [row for row in records if row["record_type"] == "run"]
        self.assertTrue(all(row["provenance"]["/config/seed/effective"]["kind"] == "unknown" for row in runs))
        verdicts = [row for row in records if row["record_type"] == "verdict"]
        self.assertEqual(6, len(verdicts))
        self.assertEqual({"YLSB-v0.3"}, {row["policy_version"] for row in verdicts})
        submissions = [row for row in records if row["record_type"] == "submission"]
        self.assertTrue(all(row["source_files"] == tree_hashes(FROZEN) for row in submissions))

    def test_reported_values_match_existing_normalized_observations(self):
        records, _ = RawReportImporter().adapter.extract(FROZEN)
        comparisons = [
            ("task_result", "task_results", "task_result_id", ("model_output", "expected_answer", "score", "format_ok", "non_empty", "http_status", "category", "failure_class_reported", "failure_class_audited")),
            ("performance", "performance", "measurement_id", ("value", "unit", "target_tokens", "repeat", "timings_cache_n", "vram", "generated_tokens", "wall_ms", "measurement_phase")),
            ("model", "models", "model_id", ("reported_name", "quant", "sha256", "file_size_bytes", "architecture")),
            ("hardware", "hardware", "reported_name", ("architecture", "architecture_code", "memory_bandwidth_gbps", "vram_each_gb", "pcie", "memory_type")),
            ("machine", "machines", "driver", ("ram", "os", "cuda", "aggregate")),
            ("runtime", "runtimes", "commit", ("version", "name", "family")),
        ]
        for kind, filename, key, fields in comparisons:
            old = {row[key]: row for row in map(json.loads, (ROOT / f"results/v0.3/normalized/{filename}.jsonl").read_text().splitlines())}
            current = [row for row in records if row["record_type"] == kind]
            self.assertEqual(len(old), len(current))
            for row in current:
                for field in fields:
                    with self.subTest(kind=kind, identifier=row[key], field=field):
                        self.assertEqual(old[row[key]].get(field), row.get(field))
        old_runs = {row["run_id"]: row for row in map(json.loads, (ROOT / "results/v0.3/normalized/runs.jsonl").read_text().splitlines())}
        for run in (row for row in records if row["record_type"] == "run"):
            old = old_runs[run["run_id"]]
            for field in ("ctx", "kv_type", "seed", "flash_attention", "tensor_split", "chat_template_candidates"):
                self.assertEqual(old["config"][field], run["config"][field])
            for field in ("model_sha256", "fixtures_sha256", "grader_sha256"):
                self.assertEqual(old["artifacts"][field], run["artifacts"][field])
            self.assertIsNone(run["config"]["mtp"])
            self.assertIsNone(run["config"]["speculative"])

    def test_import_directory_zip_relocation_and_duplicate_fingerprint(self):
        before = tree_hashes(FROZEN)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relocated = root / "relocated"
            shutil.copytree(FROZEN, relocated)
            destination = root / "normalized"
            importer = RawReportImporter(destination)
            first, inventory = importer.import_raw(FROZEN)
            second, _ = importer.import_raw(relocated)
            self.assertEqual(478, len(first.records))
            self.assertEqual(str(FROZEN.resolve()), first.source)
            self.assertTrue(all("complete_reports/" in row.get("source", {}).get("path", "") for row in first.records if row["record_type"] in {"task_result", "performance"}))
            self.assertFalse(first.duplicate)
            self.assertTrue(second.duplicate)
            self.assertEqual(first.fingerprint, second.fingerprint)
            archive = root / "submission.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                for path in FROZEN.rglob("*"):
                    if path.is_file():
                        handle.write(path, Path("bundle") / path.relative_to(FROZEN))
            zip_result, _ = importer.import_raw(archive)
            self.assertTrue(zip_result.duplicate)
            self.assertEqual(first.fingerprint, zip_result.fingerprint)
            self.assertEqual(6, inventory["runs_found"])
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            moved = root / "relocated.zip"
            shutil.copyfile(archive, moved)
            moved_result, _ = importer.import_raw(moved)
            self.assertEqual(first.fingerprint, moved_result.fingerprint)
            self.assertTrue(moved_result.duplicate)
            self.assertEqual(archive_hash, hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertEqual(before, tree_hashes(FROZEN))

    def test_corrupt_and_mixed_bundles_fail_with_source_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FROZEN, bundle)
            importer = RawReportImporter()
            raw = bundle / "complete_reports/qwen3-4b/raw.jsonl"
            original = raw.read_bytes()
            raw.write_text("\n{broken}\n")
            with self.assertRaisesRegex(RawReportError, "raw.jsonl:2"):
                importer.import_raw(bundle, dry_run=True)
            raw.write_bytes(original)
            env = bundle / "env_fingerprint.json"
            original_env = env.read_bytes()
            env.write_text("[]")
            with self.assertRaisesRegex(RawReportError, "env_fingerprint.json.*object"):
                importer.import_raw(bundle)
            env.write_bytes(original_env)
            summary = bundle / "complete_reports/qwen3-4b/summary.json"
            value = json.loads(summary.read_text())
            value["version"] = "0.4"
            summary.write_text(json.dumps(value))
            with self.assertRaises(RawReportError) as context:
                importer.import_raw(bundle)
            self.assertIsNotNone(context.exception.diagnostic)

    def test_blank_lines_keep_exact_source_line_numbers(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FROZEN, bundle)
            raw = bundle / "complete_reports/qwen3-4b/raw.jsonl"
            raw.write_bytes(b"\n" + raw.read_bytes())
            records, _ = RawReportImporter().adapter.extract(bundle)
            for row in records:
                source = row.get("source", {})
                if source.get("path") == "complete_reports/qwen3-4b/raw.jsonl":
                    actual = json.loads(raw.read_text().splitlines()[source["line"] - 1])
                    if row["record_type"] == "task_result":
                        self.assertEqual(row["task_id"], actual["id"])
                    else:
                        self.assertEqual(row["metric"], actual["section"])

    def test_dry_run_unknown_layout_and_zip_traversal_are_diagnostic(self):
        result, _ = RawReportImporter(None).import_raw(FROZEN)
        self.assertFalse(result.duplicate)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unknown = root / "unknown"
            unknown.mkdir()
            (unknown / "README.txt").write_text("not a YLSB bundle", encoding="utf-8")
            importer = RawReportImporter(root / "out")
            with self.assertRaises(RawReportError) as context:
                importer.import_raw(unknown, dry_run=True)
            self.assertIn("v0.3 UME complete_reports", str(context.exception))
            self.assertIsNotNone(context.exception.diagnostic)
            with self.assertRaises(ValueError):
                RawReportImporter(unknown / "out").import_raw(unknown)
            archive = root / "traversal.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../escape.json", "{}")
            with self.assertRaises(RawReportError):
                importer.import_raw(archive, dry_run=True)


if __name__ == "__main__":
    unittest.main()
