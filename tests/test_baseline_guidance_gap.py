import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.analyze_baseline_guidance_gap import (
    load_baseline_rows,
    load_seed_contracts,
    target_analysis,
    write_run_tsv,
)


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

    def write_non_magma_run_record(
        self,
        root: Path,
        *,
        name: str,
        baseline: str,
        seed_set_id: str,
        target_id: str = "TGT",
        budget: int = 600,
        run_time: int = 600,
        success: bool = False,
    ) -> Path:
        path = root / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "baseline": baseline,
                    "budget": budget,
                    "magma_monitor": None,
                    "seed_set_id": seed_set_id,
                    "stats": {
                        "run_time": run_time,
                        "execs_done": 1000,
                        "saved_crashes": 0,
                        "saved_hangs": 0,
                    },
                    "success": success,
                    "target_id": target_id,
                    "trigger_time_s": None,
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
        vanilla_group = next(
            group
            for group in analysis["baseline_groups"]
            if group["baseline"] == "aflplusplus_vanilla"
        )
        self.assertEqual(vanilla_group["total_reached"], 3000)
        self.assertEqual(vanilla_group["total_triggered"], 10)
        self.assertEqual(vanilla_group["total_reached_without_trigger"], 2990)
        self.assertIsNone(vanilla_group["zero_trigger_rule_of_three_95_upper_bound_per_reach"])

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

    def test_zero_trigger_runs_report_random_hit_upper_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = []
            for rep in range(1, 4):
                run_record = self.write_run_record(
                    root,
                    name=f"vanilla_{rep}",
                    baseline="aflplusplus_vanilla",
                    latest_reached=1000,
                    latest_triggered=0,
                    success=False,
                )
                records.append(
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 7200,
                        "rep": rep,
                        "run_record": str(run_record),
                        "success": False,
                        "target_id": "TGT",
                        "trigger_time_s": None,
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

        group = analysis["baseline_groups"][0]
        self.assertEqual(group["total_reached"], 3000)
        self.assertEqual(group["total_triggered"], 0)
        self.assertEqual(group["zero_trigger_runs"], 3)
        self.assertAlmostEqual(
            group["zero_trigger_rule_of_three_95_upper_bound_per_reach"],
            0.001,
        )
        self.assertEqual(group["aggregate_empirical_trigger_rate_per_reach"], 0)

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

    def test_post_reach_seed_contract_marks_non_magma_binary_flatness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_dir = str(root / "rnt_seeds")
            run_record = self.write_non_magma_run_record(
                root,
                name="vanilla",
                baseline="aflplusplus_vanilla",
                seed_set_id=seed_dir,
            )
            summary = self.write_summary(
                root,
                [
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 600,
                        "rep": 1,
                        "run_record": str(run_record),
                        "success": False,
                        "target_id": "TGT",
                        "trigger_time_s": None,
                        "valid_run": True,
                    }
                ],
            )
            contract = root / "seed_contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "schema": "formtrig_post_reach_seed_contract_v1",
                        "target_id": "TGT",
                        "seed_sets": [
                            {
                                "seed_set_id": seed_dir,
                                "seed_count": 1,
                                "rnt": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            rows = load_baseline_rows(
                [f"matched={summary}"],
                seed_contracts=load_seed_contracts([str(contract)]),
            )
            analysis = target_analysis(
                rows,
                required_baselines=["aflplusplus_vanilla"],
                min_reps=1,
                acceptable_trigger_s=600,
                hard_trigger_s=1800,
                variance_trigger_s=1800,
            )

        self.assertEqual(analysis["status"], "measured_pass")
        self.assertTrue(analysis["pretrigger_binary_flat_measured"])
        self.assertTrue(analysis["pretrigger_binary_flat_pass"])
        self.assertEqual(rows[0]["pretrigger_binary_reason"], "post_reach_seed_contract_rnt_binary_false")
        self.assertEqual(rows[0]["reach_evidence_kind"], "post_reach_seed_contract")
        self.assertIsNone(analysis["baseline_groups"][0]["aggregate_empirical_trigger_rate_per_reach"])

    def test_under_acceptable_budget_does_not_prove_endpoint_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_dir = str(root / "rnt_seeds")
            records = []
            for rep in range(1, 4):
                run_record = self.write_non_magma_run_record(
                    root,
                    name=f"vanilla_{rep}",
                    baseline="aflplusplus_vanilla",
                    seed_set_id=seed_dir,
                    budget=60,
                    run_time=60,
                )
                records.append(
                    {
                        "baseline": "aflplusplus_vanilla",
                        "budget": 60,
                        "rep": rep,
                        "run_record": str(run_record),
                        "success": False,
                        "target_id": "TGT",
                        "trigger_time_s": None,
                        "valid_run": True,
                    }
                )
            summary = self.write_summary(root, records)
            contract = root / "seed_contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "target_id": "TGT",
                        "seed_sets": [{"seed_set_id": seed_dir, "seed_count": 1, "rnt": True}],
                    }
                ),
                encoding="utf-8",
            )

            rows = load_baseline_rows(
                [f"matched={summary}"],
                seed_contracts=load_seed_contracts([str(contract)]),
            )
            analysis = target_analysis(
                rows,
                required_baselines=["aflplusplus_vanilla"],
                min_reps=3,
                acceptable_trigger_s=600,
                hard_trigger_s=1800,
                variance_trigger_s=1800,
            )

        self.assertEqual(analysis["status"], "under_budgeted")
        self.assertTrue(analysis["pretrigger_binary_flat_pass"])
        self.assertFalse(analysis["endpoint_cost_pass"])
        self.assertEqual(analysis["under_budget_baselines"], ["aflplusplus_vanilla"])
        self.assertIn("baseline_budget_below_acceptable_threshold", analysis["reasons"])

    def test_invalid_runs_are_excluded_from_replication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_dir = str(root / "rnt_seeds")
            valid_record = self.write_non_magma_run_record(
                root,
                name="valid",
                baseline="aflplusplus_cmplog",
                seed_set_id=seed_dir,
                budget=7200,
                run_time=7200,
            )
            invalid_record = self.write_non_magma_run_record(
                root,
                name="invalid",
                baseline="aflplusplus_cmplog",
                seed_set_id=seed_dir,
                budget=7200,
                run_time=0,
            )
            summary = self.write_summary(
                root,
                [
                    {
                        "baseline": "aflplusplus_cmplog",
                        "budget": 7200,
                        "rep": 1,
                        "run_record": str(valid_record),
                        "success": False,
                        "target_id": "TGT",
                        "valid_run": True,
                    },
                    {
                        "baseline": "aflplusplus_cmplog",
                        "budget": 7200,
                        "rep": 2,
                        "returncode": 1,
                        "run_record": str(invalid_record),
                        "success": False,
                        "target_id": "TGT",
                        "valid_run": False,
                    },
                ],
            )
            contract = root / "seed_contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "target_id": "TGT",
                        "seed_sets": [{"seed_set_id": seed_dir, "seed_count": 1, "rnt": True}],
                    }
                ),
                encoding="utf-8",
            )

            rows = load_baseline_rows(
                [f"matched={summary}"],
                seed_contracts=load_seed_contracts([str(contract)]),
            )
            analysis = target_analysis(
                rows,
                required_baselines=["aflplusplus_cmplog"],
                min_reps=2,
                acceptable_trigger_s=600,
                hard_trigger_s=1800,
                variance_trigger_s=1800,
            )

        self.assertEqual(analysis["status"], "under_replicated")
        self.assertEqual(analysis["baseline_groups"][0]["reps"], 1)
        self.assertEqual(analysis["invalid_baseline_runs_excluded"], 1)
        self.assertIn("invalid_baseline_runs_excluded", analysis["reasons"])

    def test_run_tsv_uses_explicit_na_for_missing_trailing_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "runs.tsv"
            write_run_tsv(
                out,
                [
                    {
                        "source_label": "matched",
                        "target_id": "TGT",
                        "baseline": "aflplusplus_vanilla",
                        "budget": 7200,
                        "rep": 1,
                        "success": False,
                        "trigger_time_s": None,
                        "live_snapshot": True,
                        "run_record": "",
                    }
                ],
            )

            lines = out.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        self.assertFalse(lines[1].endswith("\t"))
        self.assertIn("\tNA\t", lines[1])
        self.assertTrue(lines[1].endswith("\tNA"))


if __name__ == "__main__":
    unittest.main()
