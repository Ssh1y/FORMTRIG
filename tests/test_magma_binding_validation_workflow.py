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


class MagmaBindingValidationWorkflowTest(unittest.TestCase):
    def test_validation_worklist_uses_assets_to_emit_runnable_sweep(self):
        planner = load_tool("plan_magma_binding_validation")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "PDF003.yml"
            seed_dir = root / "seeds"
            site_map = root / "site_map.tsv"
            target_cwd = root / "target"
            spec.write_text("tc_id: PDF003\n", encoding="utf-8")
            seed_dir.mkdir()
            site_map.write_text("1\tcmp\tf\t1\ticmp\ta.c\t10\t2\n", encoding="utf-8")
            target_cwd.mkdir()

            drafts = root / "drafts.json"
            manifest = root / "PDF003.manifest.template"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: PDF003",
                        "category: binary-null",
                        f"seed_dir: {seed_dir}",
                        f"binding_spec: {spec}",
                        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP.tsv",
                        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD",
                        "target_cmd: TODO_BINARY @@",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "PDF003",
                                "project": "poppler",
                                "program": "pdfimages",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            assets = root / "assets.json"
            assets.write_text(
                json.dumps(
                    {
                        "targets": {
                            "PDF003": {
                                "seed_dir": str(seed_dir),
                                "site_map": str(site_map),
                                "target_cwd": str(target_cwd),
                                "target_cmd": "./pdfimages @@ /tmp/out",
                            }
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                drafts_path=drafts,
                assets_path=assets,
                rnt_status_path=None,
                duration_s=600,
                raw_root=root / "raw",
                validation_root=root / "validation",
                aflpp_dir="AFLplusplus",
                seed_preflight_max=16,
                seed_preflight_timeout=3,
            )

            self.assertEqual(payload["runnable_now_count"], 1)
            task = payload["tasks"][0]
            self.assertEqual(task["blockers"], [])
            self.assertIn(f"(cd {target_cwd}", task["command"])
            self.assertIn("run_formtrig_binding_candidate_sweep.sh", task["command"])
            self.assertIn("--candidate-kind binding-spec", task["command"])
            self.assertIn("summarize_binding_candidate_sweep.py", task["command"])
            self.assertIn("--seed-preflight-max 16", task["command"])

    def test_validation_worklist_prefers_formal_rnt_seed_dir(self):
        planner = load_tool("plan_magma_binding_validation")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "PDF003.yml"
            initial_seed_dir = root / "initial"
            rnt_seed_dir = root / "rnt" / "PDF003" / "seeds"
            site_map = root / "site_map.tsv"
            target_cwd = root / "target"
            spec.write_text("tc_id: PDF003\n", encoding="utf-8")
            initial_seed_dir.mkdir()
            rnt_seed_dir.mkdir(parents=True)
            site_map.write_text("1\tcmp\tf\t1\ticmp\ta.c\t10\t2\n", encoding="utf-8")
            target_cwd.mkdir()

            drafts = root / "drafts.json"
            manifest = root / "PDF003.manifest.template"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: PDF003",
                        "category: binary-null",
                        f"seed_dir: {initial_seed_dir}",
                        f"binding_spec: {spec}",
                        f"site_map: {site_map}",
                        f"target_cwd: {target_cwd}",
                        "target_cmd: ./pdfimages @@ /tmp/out",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "PDF003",
                                "project": "poppler",
                                "program": "pdfimages",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "PDF003",
                                "status": "formal_ready",
                                "seed_dir_exists": "true",
                                "seed_dir": str(rnt_seed_dir),
                                "seed_files": "3",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                drafts_path=drafts,
                assets_path=None,
                rnt_status_path=rnt_status,
                duration_s=600,
                raw_root=root / "raw",
                validation_root=root / "validation",
                aflpp_dir="AFLplusplus",
                seed_preflight_max=16,
                seed_preflight_timeout=3,
            )

            task = payload["tasks"][0]
            self.assertTrue(task["runnable_now"])
            self.assertEqual(task["seed_source"], "formal_rnt_corpus")
            self.assertEqual(task["seed_dir"], str(rnt_seed_dir))
            self.assertEqual(task["rnt_seed_files"], 3)
            template = planner.build_assets_template(payload)
            self.assertEqual(template["targets"]["PDF003"]["seed_dir"], str(rnt_seed_dir))
            self.assertIn("TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF003", template["targets"]["PDF003"]["site_map"])

    def test_validation_worklist_blocks_excluded_rnt_without_asset_override(self):
        planner = load_tool("plan_magma_binding_validation")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "SSL011.yml"
            initial_seed_dir = root / "initial"
            site_map = root / "site_map.tsv"
            target_cwd = root / "target"
            spec.write_text("tc_id: SSL011\n", encoding="utf-8")
            initial_seed_dir.mkdir()
            site_map.write_text("1\tcmp\tf\t1\ticmp\ta.c\t10\t2\n", encoding="utf-8")
            target_cwd.mkdir()
            manifest = root / "SSL011.manifest.template"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: SSL011",
                        "category: binary-null",
                        f"seed_dir: {initial_seed_dir}",
                        f"binding_spec: {spec}",
                        f"site_map: {site_map}",
                        f"target_cwd: {target_cwd}",
                        "target_cmd: ./asn1 @@",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts = root / "drafts.json"
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "SSL011",
                                "project": "openssl",
                                "program": "asn1",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "SSL011",
                                "status": "excluded",
                                "seed_dir_exists": "false",
                                "seed_dir": str(root / "rnt" / "SSL011" / "seeds"),
                                "seed_files": "0",
                                "blocking_reason": "no strict RNT seed",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                drafts_path=drafts,
                assets_path=None,
                rnt_status_path=rnt_status,
                duration_s=600,
                raw_root=root / "raw",
                validation_root=root / "validation",
                aflpp_dir="AFLplusplus",
                seed_preflight_max=16,
                seed_preflight_timeout=3,
            )

            task = payload["tasks"][0]
            self.assertFalse(task["runnable_now"])
            self.assertIn("formal RNT seed corpus is not ready: excluded", "; ".join(task["blockers"]))
            template = planner.build_assets_template(payload)
            self.assertEqual(template["targets"]["SSL011"]["seed_dir"], "TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011")
            self.assertEqual(template["targets"]["SSL011"]["rnt_blocker"], "no strict RNT seed")

    def test_validation_worklist_does_not_treat_todo_asset_seed_as_override(self):
        planner = load_tool("plan_magma_binding_validation")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "SSL011.yml"
            initial_seed_dir = root / "initial"
            site_map = root / "site_map.tsv"
            target_cwd = root / "target"
            spec.write_text("tc_id: SSL011\n", encoding="utf-8")
            initial_seed_dir.mkdir()
            site_map.write_text("1\tcmp\tf\t1\ticmp\ta.c\t10\t2\n", encoding="utf-8")
            target_cwd.mkdir()
            manifest = root / "SSL011.manifest.template"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: SSL011",
                        "category: binary-null",
                        f"seed_dir: {initial_seed_dir}",
                        f"binding_spec: {spec}",
                        f"site_map: {site_map}",
                        f"target_cwd: {target_cwd}",
                        "target_cmd: ./asn1 @@",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts = root / "drafts.json"
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "SSL011",
                                "project": "openssl",
                                "program": "asn1",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            assets = root / "assets.json"
            assets.write_text(
                json.dumps(
                    {
                        "targets": {
                            "SSL011": {
                                "seed_dir": "TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011",
                                "site_map": str(site_map),
                                "target_cwd": str(target_cwd),
                                "target_cmd": "./asn1 @@",
                            }
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "SSL011",
                                "status": "excluded",
                                "seed_dir_exists": "false",
                                "seed_dir": str(root / "rnt" / "SSL011" / "seeds"),
                                "seed_files": "0",
                                "blocking_reason": "no strict RNT seed",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                drafts_path=drafts,
                assets_path=assets,
                rnt_status_path=rnt_status,
                duration_s=600,
                raw_root=root / "raw",
                validation_root=root / "validation",
                aflpp_dir="AFLplusplus",
                seed_preflight_max=16,
                seed_preflight_timeout=3,
            )

            task = payload["tasks"][0]
            self.assertFalse(task["runnable_now"])
            self.assertEqual(task["seed_source"], "manifest_template_initial_corpus")
            self.assertEqual(task["seed_dir"], str(initial_seed_dir))
            self.assertIn("formal RNT seed corpus is not ready: excluded", "; ".join(task["blockers"]))

    def test_validation_worklist_blocks_rnt_from_different_program(self):
        planner = load_tool("plan_magma_binding_validation")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "SSL011.yml"
            seed_dir = root / "initial"
            rnt_seed_dir = root / "rnt" / "SSL011" / "seeds"
            site_map = root / "site_map.tsv"
            target_cwd = root / "target"
            spec.write_text("tc_id: SSL011\n", encoding="utf-8")
            seed_dir.mkdir()
            rnt_seed_dir.mkdir(parents=True)
            site_map.write_text("1\tcmp\tPKCS7_dataDecode\t1\ticmp\tpk7_doit.c\t436\t5\n", encoding="utf-8")
            target_cwd.mkdir()
            manifest = root / "SSL011.manifest.template"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: SSL011",
                        "category: binary-null",
                        f"seed_dir: {seed_dir}",
                        f"binding_spec: {spec}",
                        f"site_map: {site_map}",
                        f"target_cwd: {target_cwd}",
                        "target_cmd: ./pkcs7_decode @@",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts = root / "drafts.json"
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "SSL011",
                                "project": "openssl",
                                "program": "pkcs7_decode",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "SSL011",
                                "program": "asn1",
                                "status": "formal_ready",
                                "seed_dir_exists": "true",
                                "seed_dir": str(rnt_seed_dir),
                                "seed_files": "3",
                                "blocking_reason": "old asn1 reason",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                drafts_path=drafts,
                assets_path=None,
                rnt_status_path=rnt_status,
                duration_s=600,
                raw_root=root / "raw",
                validation_root=root / "validation",
                aflpp_dir="AFLplusplus",
                seed_preflight_max=16,
                seed_preflight_timeout=3,
            )

            task = payload["tasks"][0]
            self.assertFalse(task["runnable_now"])
            self.assertEqual(task["rnt_program"], "asn1")
            self.assertEqual(task["seed_source"], "manifest_template_initial_corpus")
            self.assertEqual(task["seed_dir"], str(seed_dir))
            blockers = "; ".join(task["blockers"])
            self.assertIn("formal RNT seed corpus is not ready for program pkcs7_decode", blockers)
            self.assertNotIn("old asn1 reason", blockers)

    def test_summarizer_writes_native_binding_validated_record(self):
        summarizer = load_tool("summarize_binding_candidate_sweep")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = root / "summary.jsonl"
            summary.write_text(
                json.dumps(
                    {
                        "index": 1,
                        "score": 400000,
                        "candidate": "PDF003.yml",
                        "out_dir": "out",
                        "exit_code": 0,
                        "diagnosis": "ok",
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
                target_id="PDF003",
                binding_spec="PDF003.yml",
                site_map="site_map.tsv",
                summary_jsonl=summary,
            )

            self.assertEqual(record["status"], "native_binding_validated")
            self.assertTrue(record["ready_for_short_gate"])
            self.assertTrue(record["checks"]["dynamic_binding_signal_pass"])
            self.assertEqual(record["blockers"], [])
            self.assertEqual(record["next_action"], "run the benefit-first short endpoint screen against faithful AFL++ family baselines")

    def test_summarizer_distinguishes_terminal_only_with_variable_semantic_roles(self):
        summarizer = load_tool("summarize_binding_candidate_sweep")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = root / "summary.jsonl"
            summary.write_text(
                json.dumps(
                    {
                        "index": 1,
                        "score": 122200,
                        "candidate": "SSL011.yml",
                        "out_dir": "out",
                        "exit_code": 0,
                        "diagnosis": "triggered",
                        "experiment_ready": False,
                        "pretrigger_lift_guidance_ready": False,
                        "has_non_trigger_progress": False,
                        "non_trigger_progress_events": 0,
                        "saved_non_trigger_progress_events": 0,
                        "saved_triggered_progress_events": 228,
                        "execs_done": 15438,
                        "reached_execs": 2026,
                        "triggered_execs": 2026,
                        "binding_signal_status": "pass",
                        "binding_signal_diagnosis": "triggered",
                        "candidate_events": 228,
                        "accepted_non_trigger_progress_events": 0,
                        "non_trigger_candidate_lift_delta": False,
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
                target_id="SSL011",
                binding_spec="SSL011.yml",
                site_map="site_map.tsv",
                summary_jsonl=summary,
            )

            self.assertEqual(
                record["status"],
                "terminal_only_variable_semantic_roles_no_pretrigger_guidance",
            )
            self.assertFalse(record["ready_for_short_gate"])
            self.assertIn("terminal signal appeared without non-trigger guidance", record["blockers"])
            self.assertIn(
                "semantic BindingSpec roles varied, but no accepted non-trigger frontier progress was observed",
                record["blockers"],
            )


if __name__ == "__main__":
    unittest.main()
