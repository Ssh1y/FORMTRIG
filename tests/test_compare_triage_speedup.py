import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.compare_formtrig_baselines import benefit_readout, classify_evidence
from tools.triage_formtrig_targets import package_row


class SpeedupClassificationTest(unittest.TestCase):
    def test_successful_baseline_can_still_be_speedup_evidence(self):
        formtrig_rows = [
            {
                "budget": 60,
                "strict_pretrigger_guidance": True,
                "terminal_count": 4,
                "trigger_time_s": 1.0,
            }
        ]
        baseline_rows = [
            {
                "source_label": "matched",
                "baseline": "aflplusplus_vanilla",
                "budget": 60,
                "success": True,
                "terminal_count": 1,
                "trigger_time_s": 20.0,
            },
            {
                "source_label": "matched",
                "baseline": "redqueen_operand",
                "budget": 60,
                "success": False,
                "terminal_count": 0,
            },
        ]

        analysis = classify_evidence(
            formtrig_rows,
            baseline_rows,
            tolerance=0,
            min_reps=2,
            required_baselines=["aflplusplus_vanilla", "redqueen_operand"],
        )

        self.assertEqual(analysis["verdict"], "speedup_but_under_replicated")
        self.assertIn("matched_baseline_also_triggers", analysis["reasons"])
        self.assertIn("formtrig_faster_than_successful_baselines", analysis["reasons"])
        self.assertEqual(analysis["missing_required_baselines"], [])
        self.assertEqual(analysis["fastest_baseline_trigger_time_s"], 20.0)
        self.assertEqual(analysis["best_formtrig_trigger_time_s"], 1.0)
        self.assertEqual(analysis["tte_speedup_over_fastest_baseline"], 20.0)

        readout = benefit_readout(formtrig_rows, analysis)
        self.assertIn("speedup benefit", readout["summary"])
        self.assertTrue(
            any("faster" in benefit for benefit in readout["primary_benefits"])
        )

    def test_triage_promotes_speedup_package_even_when_baseline_triggers(self):
        payload = {
            "comparison_id": "synthetic_speedup",
            "target_id": "SYNTH",
            "analysis": {
                "verdict": "speedup_but_under_replicated",
                "matched_baseline_count": 2,
                "missing_required_baselines": [],
                "best_formtrig_trigger_time_s": 1.0,
                "fastest_baseline_trigger_time_s": 20.0,
                "tte_speedup_over_fastest_baseline": 20.0,
                "reasons": [
                    "formtrig_terminal_oracle_present",
                    "formtrig_strict_pretrigger_guidance_present",
                    "matched_baseline_also_triggers",
                    "formtrig_faster_than_successful_baselines",
                    "low_replication",
                ],
                "baseline_groups": [
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 60,
                        "reps": 1,
                        "success_rate": 1.0,
                        "median_trigger_time_s": 20.0,
                    }
                ],
            },
            "benefit_readout": {
                "observed_benefits": ["FORMTRIG is faster"],
                "blocked_claims": ["single repetition"],
                "design_evidence": ["matched_budget_tte_speedup"],
            },
            "formtrig_runs": [
                {
                    "terminal_count": 4,
                    "strict_pretrigger_guidance": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comparison.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            row = package_row(path)

        self.assertEqual(row["package_status"], "promote_or_complete_reps")
        self.assertEqual(row["successful_baselines"], ["aflplusplus_vanilla"])
        self.assertEqual(row["tte_speedup_over_fastest_baseline"], 20.0)


if __name__ == "__main__":
    unittest.main()
