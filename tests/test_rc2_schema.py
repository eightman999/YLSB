import json
import unittest
from pathlib import Path
from statistics import fmean, pstdev

from ylsb_v04.schema import expected_performance_slots, validate_run_record


ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def synthetic_formal_record(course_id="YLSB-UME"):
    repeats = 3 if course_id == "YLSB-UME" else 5
    record = {
        "schema_version": 2,
        "run_id": "synthetic-heterogeneous",
        "course_id": course_id,
        "lane": "R0",
        "recorded_at": "2026-09-07T00:00:00Z",
        "runtime": {"name": "llama.cpp", "version": "b", "commit_hash": "a" * 40},
        "hardware": {
            "cpu": {"reported_name": None, "canonical_id": None, "cores": None, "threads": None, "memory_channels": None, "pcie_generation": None, "pcie_lanes": None, "provenance": {"kind": "unknown", "reason": "not reported"}},
            "ram": {"total_gib": 64, "provenance": {"kind": "reported", "source": "synthetic"}},
            "gpu_groups": [
                {"canonical_id": "nvidia-rtx-3060", "reported_name": "RTX 3060", "count": 1, "vram_gib_each": 12, "provenance": {"kind": "reported", "source": "synthetic"}},
                {"canonical_id": "nvidia-tesla-p100", "reported_name": "Tesla P100", "count": 1, "vram_gib_each": 16, "provenance": {"kind": "reported", "source": "synthetic"}},
            ],
            "interconnect": {"kind": "pci-e"},
            "numa": {"nodes": 1},
        },
        "environment": {"os_name": "Linux", "os_version": "test", "kernel_version": "test", "cuda_version": None, "driver_version": None, "not_applicable_reason": "synthetic"},
        "model": {"canonical_id": "model.synthetic", "reported_name": "Synthetic", "quantization": "Q4_K_M", "sha256": HASH},
        "fixture": {"path": "fixture.jsonl", "sha256": HASH},
        "grader": {"path": "grader.py", "sha256": HASH},
        "chat_template": {"id": "synthetic", "source": "test", "sha256": HASH, "thinking_disabled": True, "thinking_disabled_method": "test"},
        "runtime_config": {"ctx_size": 32768, "kv_cache": {"cache_type_k": "q8_0", "cache_type_v": "q8_0", "offload": False}, "seed": 42, "max_tokens": 128, "batch_size": 1, "ubatch_size": 1, "flash_attention": False, "split_mode": "layer", "tensor_split": [1, 1], "mtp_enabled": False, "raw_cli_args": ["--seed", "42"], "timings": {"cache_n": 1}},
        "performance_samples": [],
        "performance_summary": [],
    }
    for slot_index, (metric, point, depth) in enumerate(expected_performance_slots(course_id)):
        values = [float(slot_index + repeat + 1) for repeat in range(repeats)]
        for repeat, value in enumerate(values, 1):
            record["performance_samples"].append({"metric": metric, "point_tokens": point, "depth_tokens": depth, "repeat_index": repeat, "run_state": "cold" if repeat == 1 else "warm", "tokens_per_second": value, "vram_used_mib": 100 + repeat, "timings_cache_n": 1, "raw_output_path": f"raw/{metric}-{point}-{depth}-{repeat}.json"})
        record["performance_summary"].append({"metric": metric, "point_tokens": point, "depth_tokens": depth, "repeats_expected": repeats, "repeats_recorded": repeats, "mean_tokens_per_second": fmean(values), "standard_deviation_tokens_per_second": pstdev(values), "standard_deviation_kind": "population", "vram_peak_mib": 100 + repeats})
    return record


class Rc2SchemaTests(unittest.TestCase):
    def test_course_slots_match_profile_contract(self):
        self.assertEqual(
            {
                ("PP", 128, 0), ("PP", 512, 0), ("PP", 2048, 0),
                ("TG", 32, 0), ("TG", 128, 0),
                ("PP", 512, 8192), ("TG", 128, 8192),
            },
            set(expected_performance_slots("YLSB-UME")),
        )
        self.assertEqual(13, len(expected_performance_slots("YLSB-TAKE")))
        self.assertEqual(20, len(expected_performance_slots("YLSB-MATSU")))

    def test_canonical_and_generated_mirror_are_identical(self):
        canonical = (ROOT / "schema/run-record-v0.2.schema.json").read_bytes()
        mirror = (ROOT / "common/run_record.schema.v2.json").read_bytes()
        self.assertEqual(canonical, mirror)

    def test_heterogeneous_formal_record_is_valid(self):
        self.assertEqual([], validate_run_record(synthetic_formal_record()))

    def test_v2_contract_is_at_least_as_strict_as_v1(self):
        v1 = json.loads((ROOT / "common/run_record.schema.json").read_text())
        v2 = json.loads((ROOT / "schema/run-record-v0.2.schema.json").read_text())
        self.assertIn("commit_hash", v1["properties"]["runtime"]["required"])
        self.assertRegex(v1["properties"]["runtime"]["properties"]["commit_hash"]["pattern"], r"40")
        self.assertRegex(v2["$defs"]["runtime"]["properties"]["commit_hash"]["pattern"], r"40")
        for field in ("quantization", "sha256"):
            self.assertIn(field, v2["$defs"]["model"]["required"])
        for field in ("seed", "flash_attention", "tensor_split"):
            self.assertIn(field, v2["$defs"]["runtime_config"]["required"])
        self.assertEqual("integer", v2["$defs"]["runtime_config"]["properties"]["seed"]["type"])
        self.assertEqual("boolean", v2["$defs"]["runtime_config"]["properties"]["flash_attention"]["type"])
        self.assertNotIn("null", v2["$defs"]["performance_sample"]["properties"]["vram_used_mib"]["type"])
        self.assertNotIn("null", v2["$defs"]["performance_sample"]["properties"]["timings_cache_n"]["type"])

    def test_reproducibility_negative_cases(self):
        cases = []
        value = synthetic_formal_record()
        value["runtime"]["commit_hash"] = "abc"
        cases.append(value)
        value = synthetic_formal_record()
        del value["model"]["sha256"]
        cases.append(value)
        value = synthetic_formal_record()
        value["runtime_config"]["seed"] = None
        cases.append(value)
        value = synthetic_formal_record()
        value["runtime_config"]["flash_attention"] = None
        cases.append(value)
        value = synthetic_formal_record()
        del value["runtime_config"]["tensor_split"]
        cases.append(value)
        value = synthetic_formal_record()
        sample = value["performance_samples"][0]
        sample.pop("vram_used_mib")
        cases.append(value)
        value = synthetic_formal_record()
        value["performance_samples"][0]["timings_cache_n"] = None
        cases.append(value)
        value = synthetic_formal_record()
        value["performance_summary"] = []
        cases.append(value)
        for record in cases:
            self.assertTrue(validate_run_record(record))

    def test_summary_is_recomputed_from_repeat_samples(self):
        value = synthetic_formal_record()
        value["performance_summary"][0]["mean_tokens_per_second"] += 1
        self.assertTrue(any("mean_tokens_per_second" in error for error in validate_run_record(value)))


if __name__ == "__main__":
    unittest.main()
