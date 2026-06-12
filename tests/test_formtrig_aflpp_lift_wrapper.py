#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "formtrig" / "tools" / "run_aflpp_lift.py"


class AflppLiftWrapperTests(unittest.TestCase):
    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data))
        return path

    def sample_graph(self) -> dict:
        return {
            "target_id": "T_WRAP",
            "nodes": [
                {
                    "id": "atom:a1",
                    "type": "tc_atom",
                    "category": "compound-sequence-lifecycle",
                },
                {
                    "id": "phase:start",
                    "type": "lifecycle_phase",
                    "runtime_event_id": "phase:start",
                    "confidence": "verified",
                },
                {
                    "id": "range:start",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "phase:start",
                    "start": 3,
                    "length": 2,
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

    def sample_runtime_map(self) -> dict:
        return {
            "runtime_events": {
                "phase:start": {"event_kind": "branch", "site_id": 77}
            }
        }

    def test_dry_run_compiles_spec_and_injects_native_formtrig_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph = self.write_json(tmp_path, "graph.json", self.sample_graph())
            runtime_map = self.write_json(
                tmp_path, "runtime_map.json", self.sample_runtime_map()
            )
            spec_out = tmp_path / "lift.spec"
            report_json = tmp_path / "report.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph),
                    "--runtime-map",
                    str(runtime_map),
                    "--spec-out",
                    str(spec_out),
                    "--report-json",
                    str(report_json),
                    "--env",
                    "AFL_SKIP_CPUFREQ=1",
                    "--dry-run",
                    "--",
                    "-i",
                    "in",
                    "-o",
                    "out",
                    "--",
                    "/tmp/target",
                    "@@",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

            plan = json.loads(result.stdout)
            spec_text = spec_out.read_text()
            report = json.loads(report_json.read_text())

        self.assertEqual(plan["cmd"], ["/bin/echo", "-i", "in", "-o", "out", "--", "/tmp/target", "@@"])
        self.assertEqual(plan["env"]["FORMTRIG_AFLPP"], "1")
        self.assertEqual(plan["env"]["AFL_SKIP_CPUFREQ"], "1")
        self.assertEqual(Path(plan["env"]["FORMTRIG_LIFT_SPEC"]), spec_out.resolve())
        self.assertEqual(plan["env"]["FORMTRIG_SOURCE_OBJECTIVE"], "1")
        self.assertEqual(plan["env"]["FORMTRIG_SOURCE_SITE_REACH"], "1")
        self.assertEqual(plan["env"]["FORMTRIG_TARGET_SITE_IDS"], "77")
        self.assertIn("phase 8 77 7 1 10 1", spec_text)
        self.assertIn("range 8 77 3 2 0.85", spec_text)
        self.assertEqual(report["rules"], 2)
        self.assertEqual(report["progress_rules"], 1)
        self.assertEqual(report["range_rules"], 1)
        self.assertEqual(report["graphs"][0]["progress_site_ids"], [77])

    def test_compile_only_does_not_require_afl_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph = self.write_json(tmp_path, "graph.json", self.sample_graph())
            runtime_map = self.write_json(
                tmp_path, "runtime_map.json", self.sample_runtime_map()
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph),
                    "--runtime-map",
                    str(runtime_map),
                    "--work-dir",
                    str(tmp_path),
                    "--compile-only",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

            report = json.loads(result.stdout)
            self.assertEqual(report["rules"], 2)
            self.assertTrue(Path(report["spec"]).exists())

    def test_refuses_afl_launch_when_spec_has_no_progress_rules(self) -> None:
        graph = {
            "target_id": "T_RANGE_ONLY",
            "nodes": [
                {
                    "id": "range:only",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "range:only",
                    "start": 0,
                    "length": 1,
                    "confidence": "verified",
                }
            ],
            "edges": [],
        }
        runtime_map = {
            "runtime_events": {
                "range:only": {"event_kind": "branch", "site_id": 88}
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            runtime_map_path = self.write_json(tmp_path, "runtime_map.json", runtime_map)
            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph_path),
                    "--runtime-map",
                    str(runtime_map_path),
                    "--work-dir",
                    str(tmp_path),
                    "--dry-run",
                    "--",
                    "-i",
                    "in",
                    "-o",
                    "out",
                    "--",
                    "/tmp/target",
                ],
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no progress rules", result.stderr)

    def test_require_binding_ready_refuses_fuzzy_numeric_distance_debt(self) -> None:
        graph = {
            "target_id": "T_BIND_READY",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map = tmp_path / "sites.tsv"
            site_map.write_text(
                "123\tcmp\tparse\t7\ticmp\tsrc/parser.c\t42\t0\n"
                "124\tcmp\tparse\t8\ticmp\tsrc/parser.c\t42\t1\n"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph_path),
                    "--site-map",
                    str(site_map),
                    "--work-dir",
                    str(tmp_path),
                    "--require-binding-ready",
                    "--dry-run",
                    "--",
                    "-i",
                    "in",
                    "-o",
                    "out",
                    "--",
                    "/tmp/target",
                ],
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("binding audit is not ready", result.stderr)
        self.assertIn("needs_exact_progress_binding", result.stderr)

    def test_require_binding_ready_allows_external_exact_numeric_binding(self) -> None:
        graph = {
            "target_id": "T_BIND_READY_EXACT",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42#parse",
                    "confidence": "verified",
                },
                {
                    "id": "range:r",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "range:r",
                    "start": 0,
                    "length": 4,
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }
        runtime_map = {
            "runtime_events": {
                "source:src/parser.c:42#parse": {
                    "event_kind": "cmp",
                    "site_id": 123,
                    "source": "external-selection",
                },
                "range:r": {"event_kind": "cmp", "site_id": 123},
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            runtime_map_path = self.write_json(tmp_path, "runtime_map.json", runtime_map)
            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph_path),
                    "--runtime-map",
                    str(runtime_map_path),
                    "--work-dir",
                    str(tmp_path),
                    "--require-binding-ready",
                    "--dry-run",
                    "--",
                    "-i",
                    "in",
                    "-o",
                    "out",
                    "--",
                    "/tmp/target",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            plan = json.loads(result.stdout)

        self.assertEqual(plan["report"]["progress_rules"], 2)
        self.assertEqual(plan["binding_audit"]["graphs"][0]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
