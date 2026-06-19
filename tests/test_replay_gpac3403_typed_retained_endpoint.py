import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "replay_gpac3403_typed_retained_endpoint.py"


def hevc_header(nal_type: int, layer: int = 0) -> bytes:
    first = (((nal_type & 0x3F) << 1) & 0x7E) | ((layer >> 5) & 0x01)
    second = ((layer & 0x1F) << 3) | 1
    return bytes([first, second])


def hevc_nalu(nal_type: int, layer: int = 0, payload: bytes = b"\x80") -> bytes:
    return b"\x00\x00\x00\x01" + hevc_header(nal_type, layer) + payload


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

    def test_structure_best_selection_prefers_endpoint_scale_hevc_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            small = run_dir / "small.hevc"
            large = run_dir / "large.hevc"
            small.write_bytes(hevc_nalu(32, 0, b"\x80"))
            large.write_bytes(
                b"".join(
                    [
                        hevc_nalu(32, 0, b"\x80" * 16),
                        hevc_nalu(33, 0, b"\x80" * 16),
                        hevc_nalu(34, 7, b"\x80" * 16),
                        hevc_nalu(49, 7, b"\x80" * 16),
                        hevc_nalu(16, 7, b"\x80" * 16),
                        hevc_nalu(0, 14, b"\x80" * 16),
                        hevc_nalu(1, 14, b"\x80" * 16),
                        hevc_nalu(5, 22, b"\x80" * 16),
                    ]
                )
            )
            records = run_dir / "typed_retained_records.jsonl"
            records.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "index": 0,
                                "path": str(small),
                                "d_f_spec_lifted": 0.0,
                                "op": 0,
                                "sample": 0,
                            }
                        ),
                        json.dumps(
                            {
                                "index": 1,
                                "path": str(large),
                                "d_f_spec_lifted": 5.0,
                                "op": 47,
                                "sample": 0,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
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
                    "structure-best",
                    "--max-records",
                    "1",
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

        self.assertEqual(report["selection"], "structure-best")
        self.assertEqual(report["replayed_records"], 1)
        self.assertEqual(report["structure_profiled_records"], 1)
        self.assertGreater(report["structure_score_max"], 0)
        self.assertEqual(rows[0]["index"], 1)
        self.assertEqual(rows[0]["endpoint_selection_profile"]["nalu_count"], 8)
        self.assertIn(49, rows[0]["endpoint_selection_profile"]["unique_types"])

    def test_df_structure_selection_keeps_lift_priority_before_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            low_df = run_dir / "low_df.hevc"
            high_df = run_dir / "high_df.hevc"
            low_df.write_bytes(
                hevc_nalu(32, 0, b"\x80" * 8)
                + hevc_nalu(33, 0, b"\x80" * 8)
                + hevc_nalu(34, 0, b"\x80" * 8)
            )
            high_df.write_bytes(
                b"".join(
                    hevc_nalu(nal_type, layer, b"\x80" * 16)
                    for nal_type, layer in [
                        (32, 0),
                        (33, 0),
                        (34, 7),
                        (49, 7),
                        (16, 14),
                        (0, 14),
                        (1, 22),
                        (5, 22),
                    ]
                )
            )
            records = run_dir / "typed_retained_records.jsonl"
            records.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "index": 0,
                                "path": str(high_df),
                                "d_f_spec_lifted": 5.0,
                                "op": 47,
                                "sample": 0,
                            }
                        ),
                        json.dumps(
                            {
                                "index": 1,
                                "path": str(low_df),
                                "d_f_spec_lifted": 2.0,
                                "op": 36,
                                "sample": 0,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
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
                    "df-structure",
                    "--max-records",
                    "1",
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

        self.assertEqual(report["selection"], "df-structure")
        self.assertEqual(report["replayed_records"], 1)
        self.assertEqual(rows[0]["index"], 1)
        self.assertEqual(rows[0]["d_f_spec_lifted"], 2.0)
        self.assertGreater(rows[0]["endpoint_selection_profile"]["score"], 0)


if __name__ == "__main__":
    unittest.main()
