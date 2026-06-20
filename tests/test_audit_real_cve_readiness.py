import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_real_cve_readiness import (
    binding_validation_has_complete_role_graph,
    binding_validation_limitations,
    endpoint_demoted_delta,
    harness_admissibility_blocker,
    harness_admissibility_records,
    harness_rejects_core_evidence,
    readiness_delta_benefit,
    readiness_delta_next_action,
    readiness_delta_records,
    readiness_delta_status,
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
                "generated_at_utc": "2026-06-19T03:00:00Z",
                "claim_status": "short_gate_only_not_longrun",
                "comparison_type": "asan_baseline_prescreen",
                "duration_s": 600,
                "formtrig": {
                    "pretrigger_lift_guidance_ready": True,
                    "accepted_non_trigger_progress_events": 2,
                    "saved_non_trigger_progress_events": 2,
                    "variable_roles": ["root_observe", "use"],
                    "spec_d_f_candidate_values": [6, 4, 2],
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
        self.assertIn("600s short-gate pre-screen", benefit)
        self.assertIn("pre-trigger lifted guidance", benefit)
        self.assertIn("variable TC-rooted roles: root_observe,use", benefit)
        self.assertIn("spec D_F candidate values {6,4,2}", benefit)
        self.assertIn("valid baseline reps 6", benefit)
        self.assertIn("0 endpoint successes", benefit)

    def test_short_gate_comparison_prefers_newer_generated_record(self):
        records = [
            {
                "_path": "artifacts/formtrig_native_readiness/comparisons/old/comparison.json",
                "claim_status": "short_gate_only_not_longrun",
                "comparison_type": "asan_baseline_prescreen",
            },
            {
                "_path": "artifacts/formtrig_native_readiness/comparisons/new/comparison.json",
                "generated_at_utc": "2026-06-19T03:00:00Z",
                "claim_status": "short_gate_only_not_longrun",
                "comparison_type": "asan_baseline_prescreen",
            },
        ]

        record = short_gate_comparison(records)

        self.assertEqual(record["_path"], "artifacts/formtrig_native_readiness/comparisons/new/comparison.json")

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

    def test_readiness_delta_records_endpoint_demoted_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "gpac3403_b13_readiness_delta_20260620.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "formtrig_real_cve_readiness_delta_v1",
                        "target_id": "GPAC_3403",
                        "created_utc": "2026-06-20T04:55:00Z",
                        "delta_status": "endpoint_closure_observed_but_demoted_for_hard_pain",
                        "hard_pain_demotion_evidence": {
                            "reason": "strong baselines triggered within the acceptable threshold"
                        },
                        "readiness_implication": {
                            "next_action": "keep B13 as control evidence"
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = readiness_delta_records("GPAC_3403", root=root)

        self.assertEqual(len(records), 1)
        self.assertIn("endpoint_closure_observed", readiness_delta_status(records))
        delta = endpoint_demoted_delta(records)
        self.assertIsNotNone(delta)
        self.assertIn("strong baselines", readiness_delta_benefit(delta))
        self.assertEqual(readiness_delta_next_action(delta), "keep B13 as control evidence")


if __name__ == "__main__":
    unittest.main()
