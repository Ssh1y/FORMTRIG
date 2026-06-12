#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPILER_PATH = ROOT / "formtrig" / "tools" / "compile_lift_spec.py"

spec = importlib.util.spec_from_file_location("compile_lift_spec", COMPILER_PATH)
compile_lift_spec = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["compile_lift_spec"] = compile_lift_spec
spec.loader.exec_module(compile_lift_spec)


class LiftSpecCompilerTests(unittest.TestCase):
    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data))
        return path

    def test_lifecycle_phases_compile_only_from_external_bindings(self) -> None:
        graph = {
            "target_id": "T_LIFE",
            "nodes": [
                {
                    "id": "atom:a1",
                    "type": "tc_atom",
                    "category": "compound-sequence-lifecycle",
                },
                {
                    "id": "phase:create",
                    "type": "lifecycle_phase",
                    "runtime_event_id": "life:create",
                    "confidence": "high",
                },
                {
                    "id": "phase:use",
                    "type": "lifecycle_phase",
                    "runtime_event_id": "life:use",
                    "confidence": "high",
                },
                {
                    "id": "range:create",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "life:create",
                    "start": 0,
                    "length": 2,
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
        runtime_map = {
            "runtime_events": {
                "life:create": {"event_kind": "branch", "site_id": 101},
                "life:use": {"event_kind": "branch", "site_id": 102},
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            map_path = self.write_json(tmp_path, "map.json", runtime_map)
            loaded_map = compile_lift_spec.load_runtime_map(map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, loaded_map, [], include_comments=False
            )

        self.assertEqual(report["rules"], 3)
        self.assertEqual(report["progress_rules"], 2)
        self.assertEqual(report["range_rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(any(line.startswith("phase 8 101 7 1 10 1 ") for line in lines))
        self.assertTrue(any(line.startswith("phase 8 102 7 1 10 2 ") for line in lines))
        self.assertIn("range 8 101 0 2 0.95", lines)

    def test_unmapped_symbolic_runtime_event_is_not_guessed(self) -> None:
        graph = {
            "target_id": "T_BIN",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "producer:p",
                    "type": "producer_context",
                    "runtime_event_id": "producer:symbolic-only",
                    "confidence": "medium",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            graph_path = self.write_json(Path(tmp), "graph.json", graph)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, [], include_comments=True
            )

        runtime_lines = [line for line in lines if not line.startswith("#")]
        self.assertEqual(runtime_lines, [])
        self.assertEqual(report["rules"], 0)
        self.assertEqual(report["skipped"][0]["node"], "producer:p")

    def test_site_map_resolves_source_location_without_target_semantics(self) -> None:
        graph = {
            "target_id": "T_GUARD",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
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
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "123\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t0\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 123 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_numeric_guard_cmp_emits_boundary_distance_component(self) -> None:
        graph = {
            "target_id": "T_NUMERIC",
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
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "123\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t0\n"
                "124\tcmp\tparse\t8\ticmp\tsrc/parser.c\t42\t4\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 2)
        self.assertEqual(report["progress_rules"], 2)
        self.assertEqual(report["skipped"], [])
        self.assertEqual(len(report["binding_details"]), 1)
        self.assertEqual(report["binding_details"][0]["binding_source"], "site-map")
        self.assertTrue(report["binding_details"][0]["distance_binding_supported"])
        self.assertEqual(
            report["binding_details"][0]["emitted_metrics"],
            ["boundary_margin_distance", "hit"],
        )
        self.assertTrue(
            any(
                line.startswith("component 7 124 3 1 20 lower distance 0.0 ")
                for line in lines
            )
        )
        self.assertTrue(
            any(line.startswith("component 7 124 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_numeric_guard_window_cmp_does_not_emit_distance_component(self) -> None:
        graph = {
            "target_id": "T_NUMERIC_WINDOW",
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
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "124\tcmp\tparse\t8\ticmp\tsrc/parser.c\t42\t4\n"
                "125\tcmp\tparse\t9\ticmp\tsrc/parser.c\t42\t5\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["progress_rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertEqual(len(report["binding_details"]), 1)
        self.assertEqual(
            report["binding_details"][0]["binding_source"], "site-map-line-cluster"
        )
        self.assertFalse(report["binding_details"][0]["distance_binding_supported"])
        self.assertEqual(report["binding_details"][0]["emitted_metrics"], ["hit"])
        self.assertFalse(any(" lower distance " in line for line in lines))
        self.assertTrue(
            any(line.startswith("component 7 124 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_site_map_resolves_semicolon_source_location_candidates(self) -> None:
        graph = {
            "target_id": "T_MULTI_LOC",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "use:u",
                    "type": "use_context",
                    "source_location": "src/producer.c:10#make; src/use.c:20#consume",
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "456\tload\tconsume\t3\tload\tsrc/use.c\t20\t4\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 5 456 6 1 30 higher hit 1.0 ") for line in lines)
        )

    def test_site_map_line_fallback_when_debug_column_shifts(self) -> None:
        graph = {
            "target_id": "T_COLUMN_SHIFT",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42:8#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "222\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t7\n"
                "333\tcmp\tparse\t8\ticmp\tsrc/parser.c\t42\t11\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 7 333 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_site_map_resolves_source_window_when_target_line_shifts(self) -> None:
        graph = {
            "target_id": "T_WINDOW_SHIFT",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42:8#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "111\tbranch\tparse\t7\tbr\tsrc/parser.c\t38\t2\n"
                "222\tbranch\tother\t7\tbr\tsrc/parser.c\t42\t8\n"
                "333\tbranch\tparse\t8\tbr\tsrc/parser.c\t55\t2\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 111 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_source_root_relocates_stale_source_location_by_expression_label(self) -> None:
        graph = {
            "target_id": "T_SOURCE_RELOCATE",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "label": "pNew->nLSlot < (pNew->nLTerm+1)",
                    "source_location": "src/where.c:2769:8#whereLoopAddBtreeIndex",
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "generated"
            source_root.mkdir()
            generated = source_root / "sqlite3.c"
            generated.write_text(
                "\n".join(
                    ["int pad;"] * 99
                    + ['if( MAGMA_LOG_V("BUG", pNew->nLSlot < (pNew->nLTerm+1)) ){}']
                )
                + "\n"
            )
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "777\tbranch\twhereLoopAddBtreeIndex\t7\tbr\tsqlite3.c\t100\t8\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path,
                {},
                site_map,
                include_comments=True,
                source_roots=[source_root],
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 777 5 1 20 higher hit 1.0 ") for line in lines)
        )
        self.assertTrue(any("source_relocation=label_search" in line for line in lines))

    def test_source_relocation_takes_precedence_over_stale_window_match(self) -> None:
        graph = {
            "target_id": "T_SOURCE_RELOCATE_PRECEDENCE",
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
            lines_in_source.append('MAGMA_LOG("BUG",')
            lines_in_source.append("          row_factor_l == ((size_t)1 <<")
            lines_in_source.append("          (sizeof(png_uint_32) * 8)));")
            source.write_text("\n".join(lines_in_source) + "\n")

            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "111\tcmp\tpng_check_chunk_length\t7\ticmp\tpngrutil.c\t3170\t28\n"
                "222\tcmp\tpng_check_chunk_length\t8\ticmp\tpngrutil.c\t3190\t10\n"
                "333\tbranch\tpng_check_chunk_length\t9\tbr\tpngrutil.c\t3170\t8\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path,
                {},
                site_map,
                include_comments=True,
                source_roots=[source_root],
            )

        self.assertEqual(report["rules"], 2)
        self.assertEqual(report["skipped"], [])
        self.assertEqual(report["binding_details"][0]["binding_source"], "site-map")
        self.assertEqual(report["binding_details"][0]["site_id"], "222")
        self.assertEqual(
            report["binding_details"][0]["emitted_metrics"],
            ["boundary_margin_distance", "hit"],
        )
        self.assertTrue(
            any(line.startswith("component 7 222 3 1 20 lower distance 0.0 ") for line in lines)
        )
        self.assertFalse(any("component 7 111 " in line for line in lines))
        self.assertTrue(any("source_relocation=label_search" in line for line in lines))

    def test_same_source_line_site_cluster_chooses_deterministic_site(self) -> None:
        graph = {
            "target_id": "T_LINE_CLUSTER",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "numeric-margin"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42:8#parse",
                    "confidence": "high",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "900\tbranch\tparse\t12\tbr\tsrc/parser.c\t42\t7\n"
                "800\tbranch\tparse\t10\tbr\tsrc/parser.c\t42\t7\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 800 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_site_map_accepts_prefixed_compiled_function_names(self) -> None:
        graph = {
            "target_id": "T_PREFIXED_FUNCTION",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42:8#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "444\tbranch\tWRAPPED_parse\t7\tbr\tsrc/parser.c\t40\t2\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 444 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_zero_site_runtime_template_does_not_shadow_site_map(self) -> None:
        graph = {
            "target_id": "T_TEMPLATE_ZERO",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }
        runtime_map_json = {
            "runtime_events": {
                "source:src/parser.c:42#parse": {"event_kind": "", "site_id": 0}
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            map_path = self.write_json(tmp_path, "map.json", runtime_map_json)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "555\tbranch\tparse\t7\tbr\tsrc/parser.c\t42\t8\n"
            )
            runtime_map = compile_lift_spec.load_runtime_map(map_path)
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, runtime_map, site_map, include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 555 5 1 20 higher hit 1.0 ") for line in lines)
        )
        self.assertFalse(any("component * 0 " in line for line in lines))

    def test_producer_context_infers_predecessor_site_from_ordered_guard(self) -> None:
        graph = {
            "target_id": "T_PRODUCER_INFER",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "producer:p",
                    "type": "producer_context",
                    "runtime_event_id": "producer:symbolic",
                    "confidence": "medium",
                },
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42:8#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [
                {
                    "type": "order_before",
                    "order": "producer_before_guard",
                    "src": "producer:p",
                    "dst": "guard:g",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "100\tstore\tWRAPPED_parse\t2\tstore\tsrc/parser.c\t40\t4\n"
                "101\tbranch\tWRAPPED_parse\t3\tbr\tsrc/parser.c\t42\t8\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=True
            )

        runtime_lines = [line for line in lines if not line.startswith("#")]
        self.assertEqual(report["rules"], 2)
        self.assertEqual(report["progress_rules"], 2)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 6 100 6 1 30 higher hit 1.0 ") for line in runtime_lines)
        )
        self.assertTrue(
            any(line.startswith("component 8 101 5 1 20 higher hit 1.0 ") for line in runtime_lines)
        )
        self.assertTrue(
            any("source_inference=ordered_successor" in line for line in lines)
        )

    def test_binding_not_required_component_is_not_emitted(self) -> None:
        graph = {
            "target_id": "T_BINDING_NOT_REQUIRED",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
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
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, [], include_comments=False
            )

        self.assertEqual(lines, [])
        self.assertEqual(report["progress_rules"], 0)
        self.assertEqual(report["rules"], 0)
        self.assertEqual(report["skipped"][0]["reason"], "binding_not_required")

    def test_inferred_producer_does_not_bind_guard_when_no_predecessor_site(self) -> None:
        graph = {
            "target_id": "T_PRODUCER_NO_PREDECESSOR",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "producer:p",
                    "type": "producer_context",
                    "runtime_event_id": "producer:symbolic",
                    "confidence": "medium",
                },
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "source_location": "src/parser.c:42:8#parse",
                    "confidence": "verified",
                },
            ],
            "edges": [
                {
                    "type": "order_before",
                    "order": "producer_before_guard",
                    "src": "producer:p",
                    "dst": "guard:g",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            site_map_path = tmp_path / "sites.tsv"
            site_map_path.write_text(
                "101\tbranch\tparse\t3\tbr\tsrc/parser.c\t42\t8\n"
            )
            site_map = compile_lift_spec.parse_site_map(site_map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, site_map, include_comments=False
            )

        runtime_lines = [line for line in lines if not line.startswith("#")]
        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["progress_rules"], 1)
        self.assertEqual(report["skipped"][0]["node"], "producer:p")
        self.assertEqual(report["skipped"][0]["reason"], "site_map_no_predecessor")
        self.assertFalse(any(line.startswith("component 8 101 6 ") for line in runtime_lines))

    def test_source_prefixed_runtime_map_key_resolves_template_entries(self) -> None:
        graph = {
            "target_id": "T_TEMPLATE",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "equality/magic"},
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
                    "event_kind": "branch",
                    "site_id": 321,
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            map_path = self.write_json(tmp_path, "runtime_map.json", runtime_map)
            loaded_map = compile_lift_spec.load_runtime_map(map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, loaded_map, [], include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertTrue(
            any(line.startswith("component 8 321 5 1 20 higher hit 1.0 ") for line in lines)
        )

    def test_terminal_event_bindings_are_not_lift_progress(self) -> None:
        graph = {
            "target_id": "T_NO_ORACLE",
            "nodes": [
                {"id": "atom:a1", "type": "tc_atom", "category": "binary-state-null"},
                {
                    "id": "guard:g",
                    "type": "guard_context",
                    "runtime_event_id": "oracle:trigger",
                    "confidence": "verified",
                },
            ],
            "edges": [],
        }
        runtime_map = {
            "runtime_events": {
                "oracle:trigger": {"event_kind": "trigger", "site_id": 0}
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            graph_path = self.write_json(tmp_path, "graph.json", graph)
            map_path = self.write_json(tmp_path, "map.json", runtime_map)
            loaded_map = compile_lift_spec.load_runtime_map(map_path)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, loaded_map, [], include_comments=True
            )

        runtime_lines = [line for line in lines if not line.startswith("#")]
        self.assertEqual(runtime_lines, [])
        self.assertEqual(report["rules"], 0)
        self.assertEqual(
            report["skipped"][0]["reason"], "disallowed_lift_event_kind:2"
        )

    def test_unbound_input_range_compiles_as_static_hot_range(self) -> None:
        graph = {
            "target_id": "T_STATIC_RANGE",
            "nodes": [
                {
                    "id": "range:header",
                    "type": "candidate_input_influence_range",
                    "runtime_event_id": "format:header",
                    "start": 4,
                    "length": 3,
                    "confidence": "high",
                }
            ],
            "edges": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            graph_path = self.write_json(Path(tmp), "graph.json", graph)
            lines, report = compile_lift_spec.compile_graph(
                graph_path, {}, [], include_comments=False
            )

        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["progress_rules"], 0)
        self.assertEqual(report["range_rules"], 1)
        self.assertEqual(report["skipped"], [])
        self.assertIn("range * * 4 3 0.85", lines)


if __name__ == "__main__":
    unittest.main()
