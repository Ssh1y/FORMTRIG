import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class LiveMagmaMatchedStatusTest(unittest.TestCase):
    def test_summarizes_live_formtrig_and_baseline_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            default_dir = run_root / "formtrig" / "001_TGT" / "out" / "default"
            default_dir.mkdir(parents=True)
            (default_dir / "fuzzer_stats").write_text(
                "\n".join(
                    [
                        "run_time          : 42",
                        "execs_done        : 100",
                        "execs_per_sec     : 2.38",
                        "formtrig_reached_execs   : 80",
                        "formtrig_triggered_execs : 3",
                        "formtrig_queued_progress : 2",
                        "formtrig_frontier_updates: 1",
                        "formtrig_typed_execs     : 12",
                        "formtrig_typed_finds     : 4",
                        "formtrig_saved_triggered_log_seen: 1",
                        "formtrig_saved_non_trigger_log_seen: 0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (default_dir / "formtrig_progress.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "event": "saved_progress",
                                "triggered": False,
                                "execs_done": 7,
                            }
                        ),
                        json.dumps(
                            {
                                "event": "saved_progress",
                                "triggered": True,
                                "execs_done": 9,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            baseline_dir = (
                run_root
                / "baselines"
                / "magma"
                / "aflplusplus_vanilla_60s_rep1"
            )
            (baseline_dir / "findings" / "default").mkdir(parents=True)
            (baseline_dir / "findings" / "default" / "fuzzer_stats").write_text(
                "run_time : 30\nexecs_done : 3000\nexecs_per_sec : 100\n",
                encoding="utf-8",
            )
            monitor_dir = baseline_dir / "monitor"
            monitor_dir.mkdir()
            (monitor_dir / "30").write_text(
                "TGT_R,TGT_T\n123,0\n",
                encoding="utf-8",
            )

            output = subprocess.check_output(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "live_magma_matched_status.py"),
                    "--target-id",
                    "TGT",
                    "--run-root",
                    str(run_root),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)

        self.assertEqual(payload["formtrig"]["run_count"], 1)
        self.assertEqual(payload["formtrig"]["pretrigger_guidance_seen_runs"], 1)
        self.assertEqual(payload["formtrig"]["total_saved_non_trigger"], 1)
        self.assertEqual(payload["formtrig"]["total_saved_triggered"], 1)
        self.assertEqual(payload["baselines"]["run_count"], 1)
        self.assertEqual(payload["baselines"]["groups"][0]["total_reached"], 123)
        self.assertEqual(payload["baselines"]["groups"][0]["total_triggered"], 0)

    def test_writes_markdown_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            (run_root / "formtrig").mkdir(parents=True)
            out_md = root / "status.md"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "live_magma_matched_status.py"),
                    "--target-id",
                    "TGT",
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

        self.assertIn("Live Matched Status: TGT", text)
        self.assertIn("live_snapshot_only", text)


if __name__ == "__main__":
    unittest.main()
