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
            index = (evidence / "EVIDENCE.md").read_text(encoding="utf-8")
            self.assertIn("hard_endpoint_gap_candidate", index)
            self.assertIn("FORMTRIG reaches _T", index)


if __name__ == "__main__":
    unittest.main()
