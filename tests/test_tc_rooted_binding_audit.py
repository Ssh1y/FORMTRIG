import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_tool(name: str):
    path = Path(__file__).resolve().parents[1] / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PASSING_BINARY_SPEC = """
tc_id: PHP003
tc:
  category: binary-state-null
  expression: MAGMA_AND((bool)data, ImageInfo->Thumbnail.size < 4)
atoms:
  - id: 1
    expr: data != NULL && ImageInfo->Thumbnail.size < 4
    kind: binary-state-null
    root: ImageInfo->Thumbnail.data
bindings:
  - id: data_root
    atom: 1
    role: root_observe
    expr: observe thumbnail data root
    observe_at:
      kind: cmp
      file: ext/exif/exif.c
      line: 3918
    component: root_state
    priority: 10
    direction: lower
    value_mode: distance
  - id: data_producer
    atom: 1
    role: desired_producer
    expr: thumbnail bytes enter producer path
    observe_at:
      site_id: 2484435316
    component: producer_use
    priority: 20
    direction: higher
    value_mode: outcome
"""


ROOT_ONLY_BINARY_SPEC = """
tc_id: BAD001
tc:
  category: binary-null
  expression: a == NULL
atoms:
  - id: 1
    expr: a == NULL
    kind: binary-null
    root: a
bindings:
  - id: a_root
    atom: 1
    role: root_observe
    expr: observe a
    observe_at:
      file: src/a.c
      line: 10
    component: root_state
    priority: 10
    direction: lower
    value_mode: outcome
"""


class TcRootedBindingAuditTest(unittest.TestCase):
    def test_binary_spec_with_root_and_producer_passes_static_audit(self):
        audit_tool = load_tool("audit_binding_spec_tc_rooted")
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "PHP003.yml"
            spec.write_text(PASSING_BINARY_SPEC, encoding="utf-8")

            audit = audit_tool.audit_file(spec)

            self.assertEqual(audit["status"], "pass")
            self.assertTrue(audit["checks"]["static_root_binding_pass"])
            self.assertTrue(audit["checks"]["semantic_role_coverage_pass"])
            self.assertTrue(audit["checks"]["exact_runtime_mapping_pass"])
            self.assertEqual(audit["role_counts"]["root_observe"], 1)
            self.assertEqual(audit["role_counts"]["desired_producer"], 1)

    def test_binary_root_only_spec_is_not_tc_rooted_effective_subset(self):
        audit_tool = load_tool("audit_binding_spec_tc_rooted")
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "BAD001.yml"
            spec.write_text(ROOT_ONLY_BINARY_SPEC, encoding="utf-8")

            audit = audit_tool.audit_file(spec)

            self.assertEqual(audit["status"], "fail")
            self.assertTrue(audit["checks"]["static_root_binding_pass"])
            self.assertFalse(audit["checks"]["semantic_role_coverage_pass"])
            self.assertFalse(audit["checks"]["negative_role_rejection_pass"])
            self.assertIn(
                "atom 1 lacks producer/use/input_influence binding for binary/null TC",
                audit["blockers"],
            )

    def test_summarizer_rejects_dynamic_progress_when_static_spec_is_not_rooted(self):
        summarizer = load_tool("summarize_binding_candidate_sweep")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "BAD001.yml"
            spec.write_text(ROOT_ONLY_BINARY_SPEC, encoding="utf-8")
            summary = root / "summary.jsonl"
            summary.write_text(
                json.dumps(
                    {
                        "index": 1,
                        "score": 400000,
                        "candidate": str(spec),
                        "out_dir": "out",
                        "exit_code": 0,
                        "diagnosis": "queued_tc_rooted_progress",
                        "experiment_ready": True,
                        "pretrigger_lift_guidance_ready": True,
                        "has_non_trigger_progress": True,
                        "non_trigger_progress_events": 4,
                        "saved_non_trigger_progress_events": 2,
                        "saved_triggered_progress_events": 0,
                        "execs_done": 123,
                        "reached_execs": 20,
                        "triggered_execs": 0,
                        "binding_signal_status": "pass",
                        "binding_signal_diagnosis": "role_signal_progress_observed",
                        "candidate_events": 5,
                        "accepted_non_trigger_progress_events": 2,
                        "non_trigger_candidate_lift_delta": True,
                        "lift_delta_only_on_triggered_candidates": False,
                        "semantic_candidate_variable_roles": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            row = summarizer.best_row(summarizer.read_jsonl(summary))
            record = summarizer.build_record(
                row=row,
                target_id="BAD001",
                binding_spec=str(spec),
                site_map="site_map.tsv",
                summary_jsonl=summary,
            )

            self.assertEqual(record["status"], "static_binding_not_tc_rooted")
            self.assertFalse(record["ready_for_short_gate"])
            self.assertFalse(record["checks"]["tc_rooted_static_pass"])
            self.assertEqual(record["tc_rooted_static"]["status"], "fail")
            self.assertIn("BindingSpec failed TC-rooted static audit", record["blockers"])
            self.assertIn(
                "dynamic correlation cannot substitute for a TC-rooted BindingSpec",
                record["remaining_limitations"],
            )


if __name__ == "__main__":
    unittest.main()
