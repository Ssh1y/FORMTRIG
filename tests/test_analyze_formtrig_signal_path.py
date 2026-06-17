import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class AnalyzeFormtrigSignalPathTest(unittest.TestCase):
    def write_run(self, root: Path, name: str, events: list[dict]) -> Path:
        default_dir = root / "formtrig" / name / "out" / "default"
        default_dir.mkdir(parents=True)
        (default_dir / "fuzzer_stats").write_text(
            "\n".join(
                [
                    "run_time          : 60",
                    "execs_done        : 100",
                    "execs_per_sec     : 1.66",
                    "formtrig_reached_execs   : 90",
                    "formtrig_triggered_execs : 1",
                    "formtrig_queued_progress : 2",
                    "formtrig_frontier_updates: 1",
                    "formtrig_typed_execs     : 10",
                    "formtrig_typed_finds     : 3",
                    "formtrig_saved_non_trigger_log_seen: 0",
                    "formtrig_saved_triggered_log_seen: 1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (default_dir / "formtrig_progress.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events) + "\n",
            encoding="utf-8",
        )
        return root / "formtrig" / name

    def run_tool(self, root: Path) -> dict:
        output = subprocess.check_output(
            [
                "python3",
                str(REPO_ROOT / "tools" / "analyze_formtrig_signal_path.py"),
                "--target-id",
                "TGT",
                "--formtrig-dir",
                str(root / "formtrig"),
                "--run-root",
                str(root),
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
        )
        return json.loads(output)

    def test_terminal_after_calibrated_frontier_is_not_strict_pretrigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "calibrated_frontier",
                        "reason": "initial_frontier_seed",
                        "triggered": False,
                        "execs_done": 7,
                        "d_f": 3,
                        "d_f_spec_lifted": 3,
                        "source_flags": 2,
                    },
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "triggered": True,
                        "execs_done": 9,
                        "d_f": 0,
                        "d_f_spec_lifted": 0,
                        "source_flags": 2,
                    },
                ],
            )

            payload = self.run_tool(root)

        self.assertEqual(payload["verdict"], "terminal_after_calibrated_frontier_only")
        run = payload["runs"][0]["progress_path"]
        self.assertFalse(run["strict_pretrigger_guidance_seen"])
        self.assertEqual(run["calibrated_non_trigger_events"], 1)
        self.assertEqual(run["saved_non_trigger_events"], 0)
        self.assertEqual(run["saved_trigger_events"], 1)

    def test_saved_non_trigger_before_trigger_is_strict_pretrigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "saved_progress",
                        "reason": "lifted-feature improvement",
                        "triggered": False,
                        "execs_done": 5,
                        "d_f": 2,
                        "d_f_spec_lifted": 2,
                        "source_flags": 2,
                    },
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "triggered": True,
                        "execs_done": 9,
                        "d_f": 0,
                        "d_f_spec_lifted": 0,
                        "source_flags": 2,
                    },
                ],
            )

            payload = self.run_tool(root)

        self.assertEqual(payload["verdict"], "strict_pretrigger_guidance_observed")
        run = payload["runs"][0]["progress_path"]
        self.assertTrue(run["strict_pretrigger_guidance_seen"])
        self.assertEqual(run["first_saved_non_trigger"]["execs_done"], 5)

    def test_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(root, "001_TGT", [])
            out_md = root / "signal_path.md"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "analyze_formtrig_signal_path.py"),
                    "--target-id",
                    "TGT",
                    "--formtrig-dir",
                    str(root / "formtrig"),
                    "--out-md",
                    str(out_md),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            text = out_md.read_text(encoding="utf-8")

        self.assertIn("FORMTRIG Signal Path: TGT", text)
        self.assertIn("claim boundary", text)


if __name__ == "__main__":
    unittest.main()
