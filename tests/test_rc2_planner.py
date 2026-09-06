import json
import unittest
from pathlib import Path

from ylsb_v04.planner import CandidatePlanner, load_candidate_catalog, load_normalized_corpus, next_benchmark_candidate, retrieve_nearest_observations
from ylsb_v04.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


def _runtime():
    return load_registry("runtimes").entries


class Rc2PlannerTests(unittest.TestCase):
    def test_catalog_is_separate_and_spans_the_size_ladder(self):
        path = ROOT / "registries/candidate_models.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["entries"]), 6)
        self.assertEqual("candidate_catalog", data["registry_kind"])
        self.assertEqual("registries/models.json", data["observed_registry"])
        sizes = [entry["architecture"]["total_params_b"] for entry in data["entries"]]
        self.assertTrue(any(size < 5 for size in sizes))
        self.assertTrue(any(12 <= size <= 16 for size in sizes))
        self.assertTrue(any(27 <= size <= 35 for size in sizes))
        self.assertTrue(any(65 <= size <= 80 for size in sizes))
        self.assertTrue(any(size >= 100 for size in sizes))
        self.assertTrue(any(entry["architecture"]["type"] == "moe" for entry in data["entries"]))
        self.assertTrue(all(entry["observed"] is False for entry in data["entries"]))
        self.assertTrue(all(entry["quantization_status"] in {"reported", "estimated", "unknown"} for entry in data["entries"]))

    def test_default_catalog_has_unobserved_candidates_beyond_observed_ceiling(self):
        observed = json.loads((ROOT / "registries/models.json").read_text(encoding="utf-8"))["entries"]
        catalog = load_candidate_catalog()
        self.assertGreater(len(catalog), len(observed))
        self.assertGreater(max(item["architecture"]["total_params_b"] for item in catalog), 35)
        plan = CandidatePlanner(
            {"gpu_groups": [{"architecture": "Pascal", "vram_gib_each": 16, "count": 13, "compute_capability": 6.0, "memory_bandwidth_gbps": 732}]},
            catalog,
            _runtime(),
        ).plan()
        self.assertGreater(len(plan["candidates"]), 6)
        self.assertTrue(any(item["size_class_b"] > 35 for item in plan["envelope"]))
        self.assertTrue(all(item["prediction_status"] == "predicted" for item in plan["candidates"]))
        self.assertTrue(all(item["observed"] is False for item in plan["candidates"]))

    def test_default_runtime_registry_accepts_v100_p100_and_mixed_profiles(self):
        catalog = load_candidate_catalog()
        runtimes = load_registry("runtimes").entries
        self.assertIn("Volta", next(item for item in runtimes if item["canonical_id"] == "runtime.llama-cpp")["architectures"])
        self.assertIn("Volta", next(item for item in runtimes if item["canonical_id"] == "runtime.ollama")["architectures"])
        profiles = [
            {"gpu_groups": [{"architecture": "Volta", "vram_gib_each": 32, "count": 1, "compute_capability": 7.0}]},
            {"gpu_groups": [{"architecture": "Pascal", "vram_gib_each": 16, "count": 13, "compute_capability": 6.0}]},
            {"gpu_groups": [{"architecture": "Ampere", "vram_gib_each": 12, "count": 1, "compute_capability": 8.6}, {"architecture": "Pascal", "vram_gib_each": 16, "count": 1, "compute_capability": 6.0}]},
        ]
        plans = [CandidatePlanner(profile, catalog, runtimes).plan() for profile in profiles]
        for plan in plans:
            self.assertGreater(len(plan["candidates"]), 6)
            self.assertTrue(any(item["eligible"] for item in plan["candidates"]))
            self.assertTrue(any(item["runtime"][0]["compatibility"] in {"candidate", "experimental", "unknown"} for item in plan["candidates"] if item["runtime"]))
        self.assertNotEqual([item["model"] for item in plans[0]["ranking"]], [item["model"] for item in plans[1]["ranking"]])

    def test_hardware_profiles_have_different_architecture_ordering_and_components(self):
        catalog = load_candidate_catalog()
        profiles = {
            "v100": {"gpu_groups": [{"architecture": "Volta", "vram_gib_each": 32, "count": 1, "compute_capability": 7.0, "memory_bandwidth_gbps": 900}]},
            "p100x13": {"gpu_groups": [{"architecture": "Pascal", "vram_gib_each": 16, "count": 13, "compute_capability": 6.0, "memory_bandwidth_gbps": 732}]},
            "heterogeneous": {"gpu_groups": [{"architecture": "Ampere", "vram_gib_each": 12, "count": 1, "compute_capability": 8.6, "memory_bandwidth_gbps": 360}, {"architecture": "Pascal", "vram_gib_each": 16, "count": 1, "compute_capability": 6.0, "memory_bandwidth_gbps": 732}]},
        }
        plans = {name: CandidatePlanner(hw, catalog, _runtime()).plan() for name, hw in profiles.items()}
        order = lambda plan: [item["model"] for item in plan["ranking"]]
        self.assertNotEqual(order(plans["v100"]), order(plans["p100x13"]), "hardware profiles must affect ranking")
        self.assertEqual("low", plans["heterogeneous"]["hardware_profile"]["heterogeneous"] and plans["heterogeneous"]["ranking"][0]["confidence"])
        self.assertLess(
            plans["heterogeneous"]["ranking"][0]["score_breakdown"]["topology"],
            plans["v100"]["ranking"][0]["score_breakdown"]["topology"],
        )
        moe = next(item for item in plans["p100x13"]["ranking"] if item["architecture_type"] == "moe" and item["size_class_b"] > 100)
        dense = next(item for item in plans["p100x13"]["ranking"] if item["architecture_type"] == "dense" and item["size_class_b"] > 100)
        self.assertGreater(moe["score"], dense["score"])
        self.assertIn("active_compute_pressure", moe["score_breakdown"])
        self.assertIn("memory_headroom", moe["score_breakdown"])
        self.assertIn("heterogeneous GPU topology penalty", plans["heterogeneous"]["ranking"][0]["reason"])

    def test_adaptive_catalog_boundary_advances_and_uses_midpoint(self):
        catalog = load_candidate_catalog()
        plan = CandidatePlanner(
            {"gpu_groups": [{"architecture": "Pascal", "vram_gib_each": 16, "count": 13, "compute_capability": 6.0, "memory_bandwidth_gbps": 732}]},
            catalog,
            _runtime(),
        ).plan()
        by_size = sorted(plan["candidates"], key=lambda item: item["size_class_b"])
        small = next(item for item in by_size if item["size_class_b"] > 30)
        large = next(item for item in by_size if item["size_class_b"] > 100)
        first = next_benchmark_candidate(plan, [{"model": small["model"], "status": "success"}])
        self.assertIsNotNone(first)
        self.assertGreater(first["size_class_b"], small["size_class_b"])
        midpoint = next_benchmark_candidate(plan, [{"model": small["model"], "status": "success"}, {"model": large["model"], "status": "oom"}])
        self.assertIsNotNone(midpoint)
        self.assertGreater(midpoint["size_class_b"], small["size_class_b"])
        self.assertLess(midpoint["size_class_b"], large["size_class_b"])

    def test_prediction_never_becomes_observation_or_v03_label(self):
        plan = CandidatePlanner(
            {"gpu_groups": [{"architecture": "Volta", "vram_gib_each": 32, "count": 1, "compute_capability": 7.0}]},
            load_candidate_catalog(),
            _runtime(),
            corpus=[{"record_type": "verdict", "run_id": "v", "gates": {"S": True}}],
        ).plan()
        self.assertFalse(plan["training_labels_used"])
        self.assertTrue(all(item["prediction_status"] == "predicted" for item in plan["candidates"]))
        self.assertTrue(all(item["retrieval"]["labels_used"] is False for item in plan["candidates"]))
        self.assertNotIn("gates", json.dumps(plan["retrieval"]))

    def test_catalog_rejects_observed_or_non_predicted_markers_and_retrieval_skips_predictions(self):
        entry = json.loads((ROOT / "registries/candidate_models.json").read_text(encoding="utf-8"))["entries"][0]
        observed = dict(entry, observed=True)
        with self.assertRaises(ValueError):
            load_candidate_catalog({"entries": [observed]})
        non_prediction = dict(entry, prediction_status="success")
        with self.assertRaises(ValueError):
            load_candidate_catalog({"entries": [non_prediction]})
        predicted_observation = {
            "record_type": "observation", "run_id": "catalog-prediction",
            "prediction_status": "predicted",
            "hardware": {"gpu_groups": [{"architecture": "Volta", "vram_gib_each": 32, "count": 1}]},
            "model": entry, "runtime": {}, "performance": {"metric": "tg", "value": 1},
        }
        rows = load_normalized_corpus([predicted_observation])
        retrieval = retrieve_nearest_observations(rows, predicted_observation["hardware"], entry, {})
        self.assertEqual(0, retrieval["observed_records"])
        self.assertEqual([], retrieval["nearest"])


if __name__ == "__main__":
    unittest.main()
