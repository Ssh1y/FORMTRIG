#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "formtrig" / "tools" / "binding_spec.py"
MATERIALIZE_PATH = ROOT / "formtrig" / "tools" / "materialize_runtime_map.py"

spec = importlib.util.spec_from_file_location("binding_spec", TOOL_PATH)
binding_spec = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(TOOL_PATH.parent))
spec.loader.exec_module(binding_spec)


class BindingSpecTests(unittest.TestCase):
    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data))
        return path

    def binary_spec(self) -> dict:
        return {
            "tc_id": "T_BIN",
            "target": {"project": "toy", "binary": "toy_bin"},
            "tc": {
                "expression": "ctx->root == NULL",
                "category": "binary-state-null",
            },
            "atoms": [
                {
                    "id": "atom:a1",
                    "expr": "ctx->root == NULL",
                    "kind": "binary-state-null",
                    "root": "ctx->root",
                }
            ],
            "bindings": {
                "roots": [
                    {
                        "id": "root",
                        "atom": "atom:a1",
                        "observe_at": [
                            {
                                "file": "toy.c",
                                "line": 10,
                                "function": "parse",
                                "event_kind": "load",
                                "site_id": 100,
                            }
                        ],
                    }
                ],
                "producers": [
                    {
                        "id": "producer",
                        "atom": "atom:a1",
                        "role": "desired_producer",
                        "observe_at": [
                            {
                                "file": "toy.c",
                                "line": 20,
                                "function": "parse",
                                "event_kind": "store",
                                "site_id": 200,
                                "role": "desired_producer",
                            }
                        ],
                    }
                ],
                "uses": [
                    {
                        "id": "use",
                        "atom": "atom:a1",
                        "observe_at": [
                            {
                                "file": "toy.c",
                                "line": 30,
                                "function": "parse",
                                "event_kind": "load",
                                "site_id": 300,
                            }
                        ],
                    }
                ],
                "input_influence": [
                    {
                        "id": "root-field",
                        "atom": "atom:a1",
                        "ranges": [
                            {
                                "start": 4,
                                "length": 2,
                                "confidence": "high",
                            }
                        ],
                    }
                ],
            },
        }

    def test_valid_binding_spec_materializes_graph_and_runtime_map(self) -> None:
        spec_data = self.binary_spec()
        failures = binding_spec.validate_binding_spec(spec_data)
        self.assertEqual(failures, [])

        graph, runtime_map = binding_spec.binding_spec_to_graph_and_runtime_map(spec_data)

        self.assertEqual(graph["target_id"], "T_BIN")
        self.assertEqual(len(runtime_map["runtime_events"]), 3)
        roles = {
            item["role"] for item in runtime_map["runtime_events"].values()
        }
        self.assertEqual(roles, {"root_observe", "desired_producer", "use"})
        node_types = {node["type"] for node in graph["nodes"]}
        self.assertIn("root_context", node_types)
        self.assertIn("producer_context", node_types)
        self.assertIn("use_context", node_types)

    def test_unknown_atom_is_validation_failure(self) -> None:
        spec_data = self.binary_spec()
        spec_data["bindings"]["uses"][0]["atom"] = "atom:missing"

        failures = binding_spec.validate_binding_spec(spec_data)

        self.assertTrue(any(item["reason"] == "unknown_atom" for item in failures))

    def test_binary_binding_spec_reaches_b2_and_is_ready(self) -> None:
        spec_data = self.binary_spec()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = self.write_json(tmp_path, "binding.json", spec_data)
            graph_path = tmp_path / "graph.json"
            map_path = tmp_path / "runtime_map.json"
            audit_path = tmp_path / "audit.json"
            quality_path = tmp_path / "quality.csv"

            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL_PATH),
                    "--binding-spec",
                    str(spec_path),
                    "--graph-out",
                    str(graph_path),
                    "--runtime-map-out",
                    str(map_path),
                    "--audit-json",
                    str(audit_path),
                    "--quality-csv",
                    str(quality_path),
                    "--require-ready",
                ],
                text=True,
                capture_output=True,
            )

            audit = json.loads(audit_path.read_text())
            quality = quality_path.read_text()

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(audit["status"], "pass")
        tier = audit["graphs"][0]["binding_tiers"][0]
        self.assertEqual(tier["binding_tier"], "B2")
        self.assertTrue(tier["lift_allowed"])
        self.assertIn("T_BIN,1,binary-state-null,B2,B2,True", quality)

    def test_binary_guard_only_binding_is_not_ready(self) -> None:
        spec_data = self.binary_spec()
        spec_data["bindings"].pop("roots")
        spec_data["bindings"].pop("producers")
        spec_data["bindings"].pop("uses")
        spec_data["bindings"].pop("input_influence")
        spec_data["bindings"]["guards"] = [
            {
                "id": "guard",
                "atom": "atom:a1",
                "observe_at": [
                    {
                        "file": "toy.c",
                        "line": 12,
                        "function": "parse",
                        "event_kind": "cmp",
                        "site_id": 120,
                    }
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = self.write_json(tmp_path, "binding.json", spec_data)
            graph_path = tmp_path / "graph.json"
            map_path = tmp_path / "runtime_map.json"
            audit_path = tmp_path / "audit.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL_PATH),
                    "--binding-spec",
                    str(spec_path),
                    "--graph-out",
                    str(graph_path),
                    "--runtime-map-out",
                    str(map_path),
                    "--audit-json",
                    str(audit_path),
                    "--require-ready",
                ],
                text=True,
                capture_output=True,
            )
            audit = json.loads(audit_path.read_text())

        self.assertEqual(result.returncode, 3)
        self.assertEqual(audit["status"], "fail")
        graph_report = audit["graphs"][0]
        self.assertEqual(graph_report["status"], "insufficient_binding_tier")
        self.assertEqual(graph_report["binding_tiers"][0]["binding_tier"], "B1")

    def test_materialize_runtime_map_accepts_binding_spec_directly(self) -> None:
        spec_data = self.binary_spec()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = self.write_json(tmp_path, "binding.json", spec_data)
            runtime_map_path = tmp_path / "runtime_map.json"
            audit_path = tmp_path / "audit.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZE_PATH),
                    "--binding-spec",
                    str(spec_path),
                    "-o",
                    str(runtime_map_path),
                    "--audit-json",
                    str(audit_path),
                    "--require-ready",
                ],
                text=True,
                capture_output=True,
            )
            payload = json.loads(runtime_map_path.read_text())
            audit = json.loads(audit_path.read_text())

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(payload["summary"]["bindings"], 3)
        self.assertEqual(payload["summary"]["mutation_ready"], 1)
        self.assertEqual(audit["summary"]["mutation_ready"], 1)
        self.assertEqual(audit["graphs"][0]["binding_tiers"][0]["binding_tier"], "B2")

    def test_binding_spec_detects_semantic_role_collapse(self) -> None:
        spec_data = self.binary_spec()
        spec_data["bindings"]["roots"][0]["observe_at"][0]["site_id"] = 120
        spec_data["bindings"]["roots"][0]["observe_at"][0]["event_kind"] = "cmp"
        spec_data["bindings"]["uses"][0]["observe_at"][0]["site_id"] = 120
        spec_data["bindings"]["uses"][0]["observe_at"][0]["event_kind"] = "cmp"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = self.write_json(tmp_path, "binding.json", spec_data)
            graph_path = tmp_path / "graph.json"
            map_path = tmp_path / "runtime_map.json"
            audit_path = tmp_path / "audit.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL_PATH),
                    "--binding-spec",
                    str(spec_path),
                    "--graph-out",
                    str(graph_path),
                    "--runtime-map-out",
                    str(map_path),
                    "--audit-json",
                    str(audit_path),
                    "--require-ready",
                ],
                text=True,
                capture_output=True,
            )
            audit = json.loads(audit_path.read_text())

        self.assertEqual(result.returncode, 3)
        graph_report = audit["graphs"][0]
        self.assertEqual(graph_report["status"], "collapsed_progress_bindings")
        self.assertEqual(graph_report["collapsed_progress_count"], 1)
        self.assertEqual(
            graph_report["collapsed_progress_bindings"][0]["node_types"],
            ["root_context", "use_context"],
        )


if __name__ == "__main__":
    unittest.main()
