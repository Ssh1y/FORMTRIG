import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_planner():
    path = Path(__file__).resolve().parents[1] / "tools" / "plan_formtrig_experiment_worklist.py"
    spec = importlib.util.spec_from_file_location("plan_formtrig_experiment_worklist", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExperimentWorklistTest(unittest.TestCase):
    def test_benefit_first_worklist_gates_controls_and_unvalidated_targets(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "libarchive"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "LIBARCHIVE_2936",
                        "analysis": {
                            "verdict": "positive_speedup_matched_comparison",
                            "longrun_10m_confirmation": {"budget_s": 600},
                            "repetition_summary": "evidence/repetition_summary.json",
                        },
                        "benefit_readout": {
                            "primary_benefits": ["FORMTRIG is faster by first _T"],
                            "design_evidence": ["strict_pretrigger_guidance"],
                            "blocked_claims": ["not a baseline-impossibility case"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 1,
                                "target_id": "LIBARCHIVE_2936",
                                "source": "real_cve",
                                "project": "libarchive",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "real_cve_replacement",
                                "status": "short_gate_triaged",
                                "existing_disposition": "candidate_extend_longruns",
                                "blockers": "",
                                "source_evidence": "cve.json",
                            },
                            {
                                "rank": 2,
                                "target_id": "PDF003",
                                "source": "magma",
                                "project": "poppler",
                                "primary_category": "binary-state-null",
                                "secondary_category": "compound-sequence-lifecycle",
                                "lane": "binding_spec_first",
                                "status": "needs_short_discovery",
                                "existing_disposition": "",
                                "blockers": "no BindingSpec candidate exists yet",
                                "source_evidence": "magma.json",
                            },
                            {
                                "rank": 3,
                                "target_id": "PNG007",
                                "source": "magma",
                                "project": "libpng",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "control_or_negative",
                                "status": "do_not_promote",
                                "existing_disposition": "",
                                "blockers": "terminal-only",
                                "source_evidence": "magma.json",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            self.assertEqual(payload["task_count"], 2)
            self.assertEqual(payload["skipped_control_count"], 1)
            tasks = {task["target_id"]: task for task in payload["tasks"]}
            self.assertEqual(tasks["LIBARCHIVE_2936"]["action"], "extend_matched_longrun")
            self.assertTrue(tasks["LIBARCHIVE_2936"]["runnable_now"])
            self.assertIn(
                "scripts/run_libarchive_2936_matched_longrun.sh --duration 7200 --reps 3 --jobs 4",
                tasks["LIBARCHIVE_2936"]["command"],
            )
            self.assertIn("first-_T speedup", tasks["LIBARCHIVE_2936"]["benefit_to_prove"])
            self.assertEqual(tasks["LIBARCHIVE_2936"]["comparison_verdict"], "positive_speedup_matched_comparison")
            self.assertEqual(tasks["PDF003"]["action"], "draft_binding_spec_then_short_screen")
            self.assertIn(
                "scripts/run_magma_baselines.sh --target-id PDF003 --durations 600 --jobs 4",
                tasks["PDF003"]["post_unblock_commands"],
            )
            self.assertIn("Endpoint benefit", payload["benefit_first_rule"])

    def test_endpoint_positive_comparison_overrides_stale_validation_lane(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "tif012_b5_endpoint"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "TIF012",
                        "analysis": {
                            "verdict": "positive_endpoint_matched_comparison",
                            "matched_baseline_count": 9,
                            "missing_required_baselines": [],
                            "best_formtrig_trigger_time_s": 0.035,
                            "baseline_groups": [
                                {
                                    "baseline": "aflplusplus_vanilla",
                                    "budget": 120,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                },
                                {
                                    "baseline": "aflplusplus_cmplog",
                                    "budget": 120,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                },
                                {
                                    "baseline": "redqueen_operand",
                                    "budget": 120,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                },
                            ],
                        },
                        "benefit_readout": {
                            "primary_benefits": [
                                "FORMTRIG reaches terminal success where matched baselines do not trigger"
                            ],
                            "design_evidence": [
                                "strict_pretrigger_guidance",
                                "matched_budget_endpoint_success",
                            ],
                            "blocked_claims": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 5,
                                "target_id": "TIF012",
                                "source": "magma",
                                "project": "libtiff",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "BindingSpec candidate is not native-site-map validated; no comparison package exists yet",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            self.assertEqual(payload["task_count"], 1)
            task = payload["tasks"][0]
            self.assertEqual(task["target_id"], "TIF012")
            self.assertEqual(task["action"], "extend_matched_longrun")
            self.assertEqual(task["priority"], "P0")
            self.assertFalse(task["runnable_now"])
            self.assertEqual(task["comparison_verdict"], "positive_endpoint_matched_comparison")
            self.assertIn("endpoint benefit", task["benefit_to_prove"])
            self.assertNotIn("BindingSpec candidate", " ".join(task["blocking_issue"]))
            self.assertTrue(
                any("TIF012.b5_current_3rep.list" in command for command in task["post_unblock_commands"])
            )
            self.assertTrue(
                any("tools/compare_formtrig_baselines.py" in command for command in task["post_unblock_commands"])
            )


if __name__ == "__main__":
    unittest.main()
