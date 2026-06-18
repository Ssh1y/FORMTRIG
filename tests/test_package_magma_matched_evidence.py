import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class PackageMagmaMatchedEvidenceTest(unittest.TestCase):
    def test_packages_small_matched_evidence_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            comparison_dir = root / "comparison"
            baseline_dir = run_root / "baselines"
            formtrig_dir = run_root / "formtrig"
            gate_dir = run_root / "formtrig_gate"
            guidance_dir = run_root / "baseline_guidance_gap"

            run_root.mkdir(parents=True)
            (run_root / "live_status.json").write_text('{"target_id":"PDF003"}\n', encoding="utf-8")
            (run_root / "live_status.md").write_text("# live\n", encoding="utf-8")
            (run_root / "formtrig_signal_path.json").write_text(
                json.dumps(
                    {
                        "guidance_capability": {
                            "actionable_typed_nontrigger_runs": 1,
                            "interpretation": "stable/sortable/actionable/mutable",
                            "mutable_typed_find_runs": 1,
                            "sortable_lifted_df_runs": 1,
                            "stable_frontier_runs": 1,
                            "strict_saved_pretrigger_runs": 0,
                            "total_typed_execs": 10,
                            "total_typed_finds": 3,
                        },
                        "run_count": 1,
                        "typed_attribution": "terminal_after_typed_lifted_nontrigger_stage",
                        "verdict": "terminal_after_calibrated_frontier_only",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_root / "formtrig_signal_path.md").write_text("# path\n", encoding="utf-8")
            (run_root / "schedule_audit.json").write_text(
                '{"verdict":"single_batch_baseline_schedule"}\n',
                encoding="utf-8",
            )
            (run_root / "schedule_audit.md").write_text("# schedule\n", encoding="utf-8")

            (baseline_dir / "runs" / "aflplusplus_vanilla_60s_rep1").mkdir(parents=True)
            (baseline_dir / "summary.json").write_text('{"records":[]}\n', encoding="utf-8")
            (baseline_dir / "summary.tsv").write_text("baseline\n", encoding="utf-8")
            (baseline_dir / "runs" / "aflplusplus_vanilla_60s_rep1" / "run_record.json").write_text(
                '{"success": false}\n',
                encoding="utf-8",
            )
            (baseline_dir / "runs" / "aflplusplus_vanilla_60s_rep1" / "events.jsonl").write_text(
                "{}\n",
                encoding="utf-8",
            )

            rep_dir = formtrig_dir / "001_PDF003" / "out"
            default_dir = rep_dir / "default"
            default_dir.mkdir(parents=True)
            (formtrig_dir / "batch_summary.csv").write_text("target_id,status\n", encoding="utf-8")
            (formtrig_dir / "batch_summary.jsonl").write_text("{}\n", encoding="utf-8")
            (rep_dir / "formtrig_mutation_hook.json").write_text("{}\n", encoding="utf-8")
            (default_dir / "formtrig_summary.json").write_text("{}\n", encoding="utf-8")
            (default_dir / "formtrig_diagnosis.json").write_text("{}\n", encoding="utf-8")
            (default_dir / "fuzzer_stats").write_text("execs_done : 1\n", encoding="utf-8")

            gate_dir.mkdir(parents=True)
            (gate_dir / "gate_summary.csv").write_text("run,status\n", encoding="utf-8")
            (gate_dir / "gate_summary.jsonl").write_text("{}\n", encoding="utf-8")
            (gate_dir / "gate_report.md").write_text("# gate\n", encoding="utf-8")

            guidance_dir.mkdir(parents=True)
            (guidance_dir / "baseline_guidance_gap.json").write_text(
                '{"analysis":{"status":"measured_pass"}}\n',
                encoding="utf-8",
            )
            (guidance_dir / "baseline_guidance_gap.md").write_text("# gap\n", encoding="utf-8")
            (guidance_dir / "baseline_guidance_gap_runs.tsv").write_text("run\n", encoding="utf-8")

            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "comparison_id": "synthetic",
                        "target_id": "PDF003",
                        "analysis": {
                            "verdict": "positive_endpoint_matched_comparison",
                            "matched_baseline_count": 3,
                            "best_formtrig_trigger_time_s": 0.29,
                            "experiment_strength": {
                                "main_claim_strength": "hard_endpoint_gap_candidate"
                            },
                        },
                        "benefit_readout": {
                            "primary_benefits": ["FORMTRIG reaches _T"],
                            "blocked_claims": ["no strict pre-trigger guidance"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "package_magma_matched_evidence.py"),
                    "--target-id",
                    "PDF003",
                    "--duration",
                    "60",
                    "--reps",
                    "1",
                    "--run-root",
                    str(run_root),
                    "--comparison-dir",
                    str(comparison_dir),
                    "--baseline-dir",
                    str(baseline_dir),
                    "--formtrig-dir",
                    str(formtrig_dir),
                    "--gate-dir",
                    str(gate_dir),
                    "--guidance-dir",
                    str(guidance_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            evidence = comparison_dir / "evidence"
            self.assertTrue((evidence / "baselines" / "summary.json").exists())
            self.assertTrue((evidence / "formtrig" / "gate_summary.csv").exists())
            self.assertTrue((evidence / "guidance_gap" / "baseline_guidance_gap.json").exists())
            self.assertTrue((evidence / "live_status" / "live_status.json").exists())
            self.assertTrue((evidence / "live_status" / "live_status.md").exists())
            self.assertTrue(
                (evidence / "formtrig_signal_path" / "formtrig_signal_path.json").exists()
            )
            self.assertTrue(
                (evidence / "formtrig_signal_path" / "formtrig_signal_path.md").exists()
            )
            self.assertTrue((evidence / "schedule_audit" / "schedule_audit.json").exists())
            self.assertTrue((evidence / "schedule_audit" / "schedule_audit.md").exists())
            index = (evidence / "EVIDENCE.md").read_text(encoding="utf-8")
            self.assertIn("hard_endpoint_gap_candidate", index)
            self.assertIn("FORMTRIG reaches _T", index)
            self.assertIn("live_status/", index)
            self.assertIn("formtrig_signal_path/", index)
            self.assertIn("schedule_audit/", index)
            self.assertIn("FORMTRIG Guidance Capability", index)
            self.assertIn("stable frontier runs: `1/1`", index)
            self.assertIn("sortable lifted `D_F` runs: `1/1`", index)
            self.assertIn("total typed finds: `3` / typed execs `10`", index)
            self.assertIn("strict saved pre-trigger runs: `0/1`", index)


if __name__ == "__main__":
    unittest.main()
