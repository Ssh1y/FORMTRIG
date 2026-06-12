#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "formtrig" / "tools" / "audit_lift_bindings.py"
MATERIALIZE_PATH = ROOT / "formtrig" / "tools" / "materialize_runtime_map.py"
WRAPPER = ROOT / "formtrig" / "tools" / "run_aflpp_lift.py"

spec = importlib.util.spec_from_file_location("audit_lift_bindings", AUDIT_PATH)
audit_lift_bindings = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.path.insert(0, str(AUDIT_PATH.parent))
spec.loader.exec_module(audit_lift_bindings)


class FormtrigBindingAuditTests(unittest.TestCase):
    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data))
        return path

    def magma_like_graph(self) -> dict:
        return {
            "target_id": "M_BIND",
            "nodes": [
                {
                    "id": "atom:a1",
                    "type": "tc_atom",
                    "category": "compound-sequence-lifecycle",
                },
                {
                    "id": "phase:create",
                    "type": "lifecycle_phase",
                    "runtime_event_id": "lifecycle:create",
                    "confidence": "high",
                },
                {
                    "id": "phase:use",
                    "type": "lifecycle_phase",
                    "runtime_event_id": "lifecycle:use",
                    "confidence": "high",
                },
                {
                    "id": "range:create",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "input:create_token",
                    "start": 0,
                    "length": 1,
                    "confidence": "verified",
                },
            ],
            "edges": [
                {
                    "type": "order_constraint",
                    "order": "lifecycle_prefix",
                    "src": "phase:create",
                    "dst": "phase:use",
                }
            ],
        }

    def test_unbound_graph_writes_runtime_map_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph = self.write_json(tmp_path, "graph.json", self.magma_like_graph())
            report_json = tmp_path / "audit.json"
            template_json = tmp_path / "runtime_map.template.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_PATH),
                    "--trigger-graph",
                    str(graph),
                    "--report-json",
                    str(report_json),
                    "--template-out",
                    str(template_json),
                    "--fail-on-unrunnable",
                ],
                text=True,
                capture_output=True,
            )

            report = json.loads(report_json.read_text())
            template = json.loads(template_json.read_text())

        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["summary"]["blocked_no_progress"], 1)
        graph_report = report["graphs"][0]
        self.assertFalse(graph_report["runnable"])
        self.assertEqual(graph_report["progress_rules"], 0)
        self.assertEqual(graph_report["range_rules"], 1)
        self.assertGreaterEqual(graph_report["missing_progress_count"], 2)
        self.assertEqual(graph_report["missing_range_count"], 0)
        self.assertEqual(graph_report["static_range_count"], 1)
        self.assertIn("lifecycle:create", template["runtime_events"])
        self.assertIn("lifecycle:use", template["runtime_events"])
        self.assertNotIn("input:create_token", template["runtime_events"])

    def test_bound_graph_is_runnable_and_mutation_ready(self) -> None:
        runtime_map = {
            "runtime_events": {
                "lifecycle:create": {"event_kind": "branch", "site_id": 101},
                "lifecycle:use": {"event_kind": "branch", "site_id": 102},
                "input:create_token": {"event_kind": "branch", "site_id": 101},
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph = self.write_json(tmp_path, "graph.json", self.magma_like_graph())
            runtime_map_path = self.write_json(tmp_path, "map.json", runtime_map)
            loaded_map = audit_lift_bindings.load_runtime_map(runtime_map_path)

            report = audit_lift_bindings.graph_binding_audit(
                graph, loaded_map, []
            )

        self.assertTrue(report["runnable"])
        self.assertFalse(report["mutation_ready"])
        self.assertEqual(report["status"], "insufficient_binding_tier")
        self.assertEqual(report["progress_rules"], 2)
        self.assertEqual(report["range_rules"], 1)
        self.assertEqual(report["missing_progress_count"], 0)
        self.assertEqual(report["missing_range_count"], 0)
        self.assertEqual(report["exact_progress_bindings"], 2)
        self.assertEqual(report["fuzzy_progress_bindings"], 0)
        self.assertEqual(report["distance_progress_bindings"], 0)
        self.assertEqual(report["binding_tiers"][0]["binding_tier"], "B0")
        self.assertFalse(report["binding_tiers"][0]["lift_allowed"])
        self.assertEqual(len(report["binding_details"]), 2)

    def test_lifecycle_with_same_object_binding_reaches_b3_and_is_ready(self) -> None:
        graph = self.magma_like_graph()
        graph["nodes"].append(
            {
                "id": "same:obj",
                "type": "same_object_context",
                "runtime_event_id": "lifecycle:same_object",
                "confidence": "high",
            }
        )
        runtime_map = {
            "runtime_events": {
                "lifecycle:create": {"event_kind": "branch", "site_id": 101},
                "lifecycle:use": {"event_kind": "branch", "site_id": 102},
                "lifecycle:same_object": {
                    "event_kind": "cmp",
                    "site_id": 103,
                    "role": "same_object",
                    "component_kind": "object_identity",
                    "value_mode": "outcome",
                },
                "input:create_token": {"event_kind": "branch", "site_id": 101},
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            runtime_map_path = self.write_json(tmp_path, "map.json", runtime_map)
            loaded_map = audit_lift_bindings.load_runtime_map(runtime_map_path)

            report = audit_lift_bindings.graph_binding_audit(
                graph_path, loaded_map, []
            )

        self.assertTrue(report["mutation_ready"])
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["binding_tiers"][0]["binding_tier"], "B3")
        self.assertTrue(report["binding_tiers"][0]["lift_allowed"])

    def test_numeric_exact_cmp_reports_distance_progress_binding(self) -> None:
        graph = {
            "target_id": "T_NUMERIC_AUDIT",
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
            )
            report = audit_lift_bindings.graph_binding_audit(
                graph_path, {}, audit_lift_bindings.parse_site_map(site_map)
            )

        self.assertTrue(report["runnable"])
        self.assertEqual(report["status"], "progress_only_no_hot_ranges")
        self.assertEqual(report["exact_progress_bindings"], 1)
        self.assertEqual(report["fuzzy_progress_bindings"], 0)
        self.assertEqual(report["distance_progress_bindings"], 1)
        self.assertEqual(report["needs_exact_progress_count"], 0)
        self.assertEqual(
            report["binding_details"][0]["emitted_metrics"],
            ["boundary_margin_distance", "hit"],
        )

    def test_partial_progress_bindings_are_not_ready(self) -> None:
        graph = {
            "target_id": "T_PARTIAL_BINDING",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42#parse",
                    "confidence": "verified",
                },
                {
                    "id": "producer:p",
                    "type": "producer_context",
                    "runtime_event_id": "producer:missing",
                    "confidence": "high",
                },
                {
                    "id": "range:header",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "format:header",
                    "start": 0,
                    "length": 4,
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map = tmp_path / "sites.tsv"
            site_map.write_text("123\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t0\n")
            report = audit_lift_bindings.graph_binding_audit(
                graph_path, {}, audit_lift_bindings.parse_site_map(site_map)
            )

        self.assertTrue(report["runnable"])
        self.assertFalse(report["mutation_ready"])
        self.assertEqual(report["status"], "partial_progress_bindings")
        self.assertEqual(report["missing_progress_count"], 1)
        self.assertEqual(report["progress_rules"], 1)

    def test_binding_not_required_progress_node_is_ignored_by_audit(self) -> None:
        graph = {
            "target_id": "T_BINDING_OPTIONAL",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42#parse",
                    "confidence": "verified",
                },
                {
                    "id": "producer:p",
                    "type": "producer_context",
                    "label": "seedbank provenance",
                    "binding_required": False,
                    "confidence": "low",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map = tmp_path / "sites.tsv"
            site_map.write_text("123\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t0\n")
            report = audit_lift_bindings.graph_binding_audit(
                graph_path, {}, audit_lift_bindings.parse_site_map(site_map)
            )

        self.assertTrue(report["runnable"])
        self.assertEqual(report["status"], "insufficient_binding_tier")
        self.assertEqual(report["missing_progress_count"], 0)
        self.assertEqual(report["progress_rules"], 1)
        self.assertEqual(report["insufficient_binding_tier_count"], 1)

    def test_collapsed_semantic_progress_bindings_are_not_ready(self) -> None:
        graph = {
            "target_id": "T_COLLAPSED_PROGRESS",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "runtime_event_id": "cmp:123",
                    "confidence": "verified",
                },
                {
                    "id": "use:u",
                    "type": "use_context",
                    "runtime_event_id": "cmp:123",
                    "confidence": "verified",
                },
                {
                    "id": "range:r",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "input:7",
                    "start": 0,
                    "length": 4,
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            graph_path = self.write_json(Path(tmp), "graph.json", graph)
            report = audit_lift_bindings.graph_binding_audit(graph_path, {}, [])

        self.assertTrue(report["runnable"])
        self.assertFalse(report["mutation_ready"])
        self.assertEqual(report["status"], "collapsed_progress_bindings")
        self.assertEqual(report["collapsed_progress_count"], 1)
        self.assertEqual(
            report["collapsed_progress_bindings"][0]["node_types"],
            ["guard_context", "use_context"],
        )

    def test_numeric_fuzzy_cmp_reports_no_distance_progress_binding(self) -> None:
        graph = {
            "target_id": "T_NUMERIC_FUZZY_AUDIT",
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
            report = audit_lift_bindings.graph_binding_audit(
                graph_path, {}, audit_lift_bindings.parse_site_map(site_map)
            )
            template_json = tmp_path / "runtime_map.template.json"
            audit_lift_bindings.write_runtime_template(template_json, [report])
            template = json.loads(template_json.read_text())

        self.assertTrue(report["runnable"])
        self.assertEqual(report["status"], "needs_exact_progress_binding")
        self.assertEqual(report["exact_progress_bindings"], 0)
        self.assertEqual(report["fuzzy_progress_bindings"], 1)
        self.assertEqual(report["distance_progress_bindings"], 0)
        self.assertEqual(report["needs_exact_progress_count"], 1)
        self.assertEqual(
            report["needs_exact_progress_bindings"][0]["reason"],
            "fuzzy_binding_no_distance",
        )
        self.assertGreaterEqual(
            len(report["needs_exact_progress_bindings"][0]["candidate_bindings"]), 2
        )
        self.assertEqual(report["binding_details"][0]["emitted_metrics"], ["hit"])
        entry = template["runtime_events"]["source:src/parser.c:42#parse"]
        self.assertIn("exact_progress", entry["required_for"])
        self.assertEqual(entry["reason"], ["fuzzy_binding_no_distance"])
        self.assertGreaterEqual(len(entry["candidate_bindings"]), 2)

    def test_relocated_numeric_label_does_not_offer_stale_window_candidate(self) -> None:
        graph = {
            "target_id": "T_RELOCATED_NUMERIC_AUDIT",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "label": "row_factor_l == ((size_t)1 << (sizeof(png_uint_32) * 8))",
                    "source_location": "pngrutil.c:3174:8#png_check_chunk_length",
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "repo"
            source_root.mkdir()
            source = source_root / "pngrutil.c"
            lines_in_source = ["int pad;"] * 3169
            lines_in_source.append("if (png_ptr->chunk_name == png_IDAT) {}")
            lines_in_source.extend(["int gap;"] * 18)
            lines_in_source.append(
                'MAGMA_LOG("BUG", row_factor_l == ((size_t)1 << (sizeof(png_uint_32) * 8)));'
            )
            source.write_text("\n".join(lines_in_source) + "\n")

            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map = tmp_path / "sites.tsv"
            site_map.write_text(
                "111\tcmp\tpng_check_chunk_length\t7\ticmp\tpngrutil.c\t3170\t28\n"
                "222\tcmp\tpng_check_chunk_length\t8\ticmp\tpngrutil.c\t3189\t7\n"
                "333\tcmp\tpng_check_chunk_length\t9\ticmp\tpngrutil.c\t3189\t11\n"
            )
            report = audit_lift_bindings.graph_binding_audit(
                graph_path,
                {},
                audit_lift_bindings.parse_site_map(site_map),
                source_roots=[source_root],
            )
            template_json = tmp_path / "runtime_map.template.json"
            audit_lift_bindings.write_runtime_template(template_json, [report])
            template = json.loads(template_json.read_text())

        self.assertEqual(report["status"], "needs_exact_progress_binding")
        self.assertEqual(report["distance_progress_bindings"], 0)
        self.assertEqual(report["needs_exact_progress_count"], 1)
        self.assertEqual(
            report["binding_details"][0]["binding_source"], "site-map-line-cluster"
        )
        candidates = report["needs_exact_progress_bindings"][0]["candidate_bindings"]
        self.assertEqual({item["site_id"] for item in candidates}, {222, 333})
        entry = template["runtime_events"]["source:pngrutil.c:3189#png_check_chunk_length"]
        self.assertEqual({item["site_id"] for item in entry["candidate_bindings"]}, {222, 333})
        self.assertNotIn("source:pngrutil.c:3174:8#png_check_chunk_length", template["runtime_events"])

    def test_materialized_fuzzy_cmp_stays_fuzzy_after_reload(self) -> None:
        graph = {
            "target_id": "T_NUMERIC_MATERIALIZED_FUZZY",
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
            runtime_map = tmp_path / "runtime_map.json"
            materialize = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZE_PATH),
                    "--trigger-graph",
                    str(graph_path),
                    "--site-map",
                    str(site_map),
                    "-o",
                    str(runtime_map),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            summary = json.loads(materialize.stdout)
            payload = json.loads(runtime_map.read_text())
            loaded = audit_lift_bindings.load_runtime_map(runtime_map)
            lines, compile_report = audit_lift_bindings.compile_graph(
                graph_path, loaded, [], include_comments=False
            )
            audit_report = audit_lift_bindings.graph_binding_audit(
                graph_path, loaded, []
            )

        binding = payload["runtime_events"]["source:src/parser.c:42#parse"]
        self.assertEqual(summary["runnable"], 1)
        self.assertEqual(summary["ready"], 0)
        self.assertEqual(summary["needs_exact_progress_binding"], 1)
        self.assertTrue(str(binding["source"]).startswith("site-map-"))
        self.assertEqual(compile_report["progress_rules"], 1)
        self.assertFalse(any(" lower distance " in line for line in lines))
        self.assertEqual(
            compile_report["binding_details"][0]["emitted_metrics"], ["hit"]
        )
        self.assertEqual(audit_report["status"], "needs_exact_progress_binding")
        self.assertEqual(audit_report["distance_progress_bindings"], 0)

    def test_external_exact_cmp_selection_enables_numeric_distance(self) -> None:
        graph = {
            "target_id": "T_NUMERIC_EXTERNAL_SELECTION",
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
        runtime_map = {
            "runtime_events": {
                "source:src/parser.c:42#parse": {
                    "event_kind": "cmp",
                    "site_id": 123,
                    "source": "external-selection",
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            runtime_map_path = self.write_json(tmp_path, "runtime_map.json", runtime_map)
            loaded = audit_lift_bindings.load_runtime_map(runtime_map_path)
            lines, compile_report = audit_lift_bindings.compile_graph(
                graph_path, loaded, [], include_comments=False
            )
            audit_report = audit_lift_bindings.graph_binding_audit(
                graph_path, loaded, []
            )

        self.assertEqual(audit_report["status"], "progress_only_no_hot_ranges")
        self.assertEqual(audit_report["exact_progress_bindings"], 1)
        self.assertEqual(audit_report["fuzzy_progress_bindings"], 0)
        self.assertEqual(audit_report["distance_progress_bindings"], 1)
        self.assertIn("boundary_margin_distance", compile_report["binding_details"][0]["emitted_metrics"])
        self.assertTrue(any(" lower distance " in line for line in lines))

    def test_require_ready_rejects_materialized_fuzzy_exact_progress_debt(self) -> None:
        graph = {
            "target_id": "T_REQUIRE_READY_FUZZY",
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
            runtime_map = tmp_path / "runtime_map.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZE_PATH),
                    "--trigger-graph",
                    str(graph_path),
                    "--site-map",
                    str(site_map),
                    "-o",
                    str(runtime_map),
                    "--require-ready",
                ],
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["ready"], 0)

    def test_wrapper_refusal_can_emit_binding_audit_and_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph = self.write_json(tmp_path, "graph.json", self.magma_like_graph())
            audit_json = tmp_path / "audit.json"
            template_json = tmp_path / "runtime_map.template.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph),
                    "--work-dir",
                    str(tmp_path),
                    "--binding-audit-json",
                    str(audit_json),
                    "--binding-template-out",
                    str(template_json),
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

            audit = json.loads(audit_json.read_text())
            template = json.loads(template_json.read_text())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no progress rules", result.stderr)
        self.assertIn(str(audit_json), result.stderr)
        self.assertEqual(audit["summary"]["runnable"], 0)
        self.assertIn("lifecycle:create", template["runtime_events"])

    def test_materialized_site_map_can_drive_wrapper_compile(self) -> None:
        graph = {
            "target_id": "T_SITE",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42#parse",
                    "confidence": "verified",
                },
                {
                    "id": "range:header",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "format:header",
                    "start": 0,
                    "length": 4,
                    "confidence": "high",
                },
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map = tmp_path / "sites.tsv"
            site_map.write_text("123\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t0\n")
            runtime_map = tmp_path / "runtime_map.json"
            materialize = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZE_PATH),
                    "--trigger-graph",
                    str(graph_path),
                    "--site-map",
                    str(site_map),
                    "-o",
                    str(runtime_map),
                    "--require-progress",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            summary = json.loads(materialize.stdout)

            compile_only = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph_path),
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
            report = json.loads(compile_only.stdout)

        self.assertEqual(summary["runnable"], 1)
        self.assertEqual(summary["bindings"], 1)
        self.assertEqual(report["progress_rules"], 1)
        self.assertEqual(report["range_rules"], 1)

    def test_multisource_location_template_and_materialization(self) -> None:
        graph = {
            "target_id": "T_MULTI_SOURCE",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "use:u",
                    "type": "use_context",
                    "source_location": "src/create.c:10#create; src/use.c:20#consume",
                    "confidence": "high",
                },
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            audit_json = tmp_path / "audit.json"
            template_json = tmp_path / "runtime_map.template.json"
            audit_result = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_PATH),
                    "--trigger-graph",
                    str(graph_path),
                    "--report-json",
                    str(audit_json),
                    "--template-out",
                    str(template_json),
                    "--fail-on-unrunnable",
                ],
                text=True,
                capture_output=True,
            )
            template = json.loads(template_json.read_text())

            site_map = tmp_path / "sites.tsv"
            site_map.write_text("456\tload\tconsume\t3\tload\tsrc/use.c\t20\t4\n")
            runtime_map = tmp_path / "runtime_map.json"
            materialize = subprocess.run(
                [
                    sys.executable,
                    str(MATERIALIZE_PATH),
                    "--trigger-graph",
                    str(graph_path),
                    "--site-map",
                    str(site_map),
                    "-o",
                    str(runtime_map),
                    "--require-progress",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            summary = json.loads(materialize.stdout)
            runtime_payload = json.loads(runtime_map.read_text())

            compile_only = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--afl-fuzz",
                    "/bin/echo",
                    "--trigger-graph",
                    str(graph_path),
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
            report = json.loads(compile_only.stdout)

        self.assertEqual(audit_result.returncode, 2)
        self.assertIn("source:src/create.c:10#create", template["runtime_events"])
        self.assertIn("source:src/use.c:20#consume", template["runtime_events"])
        self.assertEqual(summary["runnable"], 1)
        self.assertEqual(summary["bindings"], 2)
        self.assertIn("source:src/create.c:10#create", runtime_payload["runtime_events"])
        self.assertIn("source:src/use.c:20#consume", runtime_payload["runtime_events"])
        self.assertEqual(report["progress_rules"], 1)

    def test_template_keeps_symbolic_runtime_id_with_source_candidates(self) -> None:
        graph = {
            "target_id": "T_RUNTIME_AND_SOURCE",
            "nodes": [
                {
                    "id": "atom:a1",
                    "type": "tc_atom",
                    "category": "compound-sequence-lifecycle",
                },
                {
                    "id": "phase:p",
                    "type": "lifecycle_phase",
                    "runtime_event_id": "lifecycle:producer",
                    "source_location": "src/a.c:10#a; src/b.c:20#b",
                    "confidence": "medium",
                },
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            template_json = tmp_path / "runtime_map.template.json"
            subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_PATH),
                    "--trigger-graph",
                    str(graph_path),
                    "--template-out",
                    str(template_json),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            template = json.loads(template_json.read_text())

        self.assertIn("lifecycle:producer", template["runtime_events"])
        self.assertIn("source:src/a.c:10#a", template["runtime_events"])
        self.assertIn("source:src/b.c:20#b", template["runtime_events"])


if __name__ == "__main__":
    unittest.main()
