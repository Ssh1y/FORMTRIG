import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class SummarizeLiveMagmaBaselinesTest(unittest.TestCase):
    def write_monitor(self, path: Path, target_id: str, reached: int, triggered: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{target_id}_R,{target_id}_T\n{reached},{triggered}\n", encoding="utf-8")

    def test_live_summary_feeds_guidance_gap_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_root = root / "baselines"
            run_dir = baseline_root / "magma" / "aflplusplus_vanilla_60s_rep1"
            default_dir = run_dir / "findings" / "default"
            default_dir.mkdir(parents=True)
            (default_dir / "fuzzer_stats").write_text(
                "run_time : 60\nexecs_done : 1234\nexecs_per_sec : 20\n",
                encoding="utf-8",
            )
            self.write_monitor(run_dir / "monitor" / "0", "TGT", 0, 0)
            self.write_monitor(run_dir / "monitor" / "30", "TGT", 10, 0)
            self.write_monitor(run_dir / "monitor" / "60", "TGT", 100, 0)

            summary_json = root / "summary.json"
            summary_tsv = root / "summary.tsv"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "summarize_live_magma_baselines.py"),
                    "--target-id",
                    "TGT",
                    "--run-root",
                    str(baseline_root),
                    "--out-json",
                    str(summary_json),
                    "--out-tsv",
                    str(summary_tsv),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            record = payload["records"][0]
            self.assertTrue(record["live_snapshot"])
            self.assertEqual(record["baseline"], "aflplusplus_vanilla")
            self.assertEqual(record["budget"], 60)
            self.assertEqual(record["rep"], 1)
            self.assertFalse(record["success"])
            self.assertEqual(record["magma_reached"], 100)
            self.assertEqual(record["magma_triggered"], 0)
            self.assertEqual(record["magma_first_reach_time_s"], 30)
            self.assertIn("live_snapshot_only", payload["claim_boundary"])
            self.assertTrue(summary_tsv.exists())

            out_dir = root / "guidance"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "analyze_baseline_guidance_gap.py"),
                    "--analysis-id",
                    "live_guidance",
                    "--target-id",
                    "TGT",
                    "--baseline-summary",
                    f"live={summary_json}",
                    "--out-dir",
                    str(out_dir),
                    "--required-baselines",
                    "aflplusplus_vanilla",
                    "--min-reps",
                    "1",
                ],
                cwd=REPO_ROOT,
                check=True,
            )
            gap = json.loads((out_dir / "baseline_guidance_gap.json").read_text(encoding="utf-8"))

        analysis = gap["analysis"]
        self.assertEqual(analysis["status"], "live_snapshot_only")
        self.assertTrue(analysis["live_snapshot_input"])
        self.assertTrue(analysis["pretrigger_binary_flat_pass"])
        self.assertTrue(analysis["endpoint_cost_pass"])
        group = analysis["baseline_groups"][0]
        self.assertEqual(group["total_reached"], 100)
        self.assertEqual(group["total_triggered"], 0)
        self.assertAlmostEqual(
            group["zero_trigger_rule_of_three_95_upper_bound_per_reach"],
            0.03,
        )

    def test_live_summary_accepts_multiple_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_root = root / "baselines"
            shard_root = root / "rep3_shard"
            run1 = baseline_root / "magma" / "aflplusplus_vanilla_60s_rep1"
            run3 = shard_root / "magma" / "aflplusplus_vanilla_60s_rep3"
            for run_dir, reached in ((run1, 10), (run3, 30)):
                default_dir = run_dir / "findings" / "default"
                default_dir.mkdir(parents=True)
                (default_dir / "fuzzer_stats").write_text(
                    "run_time : 60\nexecs_done : 1234\nexecs_per_sec : 20\n",
                    encoding="utf-8",
                )
                self.write_monitor(run_dir / "monitor" / "60", "TGT", reached, 0)

            summary_json = root / "summary.json"
            summary_tsv = root / "summary.tsv"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "summarize_live_magma_baselines.py"),
                    "--target-id",
                    "TGT",
                    "--run-root",
                    str(baseline_root),
                    "--run-root",
                    str(shard_root),
                    "--out-json",
                    str(summary_json),
                    "--out-tsv",
                    str(summary_tsv),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            payload = json.loads(summary_json.read_text(encoding="utf-8"))

        self.assertEqual(payload["run_roots"], [str(baseline_root), str(shard_root)])
        self.assertEqual(len(payload["records"]), 2)
        self.assertEqual([record["rep"] for record in payload["records"]], [1, 3])
        self.assertEqual(payload["records"][0]["source_root"], str(baseline_root))
        self.assertEqual(payload["records"][1]["source_root"], str(shard_root))
        self.assertEqual(payload["duplicate_runs"], [])


if __name__ == "__main__":
    unittest.main()
