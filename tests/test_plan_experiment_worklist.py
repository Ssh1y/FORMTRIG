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


if __name__ == "__main__":
    unittest.main()
