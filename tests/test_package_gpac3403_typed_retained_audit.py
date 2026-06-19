import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "package_gpac3403_typed_retained_audit.py"
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def nalu(hook, nal_type, layer, payload):
    return b"\x00\x00\x00\x01" + hook.make_header(nal_type, layer) + payload


def write_alias_lift(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "role_component 8 3030846436 lifecycle_event 7 1 25 higher hit 1.0 0.85 1004 1004 any",
                "role_component 7 3013921722 lifecycle_event 8 1 26 higher a 1.0 0.9 1001 1001 any",
                "role_component 8 14730514 use 6 1 40 higher not_outcome 1.0 0.8 1005 1005 any",
                "role_component 7 65063371 use 8 1 42 higher a 1.0 0.9 1003 1003 any",
                "role_component 7 115396228 root_observe 3 1 50 higher not_outcome 1.0 0.9 1006 1006 any",
                "role_component 7 1549213408 same_object 8 1 60 higher a 1.0 0.85 1002 1002 any",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_alias_runtime(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "components": 6,
                "component_values": [
                    {"source_id": 1001, "value": 0x10000},
                    {"source_id": 1002, "value": 0x10000},
                    {"source_id": 1003, "value": 0x20000},
                    {"source_id": 1004, "value": 1},
                    {"source_id": 1005, "value": 1},
                    {"source_id": 1006, "value": 1},
                ],
                "d_f_spec_lifted": 2,
                "reached": 1,
                "target_hit_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )


class PackageGpac3403TypedRetainedAuditTest(unittest.TestCase):
    def test_empty_retained_package_keeps_claim_boundary_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            out = run_dir / "package.json"
            (run_dir / "typed_retained_summary.json").write_text(
                json.dumps(
                    {
                        "schema": "formtrig_typed_retained_candidates_v1",
                        "retained_records": 0,
                        "existing_inputs": 0,
                        "missing_inputs": 0,
                        "d_f_spec_lifted": {"count": 0, "min": None, "max": None},
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "typed_retained_records.jsonl").write_text("", encoding="utf-8")

            subprocess.run(
                ["python3", str(TOOL), "--run-dir", str(run_dir), "--out", str(out)],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            package = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(package["schema"], "formtrig_gpac3403_typed_retained_audit_package_v1")
        self.assertTrue(package["structure_audit"]["available"])
        self.assertEqual(package["structure_audit"]["variant_summary"]["record_count"], 0)
        self.assertFalse(package["endpoint_audit"]["available"])
        self.assertFalse(package["alias_relation_audit"]["available"])
        self.assertEqual(package["evidence_assessment"]["retained_records"], 0)
        self.assertIn("No typed-retained candidates", package["evidence_assessment"]["claim_boundary"])

    def test_package_combines_retained_structure_and_endpoint_signatures(self):
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_package_test")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            logs = run_dir / "logs"
            logs.mkdir(parents=True)
            candidate = run_dir / "candidate.hevc"
            candidate.write_bytes(nalu(hook, 32, 0, b"\x00\x80") + nalu(hook, 34, 0, b"\x80"))
            records = run_dir / "typed_retained_records.jsonl"
            records.write_text(
                json.dumps(
                    {
                        "index": 0,
                        "op": 3,
                        "sample": 7,
                        "d_f_spec_lifted": 1.0,
                        "path": str(candidate),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "typed_retained_summary.json").write_text(
                json.dumps(
                    {
                        "schema": "formtrig_typed_retained_candidates_v1",
                        "records_jsonl": str(records),
                        "retained_records": 1,
                        "existing_inputs": 1,
                        "missing_inputs": 0,
                        "d_f_spec_lifted": {"count": 1, "min": 1.0, "max": 1.0},
                        "best_by_d_f": [{"index": 0, "path": str(candidate)}],
                    }
                ),
                encoding="utf-8",
            )
            (logs / "variant_000000.endpoint_1.stderr").write_text(
                "[HEVC] VPS max layer ID 9 but GPAC only supports 4\n",
                encoding="utf-8",
            )
            (logs / "positive_control.endpoint_1.stderr").write_text(
                "[HEVC] Wrong number of output layer sets in VPS 132, max 4 supported\n"
                "[HEVC] Failed to parse VPS extensions\n",
                encoding="utf-8",
            )
            (run_dir / "typed_retained_endpoint_replay_summary.json").write_text(
                json.dumps(
                    {
                        "endpoint_replayed_variants": 1,
                        "endpoint_sanitizer_crashes": 0,
                        "endpoint_native_crashes": 0,
                        "endpoint_timeouts": 0,
                        "duration_s": 0.1,
                    }
                ),
                encoding="utf-8",
            )
            write_alias_lift(
                run_dir / "fuzzer_out" / ".formtrig" / "formtrig_lift.normalized"
            )
            write_alias_runtime(
                run_dir / "fuzzer_out" / "default" / "formtrig_progress.jsonl"
            )
            out = run_dir / "package.json"

            subprocess.run(
                ["python3", str(TOOL), "--run-dir", str(run_dir), "--out", str(out)],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            package = json.loads(out.read_text(encoding="utf-8"))

        assessment = package["evidence_assessment"]
        self.assertEqual(assessment["retained_records"], 1)
        self.assertEqual(assessment["records_jsonl_lines"], 1)
        self.assertEqual(assessment["structure_profiled_candidates"], 1)
        self.assertEqual(assessment["endpoint_variant_files"], 1)
        self.assertEqual(assessment["endpoint_positive_control_files"], 1)
        self.assertEqual(
            package["endpoint_audit"]["report"]["summary"]["endpoint_replayed_variants"],
            1,
        )
        self.assertTrue(package["alias_relation_audit"]["available"])
        self.assertEqual(
            package["alias_relation_audit"]["report"]["verdict"]["status"],
            "release_reassign_alias_observed_terminal_cleanup_missing",
        )
        self.assertEqual(
            assessment["alias_relation_status"],
            "release_reassign_alias_observed_terminal_cleanup_missing",
        )
        self.assertFalse(assessment["alias_relation_complete"])
        self.assertTrue(assessment["alias_release_reassign_observed"])
        self.assertIn(
            "wrong_output_layer_sets",
            assessment["positive_control_signatures_absent_from_variants"],
        )
        self.assertIn("structure and endpoint evidence", assessment["claim_boundary"])
        self.assertIn("Alias/free relation audit is not terminal-complete", assessment["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
