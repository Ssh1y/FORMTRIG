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
            (run_root / "schedule_audit.json").write_text(
                json.dumps(
                    {
                        "verdict": "multi_batch_baseline_schedule",
                        "baseline_run_count": 3,
                        "baseline_jobs": 1,
                        "baseline_batches": 3,
                        "formtrig_jobs": 1,
                        "recommended_baseline_jobs_for_one_batch": 3,
                        "ideal_baseline_wall_s": 180,
                    }
                )
                + "\n",
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
        self.assertEqual(payload["baseline_root"], str(run_root / "baselines"))
        self.assertEqual(payload["baseline_roots"], [str(run_root / "baselines")])
        self.assertEqual(payload["baselines"]["run_count"], 1)
        self.assertEqual(payload["baselines"]["runs"][0]["source_root"], str(run_root / "baselines"))
        self.assertEqual(payload["baselines"]["groups"][0]["total_reached"], 123)
        self.assertEqual(payload["baselines"]["groups"][0]["total_triggered"], 0)
        self.assertEqual(payload["baselines"]["groups"][0]["zero_trigger_runs"], 1)
        self.assertAlmostEqual(
            payload["baselines"]["groups"][0][
                "zero_trigger_rule_of_three_95_upper_bound_per_reach"
            ],
            3.0 / 123.0,
        )
        self.assertEqual(payload["schedule"]["verdict"], "multi_batch_baseline_schedule")
        self.assertEqual(payload["schedule"]["baseline_run_count"], 3)
        self.assertEqual(payload["schedule"]["observed_baseline_runs"], 1)
        self.assertEqual(payload["schedule"]["missing_baseline_runs"], 2)
        self.assertEqual(payload["schedule"]["baseline_batches"], 3)

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
        self.assertIn("baseline roots:", text)
        self.assertIn("live_snapshot_only", text)
        self.assertIn("## Schedule", text)
        self.assertIn("missing_schedule_audit", text)
        self.assertIn("zero-T 95% ub", text)

    def test_accepts_external_baseline_dir_for_merged_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            (run_root / "formtrig").mkdir(parents=True)
            baseline_root = root / "merged_baselines"
            run_dir = baseline_root / "magma" / "redqueen_operand_60s_rep3"
            (run_dir / "findings" / "default").mkdir(parents=True)
            (run_dir / "findings" / "default" / "fuzzer_stats").write_text(
                "run_time : 60\nexecs_done : 3000\nexecs_per_sec : 100\n",
                encoding="utf-8",
            )
            monitor_dir = run_dir / "monitor"
            monitor_dir.mkdir()
            (monitor_dir / "30").write_text(
                "TGT_R,TGT_T\n100,0\n",
                encoding="utf-8",
            )
            (monitor_dir / "60").write_text(
                "TGT_R,TGT_T\n200,7\n",
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
                    "--baseline-dir",
                    str(baseline_root),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)

        self.assertEqual(payload["baseline_root"], str(baseline_root))
        self.assertEqual(payload["baseline_roots"], [str(baseline_root)])
        self.assertEqual(payload["baselines"]["run_count"], 1)
        self.assertEqual(payload["baselines"]["triggered_runs"], 1)
        self.assertEqual(payload["baselines"]["duplicate_runs"], [])
        self.assertEqual(payload["baselines"]["groups"][0]["baseline"], "redqueen_operand")
        self.assertEqual(payload["baselines"]["groups"][0]["total_reached"], 200)
        self.assertEqual(payload["baselines"]["groups"][0]["total_triggered"], 7)
        self.assertEqual(payload["baselines"]["runs"][0]["first_trigger_time_s"], 60)

    def test_accepts_repeated_baseline_dirs_for_live_shards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            (run_root / "formtrig").mkdir(parents=True)
            rep1_root = root / "baselines"
            rep3_root = root / "rep3_shard"
            for baseline_root, run_name, reached in (
                (rep1_root, "aflplusplus_vanilla_60s_rep1", 100),
                (rep3_root, "aflplusplus_vanilla_60s_rep3", 300),
            ):
                run_dir = baseline_root / "magma" / run_name
                (run_dir / "findings" / "default").mkdir(parents=True)
                (run_dir / "findings" / "default" / "fuzzer_stats").write_text(
                    "run_time : 60\nexecs_done : 3000\nexecs_per_sec : 100\n",
                    encoding="utf-8",
                )
                (run_dir / "monitor").mkdir()
                (run_dir / "monitor" / "60").write_text(
                    f"TGT_R,TGT_T\n{reached},0\n",
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
                    "--baseline-dir",
                    str(rep1_root),
                    "--baseline-dir",
                    str(rep3_root),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)

        self.assertEqual(payload["baseline_roots"], [str(rep1_root), str(rep3_root)])
        self.assertEqual(payload["baselines"]["run_count"], 2)
        self.assertEqual(payload["baselines"]["groups"][0]["total_reached"], 400)
        self.assertEqual(payload["baselines"]["duplicate_runs"], [])
        self.assertEqual(
            [row["source_root"] for row in payload["baselines"]["runs"]],
            [str(rep1_root), str(rep3_root)],
        )

    def test_repeated_baseline_dirs_prefer_later_duplicate_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run"
            (run_root / "formtrig").mkdir(parents=True)
            original_root = root / "baselines"
            shard_root = root / "rep3_shard"
            for baseline_root, reached, run_time in (
                (original_root, 10, 60),
                (shard_root, 300, 3600),
            ):
                run_dir = baseline_root / "magma" / "aflplusplus_vanilla_60s_rep3"
                (run_dir / "findings" / "default").mkdir(parents=True)
                (run_dir / "findings" / "default" / "fuzzer_stats").write_text(
                    f"run_time : {run_time}\nexecs_done : 3000\nexecs_per_sec : 100\n",
                    encoding="utf-8",
                )
                (run_dir / "monitor").mkdir()
                (run_dir / "monitor" / "60").write_text(
                    f"TGT_R,TGT_T\n{reached},0\n",
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
                    "--baseline-dir",
                    str(original_root),
                    "--baseline-dir",
                    str(shard_root),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)

        self.assertEqual(payload["baselines"]["raw_run_count"], 2)
        self.assertEqual(payload["baselines"]["run_count"], 1)
        self.assertEqual(payload["baselines"]["groups"][0]["total_reached"], 300)
        self.assertEqual(payload["baselines"]["runs"][0]["source_root"], str(shard_root))
        self.assertEqual(payload["baselines"]["duplicate_run_names"], ["aflplusplus_vanilla_60s_rep3"])
        self.assertEqual(len(payload["baselines"]["duplicate_runs"]), 1)
        self.assertEqual(payload["baselines"]["duplicate_runs"][0]["policy"], "prefer-later")
        self.assertEqual(
            payload["baselines"]["duplicate_runs"][0]["discarded_source_root"],
            str(original_root),
        )
        self.assertEqual(
            payload["baselines"]["duplicate_runs"][0]["kept_source_root"],
            str(shard_root),
        )


if __name__ == "__main__":
    unittest.main()
