import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "analyze_gpac3403_alias_gap.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_lift(path: Path) -> None:
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


def progress_record(index: int, alias_ptr: int, cleanup_ptr: int) -> dict:
    return {
        "event": "frontier_update",
        "reason": "dominates",
        "execs_done": 100 + index,
        "queue_id": index,
        "trace_signature": f"trace{index}",
        "components": 6,
        "component_values": [
            {"source_id": 1001, "value": alias_ptr},
            {"source_id": 1002, "value": alias_ptr},
            {"source_id": 1003, "value": cleanup_ptr},
            {"source_id": 1004, "value": 1},
            {"source_id": 1005, "value": 1},
            {"source_id": 1006, "value": 1},
        ],
        "d_f_spec_lifted": 2,
        "reached": 1,
        "target_hit_count": 1,
    }


class AnalyzeGpac3403AliasGapTest(unittest.TestCase):
    def test_stable_nonzero_cleanup_offset_is_reported(self):
        tool = load_module(TOOL, "analyze_gpac3403_alias_gap_stable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lift = root / "lift.normalized"
            runtime = root / "progress.jsonl"
            write_lift(lift)
            runtime.write_text(
                "\n".join(
                    [
                        json.dumps(progress_record(1, 0x10000, 0x9000)),
                        json.dumps(progress_record(2, 0x20000, 0x19000)),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = tool.build_report(lift, [runtime])

        self.assertEqual(report["verdict"]["status"], "stable_nonzero_cleanup_offset")
        self.assertEqual(report["verdict"]["stable_nonzero_cleanup_offsets"], [-0x7000])
        runtime_summary = report["runtimes"][0]
        self.assertTrue(runtime_summary["stable_cleanup_offset"]["present"])
        self.assertEqual(runtime_summary["relation_counts"]["release_reassign_with_cleanup_records"], 2)
        self.assertEqual(runtime_summary["delta_histogram"], [{"value": -0x7000, "count": 2}])
        self.assertEqual(runtime_summary["top_records"][0]["cleanup_minus_alias_deltas"], [-0x7000])

    def test_complete_alias_free_relation_takes_precedence(self):
        tool = load_module(TOOL, "analyze_gpac3403_alias_gap_complete")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lift = root / "lift.normalized"
            runtime = root / "progress.jsonl"
            write_lift(lift)
            runtime.write_text(json.dumps(progress_record(1, 0x30000, 0x30000)) + "\n", encoding="utf-8")

            report = tool.build_report(lift, [runtime])

        self.assertEqual(report["verdict"]["status"], "alias_free_relation_proven")
        self.assertTrue(report["verdict"]["complete_alias_free_relation"])
        self.assertEqual(report["runtimes"][0]["relation_counts"]["complete_alias_free_relation_records"], 1)

    def test_single_cleanup_multiple_release_aliases_is_lifecycle_gap(self):
        tool = load_module(TOOL, "analyze_gpac3403_alias_gap_single_cleanup")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lift = root / "lift.normalized"
            runtime = root / "progress.jsonl"
            write_lift(lift)
            runtime.write_text(
                "\n".join(
                    [
                        json.dumps(progress_record(1, 0x10000, 0x9000)),
                        json.dumps(progress_record(2, 0x20000, 0x9000)),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = tool.build_report(lift, [runtime])

        runtime_summary = report["runtimes"][0]
        self.assertEqual(report["verdict"]["status"], "single_cleanup_multiple_release_aliases")
        self.assertEqual(runtime_summary["unique_release_same_object_values"], 2)
        self.assertEqual(runtime_summary["unique_cleanup_values"], 1)
        self.assertIn("sample/lifecycle correlation gap", report["verdict"]["interpretation"])

    def test_cli_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lift = root / "lift.normalized"
            runtime = root / "progress.jsonl"
            out_json = root / "alias_gap.json"
            out_md = root / "alias_gap.md"
            write_lift(lift)
            runtime.write_text(json.dumps(progress_record(1, 0x10000, 0x9000)) + "\n", encoding="utf-8")

            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--lift-spec",
                    str(lift),
                    "--runtime-jsonl",
                    str(runtime),
                    "--out-json",
                    str(out_json),
                    "--out-md",
                    str(out_md),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            report = json.loads(out_json.read_text(encoding="utf-8"))
            markdown = out_md.read_text(encoding="utf-8")

        self.assertEqual(report["schema"], "formtrig_gpac3403_alias_gap_analysis_v1")
        self.assertIn("stable_nonzero_cleanup_offset", markdown)
        self.assertIn("Claim boundary", markdown)


if __name__ == "__main__":
    unittest.main()
