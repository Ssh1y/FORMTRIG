import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class CheckMagmaMatchedFinalizeReadyTest(unittest.TestCase):
    def write_run(
        self,
        root: Path,
        name: str,
        *,
        complete: bool = True,
    ) -> None:
        run_dir = root / "runs" / name
        run_dir.mkdir(parents=True, exist_ok=True)
        if complete:
            (run_dir / "run_record.json").write_text('{"ok": true}\n', encoding="utf-8")
        (run_dir / "status.json").write_text('{"status": "done"}\n', encoding="utf-8")

    def write_active_run(self, root: Path, run_root: Path, baseline_roots: list[Path]) -> Path:
        active = root / "active_runs.json"
        active.write_text(
            json.dumps(
                {
                    "runs": [
                        {
                            "target_id": "TGT",
                            "duration_s": 60,
                            "repetitions": 2,
                            "run_root": str(run_root),
                            "guidance_out": str(root / "guidance"),
                            "comparison_out": str(root / "comparison"),
                            "baseline_roots": [str(path) for path in baseline_roots],
                        }
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return active

    def test_not_ready_when_later_duplicate_shard_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "matched"
            run_root.mkdir()
            (run_root / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "target_id": "TGT",
                        "baselines": "aflplusplus_vanilla,redqueen_operand",
                        "duration_s": 60,
                        "reps": 2,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            original = root / "baselines"
            shard = root / "rep2_shard"
            for name in (
                "aflplusplus_vanilla_60s_rep1",
                "redqueen_operand_60s_rep1",
                "aflplusplus_vanilla_60s_rep2",
                "redqueen_operand_60s_rep2",
            ):
                self.write_run(original, name)
            self.write_run(shard, "aflplusplus_vanilla_60s_rep2", complete=False)
            self.write_run(shard, "redqueen_operand_60s_rep2")
            active = self.write_active_run(root, run_root, [original, shard])

            output = subprocess.check_output(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "check_magma_matched_finalize_ready.py"),
                    "--active-runs",
                    str(active),
                    "--target-id",
                    "TGT",
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)
            failed = subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "check_magma_matched_finalize_ready.py"),
                    "--active-runs",
                    str(active),
                    "--target-id",
                    "TGT",
                    "--format",
                    "json",
                    "--fail-if-not-ready",
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        self.assertFalse(payload["ready_to_finalize"])
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(payload["expected_run_count"], 4)
        self.assertEqual(payload["selected_run_count"], 4)
        self.assertEqual(payload["complete_selected_run_count"], 3)
        self.assertEqual(
            [row["run"] for row in payload["incomplete_runs"]],
            ["aflplusplus_vanilla_60s_rep2"],
        )
        self.assertEqual(len(payload["duplicate_runs"]), 2)

    def test_ready_when_all_later_duplicate_shard_records_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "matched"
            run_root.mkdir()
            (run_root / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "target_id": "TGT",
                        "baselines": "aflplusplus_vanilla,redqueen_operand",
                        "duration_s": 60,
                        "reps": 2,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            original = root / "baselines"
            shard = root / "rep2_shard"
            self.write_run(original, "aflplusplus_vanilla_60s_rep1")
            self.write_run(original, "redqueen_operand_60s_rep1")
            self.write_run(original, "aflplusplus_vanilla_60s_rep2")
            self.write_run(original, "redqueen_operand_60s_rep2")
            self.write_run(shard, "aflplusplus_vanilla_60s_rep2")
            self.write_run(shard, "redqueen_operand_60s_rep2")
            active = self.write_active_run(root, run_root, [original, shard])

            output = subprocess.check_output(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "check_magma_matched_finalize_ready.py"),
                    "--active-runs",
                    str(active),
                    "--target-id",
                    "TGT",
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)

        self.assertTrue(payload["ready_to_finalize"])
        self.assertEqual(payload["complete_selected_run_count"], 4)
        self.assertEqual(payload["missing_runs"], [])
        self.assertEqual(payload["incomplete_runs"], [])
        self.assertIn("--duplicate-policy", payload["merge_command"])
        self.assertIn("prefer-later", payload["merge_command"])
        self.assertEqual(payload["finalize_command"][0], "scripts/finalize_magma_matched_run.sh")


if __name__ == "__main__":
    unittest.main()
