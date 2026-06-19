import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_real_cve_readiness import (
    binding_validation_has_complete_role_graph,
    binding_validation_limitations,
    harness_admissibility_blocker,
    harness_admissibility_records,
    harness_rejects_core_evidence,
    short_gate_benefit,
    short_gate_comparison,
)


class RealCveReadinessAuditTest(unittest.TestCase):
    def test_harness_admissibility_rejects_core_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "raw" / "libxml2_1107_harness_admissibility.json"
            path.parent.mkdir()
            path.write_text(
                json.dumps(
                    {
                        "schema": "formtrig_harness_admissibility_v1",
                        "target_id": "LIBXML2_1107",
                        "status": "inadmissible_core_evidence",
                        "core_evidence_allowed": False,
                        "summary": "harness exposes an artificial trigger-control knob",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = harness_admissibility_records("LIBXML2_1107", root=root)

        self.assertEqual(len(records), 1)
        self.assertTrue(harness_rejects_core_evidence(records))
        blocker = harness_admissibility_blocker(records)
        self.assertIn("inadmissible_core_evidence", blocker)
        self.assertIn("artificial trigger-control knob", blocker)

    def test_short_gate_benefit_is_reported_without_speedup_claim(self):
        records = [
            {
                "_path": "artifacts/formtrig_native_readiness/comparisons/example/comparison.json",
                "claim_status": "short_gate_only_not_longrun",
                "comparison_type": "asan_baseline_prescreen",
                "formtrig": {
                    "pretrigger_lift_guidance_ready": True,
                    "accepted_non_trigger_progress_events": 2,
                    "saved_non_trigger_progress_events": 2,
                },
                "baselines": {
                    "summary": [
                        {"baseline": "aflplusplus_vanilla", "valid_reps": 3, "endpoint_successes": 0},
                        {"baseline": "aflplusplus_cmplog", "valid_reps": 3, "endpoint_successes": 0},
                    ]
                },
            }
        ]

        record = short_gate_comparison(records)

        self.assertIsNotNone(record)
        benefit = short_gate_benefit(record)
        self.assertIn("pre-trigger lifted guidance", benefit)
        self.assertIn("valid baseline reps 6", benefit)
        self.assertIn("0 endpoint successes", benefit)

    def test_binding_validation_limitations_block_mechanism_promotion(self):
        records = [
            {
                "status": "native_binding_validated",
                "_path": "binding/pass.json",
            },
            {
                "status": "alias_role_repaired_cleanup_use_not_captured",
                "_path": "binding/gpac_b3.json",
                "summary": {
                    "action": "make cleanup-use observable before matched endpoint long-runs"
                },
            },
        ]

        limitations = binding_validation_limitations(records)

        self.assertEqual(len(limitations), 1)
        self.assertIn("alias_role_repaired_cleanup_use_not_captured", limitations[0])
        self.assertIn("cleanup-use observable", limitations[0])

    def test_complete_role_graph_validation_supersedes_prior_limitations(self):
        records = [
            {
                "status": "alias_role_repaired_cleanup_use_not_captured",
                "_path": "binding/gpac_b3.json",
                "summary": {
                    "action": "make cleanup-use observable before matched endpoint long-runs"
                },
            },
            {
                "status": "complete_role_graph_preabort_verified",
                "_path": "binding/gpac_b5.json",
            },
        ]

        limitations = binding_validation_limitations(records)

        self.assertTrue(binding_validation_has_complete_role_graph(records))
        self.assertEqual(limitations, [])


if __name__ == "__main__":
    unittest.main()
