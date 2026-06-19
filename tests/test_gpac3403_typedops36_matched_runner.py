import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class Gpac3403TypedOps36MatchedRunnerTest(unittest.TestCase):
    def test_dry_run_emits_corrected_formtrig_and_baseline_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_typedops36_matched_longrun.sh"),
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
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 8)
            self.assertEqual(
                {(record["arm"], record["rep"]) for record in records},
                {
                    ("formtrig", 1),
                    ("aflplusplus_vanilla", 1),
                    ("aflplusplus_cmplog", 1),
                    ("redqueen_operand", 1),
                    ("formtrig", 2),
                    ("aflplusplus_vanilla", 2),
                    ("aflplusplus_cmplog", 2),
                    ("redqueen_operand", 2),
                },
            )
            for record in records:
                self.assertEqual(record["typed_ops"], 36)
                self.assertEqual(record["typed_mutation_max"], 64)
                self.assertEqual(record["duration_s"], 60)

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["target_id"], "GPAC_3403")
            self.assertEqual(metadata["typed_ops"], 36)
            self.assertEqual(metadata["typed_mutation_max"], 64)
            self.assertIn("MP4Box", metadata["target_cmd"])
            self.assertIn("-cat @@ ", metadata["target_cmd"])
            self.assertIn("white.mp4", metadata["target_cmd"])

            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("run_formtrig_aflpp_campaign.sh", plan)
            self.assertIn("--typed-ops 36", plan)
            self.assertIn("FORMTRIG_TYPED_MUTATION_MAX=64", plan)
            self.assertIn("GPAC_3403.native_b6_hevc_annexb_input_candidate.yml", plan)
            self.assertIn("MP4Box -cat @@ ", plan)
            self.assertIn("aflplusplus_vanilla", plan)
            self.assertIn("aflplusplus_cmplog", plan)
            self.assertIn("redqueen_operand", plan)
            self.assertIn("--cmplog-binary", plan)
            self.assertIn("AFL_NO_AFFINITY=1", plan)
            self.assertIn("ASAN_OPTIONS=abort_on_error=1", plan)

    def test_dry_run_supports_nohook_ablation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_nohook"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_typedops36_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "30",
                    "--reps",
                    "1",
                    "--arms",
                    "formtrig,formtrig_nohook",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["arm"] for record in records], ["formtrig", "formtrig_nohook"])
            commands = {record["arm"]: record["command"] for record in records}
            self.assertNotIn("--no-mutation-hook", commands["formtrig"])
            self.assertIn("--no-mutation-hook", commands["formtrig_nohook"])


if __name__ == "__main__":
    unittest.main()
