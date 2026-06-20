import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "draft_real_cve_binding_specs.py"
    spec = importlib.util.spec_from_file_location("draft_real_cve_binding_specs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DraftRealCveBindingSpecsTest(unittest.TestCase):
    def test_trigger_graph_draft_is_static_tc_rooted_without_unsourced_producer(self):
        drafts = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_dir = root / "graphs"
            tcir_dir = root / "tcir"
            spec_dir = root / "specs"
            graph_dir.mkdir()
            tcir_dir.mkdir()
            inventory = root / "inventory.json"
            inventory.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "LIBARCHIVE_2935",
                                "project": "libarchive",
                                "run_command": "benchmarks/cve_build/libarchive-a819-asan/libarchive_write_replay @@",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (tcir_dir / "LIBARCHIVE_2935.json").write_text(
                json.dumps(
                    {
                        "target_id": "LIBARCHIVE_2935",
                        "expression": "extension length exceeds allocated identifier buffer",
                        "atoms": [
                            {
                                "atom_id": "a1",
                                "category": "numeric-margin",
                                "composition": "all_of",
                                "expression": "extension length exceeds allocated identifier buffer",
                                "root_variables": ["identifier", "extension", "allocation"],
                                "source_location": "libarchive/archive_write_set_format_iso9660.c:5913#idr_extend_identifier",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (graph_dir / "LIBARCHIVE_2935.json").write_text(
                json.dumps(
                    {
                        "nodes": [
                            {
                                "id": "site:1",
                                "type": "target_site_context",
                                "source_location": "libarchive/archive_write_set_format_iso9660.c:5913#idr_extend_identifier",
                            },
                            {
                                "id": "guard:1",
                                "type": "guard_context",
                                "source_location": "libarchive/archive_write_set_format_iso9660.c:5913#idr_extend_identifier",
                            },
                            {
                                "id": "use:1",
                                "type": "use_context",
                                "source_location": "libarchive/archive_write_set_format_iso9660.c:5913#idr_extend_identifier",
                            },
                            {
                                "id": "producer:1",
                                "type": "producer_context",
                                "source_location": "",
                            },
                            {
                                "id": "range:len",
                                "type": "candidate_input_influence_range",
                                "start": 16,
                                "length": 1,
                                "range_kind": "binary_length_prefix",
                                "integer_values": [255, 5, 0],
                                "confidence_score": 0.75,
                                "root_priority": 1,
                                "label": "id:000000[16:17]",
                            },
                            {
                                "id": "range:payload",
                                "type": "candidate_input_influence_range",
                                "start": 17,
                                "length": 4,
                                "range_kind": "binary_length_payload",
                                "confidence_score": 0.55,
                                "label": "id:000000[17:21]",
                            },
                            {
                                "id": "repair:1",
                                "type": "repair_hook",
                                "configured": False,
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = drafts.build_drafts(
                target_ids=["LIBARCHIVE_2935"],
                trigger_graph_dir=graph_dir,
                tcir_dir=tcir_dir,
                cve_inventory=inventory,
                spec_dir=spec_dir,
                overwrite=False,
            )

            self.assertEqual(payload["draft_count"], 1)
            row = payload["drafts"][0]
            self.assertEqual(row["input_range_count"], 2)
            self.assertTrue(
                any("producer_context has no source_location" in item for item in row["limitations"])
            )
            spec_path = Path(row["binding_spec"])
            text = spec_path.read_text(encoding="utf-8")
            self.assertIn("role: 'root_observe'", text)
            self.assertIn("role: 'guard'", text)
            self.assertIn("role: 'use'", text)
            self.assertIn("role: 'input_influence'", text)
            self.assertIn("range_start: 16", text)
            self.assertIn("range_len: 1", text)
            self.assertIn("mutation_value: 255", text)
            self.assertNotIn("role: 'desired_producer'", text)

            from tools.audit_binding_spec_tc_rooted import audit_file

            audit = audit_file(spec_path)
            self.assertEqual(audit["status"], "pass")
            self.assertEqual(audit["role_counts"]["input_influence"], 2)


if __name__ == "__main__":
    unittest.main()
