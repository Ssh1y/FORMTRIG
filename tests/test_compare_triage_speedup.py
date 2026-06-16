import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.compare_formtrig_baselines import (
    benefit_readout,
    classify_evidence,
    load_formtrig_rows,
)
from tools.triage_formtrig_targets import package_row, target_rows


class SpeedupClassificationTest(unittest.TestCase):
    def test_endpoint_benefit_does_not_require_strict_pretrigger_gate(self):
        formtrig_rows = [
            {
                "budget": 120,
                "strict_pretrigger_guidance": False,
                "terminal_count": 1150,
                "trigger_time_s": 0.036,
            }
        ]
        baseline_rows = [
            {
                "source_label": "matched",
                "baseline": "aflplusplus_vanilla",
                "budget": 120,
                "success": False,
                "terminal_count": 0,
            },
            {
                "source_label": "matched",
                "baseline": "aflplusplus_cmplog",
                "budget": 120,
                "success": False,
                "terminal_count": 0,
            },
            {
                "source_label": "matched",
                "baseline": "redqueen_operand",
                "budget": 120,
                "success": False,
                "terminal_count": 0,
            },
        ]

        analysis = classify_evidence(
            formtrig_rows,
            baseline_rows,
            tolerance=0,
            min_reps=2,
            required_baselines=[
                "aflplusplus_vanilla",
                "aflplusplus_cmplog",
                "redqueen_operand",
            ],
        )

        self.assertEqual(analysis["verdict"], "positive_endpoint_but_under_replicated")
        self.assertIn(
            "formtrig_endpoint_where_matched_baselines_do_not_trigger",
            analysis["reasons"],
        )
        self.assertIn("formtrig_strict_pretrigger_guidance_missing", analysis["reasons"])

        readout = benefit_readout(formtrig_rows, analysis)
        self.assertTrue(
            any(
                "matched baselines do not trigger" in benefit
                for benefit in readout["primary_benefits"]
            )
        )
        self.assertIn("matched_budget_endpoint_success", readout["design_evidence"])

    def test_formtrig_rows_use_exact_progress_queue_trigger_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "default"
            queue = default / "queue"
            queue.mkdir(parents=True)
            (queue / "id:000020,src:000013,time:36,execs:146,op:ftgtype,pos:4,+cov").write_bytes(
                b"seed"
            )
            (default / "formtrig_progress.jsonl").write_text(
                json.dumps(
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "queue_id": 20,
                        "execs_done": 153,
                        "triggered": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            gate = root / "gate_summary.csv"
            gate.write_text(
                "suite,run,run_time,execs_done,terminal_triggered,first_terminal_time_s,"
                "out_dir,binding_signal_status\n"
                f"suite,run,120,8202,1150,0,{default},pass\n",
                encoding="utf-8",
            )

            rows = load_formtrig_rows([f"b5={gate}"], "TIF012")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trigger_time_s"], 0.036)
        self.assertEqual(rows[0]["trigger_execs"], 146)
        self.assertEqual(
            rows[0]["trigger_time_kind"], "formtrig_progress_queue_filename_exact"
        )

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

    def test_triage_uses_2h_next_action_after_10m_confirmation(self):
        payload = {
            "comparison_id": "synthetic_speedup_10m",
            "target_id": "SYNTH",
            "analysis": {
                "verdict": "positive_speedup_matched_comparison",
                "matched_baseline_count": 1,
                "missing_required_baselines": [],
                "best_formtrig_trigger_time_s": 1.0,
                "fastest_baseline_trigger_time_s": 20.0,
                "tte_speedup_over_fastest_baseline": 20.0,
                "reasons": [
                    "formtrig_terminal_oracle_present",
                    "formtrig_strict_pretrigger_guidance_present",
                    "matched_baseline_also_triggers",
                    "formtrig_faster_than_successful_baselines",
                ],
                "baseline_groups": [
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 600,
                        "reps": 1,
                        "success_rate": 1.0,
                        "median_trigger_time_s": 20.0,
                    }
                ],
            },
            "benefit_readout": {
                "observed_benefits": ["FORMTRIG 10m speedup confirmed"],
                "blocked_claims": [],
                "design_evidence": ["matched_budget_tte_speedup"],
            },
            "formtrig_runs": [
                {
                    "terminal_count": 4,
                    "strict_pretrigger_guidance": True,
                }
            ],
            "longrun_10m_confirmation": {
                "formtrig_first_trigger_time_s": 1.0,
                "fastest_successful_baseline_trigger_time_s": 20.0,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comparison.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            row = package_row(path)

        self.assertTrue(row["longrun_10m_confirmed"])
        target = target_rows([row], [])[0]
        self.assertEqual(target["disposition"], "candidate_extend_longruns")
        self.assertIn("2h matched repetitions", target["next_action"])


if __name__ == "__main__":
    unittest.main()
