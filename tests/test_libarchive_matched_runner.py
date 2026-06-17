import csv
import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class LibarchiveMatchedRunnerTest(unittest.TestCase):
    def test_generic_hook_writes_target_agnostic_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orig = root / "orig"
            mut = root / "mut"
            out = root / "out"
            orig.write_bytes(b"alpha_beta")
            mut.write_bytes(b"alphaXbeta")

            subprocess.run(
                [
                    str(REPO_ROOT / "scripts" / "formtrig_hooks" / "generic_ascii_delimiter_hook.py"),
                    str(orig),
                    str(mut),
                    str(out),
                    "10",
                    "0",
                    "5",
                    "5",
                    "1",
                    "2",
                    "0",
                    "0",
                    "1",
                    "1",
                    "4",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            result = out.read_bytes()
            self.assertTrue(result)
            self.assertLessEqual(len(result), 4096)
            self.assertNotEqual(result, orig.read_bytes())

    def test_dry_run_emits_matched_formtrig_and_baseline_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "matched"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_libarchive_2936_matched_longrun.sh"),
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
            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("scripts/run_formtrig_aflpp_campaign.sh", plan)
            self.assertIn("tools/run_post_reach_baseline.py", plan)
            self.assertIn("--budget-sec 60", plan)
            self.assertIn("5000+", plan)

    def test_dry_run_emits_formtrig_ablation_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ablations"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_libarchive_2936_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "60",
                    "--reps",
                    "1",
                    "--arms",
                    "formtrig,formtrig_nohook,formtrig_generic_hook",
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

            self.assertEqual(
                [(record["arm"], record["rep"]) for record in records],
                [
                    ("formtrig", 1),
                    ("formtrig_nohook", 1),
                    ("formtrig_generic_hook", 1),
                ],
            )
            commands = {record["arm"]: record["command"] for record in records}
            self.assertNotIn("--no-mutation-hook", commands["formtrig"])
            self.assertNotIn("--mutation-hook", commands["formtrig"])
            self.assertIn("--no-mutation-hook", commands["formtrig_nohook"])
            self.assertIn("--mutation-hook", commands["formtrig_generic_hook"])
            self.assertIn("generic_ascii_delimiter_hook.py", commands["formtrig_generic_hook"])

    def test_gate_prefers_exact_crash_filename_time_and_execs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default_dir = root / "campaign" / "default"
            crash_dir = default_dir / "crashes"
            crash_dir.mkdir(parents=True)
            (default_dir / "formtrig_diagnosis.json").write_text(
                json.dumps(
                    {
                        "experiment_ready": True,
                        "pretrigger_lift_guidance_ready": True,
                        "non_trigger_candidate_lift_delta": True,
                        "lift_delta_only_on_triggered_candidates": False,
                        "saved_non_trigger_progress_events": 1,
                        "saved_triggered_progress_events": 1,
                        "terminal_triggered_execs": 1,
                        "formtrig_queued_progress": 1,
                        "formtrig_reached_execs": 1,
                        "spec_lifted_events": 1,
                        "heuristic_lifted_events": 0,
                        "manual_lifted_events": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (default_dir / "formtrig_summary.json").write_text(
                json.dumps(
                    {
                        "spec_lifted_events": 1,
                        "heuristic_lifted_events": 0,
                        "manual_lifted_events": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (default_dir / "formtrig_binding_signal_diagnosis.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "diagnosis": "role_signal_progress_observed",
                        "accepted_non_trigger_progress_events": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (default_dir / "fuzzer_stats").write_text(
                "run_time        : 60\nexecs_done      : 100\nexecs_per_sec   : 1.67\n",
                encoding="utf-8",
            )
            (
                crash_dir
                / "id:000000,sig:11,src:000000,time:1220,execs:32,op:ftgtype,pos:18"
            ).write_text("crash", encoding="utf-8")

            gate_out = root / "gate"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "formtrig_experiment_gate.sh"),
                    "--terminal-oracle-only",
                    "--out",
                    str(gate_out),
                    "--run",
                    f"rep1={root / 'campaign'}",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            with (gate_out / "gate_summary.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["first_terminal_time_s"], "1.22")
            self.assertEqual(row["first_terminal_time_kind"], "afl_crash_filename_exact")
            self.assertEqual(row["first_terminal_execs"], "32")


if __name__ == "__main__":
    unittest.main()
