import json
import tempfile
import unittest
import zipfile
import shutil
from pathlib import Path

from ylsb_v04.importer import SubmissionImporter
from ylsb_v04.registry import Registry, load_registry
from ylsb_v04.schema import migrate_v03_record, validate_normalized_record, validate_run_record
from tests.test_rc2_schema import synthetic_formal_record


def run_record(**overrides):
    # Keep all positive run fixtures on the RC2 formal contract.  Negative
    # callers still replace the requested subtree below this helper's API.
    value = synthetic_formal_record()
    value.update(overrides)
    return value


class SchemaImportTests(unittest.TestCase):
    def test_real_v04_corpus_and_relocation_duplicate(self):
        source = Path(__file__).parents[1] / "results/v0.4-rc1/normalized"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relocated = root / "relocated"
            shutil.copytree(source, relocated)
            importer = SubmissionImporter(root / "out")
            first = importer.import_submission(source)
            second = importer.import_submission(relocated)
            self.assertEqual(473, len(first.records))  # 472 JSONL rows plus planner.json
            self.assertFalse(first.duplicate)
            self.assertTrue(second.duplicate)
            self.assertEqual(first.fingerprint, second.fingerprint)

    def test_real_v03_corpus_migrates_to_v02(self):
        source = Path(__file__).parents[1] / "results/v0.3/normalized"
        with tempfile.TemporaryDirectory() as tmp:
            result = SubmissionImporter(Path(tmp) / "out").import_submission(source)
            self.assertEqual(472, len(result.records))
            self.assertEqual({"normalized-corpus-v0.2"}, {row["schema_version"] for row in result.records})
            self.assertTrue(all(not validate_normalized_record(row) for row in result.records))

    def test_existing_destination_entity_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); first = root / "first"; second = root / "second"
            first.mkdir(); second.mkdir()
            base = {"schema_version": "normalized-corpus-v0.2", "record_type": "model", "model_id": "m", "reported_name": "A", "canonical_name": "A", "architecture": {}, "quant": "Q4", "format": "GGUF", "provenance": {"kind": "reported", "source": "test"}}
            (first / "model.json").write_text(json.dumps(base)); importer = SubmissionImporter(root / "out"); importer.import_submission(first)
            base["canonical_name"] = "B"; (second / "model.json").write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError, "model ID collision"):
                importer.import_submission(second)

    def test_types_and_provenance_are_checked(self):
        bad = run_record(hardware={"cpu": {}, "ram": {"total_gib": "32"}, "gpu_groups": []})
        self.assertTrue(validate_run_record(bad))
        self.assertTrue(validate_run_record({**run_record(), "hardware": {**run_record()["hardware"], "gpu_groups": [{"canonical_id": "x", "reported_name": "x", "count": 1, "vram_gib_each": 1, "provenance": {"kind": "future"}}]}}))
        self.assertTrue(validate_normalized_record({"schema_version": "normalized-corpus-v0.2", "record_type": "import", "provenance": {}}))

    def test_migration_keeps_provenance_and_unknown_hardware(self):
        value = migrate_v03_record({"record_type": "run", "run_id": "r", "hardware": {"gpu": {"model": "reported GPU", "count": 1, "vram_gib_each": 8}}, "provenance": {"kind": "reported", "source": "legacy"}})
        self.assertEqual("legacy", value["provenance"]["source"])
        self.assertIsNone(value["hardware"]["gpu_groups"][0]["canonical_id"])
        self.assertEqual("unknown", value["hardware"]["cpu"]["provenance"]["kind"])

    def test_relocation_duplicate_and_model_hardware_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_a = root / "one"; source_a.mkdir()
            source_b = root / "two"; source_b.mkdir()
            payload = {"record_type": "run", "run_id": "r", "model_id": "m", "hardware_id": "h", "provenance": {"kind": "reported"}}
            (source_a / "run.json").write_text(json.dumps(payload))
            (source_b / "run.json").write_text(json.dumps(payload))
            out = root / "out"
            importer = SubmissionImporter(out)
            self.assertFalse(importer.import_submission(source_a).duplicate)
            self.assertTrue(importer.import_submission(source_b).duplicate)

    def test_zip_prefix_does_not_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / "out"
            payload = {"record_type": "run", "run_id": "r", "model_id": "m", "hardware_id": "h", "provenance": {"kind": "reported"}}
            for name, prefix in (("a.zip", "prefix-a"), ("b.zip", "prefix-b")):
                with zipfile.ZipFile(root / name, "w") as archive:
                    archive.writestr(f"{prefix}/run.json", json.dumps(payload))
            importer = SubmissionImporter(out)
            self.assertFalse(importer.import_submission(root / "a.zip").duplicate)
            self.assertTrue(importer.import_submission(root / "b.zip").duplicate)

    def test_alias_collision_and_provenance_preservation(self):
        with self.assertRaises(ValueError):
            Registry("models", {"entries": [{"canonical_id": "a", "canonical_name": "same"}, {"canonical_id": "b", "canonical_name": "SAME"}]})
        resolved = load_registry("hardware").resolve("RTX 3060")
        self.assertEqual("registry", resolved["provenance"]["kind"])
        unknown = load_registry("hardware").resolve("unlisted")
        self.assertIsNone(unknown["canonical_id"])
        self.assertEqual("unknown", unknown["provenance"]["kind"])


if __name__ == "__main__":
    unittest.main()
