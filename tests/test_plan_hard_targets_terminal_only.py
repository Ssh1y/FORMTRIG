import importlib.util
from pathlib import Path
import unittest


def load_planner():
    path = Path(__file__).resolve().parents[1] / "tools" / "plan_formtrig_hard_targets.py"
    spec = importlib.util.spec_from_file_location("plan_formtrig_hard_targets", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TerminalOnlyValidationTest(unittest.TestCase):
    def test_terminal_only_validation_does_not_promote(self):
        planner = load_planner()
        record = {
            "schema": "formtrig_binding_candidate_validation_v1",
            "target_id": "PNG007",
            "status": "terminal_only_no_pretrigger_guidance",
            "ready_for_short_gate": False,
            "native_site_map_validated": True,
            "blockers": [
                "pre-trigger lift guidance is not ready",
                "terminal signal appeared without non-trigger guidance",
            ],
            "checks": {
                "binding_spec_compile_pass": True,
                "lift_audit_pass": True,
                "binding_signal_pass": True,
                "terminal_triggered": True,
                "non_trigger_candidate_lift_delta": False,
            },
            "benefit_readout": {
                "terminal_triggered": True,
                "pretrigger_lift_guidance_ready": False,
            },
        }
        planner.binding_validation_records = lambda target_id: [record]

        self.assertTrue(planner.binding_validation_terminal_only("PNG007"))
        self.assertEqual(
            planner.binding_validation_terminal_only_blockers("PNG007"),
            [
                "pre-trigger lift guidance is not ready",
                "terminal signal appeared without non-trigger guidance",
            ],
        )
        self.assertFalse(planner.binding_spec_validated("PNG007"))
        self.assertEqual(
            planner.lane_for(
                "magma",
                "binary-state-null",
                "",
                ["PNG007.native_b3_current_root46.yml"],
                False,
                "",
                terminal_only_validation=True,
            ),
            "control_or_negative",
        )
        status, blockers = planner.status_for(
            "magma",
            "binary-state-null",
            "",
            ["PNG007.native_b3_current_root46.yml"],
            False,
            "",
            0,
            has_external_input=True,
            has_commit=True,
            terminal_only_validation=True,
        )
        self.assertEqual(status, "do_not_promote")
        self.assertIn("terminal-only", blockers[0])


if __name__ == "__main__":
    unittest.main()
