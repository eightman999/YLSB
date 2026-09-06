import unittest
from pathlib import Path

from ylsb_v04.planner import CandidatePlanner, estimate_model_fit, load_normalized_corpus, next_benchmark_candidate


ROOT = Path(__file__).resolve().parents[1]


class PlannerTests(unittest.TestCase):
    def test_normalized_join_and_verdict_label_invariance(self):
        corpus = load_normalized_corpus(ROOT / "results/v0.3/normalized")
        self.assertGreater(len(corpus), 0)
        self.assertTrue(corpus[0]["performance"])
        self.assertEqual({"run", "machine", "model", "runtime", "performance"}, set(corpus[0]["provenance"]))
        hardware = {"gpu_groups": [{"architecture": "Ampere", "vram_gib_each": 12, "count": 1}]}
        model = {"canonical_id": "m", "format": "GGUF", "bpw": 4, "architecture": {"type": "dense", "total_params_b": 4, "active_params_b": 4}}
        runtime = {"canonical_id": "r", "name": "llama.cpp", "supported_formats": ["GGUF"], "architectures": ["Ampere"]}
        first = CandidatePlanner(hardware, [model], [runtime], corpus).plan()["candidates"][0]["retrieval"]
        altered = [dict(row, gates={"fake": True}, policy_version="YLSB-v0.3") for row in corpus]
        second = CandidatePlanner(hardware, [model], [runtime], altered).plan()["candidates"][0]["retrieval"]
        self.assertEqual(first, second)
        self.assertTrue(first["nearest"])
        self.assertFalse(first["labels_used"])

    def test_mixed_joined_and_raw_rows_are_not_mode_switched(self):
        joined = {"record_type": "observation", "run_id": "j", "hardware": {"gpu_groups": [{"architecture": "Ampere", "vram_gib_each": 12}]}, "model": {"architecture": {"type": "dense", "total_params_b": 4}}, "runtime": {}, "performance": {"metric": "tg", "value": 1}}
        raw = [{"record_type": "run", "run_id": "r", "machine_id": "machine", "model_id": "model", "runtime_id": "runtime"}, {"record_type": "machine", "machine_id": "machine", "gpu_ids": ["gpu"], "ram": {}, "aggregate": {}}, {"record_type": "hardware", "hardware_id": "gpu", "architecture": "Pascal", "vram_each_gb": 16, "count": 1}, {"record_type": "model", "model_id": "model", "architecture": {"type": "dense", "total_params_b": 8}}, {"record_type": "runtime", "runtime_id": "runtime", "name": "llama.cpp"}, {"record_type": "performance", "run_id": "r", "metric": "tg", "value": 2}]
        rows = load_normalized_corpus([joined, *raw])
        self.assertEqual({"j", "r"}, {row["run_id"] for row in rows})

    def test_no_practical_fit_does_not_fill_practical_window(self):
        hardware = {"gpu_groups": [{"architecture": "Pascal", "vram_gib_each": 1, "count": 1}]}
        models = [{"canonical_id": str(size), "format": "GGUF", "architecture": {"type": "dense", "total_params_b": size, "active_params_b": size}} for size in (35, 110, 235)]
        runtime = [{"canonical_id": "r", "name": "llama.cpp", "supported_formats": ["GGUF"], "architectures": ["Pascal"]}]
        plan = CandidatePlanner(hardware, models, runtime).plan()
        self.assertIsNone(plan["meaningful_window"]["practical_upper_bound"])
        self.assertIsNone(plan["meaningful_window"]["sweet_spot"])
        self.assertIsNotNone(plan["meaningful_window"]["capacity_frontier"])
        self.assertIsNone(plan["slots"]["L"])
        self.assertIsNone(plan["slots"]["D"])

    def test_unknown_runtime_facts_need_validation_and_are_low_confidence(self):
        model = {"format": "GGUF", "architecture": {"type": "dense", "total_params_b": 4}}
        runtime = {"canonical_id": "vllm", "name": "vLLM", "supported_formats": ["GGUF"], "architectures": ["Ampere"], "min_compute_capability": 7.5, "min_driver_version": 550, "source": "spec", "retrieved_at": "2026-09-07", "spec_version": "test"}
        item = CandidatePlanner({"gpu_groups": [{"architecture": "Ampere", "vram_gib_each": 12}]}, [model], [runtime]).plan()["candidates"][0]["runtime"][0]
        self.assertEqual("unknown", item["compatibility"])
        self.assertEqual("needs_validation", item["validation_status"])
        self.assertEqual("low", item["confidence"])
        self.assertEqual("2026-09-07", item["provenance"]["retrieved_at"])

    def test_known_unsupported_runtime_is_rejected(self):
        model = {"format": "GGUF", "architecture": {"type": "dense", "total_params_b": 4}}
        runtime = {"canonical_id": "vllm", "name": "vLLM", "supported_formats": ["GGUF"], "architectures": ["Ampere"], "min_compute_capability": 7.5}
        item = CandidatePlanner({"gpu_groups": [{"architecture": "Pascal", "compute_capability": 6.0, "vram_gib_each": 16}]}, [model], [runtime]).plan()["candidates"][0]["runtime"][0]
        self.assertEqual("reject", item["compatibility"])
        self.assertEqual("high", item["confidence"])

    def test_adaptive_outcomes_expand_and_close_boundary(self):
        plan = {"candidates": [{"model": str(size), "size_class_b": size, "eligible": True} for size in (35, 70, 110, 235)], "anchor": {"model": "35"}}
        self.assertEqual("70", next_benchmark_candidate(plan, [{"model": "35", "status": "easy"}])["model"])
        self.assertEqual("110", next_benchmark_candidate(plan, [{"model": "235", "status": "oom"}])["model"])
        self.assertEqual("70", next_benchmark_candidate(plan, [{"model": "35", "status": "easy"}, {"model": "110", "status": "barely"}, {"model": "235", "status": "oom"}])["model"])

    def test_fit_uses_known_artifact_and_separates_moe_pressures(self):
        fit = estimate_model_fit({"gpu_groups": [{"architecture": "Pascal", "vram_gib_each": 16, "count": 2}]}, {"format": "GGUF", "file_size_bytes": 8 * 1024**3, "architecture": {"type": "moe", "total_params_b": 235, "active_params_b": 35}})
        self.assertEqual("known_artifact_bytes", fit["weight_source"])
        self.assertEqual(235, fit["memory_params_b"])
        self.assertEqual(35, fit["compute_active_params_b"])
        self.assertIn("layer_split", fit["allocation"])


if __name__ == "__main__":
    unittest.main()
