import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = REPO_ROOT / "tools" / "gpac3403_lifecycle_gap_audit.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Gpac3403LifecycleGapAuditTest(unittest.TestCase):
    def test_reports_parser_proximity_without_alias_terminal(self):
        audit = load_module(AUDIT_PATH, "gpac3403_lifecycle_gap_audit_report")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binding = root / "binding.yml"
            binding.write_text(
                """tc_id: 'GPAC_3403'
tc:
  category: 'compound-sequence-lifecycle'
  expression: 'same sample buffer is freed twice'
bindings:
  - id: 'release'
    atom: 1
    role: 'lifecycle_event'
    site_id: 3030846436
  - id: 'cleanup'
    atom: 1
    role: 'use'
    site_id: 14730514
  - id: 'same'
    atom: 1
    role: 'same_object'
    site_id: 1549213408
    relation_from: 'lifecycle_event'
    relation_to: 'use'
    object_expr: 'GF_ISOSample.data==GF_BitStream.original'
""",
                encoding="utf-8",
            )
            diagnosis = root / "diagnosis.json"
            diagnosis.write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "diagnosis": "role_signal_progress_observed",
                        "non_trigger_candidate_lift_delta": True,
                        "atoms": [
                            {
                                "atom_id": 1,
                                "category": "compound-sequence-lifecycle",
                                "diagnosis": "constant_lift_signal",
                                "bound_roles": [
                                    "root_observe",
                                    "lifecycle_event",
                                    "use",
                                    "same_object",
                                ],
                                "sampled_roles": [
                                    "root_observe",
                                    "lifecycle_event",
                                    "use",
                                    "same_object",
                                ],
                                "candidate_sampled_roles": [
                                    "root_observe",
                                    "lifecycle_event",
                                    "use",
                                    "same_object",
                                ],
                                "roles": [
                                    {
                                        "role": "same_object",
                                        "samples": 2,
                                        "candidate_samples": 1,
                                        "unique_values": 1,
                                        "candidate_unique_values": 1,
                                        "values": [1234],
                                        "candidate_values": [1234],
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            progress = root / "progress.jsonl"
            progress.write_text(
                json.dumps(
                    {
                        "event": "typed_retain",
                        "d_f_spec_lifted": 2,
                        "component_values": [
                            {"role": 8, "value": 1234},
                        ],
                        "atom_signal_values": [
                            {"role_bits": 1 << 7, "flags": 0, "object_id_bucket": 0}
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            summary = root / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "execs_done": 200,
                        "formtrig_triggered_execs": 0,
                        "d_f_spec_lifted_min": 1,
                        "d_f_spec_lifted_max": 2,
                    }
                ),
                encoding="utf-8",
            )
            endpoint = root / "endpoint_package.json"
            endpoint.write_text(
                json.dumps(
                    {
                        "endpoint_audit": {
                            "report": {
                                "variant": {
                                    "metrics": {
                                        "hevc_import_files": 4,
                                        "asan_double_free_files": 0,
                                    }
                                },
                                "positive_control": {
                                    "metrics": {"asan_double_free_files": 1}
                                },
                                "contrast": {
                                    "variant_files": 8,
                                    "positive_control_files": 1,
                                    "positive_control_signatures_absent_from_variants": [
                                        "asan",
                                        "asan_double_free",
                                    ],
                                    "top_variants_by_positive_overlap": [
                                        {
                                            "variant_index": 5,
                                            "matched_positive_signatures": [
                                                "track_importing_hevc",
                                                "hevc_import_results",
                                            ],
                                            "missing_positive_signatures": [
                                                "asan",
                                                "asan_double_free",
                                            ],
                                        }
                                    ],
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            args = type(
                "Args",
                (),
                {
                    "binding_spec": binding,
                    "binding_diagnosis": diagnosis,
                    "progress_jsonl": progress,
                    "summary_json": summary,
                    "endpoint_package": endpoint,
                },
            )
            report = audit.build_report(args)

        self.assertEqual(
            report["verdict"]["status"],
            "parser_proximity_without_alias_terminal",
        )
        self.assertEqual(
            report["verdict"]["primary_gap"],
            "same_object_relation_semantics_missing",
        )
        self.assertTrue(report["verdict"]["guidance_effect"]["r_to_parser_neighborhood"])
        self.assertFalse(
            report["verdict"]["guidance_effect"]["r_to_lifecycle_alias_terminal"]
        )
        self.assertTrue(report["verdict"]["same_object_signal_sparse"])


if __name__ == "__main__":
    unittest.main()
