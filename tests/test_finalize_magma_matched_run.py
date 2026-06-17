import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class FinalizeMagmaMatchedRunTest(unittest.TestCase):
    def test_dry_run_emits_complete_finalize_flow_from_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            guidance_out = root / "guidance"
            comparison_out = root / "comparison"
            run_root.mkdir()
            (run_root / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "target_id": "PDF003",
                        "duration_s": 60,
                        "reps": 2,
                        "baselines": "aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "finalize_magma_matched_run.sh"),
                    "--run-root",
                    str(run_root),
                    "--guidance-out",
                    str(guidance_out),
                    "--comparison-out",
                    str(comparison_out),
                    "--mode",
                    "dry-run",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (run_root / "finalize_plan.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            plan = (run_root / "finalize_plan.sh").read_text(encoding="utf-8")

        self.assertEqual(
            [record["step"] for record in records],
            [
                "schedule_audit",
                "live_status",
                "formtrig_signal_path",
                "formtrig_gate",
                "baseline_guidance_gap",
                "comparison",
                "evidence_bundle",
            ],
        )
        self.assertIn("audit_magma_matched_schedule.py", plan)
        self.assertIn("live_magma_matched_status.py", plan)
        self.assertIn("analyze_formtrig_signal_path.py", plan)
        self.assertIn("formtrig_experiment_gate.sh", plan)
        self.assertIn("analyze_baseline_guidance_gap.py", plan)
        self.assertIn("compare_formtrig_baselines.py", plan)
        self.assertIn("package_magma_matched_evidence.py", plan)
        self.assertIn("rep1=", plan)
        self.assertIn("rep2=", plan)
        self.assertIn(str(guidance_out), plan)
        self.assertIn(str(comparison_out), plan)


if __name__ == "__main__":
    unittest.main()
