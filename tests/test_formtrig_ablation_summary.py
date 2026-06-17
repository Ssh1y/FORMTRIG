import csv
import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


GATE_FIELDS = [
    "suite",
    "run",
    "status",
    "reasons",
    "run_time",
    "execs_done",
    "execs_per_sec",
    "reached",
    "terminal_triggered",
    "first_terminal_time_s",
    "first_terminal_time_kind",
    "first_terminal_execs",
    "queued_progress",
    "accepted_non_trigger",
    "saved_non_trigger",
    "saved_triggered",
    "spec_lifted",
    "heuristic_lifted",
    "manual_lifted",
    "experiment_ready",
    "pretrigger_lift_guidance_ready",
    "non_trigger_candidate_lift_delta",
    "lift_delta_only_on_triggered",
    "binding_signal_status",
    "binding_signal_diagnosis",
    "out_dir",
]


def write_gate(root: Path, label: str, tte: float, execs: int, hook_source: str) -> tuple[Path, Path]:
    run_dir = root / label / "default"
    run_dir.mkdir(parents=True)
    (run_dir / "fuzzer_stats").write_text(
        "formtrig_typed_execs     : 256\n"
        "formtrig_typed_finds     : 7\n"
        "formtrig_typed_skips     : 1\n",
        encoding="utf-8",
    )
    gate = root / f"{label}.csv"
    with gate.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GATE_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "suite": "suite",
                "run": label,
                "status": "pass",
                "reasons": "ok",
                "run_time": "60",
                "execs_done": "1000",
                "execs_per_sec": "10",
                "reached": "100",
                "terminal_triggered": "1",
                "first_terminal_time_s": str(tte),
                "first_terminal_time_kind": "afl_crash_filename_exact",
                "first_terminal_execs": str(execs),
                "queued_progress": "1",
                "accepted_non_trigger": "1",
                "saved_non_trigger": "1",
                "saved_triggered": "0",
                "spec_lifted": "1",
                "heuristic_lifted": "0",
                "manual_lifted": "0",
                "experiment_ready": "true",
                "pretrigger_lift_guidance_ready": "true",
                "non_trigger_candidate_lift_delta": "true",
                "lift_delta_only_on_triggered": "false",
                "binding_signal_status": "pass",
                "binding_signal_diagnosis": "role_signal_progress_observed",
                "out_dir": str(run_dir),
            }
        )
    hook = root / f"{label}.hook.json"
    hook.write_text(
        json.dumps(
            {
                "enabled": hook_source != "disabled_ablation",
                "source": hook_source,
                "path": None,
                "sha256": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return gate, hook


class FormtrigAblationSummaryTest(unittest.TestCase):
    def test_summarizer_marks_hook_acceleration_and_control_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooked_gate, hooked_hook = write_gate(root, "hooked", 1.0, 10, "binding_spec")
            nohook_gate, nohook_hook = write_gate(root, "nohook", 20.0, 200, "disabled_ablation")
            generic_gate, generic_hook = write_gate(root, "generic", 50.0, 500, "cli_override")
            out_dir = root / "out"

            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "summarize_formtrig_ablation.py"),
                    "--ablation-id",
                    "unit",
                    "--target-id",
                    "LIBARCHIVE_2936",
                    "--gate",
                    f"hooked={hooked_gate}",
                    "--gate",
                    f"nohook={nohook_gate}",
                    "--gate",
                    f"generic={generic_gate}",
                    "--hook-metadata",
                    f"hooked={hooked_hook}",
                    "--hook-metadata",
                    f"nohook={nohook_hook}",
                    "--hook-metadata",
                    f"generic={generic_hook}",
                    "--min-reps",
                    "1",
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            payload = json.loads((out_dir / "ablation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(
                payload["analysis"]["verdict"],
                "target_specific_hook_accelerates_ablation_controls",
            )
            self.assertEqual(payload["analysis"]["nohook_time_speedup"], 20.0)
            self.assertIn(
                "controls also trigger, so this target remains weak SOTA-gap evidence",
                payload["analysis"]["blocked_claims"],
            )


if __name__ == "__main__":
    unittest.main()
