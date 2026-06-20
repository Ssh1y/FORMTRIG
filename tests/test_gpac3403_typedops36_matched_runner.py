import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class Gpac3403TypedOps36MatchedRunnerTest(unittest.TestCase):
    def test_dry_run_emits_corrected_formtrig_and_baseline_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_typedops36_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "60",
                    "--reps",
                    "2",
                    "--jobs",
                    "2",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 8)
            self.assertEqual(
                {(record["arm"], record["rep"]) for record in records},
                {
                    ("formtrig", 1),
                    ("aflplusplus_vanilla", 1),
                    ("aflplusplus_cmplog", 1),
                    ("redqueen_operand", 1),
                    ("formtrig", 2),
                    ("aflplusplus_vanilla", 2),
                    ("aflplusplus_cmplog", 2),
                    ("redqueen_operand", 2),
                },
            )
            for record in records:
                self.assertEqual(record["typed_ops"], 36)
                self.assertEqual(record["typed_op_start"], 0)
                self.assertEqual(record["typed_schedule"], "op-first")
                self.assertEqual(record["typed_mutation_max"], 64)
                self.assertEqual(record["typed_retain_max"], 0)
                self.assertEqual(record["typed_retain_mode"], "signal")
                self.assertEqual(record["duration_s"], 60)

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["target_id"], "GPAC_3403")
            self.assertEqual(metadata["typed_ops"], 36)
            self.assertEqual(metadata["typed_op_start"], 0)
            self.assertEqual(metadata["typed_schedule"], "op-first")
            self.assertEqual(metadata["typed_mutation_max"], 64)
            self.assertEqual(metadata["typed_retain_max"], 0)
            self.assertEqual(metadata["typed_retain_mode"], "signal")
            self.assertIn("MP4Box", metadata["target_cmd"])
            self.assertIn("-cat @@ ", metadata["target_cmd"])
            self.assertIn("white.mp4", metadata["target_cmd"])

            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("run_formtrig_aflpp_campaign.sh", plan)
            self.assertIn("--typed-ops 36", plan)
            self.assertIn("FORMTRIG_TYPED_OP_START=0", plan)
            self.assertIn("FORMTRIG_TYPED_SCHEDULE=op-first", plan)
            self.assertIn("FORMTRIG_TYPED_MUTATION_MAX=64", plan)
            self.assertIn("GPAC_3403.native_b6_hevc_annexb_input_candidate.yml", plan)
            self.assertIn("MP4Box -cat @@ ", plan)
            self.assertIn("aflplusplus_vanilla", plan)
            self.assertIn("aflplusplus_cmplog", plan)
            self.assertIn("redqueen_operand", plan)
            self.assertIn("--cmplog-binary", plan)
            self.assertIn("AFL_NO_AFFINITY=1", plan)
            self.assertIn("ASAN_OPTIONS=abort_on_error=1", plan)

    def test_typedops40_wrapper_enables_access_unit_ops(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_typedops40"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_typedops40_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "30",
                    "--reps",
                    "1",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(records)
            self.assertTrue(all(record["typed_ops"] == 40 for record in records))

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["typed_ops"], 40)

            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("--typed-ops 40", plan)

    def test_b7_relation_endpoint_gate_defaults_to_alias_audit_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_b7_endpoint_gate"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_b7_relation_endpoint_gate.sh"),
                    "--mode",
                    "dry-run",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["arm"], "formtrig")
            self.assertEqual(records[0]["duration_s"], 600)
            self.assertEqual(records[0]["typed_ops"], 52)
            self.assertEqual(records[0]["typed_op_start"], 44)
            self.assertEqual(records[0]["typed_schedule"], "op-first")
            self.assertEqual(records[0]["typed_mutation_max"], 256)
            self.assertEqual(records[0]["typed_retain_max"], 256)
            self.assertEqual(records[0]["typed_retain_mode"], "all")

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["arms"], "formtrig")
            self.assertEqual(metadata["baselines"], "")
            self.assertEqual(metadata["seed_preflight"], "require")
            self.assertIn(
                "GPAC_3403.native_b7_relation_value_candidate.yml",
                metadata["binding_spec"],
            )
            self.assertEqual(metadata["typed_ops"], 52)
            self.assertEqual(metadata["typed_op_start"], 44)
            self.assertEqual(metadata["typed_retain_endpoint_replay"], "on")
            self.assertEqual(metadata["typed_retain_endpoint_selection"], "df-structure-op-diverse")
            self.assertEqual(metadata["typed_retain_endpoint_variant_suffix"], ".hevc")
            self.assertEqual(metadata["typed_retain_endpoint_max_records"], 128)
            self.assertIn("GPAC_3403.poc", metadata["typed_retain_endpoint_positive_control"])

            plan = (out_dir / "run_plan.sh").read_text(encoding="utf-8")
            self.assertIn("FORMTRIG_TYPED_OP_START=44", plan)
            self.assertIn("FORMTRIG_TYPED_RETAIN_MODE=all", plan)
            self.assertIn("GPAC_3403.native_b7_relation_value_candidate.yml", plan)
            runner = (
                REPO_ROOT / "scripts" / "run_gpac3403_b7_relation_endpoint_gate.sh"
            ).read_text(encoding="utf-8")
            self.assertIn("--seed-preflight-timeout 10", runner)
            self.assertIn("--typed-retain-endpoint-replay", runner)
            self.assertIn("--typed-retain-endpoint-selection df-structure-op-diverse", runner)
            self.assertIn("--typed-retain-endpoint-variant-suffix .hevc", runner)
            self.assertIn("GPAC_3403.native_b7_relation_value_candidate.yml", runner)
            self.assertIn("GPAC_3403.poc", runner)

    def test_b12_scal_ref_scaffold_wrapper_uses_mp4_seed_and_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_b12_scaffold"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_b12_scal_ref_scaffold_matched.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "30",
                    "--reps",
                    "1",
                    "--arms",
                    "formtrig,aflplusplus_vanilla",
                    "--baselines",
                    "aflplusplus_vanilla",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["arm"] for record in records], ["formtrig", "aflplusplus_vanilla"])
            self.assertTrue(all(record["seed_format"] == "mp4-scal-ref-scaffold" for record in records))
            self.assertTrue(
                all(record["mutation_hook_override"].endswith("mp4_box_structure_hook.py") for record in records)
            )
            self.assertTrue(all(record["typed_ops"] == 64 for record in records))
            self.assertTrue(all(record["typed_mutation_max"] == 256 for record in records))
            self.assertTrue(all(record["typed_retain_max"] == 128 for record in records))
            self.assertTrue(all(record["duration_s"] == 30 for record in records))

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["seed_format"], "mp4-scal-ref-scaffold")
            self.assertIn("gpac3403_b12_scal_ref_scaffold_20260620/corpus", metadata["seed_dir"])
            self.assertIn("GPAC_3403.native_b10_extractor_return_candidate.yml", metadata["binding_spec"])
            self.assertTrue(metadata["mutation_hook_override"].endswith("mp4_box_structure_hook.py"))
            self.assertEqual(metadata["typed_ops"], 64)
            self.assertEqual(metadata["typed_mutation_max"], 256)
            self.assertEqual(metadata["typed_retain_max"], 128)
            self.assertEqual(metadata["typed_retain_mode"], "all")

            commands = {record["arm"]: record["command"] for record in records}
            self.assertIn("--mutation-hook", commands["formtrig"])
            self.assertIn("mp4_box_structure_hook.py", commands["formtrig"])
            self.assertIn("GPAC_3403.native_b10_extractor_return_candidate.yml", commands["formtrig"])
            self.assertIn(metadata["seed_dir"], commands["formtrig"])
            self.assertIn(metadata["seed_dir"], commands["aflplusplus_vanilla"])

    def test_b12_scal_ref_endpoint_gate_enables_endpoint_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_b12_endpoint"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_b12_scal_ref_endpoint_gate.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "15",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["arm"] for record in records], ["formtrig"])
            self.assertTrue(all(record["seed_format"] == "mp4-scal-ref-scaffold" for record in records))
            self.assertTrue(all(record["typed_retain_max"] == 128 for record in records))
            self.assertEqual(records[0]["duration_s"], 15)

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["arms"], "formtrig")
            self.assertEqual(metadata["baselines"], "")
            self.assertEqual(metadata["typed_retain_endpoint_replay"], "on")
            self.assertEqual(metadata["typed_retain_endpoint_selection"], "best-d-f")
            self.assertEqual(metadata["typed_retain_endpoint_timeout"], 5)
            self.assertEqual(metadata["typed_retain_endpoint_replays"], 1)
            self.assertEqual(metadata["typed_retain_endpoint_max_records"], 32)
            self.assertIn("gpac3403_b12_scal_ref_scaffold_20260620/corpus", metadata["seed_dir"])
            self.assertIn("gpac3403_b11_scal_ref_preseed_probe_20260620T023303Z", metadata["typed_retain_endpoint_positive_control"])

            runner = (
                REPO_ROOT / "scripts" / "run_gpac3403_b12_scal_ref_endpoint_gate.sh"
            ).read_text(encoding="utf-8")
            self.assertIn("--enhanced-mode copy-base", runner)
            self.assertIn("--enhanced-mode mutated", runner)
            self.assertIn("--typed-retain-endpoint-replay on", runner)
            self.assertIn("--typed-retain-endpoint-selection best-d-f", runner)

    def test_b13_scal_ref_payload_gate_uses_gpac_payload_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_b13_payload"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_b13_scal_ref_payload_endpoint_gate.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "15",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["arm"] for record in records], ["formtrig"])
            self.assertEqual(records[0]["typed_op_start"], 52)
            self.assertTrue(records[0]["mutation_hook_override"].endswith("gpac_scal_ref_mp4_hook.py"))

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["typed_op_start"], 52)
            self.assertEqual(metadata["typed_schedule"], "op-first")
            self.assertEqual(metadata["typed_retain_endpoint_replay"], "on")
            self.assertTrue(metadata["mutation_hook_override"].endswith("gpac_scal_ref_mp4_hook.py"))

            runner = (
                REPO_ROOT / "scripts" / "run_gpac3403_b13_scal_ref_payload_endpoint_gate.sh"
            ).read_text(encoding="utf-8")
            self.assertIn("FORMTRIG_GPAC3403_HEVC_SAMPLE_BIAS", runner)
            self.assertIn("gpac_scal_ref_mp4_hook.py", runner)

    def test_dry_run_supports_nohook_ablation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_nohook"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_typedops36_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "30",
                    "--reps",
                    "1",
                    "--arms",
                    "formtrig,formtrig_nohook",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["arm"] for record in records], ["formtrig", "formtrig_nohook"])
            commands = {record["arm"]: record["command"] for record in records}
            self.assertNotIn("--no-mutation-hook", commands["formtrig"])
            self.assertIn("--no-mutation-hook", commands["formtrig_nohook"])

    def test_dry_run_can_enable_typed_candidate_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "gpac3403_retain"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts" / "run_gpac3403_typedops36_matched_longrun.sh"),
                    "--mode",
                    "dry-run",
                    "--duration",
                    "30",
                    "--reps",
                    "1",
                    "--arms",
                    "formtrig,aflplusplus_vanilla",
                    "--typed-retain-max",
                    "32",
                    "--typed-op-start",
                    "24",
                    "--typed-schedule",
                    "sample-first",
                    "--typed-retain-mode",
                    "hook",
                    "--typed-retain-endpoint-replay",
                    "on",
                    "--typed-retain-endpoint-timeout",
                    "3",
                    "--typed-retain-endpoint-replays",
                    "2",
                    "--typed-retain-endpoint-max-records",
                    "5",
                    "--typed-retain-endpoint-selection",
                    "op-diverse",
                    "--typed-retain-endpoint-cmd",
                    "python3 endpoint.py @@",
                    "--out",
                    str(out_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            records = [
                json.loads(line)
                for line in (out_dir / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 2)
            self.assertTrue(all(record["typed_op_start"] == 24 for record in records))
            self.assertTrue(all(record["typed_schedule"] == "sample-first" for record in records))
            self.assertTrue(all(record["typed_retain_max"] == 32 for record in records))
            self.assertTrue(all(record["typed_retain_mode"] == "hook" for record in records))
            commands = {record["arm"]: record["command"] for record in records}
            self.assertIn("FORMTRIG_TYPED_OP_START=24", commands["formtrig"])
            self.assertIn("FORMTRIG_TYPED_SCHEDULE=sample-first", commands["formtrig"])
            self.assertIn("FORMTRIG_TYPED_RETAIN_MAX=32", commands["formtrig"])
            self.assertIn("FORMTRIG_TYPED_RETAIN_DIR=", commands["formtrig"])
            self.assertIn("FORMTRIG_TYPED_RETAIN_MODE=hook", commands["formtrig"])
            self.assertIn("typed_retained", commands["formtrig"])
            self.assertNotIn("FORMTRIG_TYPED_RETAIN_MAX", commands["aflplusplus_vanilla"])
            self.assertNotIn("FORMTRIG_TYPED_RETAIN_DIR", commands["aflplusplus_vanilla"])
            self.assertNotIn("FORMTRIG_TYPED_RETAIN_MODE", commands["aflplusplus_vanilla"])

            metadata = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["typed_op_start"], 24)
            self.assertEqual(metadata["typed_schedule"], "sample-first")
            self.assertEqual(metadata["typed_retain_max"], 32)
            self.assertEqual(metadata["typed_retain_mode"], "hook")
            self.assertEqual(metadata["typed_retain_endpoint_replay"], "on")
            self.assertEqual(metadata["typed_retain_endpoint_timeout"], 3)
            self.assertEqual(metadata["typed_retain_endpoint_replays"], 2)
            self.assertEqual(metadata["typed_retain_endpoint_max_records"], 5)
            self.assertEqual(metadata["typed_retain_endpoint_selection"], "op-diverse")
            self.assertEqual(metadata["typed_retain_endpoint_cmd"], "python3 endpoint.py @@")

            runner = (
                REPO_ROOT / "scripts" / "run_gpac3403_typedops36_matched_longrun.sh"
            ).read_text(encoding="utf-8")
            self.assertIn("replay_gpac3403_typed_retained_endpoint.py", runner)
            self.assertIn("package_gpac3403_typed_retained_audit.py", runner)
            self.assertIn("analyze_gpac3403_alias_gap.py", runner)
            self.assertIn("alias_gap_analysis.json", runner)
            self.assertIn("typed_retained_endpoint_records.jsonl", runner)
            self.assertIn("typed_retained_audit_package.json", runner)


if __name__ == "__main__":
    unittest.main()
