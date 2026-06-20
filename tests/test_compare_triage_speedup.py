import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.compare_formtrig_baselines import (
    apply_baseline_guidance_gap,
    benefit_readout,
    classify_evidence,
    load_baseline_rows,
    load_formtrig_rows,
)
from tools.triage_formtrig_targets import package_row, target_rows


class SpeedupClassificationTest(unittest.TestCase):
    def test_load_baseline_rows_skips_invalid_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "baseline_summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "GPAC_3403",
                                "baseline": "aflplusplus_vanilla",
                                "budget": 60,
                                "rep": 1,
                                "valid_run": True,
                                "success": False,
                                "execs_done": 1200,
                            },
                            {
                                "target_id": "GPAC_3403",
                                "baseline": "aflplusplus_cmplog",
                                "budget": 60,
                                "rep": 1,
                                "valid_run": False,
                                "returncode": 1,
                                "success": False,
                                "execs_done": 0,
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            rows = load_baseline_rows([f"matched={summary}"], "GPAC_3403")

        self.assertEqual([row["baseline"] for row in rows], ["aflplusplus_vanilla"])

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
            min_reps=1,
            required_baselines=[
                "aflplusplus_vanilla",
                "aflplusplus_cmplog",
                "redqueen_operand",
            ],
        )

        self.assertEqual(analysis["verdict"], "positive_endpoint_matched_comparison")
        self.assertIn(
            "formtrig_endpoint_where_matched_baselines_do_not_trigger",
            analysis["reasons"],
        )
        self.assertIn("formtrig_strict_pretrigger_guidance_missing", analysis["reasons"])
        self.assertTrue(
            analysis["experiment_strength"]["baseline_guidance_gap"][
                "required_for_hard_sota_pain"
            ]
        )
        self.assertEqual(
            analysis["experiment_strength"]["baseline_guidance_gap"]["status"],
            "not_measured",
        )

        readout = benefit_readout(formtrig_rows, analysis)
        self.assertTrue(
            any(
                "matched baselines do not trigger" in benefit
                for benefit in readout["primary_benefits"]
            )
        )
        self.assertIn("matched_budget_endpoint_success", readout["design_evidence"])
        self.assertIn("baseline_guidance_gap_required", readout["design_evidence"])
        self.assertTrue(
            any("baseline no-guidance proof" in claim for claim in readout["blocked_claims"])
        )

    def test_incomplete_required_baseline_set_downgrades_hard_strength(self):
        analysis = classify_evidence(
            formtrig_rows=[
                {
                    "budget": 60,
                    "strict_pretrigger_guidance": True,
                    "terminal_count": 1,
                    "trigger_time_s": 2.0,
                }
            ],
            baseline_rows=[
                {
                    "source_label": "matched",
                    "baseline": "aflplusplus_vanilla",
                    "budget": 60,
                    "rep": 1,
                    "success": False,
                    "terminal_count": 0,
                }
            ],
            tolerance=0,
            min_reps=3,
            required_baselines=[
                "aflplusplus_vanilla",
                "aflplusplus_cmplog",
                "redqueen_operand",
            ],
        )

        self.assertEqual(analysis["verdict"], "incomplete_required_baseline_set")
        self.assertEqual(
            analysis["experiment_strength"]["main_claim_strength"],
            "incomplete_matched_evidence",
        )
        self.assertFalse(
            analysis["experiment_strength"]["baseline_guidance_gap"][
                "required_for_hard_sota_pain"
            ]
        )

    def test_measured_guidance_gap_unblocks_hard_endpoint_readout(self):
        formtrig_rows = [
            {
                "budget": 600,
                "strict_pretrigger_guidance": False,
                "terminal_count": 502,
                "trigger_time_s": 0.29,
            }
            for _ in range(3)
        ]
        baseline_rows = []
        for baseline in (
            "aflplusplus_vanilla",
            "aflplusplus_cmplog",
            "redqueen_operand",
        ):
            for rep in range(3):
                baseline_rows.append(
                    {
                        "source_label": "matched",
                        "baseline": baseline,
                        "budget": 600,
                        "rep": rep + 1,
                        "success": False,
                        "terminal_count": 0,
                    }
                )

        analysis = classify_evidence(
            formtrig_rows,
            baseline_rows,
            tolerance=0,
            min_reps=3,
            required_baselines=[
                "aflplusplus_vanilla",
                "aflplusplus_cmplog",
                "redqueen_operand",
            ],
        )
        apply_baseline_guidance_gap(
            analysis,
            {
                "analysis_id": "synthetic_gap",
                "target_id": "PDF003",
                "analysis": {
                    "status": "measured_pass",
                    "interpretation": "baseline evidence supports a hard binary-TC no-guidance candidate",
                    "pretrigger_binary_flat_measured": True,
                    "pretrigger_binary_flat_pass": True,
                    "endpoint_cost_pass": True,
                    "reasons": [
                        "pretrigger_binary_oracle_flat_before_T",
                        "baseline_endpoint_cost_late_missing_or_high_variance",
                    ],
                    "baseline_groups": [],
                },
            },
            Path("gap.json"),
            target_id="PDF003",
        )

        gap = analysis["experiment_strength"]["baseline_guidance_gap"]
        self.assertEqual(gap["status"], "measured_pass")
        self.assertTrue(gap["pretrigger_binary_flat_pass"])
        self.assertIn("baseline_guidance_gap_measured_pass", analysis["reasons"])

        readout = benefit_readout(formtrig_rows, analysis)
        self.assertIn("baseline_guidance_gap_measured", readout["design_evidence"])
        self.assertFalse(
            any("baseline no-guidance proof" in claim for claim in readout["blocked_claims"])
        )

    def test_under_budgeted_guidance_gap_blocks_hard_endpoint_readout_precisely(self):
        formtrig_rows = [
            {
                "budget": 60,
                "strict_pretrigger_guidance": True,
                "terminal_count": 2,
                "trigger_time_s": 2.4,
            }
            for _ in range(3)
        ]
        baseline_rows = []
        for baseline in (
            "aflplusplus_vanilla",
            "aflplusplus_cmplog",
            "redqueen_operand",
        ):
            for rep in range(3):
                baseline_rows.append(
                    {
                        "source_label": "matched",
                        "baseline": baseline,
                        "budget": 60,
                        "rep": rep + 1,
                        "success": False,
                        "terminal_count": 0,
                    }
                )

        analysis = classify_evidence(
            formtrig_rows,
            baseline_rows,
            tolerance=0,
            min_reps=3,
            required_baselines=[
                "aflplusplus_vanilla",
                "aflplusplus_cmplog",
                "redqueen_operand",
            ],
        )
        apply_baseline_guidance_gap(
            analysis,
            {
                "analysis_id": "synthetic_under_budgeted_gap",
                "target_id": "GPAC_3403",
                "analysis": {
                    "status": "under_budgeted",
                    "interpretation": "baseline runs are shorter than the acceptable trigger threshold",
                    "pretrigger_binary_flat_measured": True,
                    "pretrigger_binary_flat_pass": True,
                    "endpoint_cost_pass": False,
                    "reasons": [
                        "baseline_budget_below_acceptable_threshold",
                        "pretrigger_binary_oracle_flat_before_T",
                    ],
                    "baseline_groups": [],
                },
            },
            Path("gap.json"),
            target_id="GPAC_3403",
        )

        readout = benefit_readout(formtrig_rows, analysis)

        self.assertIn("baseline_guidance_gap_required", readout["design_evidence"])
        self.assertTrue(
            any("under-budgeted" in claim for claim in readout["blocked_claims"])
        )
        self.assertFalse(
            any("not measured" in claim for claim in readout["blocked_claims"])
        )

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

    def test_formtrig_rows_normalize_manifest_batch_summary_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            default = out_dir / "default"
            default.mkdir(parents=True)
            manifest = root / "PHP003.native_b2_thumbnail_guard.600s.manifest"
            manifest.write_text(
                "target_id: PHP003\n"
                "duration: 600\n",
                encoding="utf-8",
            )
            (default / "formtrig_summary.json").write_text(
                json.dumps(
                    {
                        "execs_done": 205673,
                        "formtrig_reached_execs": 121014,
                        "non_trigger_progress_events": 6,
                        "saved_non_trigger_progress_events": 6,
                        "terminal_triggered_execs": 0,
                        "spec_lifted_events": 4203,
                        "heuristic_lifted_events": 0,
                        "manual_lifted_events": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue = default / "queue"
            queue.mkdir()
            queue_file = (
                queue / "id:000123,src:000001,time:1358,execs:9021,op:ftgtype,pos:8"
            )
            queue_file.write_bytes(b"seed")
            (default / "formtrig_progress.jsonl").write_text(
                json.dumps(
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "queue_id": 123,
                        "execs_done": 9077,
                        "triggered": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (default / "formtrig_diagnosis.json").write_text(
                json.dumps(
                    {
                        "experiment_ready": True,
                        "pretrigger_lift_guidance_ready": True,
                        "lift_delta_only_on_triggered_candidates": False,
                        "binding_signal_status": "pass",
                        "binding_signal_diagnosis": "role_signal_progress_observed",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            gate = root / "batch_summary.csv"
            gate.write_text(
                "manifest,target_id,status,experiment_ready,pretrigger_lift_guidance_ready,"
                "diagnosis,progress_status,has_non_trigger_progress,non_trigger_progress,"
                "saved_non_trigger_progress,saved_triggered_progress,execs_done,reached,"
                "triggered,queued_progress,spec_lifted,heuristic_lifted,manual_lifted,"
                "d_f_constant,out_dir,log\n"
                f'"{manifest}","PHP003","ok","true","true","queued_tc_rooted_progress",'
                f'"progress_queued","true",6,6,0,205673,121014,0,6,4203,0,0,'
                f'"true","{out_dir}","{root / "batch_run.log"}"\n',
                encoding="utf-8",
            )

            rows = load_formtrig_rows([f"formtrig_600s_1rep={gate}"], "PHP003")

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["budget"], 600)
        self.assertEqual(row["run_time"], 600)
        self.assertEqual(row["accepted_non_trigger"], 6)
        self.assertEqual(row["saved_non_trigger"], 6)
        self.assertEqual(row["terminal_count"], 0)
        self.assertEqual(row["spec_lifted"], 4203)
        self.assertEqual(row["reached"], 121014)
        self.assertEqual(row["binding_signal_status"], "pass")
        self.assertEqual(row["trigger_time_s"], 1.358)
        self.assertEqual(row["trigger_execs"], 9021)
        self.assertTrue(row["strict_pretrigger_guidance"])

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

    def test_fast_successful_baseline_is_not_hard_pain_evidence(self):
        formtrig_rows = [
            {
                "budget": 7200,
                "strict_pretrigger_guidance": True,
                "terminal_count": 10,
                "trigger_time_s": 1.358,
            },
            {
                "budget": 7200,
                "strict_pretrigger_guidance": True,
                "terminal_count": 23,
                "trigger_time_s": 2.32,
            },
            {
                "budget": 7200,
                "strict_pretrigger_guidance": True,
                "terminal_count": 46,
                "trigger_time_s": 1.494,
            },
        ]
        baseline_rows = []
        for baseline, ttes in {
            "aflplusplus_vanilla": [42.154, 369.432, 56.056],
            "aflplusplus_cmplog": [51.275, 537.231, 52.977],
            "redqueen_operand": [9.456, 39.068, 32.517],
        }.items():
            for rep, tte in enumerate(ttes, 1):
                baseline_rows.append(
                    {
                        "source_label": "matched",
                        "baseline": baseline,
                        "budget": 7200,
                        "rep": rep,
                        "success": True,
                        "terminal_count": 1,
                        "trigger_time_s": tte,
                    }
                )

        analysis = classify_evidence(
            formtrig_rows,
            baseline_rows,
            tolerance=0,
            min_reps=3,
            required_baselines=[
                "aflplusplus_vanilla",
                "aflplusplus_cmplog",
                "redqueen_operand",
            ],
        )

        self.assertEqual(analysis["verdict"], "positive_speedup_matched_comparison")
        self.assertEqual(
            analysis["experiment_strength"]["main_claim_strength"],
            "not_hard_pain_baseline_fast_enough",
        )
        self.assertIn(
            "baseline_fastest_trigger_time_is_under_acceptable_threshold",
            analysis["experiment_strength"]["reasons"],
        )
        self.assertFalse(
            analysis["experiment_strength"]["baseline_guidance_gap"][
                "required_for_hard_sota_pain"
            ]
        )
        self.assertTrue(
            any("speedup/control" in step for step in analysis["experiment_strength"]["recommended_design_actions"])
        )
        self.assertIn("not_hard_pain_baseline_fast_enough", analysis["reasons"])
        self.assertTrue(
            any("move main budget" in step for step in analysis["next_steps"])
        )
        self.assertFalse(
            any("complete repetitions/longer runs" in step for step in analysis["next_steps"])
        )

        readout = benefit_readout(formtrig_rows, analysis)
        self.assertIn("experiment_strength_gate", readout["design_evidence"])
        self.assertTrue(
            any("acceptable-time threshold" in claim for claim in readout["blocked_claims"])
        )

    def test_unstable_or_long_tail_baselines_remain_hard_speedup_candidate(self):
        formtrig_rows = [
            {
                "budget": 7200,
                "strict_pretrigger_guidance": True,
                "terminal_count": 100,
                "trigger_time_s": 0.035,
            }
        ]
        baseline_rows = [
            {
                "source_label": "matched",
                "baseline": "aflplusplus_vanilla",
                "budget": 7200,
                "rep": 1,
                "success": True,
                "terminal_count": 1,
                "trigger_time_s": 1930.0,
            },
            {
                "source_label": "matched",
                "baseline": "aflplusplus_vanilla",
                "budget": 7200,
                "rep": 2,
                "success": True,
                "terminal_count": 1,
                "trigger_time_s": 2410.0,
            },
            {
                "source_label": "matched",
                "baseline": "aflplusplus_vanilla",
                "budget": 7200,
                "rep": 3,
                "success": True,
                "terminal_count": 1,
                "trigger_time_s": 2560.0,
            },
            {
                "source_label": "matched",
                "baseline": "aflplusplus_cmplog",
                "budget": 7200,
                "rep": 1,
                "success": False,
                "terminal_count": 0,
            },
            {
                "source_label": "matched",
                "baseline": "aflplusplus_cmplog",
                "budget": 7200,
                "rep": 2,
                "success": False,
                "terminal_count": 0,
            },
            {
                "source_label": "matched",
                "baseline": "aflplusplus_cmplog",
                "budget": 7200,
                "rep": 3,
                "success": True,
                "terminal_count": 1,
                "trigger_time_s": 4950.0,
            },
        ]

        analysis = classify_evidence(
            formtrig_rows,
            baseline_rows,
            tolerance=0,
            min_reps=3,
            required_baselines=["aflplusplus_vanilla", "aflplusplus_cmplog"],
        )

        self.assertEqual(analysis["verdict"], "positive_speedup_matched_comparison")
        self.assertEqual(
            analysis["experiment_strength"]["main_claim_strength"],
            "hard_speedup_or_reliability_candidate",
        )
        self.assertIn(
            "some_required_baseline_families_fail_or_are_unstable",
            analysis["experiment_strength"]["reasons"],
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

    def test_triage_routes_near_seed_speedup_to_harder_experiment_design(self):
        payload = {
            "comparison_id": "synthetic_near_seed_speedup",
            "target_id": "SYNTH",
            "analysis": {
                "verdict": "positive_speedup_matched_comparison",
                "matched_baseline_count": 9,
                "missing_required_baselines": [],
                "best_formtrig_trigger_time_s": 1.0,
                "fastest_baseline_trigger_time_s": 9.0,
                "tte_speedup_over_fastest_baseline": 9.0,
                "experiment_strength": {
                    "main_claim_strength": "weak_near_seed_or_harness_shaped_speedup",
                    "recommended_design_actions": [
                        "rerun with a higher-fidelity/raw-format harness or a farther RNT seed",
                        "add no-hook and generic-hook FORMTRIG ablations",
                    ],
                },
                "baseline_groups": [
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 7200,
                        "reps": 3,
                        "success_rate": 1.0,
                        "median_trigger_time_s": 20.0,
                    }
                ],
            },
            "benefit_readout": {
                "observed_benefits": ["FORMTRIG is faster"],
                "blocked_claims": [
                    "current experiment is too near-trigger or harness-shaped to serve as main SOTA-gap evidence"
                ],
                "design_evidence": ["experiment_strength_gate"],
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
            target = target_rows([row], [])[0]

        self.assertEqual(row["package_status"], "needs_harder_experiment_design")
        self.assertEqual(row["main_claim_strength"], "weak_near_seed_or_harness_shaped_speedup")
        self.assertEqual(target["disposition"], "needs_harder_experiment_design")
        self.assertEqual(
            target["sota_pain_class"], "not_visible_near_seed_or_harness_shaped"
        )
        self.assertIn("does not expose a hard SOTA gap", target["sota_pain_evidence"])
        self.assertIn("higher-fidelity", target["next_action"])

    def test_triage_rejects_speedup_when_baseline_time_cost_is_acceptable(self):
        packages = [
            {
                "comparison_id": "old_endpoint",
                "target_id": "TIF012",
                "package_status": "promote_or_extend_longruns",
                "verdict": "positive_endpoint_matched_comparison",
                "matched_baselines": 9,
                "successful_baselines": [],
                "fastest_baseline_trigger_time_s": None,
                "best_formtrig_trigger_time_s": 0.035,
                "tte_speedup_over_fastest_baseline": None,
                "main_claim_strength": "",
                "max_budget_s": 120,
                "formtrig_terminal": True,
                "strict_pretrigger_guidance": True,
                "observed_benefits": [
                    "FORMTRIG reaches terminal success where matched baselines do not trigger"
                ],
                "blocked_claims": [],
                "source_path": "old.json",
            },
            {
                "comparison_id": "long_tail_speedup",
                "target_id": "TIF012",
                "package_status": "promote_or_extend_longruns",
                "verdict": "positive_speedup_matched_comparison",
                "matched_baselines": 9,
                "successful_baselines": [
                    "aflplusplus_vanilla",
                    "aflplusplus_cmplog",
                    "redqueen_operand",
                ],
                "fastest_baseline_trigger_time_s": 210.0,
                "fastest_baseline_family_median_trigger_time_s": 1410.0,
                "best_formtrig_trigger_time_s": 0.034,
                "tte_speedup_over_fastest_baseline": 6176.47,
                "main_claim_strength": "hard_speedup_or_reliability_candidate",
                "max_budget_s": 7200,
                "formtrig_terminal": True,
                "strict_pretrigger_guidance": True,
                "observed_benefits": ["FORMTRIG speedup against long-tail baselines"],
                "blocked_claims": [],
                "source_path": "long.json",
            },
        ]

        row = target_rows(packages, [])[0]

        self.assertEqual(row["best_package"], "long_tail_speedup")
        self.assertEqual(
            row["baseline_triggers"],
            "aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand",
        )
        self.assertEqual(row["fastest_baseline_trigger_time_s"], 210.0)
        self.assertEqual(
            row["sota_pain_class"], "not_visible_baseline_time_cost_acceptable"
        )
        self.assertIn("acceptable-time threshold", row["sota_pain_evidence"])
        self.assertIn("baseline family_median_T=1410s", row["sota_pain_evidence"])

    def test_triage_marks_unacceptable_baseline_cost_as_visible_sota_pain(self):
        packages = [
            {
                "comparison_id": "hard_speedup",
                "target_id": "SYNTH_HARD",
                "package_status": "promote_or_extend_longruns",
                "verdict": "positive_speedup_matched_comparison",
                "matched_baselines": 9,
                "successful_baselines": [
                    "aflplusplus_vanilla",
                    "aflplusplus_cmplog",
                    "redqueen_operand",
                ],
                "fastest_baseline_trigger_time_s": 1900.0,
                "fastest_baseline_family_median_trigger_time_s": 3600.0,
                "best_formtrig_trigger_time_s": 0.5,
                "tte_speedup_over_fastest_baseline": 3800.0,
                "main_claim_strength": "hard_speedup_or_reliability_candidate",
                "max_budget_s": 7200,
                "formtrig_terminal": True,
                "strict_pretrigger_guidance": True,
                "observed_benefits": ["FORMTRIG speedup against high-cost baselines"],
                "blocked_claims": [],
                "source_path": "hard.json",
            },
        ]

        row = target_rows(packages, [])[0]

        self.assertEqual(row["sota_pain_class"], "visible_hard_speedup_or_reliability")
        self.assertIn("unstable or has low success", row["sota_pain_evidence"])
        self.assertIn("baseline fastest_T=1900s", row["sota_pain_evidence"])

    def test_guidance_gap_fail_fast_overrides_hard_speedup_candidate(self):
        packages = [
            {
                "comparison_id": "hard_speedup",
                "target_id": "SYNTH_HARD",
                "package_status": "promote_or_extend_longruns",
                "verdict": "positive_speedup_matched_comparison",
                "matched_baselines": 9,
                "successful_baselines": ["aflplusplus_vanilla"],
                "fastest_baseline_trigger_time_s": 1900.0,
                "best_formtrig_trigger_time_s": 0.5,
                "tte_speedup_over_fastest_baseline": 3800.0,
                "main_claim_strength": "hard_speedup_or_reliability_candidate",
                "max_budget_s": 7200,
                "formtrig_terminal": True,
                "strict_pretrigger_guidance": True,
                "observed_benefits": ["FORMTRIG speedup against high-cost baselines"],
                "blocked_claims": [],
                "source_path": "hard.json",
            },
        ]
        guidance = {
            "SYNTH_HARD": {
                "target_id": "SYNTH_HARD",
                "status": "fail_fast_baseline",
                "interpretation": "a faithful baseline reaches _T within the acceptable threshold",
                "fastest_successful_baseline_trigger_time_s": 120.0,
                "pretrigger_binary_flat_pass": True,
                "source_path": "gap.json",
            }
        }

        row = target_rows(packages, [], guidance)[0]

        self.assertEqual(row["disposition"], "demote_to_control_or_negative")
        self.assertEqual(row["sota_pain_class"], "not_visible_baseline_time_cost_acceptable")
        self.assertEqual(row["baseline_guidance_gap_status"], "fail_fast_baseline")
        self.assertIn("fastest_baseline_T=120s", row["baseline_guidance_gap_evidence"])
        self.assertIn("baseline guidance-gap gate is not measured_pass", row["blocked_claims"])

    def test_triage_prefers_replicated_endpoint_package_over_stale_negative(self):
        packages = [
            {
                "comparison_id": "old_negative",
                "target_id": "TIF012",
                "package_status": "control_or_negative",
                "verdict": "baseline_also_triggers_not_sota_advantage",
                "matched_baselines": 3,
                "successful_baselines": ["aflplusplus_vanilla"],
                "fastest_baseline_trigger_time_s": 300.0,
                "best_formtrig_trigger_time_s": None,
                "formtrig_terminal": False,
                "strict_pretrigger_guidance": True,
                "observed_benefits": ["old mechanism-only evidence"],
                "blocked_claims": ["matched baselines also trigger"],
                "source_path": "old.json",
            },
            {
                "comparison_id": "new_endpoint",
                "target_id": "TIF012",
                "package_status": "promote_or_extend_longruns",
                "verdict": "positive_endpoint_matched_comparison",
                "matched_baselines": 9,
                "successful_baselines": [],
                "fastest_baseline_trigger_time_s": None,
                "best_formtrig_trigger_time_s": 0.035,
                "formtrig_terminal": True,
                "strict_pretrigger_guidance": True,
                "observed_benefits": [
                    "FORMTRIG reaches terminal success where matched baselines do not trigger"
                ],
                "blocked_claims": [],
                "source_path": "new.json",
            },
        ]

        rows = target_rows(packages, [])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["disposition"], "candidate_extend_longruns")
        self.assertEqual(rows[0]["priority"], 18)
        self.assertEqual(rows[0]["best_package"], "new_endpoint")
        self.assertEqual(rows[0]["baseline_triggers"], "")
        self.assertEqual(rows[0]["fastest_baseline_trigger_time_s"], "")
        self.assertIn("longer matched-budget", rows[0]["next_action"])
        self.assertNotIn("matched baselines also trigger", rows[0]["blocked_claims"])

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
