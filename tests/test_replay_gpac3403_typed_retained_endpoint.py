import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "replay_gpac3403_typed_retained_endpoint.py"


class ReplayGpac3403TypedRetainedEndpointTest(unittest.TestCase):
    def test_replays_retained_records_and_writes_endpoint_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            candidate = run_dir / "candidate.hevc"
            candidate.write_bytes(b"\x00\x00\x00\x01\x40\x01\x80")
            records = run_dir / "typed_retained_records.jsonl"
            records.write_text(
                json.dumps(
                    {
                        "index": 0,
                        "path": str(candidate),
                        "d_f_spec_lifted": 0.5,
                        "op": 39,
                        "sample": 2,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            endpoint_code = (
                "import sys; "
                "sys.stderr.write('[HEVC] VPS max layer ID 9 but GPAC only supports 4\\n'); "
                "sys.exit(0)"
            )
            endpoint_cmd = f"{shlex.quote(sys.executable)} -c {shlex.quote(endpoint_code)} @@"
            summary = run_dir / "summary.json"
            enriched = run_dir / "endpoint_records.jsonl"

            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--run-dir",
                    str(run_dir),
                    "--endpoint-cmd",
                    endpoint_cmd,
                    "--out-summary",
                    str(summary),
                    "--out-records-jsonl",
                    str(enriched),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            report = json.loads(summary.read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in enriched.read_text(encoding="utf-8").splitlines()]
            variant_stderr_exists = (run_dir / "logs" / "variant_000000.endpoint_1.stderr").is_file()

        self.assertEqual(report["schema"], "formtrig_gpac3403_typed_retained_endpoint_replay_v1")
        self.assertEqual(report["input_records"], 1)
        self.assertEqual(report["existing_inputs"], 1)
        self.assertEqual(report["replayed_records"], 1)
        self.assertEqual(report["endpoint_replayed_variants"], 1)
        self.assertEqual(report["endpoint_exit_code_counts"]["0"], 1)
        self.assertEqual(report["d_f_spec_lifted_min"], 0.5)
        self.assertTrue(variant_stderr_exists)
        self.assertEqual(rows[0]["endpoint_replay_source"], "FORMTRIG_TYPED_RETAIN")
        self.assertEqual(rows[0]["endpoint_probes"][0]["exit_code"], 0)

    def test_replays_positive_control_and_detects_sanitizer_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            candidate = run_dir / "candidate.hevc"
            positive = run_dir / "positive.hevc"
            candidate.write_bytes(b"candidate")
            positive.write_bytes(b"positive")
            (run_dir / "typed_retained_records.jsonl").write_text(
                json.dumps({"index": 4, "path": str(candidate), "d_f_spec_lifted": 1.0}) + "\n",
                encoding="utf-8",
            )
            endpoint_code = (
                "import sys; "
                "sys.stderr.write('SUMMARY: AddressSanitizer: double-free\\n'); "
                "sys.exit(86)"
            )
            endpoint_cmd = f"{shlex.quote(sys.executable)} -c {shlex.quote(endpoint_code)} @@"
            summary = run_dir / "summary.json"

            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--run-dir",
                    str(run_dir),
                    "--endpoint-cmd",
                    endpoint_cmd,
                    "--endpoint-positive-control",
                    str(positive),
                    "--out-summary",
                    str(summary),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            report = json.loads(summary.read_text(encoding="utf-8"))
            variant_stderr_exists = (run_dir / "logs" / "variant_000004.endpoint_1.stderr").is_file()
            positive_stderr_exists = (run_dir / "logs" / "positive_control.endpoint_1.stderr").is_file()

        self.assertEqual(report["endpoint_sanitizer_crashes"], 1)
        self.assertEqual(report["positive_control_probe_runs"], 1)
        self.assertEqual(report["positive_control_sanitizer_crashes"], 1)
        self.assertTrue(variant_stderr_exists)
        self.assertTrue(positive_stderr_exists)

    def test_op_diverse_selection_spreads_across_retained_operator_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            records = run_dir / "typed_retained_records.jsonl"
            with records.open("w", encoding="utf-8") as handle:
                for index in range(10):
                    candidate = run_dir / f"candidate_{index}.hevc"
                    candidate.write_bytes(f"candidate {index}".encode("ascii"))
                    handle.write(
                        json.dumps(
                            {
                                "index": index,
                                "path": str(candidate),
                                "d_f_spec_lifted": None,
                                "op": index,
                                "sample": 0,
                            }
                        )
                        + "\n"
                    )
            endpoint_code = "import sys; sys.exit(0)"
            endpoint_cmd = f"{shlex.quote(sys.executable)} -c {shlex.quote(endpoint_code)} @@"
            summary = run_dir / "summary.json"
            enriched = run_dir / "endpoint_records.jsonl"

            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--run-dir",
                    str(run_dir),
                    "--endpoint-cmd",
                    endpoint_cmd,
                    "--selection",
                    "op-diverse",
                    "--max-records",
                    "4",
                    "--out-summary",
                    str(summary),
                    "--out-records-jsonl",
                    str(enriched),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            report = json.loads(summary.read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in enriched.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(report["selection"], "op-diverse")
        self.assertEqual(report["replayed_records"], 4)
        self.assertEqual([row["op"] for row in rows], [0, 3, 6, 9])


if __name__ == "__main__":
    unittest.main()
