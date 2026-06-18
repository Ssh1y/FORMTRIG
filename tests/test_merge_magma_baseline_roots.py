import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class MergeMagmaBaselineRootsTest(unittest.TestCase):
    def write_run(
        self,
        root: Path,
        name: str,
        *,
        baseline: str,
        rep: int,
        reached: int,
        triggered: int,
    ) -> None:
        run_dir = root / "runs" / name
        run_dir.mkdir(parents=True)
        config = {"rep": rep}
        (run_dir / "run_config.json").write_text(
            json.dumps(config) + "\n",
            encoding="utf-8",
        )
        record = {
            "baseline": baseline,
            "budget": 7200,
            "config_path": str(run_dir / "run_config.json"),
            "magma_monitor": {
                "first_reach": {"time_s": 90},
                "snapshot_count": 3,
            },
            "run_id": f"PDF003:{baseline}:rep{rep}",
            "stats": {
                "execs_done": 1000 + rep,
                "execs_per_sec": 10,
                "magma_reached": reached,
                "magma_triggered": triggered,
                "run_time": 7200,
            },
            "success": triggered > 0,
            "target_id": "PDF003",
        }
        (run_dir / "run_record.json").write_text(
            json.dumps(record) + "\n",
            encoding="utf-8",
        )
        (run_dir / "events.jsonl").write_text("{}\n", encoding="utf-8")
        (run_dir / "status.json").write_text('{"ok":true}\n', encoding="utf-8")
        (run_dir / "captain_stdout.log").write_text("stdout\n", encoding="utf-8")
        (run_dir / "captain_stderr.log").write_text("stderr\n", encoding="utf-8")

    def test_merges_shards_and_rebuilds_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shard1 = root / "shard1"
            shard2 = root / "shard2"
            out = root / "merged"
            shard1.mkdir()
            shard2.mkdir()
            (shard1 / "run_metadata.txt").write_text(
                "target_id=PDF003\nreps=3\n",
                encoding="utf-8",
            )
            self.write_run(
                shard1,
                "aflplusplus_vanilla_7200s_rep1",
                baseline="aflplusplus_vanilla",
                rep=1,
                reached=10,
                triggered=0,
            )
            self.write_run(
                shard2,
                "aflplusplus_vanilla_7200s_rep2",
                baseline="aflplusplus_vanilla",
                rep=2,
                reached=20,
                triggered=0,
            )

            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "merge_magma_baseline_roots.py"),
                    "--out",
                    str(out),
                    "--source",
                    str(shard1),
                    "--source",
                    str(shard2),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(len(summary["records"]), 2)
            self.assertEqual(summary["groups"][0]["reps"], 2)
            self.assertTrue((out / "summary.tsv").exists())
            self.assertTrue((out / "baseline_merge_metadata.json").exists())
            self.assertTrue((out / "baseline_merge_metadata.md").exists())
            copied_record = json.loads(
                (
                    out
                    / "runs"
                    / "aflplusplus_vanilla_7200s_rep1"
                    / "run_record.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                copied_record["config_path"],
                str(out / "runs" / "aflplusplus_vanilla_7200s_rep1" / "run_config.json"),
            )

    def test_refuses_duplicate_run_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shard1 = root / "shard1"
            shard2 = root / "shard2"
            out = root / "merged"
            shard1.mkdir()
            shard2.mkdir()
            self.write_run(
                shard1,
                "aflplusplus_vanilla_7200s_rep1",
                baseline="aflplusplus_vanilla",
                rep=1,
                reached=10,
                triggered=0,
            )
            self.write_run(
                shard2,
                "aflplusplus_vanilla_7200s_rep1",
                baseline="aflplusplus_vanilla",
                rep=1,
                reached=20,
                triggered=0,
            )

            result = subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "merge_magma_baseline_roots.py"),
                    "--out",
                    str(out),
                    "--source",
                    str(shard1),
                    "--source",
                    str(shard2),
                ],
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate baseline run directory", result.stderr)

    def test_refuses_incomplete_run_without_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shard = root / "shard"
            out = root / "merged"
            (shard / "runs" / "aflplusplus_vanilla_7200s_rep1").mkdir(parents=True)

            result = subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "merge_magma_baseline_roots.py"),
                    "--out",
                    str(out),
                    "--source",
                    str(shard),
                ],
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing run_record.json", result.stderr)


if __name__ == "__main__":
    unittest.main()
