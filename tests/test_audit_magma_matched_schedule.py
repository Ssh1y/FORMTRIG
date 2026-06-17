import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class AuditMagmaMatchedScheduleTest(unittest.TestCase):
    def run_tool(self, run_root: Path) -> dict:
        output = subprocess.check_output(
            [
                "python3",
                str(REPO_ROOT / "tools" / "audit_magma_matched_schedule.py"),
                "--run-root",
                str(run_root),
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
        )
        return json.loads(output)

    def test_uses_new_metadata_schedule_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            run_root.mkdir()
            (run_root / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "target_id": "PDF003",
                        "mode": "dry-run",
                        "duration_s": 7200,
                        "reps": 3,
                        "baselines": "aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand",
                        "formtrig_jobs": 3,
                        "baseline_jobs": 9,
                        "baseline_count": 3,
                        "baseline_run_count": 9,
                        "baseline_batches": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = self.run_tool(run_root)

        self.assertEqual(payload["verdict"], "single_batch_baseline_schedule")
        self.assertEqual(payload["baseline_run_count"], 9)
        self.assertEqual(payload["baseline_batches"], 1)
        self.assertEqual(payload["recommended_baseline_jobs_for_one_batch"], 9)

    def test_falls_back_to_run_plan_for_old_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            run_root.mkdir()
            (run_root / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "target_id": "PDF003",
                        "mode": "execute",
                        "duration_s": 7200,
                        "reps": 3,
                        "baselines": "aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            records = [
                {
                    "step": "formtrig_batch",
                    "duration_s": 7200,
                    "reps": 3,
                    "command": "scripts/run_formtrig_manifest_batch.sh --jobs 3",
                    "log": "formtrig.log",
                },
                {
                    "step": "magma_baselines",
                    "duration_s": 7200,
                    "reps": 3,
                    "command": (
                        "scripts/run_magma_baselines.sh --durations 7200 "
                        "--baselines aflplusplus_vanilla\\,aflplusplus_cmplog\\,redqueen_operand "
                        "--reps 3 --jobs 3"
                    ),
                    "log": "baseline.log",
                },
            ]
            (run_root / "run_plan.jsonl").write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )

            payload = self.run_tool(run_root)

        self.assertEqual(payload["verdict"], "multi_batch_baseline_schedule")
        self.assertEqual(payload["baseline_count"], 3)
        self.assertEqual(payload["baseline_run_count"], 9)
        self.assertEqual(payload["formtrig_jobs"], 3)
        self.assertEqual(payload["baseline_jobs"], 3)
        self.assertEqual(payload["baseline_batches"], 3)
        self.assertEqual(payload["ideal_baseline_wall_s"], 21600)

    def test_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            run_root.mkdir()
            (run_root / "run_metadata.json").write_text(
                '{"target_id":"TGT","duration_s":60,"reps":1,"baselines":"a","baseline_jobs":1}\n',
                encoding="utf-8",
            )
            out_md = Path(tmp) / "audit.md"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "audit_magma_matched_schedule.py"),
                    "--run-root",
                    str(run_root),
                    "--out-md",
                    str(out_md),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            text = out_md.read_text(encoding="utf-8")

        self.assertIn("Magma Matched Schedule Audit", text)
        self.assertIn("claim boundary", text)


if __name__ == "__main__":
    unittest.main()
