import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.analyze_baseline_guidance_gap import load_baseline_rows, target_analysis


class BaselineGuidanceGapTest(unittest.TestCase):
    def write_summary(self, root: Path, records: list[dict]) -> Path:
        summary = root / "summary.json"
        summary.write_text(json.dumps({"records": records}), encoding="utf-8")
        return summary

    def write_run_record(
        self,
        root: Path,
        *,
        name: str,
        baseline: str,
        target_id: str = "TGT",
        budget: int = 7200,
        first_reach_time: int = 60,
        first_trigger_time: int | None = None,
        latest_reached: int = 1000,
        latest_triggered: int = 0,
        success: bool = False,
    ) -> Path:
        monitor = {
            "bug_id": target_id,
            "first_reach": {
                "bug_id": target_id,
                "kind": "poll",
                "reached": 1,
                "time_s": first_reach_time,
                "triggered": 0,
            },
            "first_trigger": None
            if first_trigger_time is None
            else {
                "bug_id": target_id,
                "kind": "poll",
                "reached": latest_reached,
                "time_s": first_trigger_time,
                "triggered": latest_triggered or 1,
            },
            "latest": {
                "bug_id": target_id,
                "kind": "final",
                "reached": latest_reached,
                "triggered": latest_triggered,
            },
        }
        path = root / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "baseline": baseline,
                    "budget": budget,
                    "magma_monitor": monitor,
                    "success": success,
                    "target_id": target_id,
                    "trigger_time_s": first_trigger_time,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_passes_when_binary_flat_and_baselines_are_missing_or_late(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = []
            for baseline in ["aflplusplus_vanilla", "aflplusplus_cmplog"]:
                for rep in range(1, 4):
                    run_record = self.write_run_record(
                        root,
                        name=f"{baseline}_{rep}",
                        baseline=baseline,
                        first_trigger_time=None if rep < 3 else 3600,
                        latest_triggered=0 if rep < 3 else 10,
                        success=rep == 3,
                    )
                    records.append(
                        {
                            "baseline": baseline,
                            "budget": 7200,
                            "rep": rep,
                            "run_record": str(run_record),
                            "success": rep == 3,
                            "target_id": "TGT",
                            "trigger_time_s": None if rep < 3 else 3600,
                        }
                    )
            summary = self.write_summary(root, records)

            rows = load_baseline_rows([f"matched={summary}"])
            analysis = target_analysis(
                rows,
                required_baselines=["aflplusplus_vanilla", "aflplusplus_cmplog"],
                min_reps=3,
                acceptable_trigger_s=600,
                hard_trigger_s=1800,
                variance_trigger_s=1800,
            )

        self.assertEqual(analysis["status"], "measured_pass")
        self.assertTrue(analysis["pretrigger_binary_flat_pass"])
        self.assertTrue(analysis["endpoint_cost_pass"])
        self.assertIn("pretrigger_binary_oracle_flat_before_T", analysis["reasons"])

    def test_fast_successful_baseline_demotes_hard_pain_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = []
            for rep, tte in enumerate([120, 180, 240], 1):
                run_record = self.write_run_record(
                    root,
                    name=f"vanilla_{rep}",
                    baseline="aflplusplus_vanilla",
                    first_trigger_time=tte,
                    latest_triggered=10,
                    success=True,
                )
                records.append(
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 600,
                        "rep": rep,
                        "run_record": str(run_record),
                        "success": True,
                        "target_id": "TGT",
                        "trigger_time_s": tte,
                    }
                )
            summary = self.write_summary(root, records)

            rows = load_baseline_rows([f"matched={summary}"])
            analysis = target_analysis(
                rows,
                required_baselines=["aflplusplus_vanilla"],
                min_reps=3,
                acceptable_trigger_s=600,
                hard_trigger_s=1800,
                variance_trigger_s=1800,
            )

        self.assertEqual(analysis["status"], "fail_fast_baseline")
        self.assertTrue(analysis["pretrigger_binary_flat_pass"])
        self.assertFalse(analysis["endpoint_cost_pass"])
        self.assertIn("fast_successful_baseline_within_acceptable_threshold", analysis["reasons"])

    def test_missing_monitor_keeps_no_guidance_claim_unmeasured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = self.write_summary(
                root,
                [
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 7200,
                        "rep": 1,
                        "success": False,
                        "target_id": "TGT",
                        "trigger_time_s": None,
                    }
                ],
            )

            rows = load_baseline_rows([f"matched={summary}"])
            analysis = target_analysis(
                rows,
                required_baselines=["aflplusplus_vanilla"],
                min_reps=1,
                acceptable_trigger_s=600,
                hard_trigger_s=1800,
                variance_trigger_s=1800,
            )

        self.assertEqual(analysis["status"], "not_measured")
        self.assertFalse(analysis["pretrigger_binary_flat_measured"])
        self.assertIn("pretrigger_binary_flatness_not_measured_for_all_runs", analysis["reasons"])


if __name__ == "__main__":
    unittest.main()
