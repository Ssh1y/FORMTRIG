#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEALTH_PATH = ROOT / "formtrig" / "tools" / "check_runtime_progress_health.py"

spec = importlib.util.spec_from_file_location("check_runtime_progress_health", HEALTH_PATH)
check_runtime_progress_health = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["check_runtime_progress_health"] = check_runtime_progress_health
spec.loader.exec_module(check_runtime_progress_health)


class RuntimeProgressHealthTests(unittest.TestCase):
    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data))
        return path

    def write_progress_log(self, path: Path, values: list[float], *, triggered: bool = False) -> None:
        source_id = 1111
        context_hash = "00000000000008ae"
        lines = []
        for index, value in enumerate(values):
            lines.append(
                json.dumps(
                    {
                        "event": "frontier_reject",
                        "reason": "unit",
                        "queue_id": index,
                        "reached": 1,
                        "triggered": 1 if triggered else 0,
                        "d_f": value,
                        "component_values": [
                            {
                                "kind": 3,
                                "atom_id": 1,
                                "priority": 20,
                                "flags": 21,
                                "source_id": source_id,
                                "context_hash": context_hash,
                                "value": value,
                                "confidence": 0.95,
                            }
                        ],
                    }
                )
            )
        path.write_text("\n".join(lines) + "\n")

    def write_distance_spec(self, path: Path) -> None:
        path.write_text(
            "component 7 123 3 1 20 lower distance 0.0 0.95 1111 2222\n"
        )

    def write_lifted_hit_spec(self, path: Path) -> None:
        path.write_text(
            "component 7 123 5 1 20 higher hit 1.0 0.95 1111 2222\n"
        )

    def write_lifted_progress_log(self, path: Path, values: list[float]) -> None:
        source_id = 1111
        context_hash = "00000000000008ae"
        lines = []
        for index, value in enumerate(values):
            lines.append(
                json.dumps(
                    {
                        "event": "frontier_reject",
                        "reason": "unit",
                        "queue_id": index,
                        "reached": 1,
                        "triggered": 0,
                        "d_f": value,
                        "component_values": [
                            {
                                "kind": 5,
                                "atom_id": 1,
                                "priority": 20,
                                "flags": 22,
                                "source_id": source_id,
                                "context_hash": context_hash,
                                "value": value,
                                "confidence": 0.95,
                            }
                        ],
                    }
                )
            )
        path.write_text("\n".join(lines) + "\n")

    def test_single_atom_distance_zero_without_trigger_is_suspect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = tmp_path / "formtrig.lift.spec"
            self.write_distance_spec(spec_path)
            report = self.write_json(
                tmp_path, "formtrig_lift_report.json", {"spec": str(spec_path)}
            )
            graph = self.write_json(
                tmp_path,
                "graph.json",
                {
                    "target_id": "T",
                    "nodes": [
                        {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"}
                    ],
                    "edges": [],
                },
            )
            progress = tmp_path / "formtrig_progress.jsonl"
            self.write_progress_log(progress, [9.0, 0.0, 3.0])

            health = check_runtime_progress_health.build_report(
                lift_report_path=report,
                spec_path=None,
                progress_log_path=progress,
                trigger_graphs=[graph],
                min_samples=1,
                max_events=100,
            )

        self.assertEqual(health["status"], "suspect")
        self.assertEqual(health["issue_counts"]["error"], 1)
        self.assertEqual(
            health["components"][0]["issues"][0]["reason"],
            "distance_zero_without_terminal_trigger",
        )

    def test_compound_atom_distance_zero_is_warning_not_terminal_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = tmp_path / "formtrig.lift.spec"
            self.write_distance_spec(spec_path)
            report = self.write_json(
                tmp_path, "formtrig_lift_report.json", {"spec": str(spec_path)}
            )
            graph = self.write_json(
                tmp_path,
                "graph.json",
                {
                    "target_id": "T",
                    "nodes": [
                        {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"},
                        {"id": "atom:a2", "type": "tc_atom", "category": "binary-state-null"},
                    ],
                    "edges": [],
                },
            )
            progress = tmp_path / "formtrig_progress.jsonl"
            self.write_progress_log(progress, [0.0, 2.0])

            health = check_runtime_progress_health.build_report(
                lift_report_path=report,
                spec_path=None,
                progress_log_path=progress,
                trigger_graphs=[graph],
                min_samples=1,
                max_events=100,
            )

        self.assertEqual(health["status"], "weak")
        self.assertEqual(health["issue_counts"]["warning"], 1)
        self.assertEqual(health["issue_counts"]["error"], 0)

    def test_nonzero_varying_distance_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = tmp_path / "formtrig.lift.spec"
            self.write_distance_spec(spec_path)
            report = self.write_json(
                tmp_path, "formtrig_lift_report.json", {"spec": str(spec_path)}
            )
            graph = self.write_json(
                tmp_path,
                "graph.json",
                {
                    "target_id": "T",
                    "nodes": [
                        {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"}
                    ],
                    "edges": [],
                },
            )
            progress = tmp_path / "formtrig_progress.jsonl"
            self.write_progress_log(progress, [9.0, 7.0, 3.0])

            health = check_runtime_progress_health.build_report(
                lift_report_path=report,
                spec_path=None,
                progress_log_path=progress,
                trigger_graphs=[graph],
                min_samples=1,
                max_events=100,
            )

        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["components"][0]["unique_nontrigger_values"], 3)

    def test_flat_lifted_hit_component_is_weak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = tmp_path / "formtrig.lift.spec"
            self.write_lifted_hit_spec(spec_path)
            report = self.write_json(
                tmp_path, "formtrig_lift_report.json", {"spec": str(spec_path)}
            )
            graph = self.write_json(
                tmp_path,
                "graph.json",
                {
                    "target_id": "T",
                    "nodes": [
                        {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"}
                    ],
                    "edges": [],
                },
            )
            progress = tmp_path / "formtrig_progress.jsonl"
            self.write_lifted_progress_log(progress, [1.0, 1.0, 1.0])

            health = check_runtime_progress_health.build_report(
                lift_report_path=report,
                spec_path=None,
                progress_log_path=progress,
                trigger_graphs=[graph],
                min_samples=1,
                max_events=100,
            )

        self.assertEqual(health["status"], "weak")
        self.assertEqual(health["distance_components"], 0)
        self.assertEqual(health["progress_components"], 1)
        self.assertFalse(health["components"][0]["is_distance"])
        self.assertEqual(
            health["components"][0]["issues"][0]["reason"],
            "lifted_component_low_entropy",
        )

    def test_varying_lifted_hit_component_is_ok_without_distance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = tmp_path / "formtrig.lift.spec"
            self.write_lifted_hit_spec(spec_path)
            report = self.write_json(
                tmp_path, "formtrig_lift_report.json", {"spec": str(spec_path)}
            )
            graph = self.write_json(
                tmp_path,
                "graph.json",
                {
                    "target_id": "T",
                    "nodes": [
                        {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"}
                    ],
                    "edges": [],
                },
            )
            progress = tmp_path / "formtrig_progress.jsonl"
            self.write_lifted_progress_log(progress, [0.0, 1.0, 2.0])

            health = check_runtime_progress_health.build_report(
                lift_report_path=report,
                spec_path=None,
                progress_log_path=progress,
                trigger_graphs=[graph],
                min_samples=1,
                max_events=100,
            )

        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["distance_components"], 0)
        self.assertEqual(health["progress_components"], 1)
        self.assertEqual(health["components"][0]["unique_nontrigger_values"], 3)

    def test_cli_fails_on_suspect_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_path = tmp_path / "formtrig.lift.spec"
            self.write_distance_spec(spec_path)
            report = self.write_json(
                tmp_path, "formtrig_lift_report.json", {"spec": "/magma_shared/formtrig_lift/formtrig.lift.spec"}
            )
            graph = self.write_json(
                tmp_path,
                "graph.json",
                {
                    "target_id": "T",
                    "nodes": [
                        {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"}
                    ],
                    "edges": [],
                },
            )
            progress = tmp_path / "formtrig_progress.jsonl"
            self.write_progress_log(progress, [0.0])
            out = tmp_path / "health.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(HEALTH_PATH),
                    "--lift-report",
                    str(report),
                    "--progress-log",
                    str(progress),
                    "--trigger-graph",
                    str(graph),
                    "--report-json",
                    str(out),
                    "--fail-on-suspect",
                ],
                text=True,
                capture_output=True,
            )
            payload = json.loads(out.read_text())

        self.assertEqual(result.returncode, 4)
        self.assertEqual(payload["status"], "suspect")


if __name__ == "__main__":
    unittest.main()
