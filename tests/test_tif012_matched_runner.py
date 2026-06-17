import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class Tif012MatchedRunnerTest(unittest.TestCase):
    def test_generic_magma_runner_dry_run_emits_parallel_matched_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "pdf003"
            manifest = root / "PDF003.manifest"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: PDF003",
                        "category: binary-null",
                        "afl_args: -t 5000",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest_list = root / "PDF003.current_2rep.list"
            manifest_list.write_text(f"{manifest}\n{manifest}\n", encoding="utf-8")

            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_magma_matched_longrun.sh"),
                    "--target-id",
                    "PDF003",
                    "--mode",
                    "dry-run",
                    "--duration",
                    "60",
                    "--reps",
                    "2",
                    "--jobs",
                    "2",
                    "--out",
                    str(out_dir),
                    "--manifest-list",
                    str(manifest_list),
                    "--no-build-baselines",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [record["step"] for record in records],
                [
                    "formtrig_batch",
                    "magma_baselines",
                    "live_status",
                    "formtrig_gate",
                    "baseline_guidance_gap",
                    "comparison",
                    "evidence_bundle",
                ],
            )
            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertTrue(metadata["parallel_arms"])
            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("run_formtrig_manifest_batch.sh", plan)
            self.assertIn("run_magma_baselines.sh", plan)
            self.assertIn("live_magma_matched_status.py", plan)
            self.assertIn("analyze_baseline_guidance_gap.py", plan)
            self.assertIn("compare_formtrig_baselines.py", plan)
            self.assertIn("package_magma_matched_evidence.py", plan)
            self.assertIn("--afl-arg -t --afl-arg 5000", plan)
            self.assertIn("001_PDF003/out", plan)
            self.assertIn("002_PDF003/out", plan)

    def test_dry_run_emits_complete_matched_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "tif012"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_tif012_b5_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "60",
                    "--reps",
                    "2",
                    "--jobs",
                    "2",
                    "--out",
                    str(out_dir),
                    "--no-build-baselines",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(
                [record["step"] for record in records],
                ["formtrig_batch", "magma_baselines", "formtrig_gate", "comparison"],
            )
            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("run_formtrig_manifest_batch.sh", plan)
            self.assertIn("run_magma_baselines.sh", plan)
            self.assertIn("formtrig_experiment_gate.sh", plan)
            self.assertIn("compare_formtrig_baselines.py", plan)
            self.assertIn("--duration 60", plan)
            self.assertIn("--durations 60", plan)
            self.assertIn("--reps 2", plan)
            self.assertIn("--no-build", plan)
            self.assertIn("001_TIF012/out", plan)
            self.assertIn("002_TIF012/out", plan)

            manifest_list = out_dir / "formtrig_manifest_list.txt"
            self.assertEqual(
                len(manifest_list.read_text(encoding="utf-8").splitlines()),
                2,
            )

    def test_manifest_batch_uses_unique_dirs_for_duplicate_targets(self):
        script = (REPO_ROOT / "scripts" / "run_formtrig_manifest_batch.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("declare -A target_counts", script)
        self.assertIn('target_counts["$target_id_for_count"]', script)
        self.assertIn('${target_counts["$target_id"]:-0}" -gt 1', script)


if __name__ == "__main__":
    unittest.main()
