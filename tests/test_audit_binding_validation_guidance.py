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


class AuditBindingValidationGuidanceTest(unittest.TestCase):
    def test_classifies_terminal_only_and_strict_pretrigger_guidance(self):
        tool = load_tool("audit_binding_validation_guidance")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "strong.validation.json").write_text(
                json.dumps(
                    {
                        "target_id": "TIF012",
                        "status": "native_binding_validated",
                        "ready_for_short_gate": True,
                        "benefit_readout": {
                            "terminal_triggered": True,
                            "pretrigger_lift_guidance_ready": True,
                            "saved_non_trigger_progress_events": 3,
                            "non_trigger_progress_events": 3,
                            "execs_done": 100,
                        },
                        "binding_signal": {
                            "accepted_non_trigger_progress_events": 3,
                            "candidate_events": 44,
                        },
                        "checks": {"terminal_triggered": True},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "terminal.validation.json").write_text(
                json.dumps(
                    {
                        "target_id": "SSL015",
                        "status": "terminal_only_variable_semantic_roles_no_pretrigger_guidance",
                        "ready_for_short_gate": False,
                        "benefit_readout": {
                            "terminal_triggered": True,
                            "pretrigger_lift_guidance_ready": False,
                            "saved_non_trigger_progress_events": 0,
                        },
                        "binding_signal": {
                            "accepted_non_trigger_progress_events": 0,
                            "candidate_events": 20,
                        },
                        "checks": {"terminal_triggered": True},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "soft.validation.json").write_text(
                json.dumps(
                    {
                        "target_id": "PDF003",
                        "status": "native_binding_validated",
                        "ready_for_short_gate": True,
                        "benefit_readout": {
                            "terminal_triggered": False,
                            "pretrigger_lift_guidance_ready": True,
                            "saved_non_trigger_progress_events": 0,
                        },
                        "binding_signal": {
                            "accepted_non_trigger_progress_events": 0,
                            "candidate_events": 12,
                        },
                        "checks": {"non_trigger_candidate_lift_delta": True},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            audit = tool.build_audit([str(root)])
            by_target = {row["target_id"]: row for row in audit["targets"]}

            self.assertEqual(
                by_target["TIF012"]["disposition"],
                "mechanism_and_endpoint_candidate",
            )
            self.assertTrue(by_target["TIF012"]["strict_pretrigger_guidance"])
            self.assertEqual(
                by_target["SSL015"]["disposition"],
                "terminal_only_control",
            )
            self.assertFalse(by_target["SSL015"]["strict_pretrigger_guidance"])
            self.assertEqual(
                by_target["PDF003"]["disposition"],
                "soft_signal_needs_frontier_evidence",
            )
            self.assertFalse(by_target["PDF003"]["strict_pretrigger_guidance"])

    def test_static_non_rooted_binding_overrides_dynamic_progress(self):
        tool = load_tool("audit_binding_validation_guidance")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.validation.json").write_text(
                json.dumps(
                    {
                        "target_id": "BAD001",
                        "status": "static_binding_not_tc_rooted",
                        "ready_for_short_gate": False,
                        "tc_rooted_static": {
                            "status": "fail",
                            "blockers": [
                                "atom 1 lacks producer/use/input_influence binding for binary/null TC"
                            ],
                        },
                        "benefit_readout": {
                            "terminal_triggered": False,
                            "pretrigger_lift_guidance_ready": True,
                            "saved_non_trigger_progress_events": 2,
                            "non_trigger_progress_events": 2,
                        },
                        "binding_signal": {
                            "accepted_non_trigger_progress_events": 2,
                            "candidate_events": 5,
                        },
                        "checks": {"non_trigger_candidate_lift_delta": True},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            audit = tool.build_audit([str(root)])
            row = audit["targets"][0]

            self.assertEqual(row["disposition"], "static_binding_not_tc_rooted")
            self.assertEqual(row["tc_rooted_static_status"], "fail")
            self.assertFalse(row["strict_pretrigger_guidance"])
            self.assertFalse(row["soft_pretrigger_signal"])
            self.assertEqual(
                row["next_action"],
                "repair the BindingSpec semantic roles before using dynamic progress as guidance evidence",
            )


if __name__ == "__main__":
    unittest.main()
