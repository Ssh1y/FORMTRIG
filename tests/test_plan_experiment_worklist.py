import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_planner():
    path = Path(__file__).resolve().parents[1] / "tools" / "plan_formtrig_experiment_worklist.py"
    spec = importlib.util.spec_from_file_location("plan_formtrig_experiment_worklist", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExperimentWorklistTest(unittest.TestCase):
    def test_benefit_first_worklist_gates_controls_and_unvalidated_targets(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "libarchive"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "LIBARCHIVE_2936",
                        "analysis": {
                            "verdict": "positive_speedup_matched_comparison",
                            "longrun_10m_confirmation": {"budget_s": 600},
                            "repetition_summary": "evidence/repetition_summary.json",
                        },
                        "benefit_readout": {
                            "primary_benefits": ["FORMTRIG is faster by first _T"],
                            "design_evidence": ["strict_pretrigger_guidance"],
                            "blocked_claims": ["not a baseline-impossibility case"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 1,
                                "target_id": "LIBARCHIVE_2936",
                                "source": "real_cve",
                                "project": "libarchive",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "real_cve_replacement",
                                "status": "short_gate_triaged",
                                "existing_disposition": "candidate_extend_longruns",
                                "blockers": "",
                                "source_evidence": "cve.json",
                            },
                            {
                                "rank": 2,
                                "target_id": "PDF003",
                                "source": "magma",
                                "project": "poppler",
                                "primary_category": "binary-state-null",
                                "secondary_category": "compound-sequence-lifecycle",
                                "lane": "binding_spec_first",
                                "status": "needs_short_discovery",
                                "existing_disposition": "",
                                "blockers": "no BindingSpec candidate exists yet",
                                "source_evidence": "magma.json",
                            },
                            {
                                "rank": 3,
                                "target_id": "PNG007",
                                "source": "magma",
                                "project": "libpng",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "control_or_negative",
                                "status": "do_not_promote",
                                "existing_disposition": "",
                                "blockers": "terminal-only",
                                "source_evidence": "magma.json",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            self.assertEqual(payload["task_count"], 2)
            self.assertEqual(payload["skipped_control_count"], 1)
            tasks = {task["target_id"]: task for task in payload["tasks"]}
            self.assertEqual(tasks["LIBARCHIVE_2936"]["action"], "extend_matched_longrun")
            self.assertTrue(tasks["LIBARCHIVE_2936"]["runnable_now"])
            self.assertIn(
                "scripts/run_libarchive_2936_matched_longrun.sh --duration 7200 --reps 3 --jobs 4",
                tasks["LIBARCHIVE_2936"]["command"],
            )
            self.assertIn("first-_T speedup", tasks["LIBARCHIVE_2936"]["benefit_to_prove"])
            self.assertEqual(tasks["LIBARCHIVE_2936"]["comparison_verdict"], "positive_speedup_matched_comparison")
            self.assertEqual(tasks["PDF003"]["action"], "draft_binding_spec_then_short_screen")
            self.assertIn(
                "scripts/run_magma_baselines.sh --target-id PDF003 --durations 600 --jobs 4",
                tasks["PDF003"]["post_unblock_commands"],
            )
            self.assertIn("Endpoint benefit", payload["benefit_first_rule"])

    def test_weak_near_seed_speedup_routes_to_experiment_design_work(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "libarchive"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "LIBARCHIVE_2936",
                        "analysis": {
                            "verdict": "positive_speedup_matched_comparison",
                            "matched_baseline_count": 9,
                            "experiment_strength": {
                                "main_claim_strength": "weak_near_seed_or_harness_shaped_speedup",
                                "recommended_design_actions": [
                                    "rerun with a higher-fidelity/raw-format harness or a farther RNT seed",
                                    "add no-hook and generic-hook FORMTRIG ablations",
                                ],
                            },
                        },
                        "benefit_readout": {
                            "primary_benefits": ["FORMTRIG is faster by first _T"],
                            "design_evidence": ["strict_pretrigger_guidance"],
                            "blocked_claims": [
                                "current experiment is too near-trigger or harness-shaped"
                            ],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 1,
                                "target_id": "LIBARCHIVE_2936",
                                "source": "real_cve",
                                "project": "libarchive",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "real_cve_replacement",
                                "status": "short_gate_triaged",
                                "existing_disposition": "candidate_extend_longruns",
                                "blockers": "",
                                "source_evidence": "cve.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "improve_experiment_design")
            self.assertFalse(task["runnable_now"])
            self.assertIn("SOTA R2T pain", task["benefit_to_prove"])
            self.assertTrue(
                any("higher-fidelity" in step for step in task["post_unblock_commands"])
            )

    def test_target_level_triage_can_skip_stale_main_queue_entry(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            triage_path = root / "triage.json"
            comparison_root = root / "comparisons"
            comparison_root.mkdir()
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 1,
                                "target_id": "PNG006",
                                "source": "magma",
                                "project": "libpng",
                                "primary_category": "binary-state-null",
                                "secondary_category": "compound-sequence-lifecycle",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "candidate_extend_longruns",
                                "blockers": "",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            triage_path.write_text(
                json.dumps(
                    {
                        "targets": [
                            {
                                "target_id": "PNG006",
                                "sota_pain_class": "not_visible_baseline_visible_no_formtrig_advantage",
                                "sota_pain_evidence": "matched faithful baselines trigger",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                triage_path=triage_path,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            self.assertEqual(payload["task_count"], 0)
            self.assertEqual(payload["skipped_control_count"], 1)
            skipped = payload["skipped_controls"][0]
            self.assertEqual(skipped["target_id"], "PNG006")
            self.assertEqual(skipped["reason"], "sota_pain_triage_not_main_budget")
            self.assertEqual(
                skipped["sota_pain_class"],
                "not_visible_baseline_visible_no_formtrig_advantage",
            )

    def test_target_level_near_seed_triage_routes_to_design_work(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            triage_path = root / "triage.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "libarchive"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "LIBARCHIVE_2936",
                        "analysis": {
                            "verdict": "positive_speedup_matched_comparison",
                            "matched_baseline_count": 9,
                        },
                        "benefit_readout": {
                            "primary_benefits": ["FORMTRIG is faster by first _T"],
                            "design_evidence": ["strict_pretrigger_guidance"],
                            "blocked_claims": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 1,
                                "target_id": "LIBARCHIVE_2936",
                                "source": "real_cve",
                                "project": "libarchive",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "real_cve_replacement",
                                "status": "short_gate_triaged",
                                "existing_disposition": "candidate_extend_longruns",
                                "blockers": "",
                                "source_evidence": "cve.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            triage_path.write_text(
                json.dumps(
                    {
                        "targets": [
                            {
                                "target_id": "LIBARCHIVE_2936",
                                "sota_pain_class": "not_visible_near_seed_or_harness_shaped",
                                "sota_pain_evidence": "all required baseline families trigger early",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                triage_path=triage_path,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "improve_experiment_design")
            self.assertEqual(task["sota_pain_class"], "not_visible_near_seed_or_harness_shaped")
            self.assertIn("baseline families trigger early", task["sota_pain_evidence"])

    def test_native_build_dependency_preflight_is_surfaced_in_worklist(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_root.mkdir()
            build_root = root / "magma_native_builds"
            php_plan = build_root / "PHP009" / "build_plan.json"
            php_plan.parent.mkdir(parents=True)
            php_plan.write_text(
                json.dumps(
                    {
                        "target_id": "PHP009",
                        "dependency_preflight": {
                            "status": "missing",
                            "apt_package_hints": ["bison", "re2c"],
                            "checks": [
                                {
                                    "id": "php_bison",
                                    "status": "missing",
                                    "apt_package_hints": ["bison"],
                                },
                                {
                                    "id": "php_re2c",
                                    "status": "missing",
                                    "apt_package_hints": ["re2c"],
                                },
                            ],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 6,
                                "target_id": "PHP009",
                                "source": "magma",
                                "project": "php",
                                "primary_category": "compound-sequence-lifecycle",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "BindingSpec candidate is not native-site-map validated",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                native_build_root=build_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertIn("native build dependencies missing: bison re2c", task["blocking_issue"])
            self.assertIn("php_bison apt=bison", task["blocking_issue"])
            self.assertIn("sudo apt-get install -y bison re2c", task["post_unblock_commands"])
            self.assertIn(str(php_plan), task["evidence_paths"])

    def test_ready_binding_validation_routes_to_matched_short_screen(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            validation_root = root / "binding_validation"
            manifest_root = root / "manifests"
            comparison_root.mkdir()
            validation_root.mkdir()
            manifest_root.mkdir()
            manifest_list = manifest_root / "PHP009.current_1rep.list"
            manifest_list.write_text(
                "artifacts/formtrig_native_readiness/manifests/PHP009.native_draft_magma_canary.600s.manifest\n",
                encoding="utf-8",
            )
            validation_path = validation_root / "PHP009.native_draft_magma_canary.60s.validation.json"
            validation_path.write_text(
                json.dumps(
                    {
                        "target_id": "PHP009",
                        "status": "native_binding_validated",
                        "ready_for_short_gate": True,
                        "generated_at_utc": "2026-06-17T15:36:16+00:00",
                        "benefit_readout": {
                            "pretrigger_lift_guidance_ready": True,
                            "non_trigger_progress_events": 2,
                            "terminal_triggered": True,
                        },
                        "binding_signal": {
                            "status": "pass",
                            "candidate_events": 3233,
                        },
                        "source": {
                            "summary_jsonl": "artifacts/formtrig_native_readiness/raw/php009_binding_validation_60s/summary.jsonl"
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 6,
                                "target_id": "PHP009",
                                "source": "magma",
                                "project": "php",
                                "primary_category": "numeric-margin",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "BindingSpec candidate is not native-site-map validated",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                binding_validation_root=validation_root,
                manifest_root=manifest_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "run_validated_matched_short_screen")
            self.assertTrue(task["runnable_now"])
            self.assertEqual(task["blocking_issue"], [])
            self.assertIn("scripts/run_magma_baselines.sh --target-id PHP009", task["command"])
            self.assertIn("scripts/run_formtrig_manifest_batch.sh --manifest-list", task["command"])
            self.assertIn(str(manifest_list), task["command"])
            self.assertIn("baseline-visible binary TC flatness before _T", task["primary_endpoint_metrics"])
            self.assertIn(str(validation_path), task["evidence_paths"])
            self.assertIn(
                "artifacts/formtrig_native_readiness/raw/php009_binding_validation_60s/summary.jsonl",
                task["evidence_paths"],
            )

    def test_short_triage_ready_with_strict_validation_runs_matched_short_screen(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            validation_root = root / "binding_validation"
            manifest_root = root / "manifests"
            comparison_root.mkdir()
            validation_root.mkdir()
            manifest_root.mkdir()
            manifest_list = manifest_root / "PHP003.current_1rep.list"
            manifest_list.write_text("PHP003.native_b2_thumbnail_guard.600s.manifest\n", encoding="utf-8")
            validation_path = validation_root / "PHP003.native_b2_thumbnail_guard_candidate.validation.json"
            validation_path.write_text(
                json.dumps(
                    {
                        "target_id": "PHP003",
                        "status": "native_binding_validated",
                        "ready_for_short_gate": True,
                        "generated_at_utc": "2026-06-18T09:20:00+00:00",
                        "benefit_readout": {
                            "pretrigger_lift_guidance_ready": True,
                            "non_trigger_progress_events": 4,
                            "saved_non_trigger_progress_events": 4,
                            "terminal_triggered": False,
                        },
                        "binding_signal": {
                            "status": "pass",
                            "accepted_non_trigger_progress_events": 4,
                            "candidate_events": 4090,
                        },
                        "checks": {
                            "non_trigger_candidate_lift_delta": True,
                            "lift_delta_only_on_triggered": False,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 2,
                                "target_id": "PHP003",
                                "source": "magma",
                                "project": "php",
                                "primary_category": "compound-sequence-lifecycle",
                                "secondary_category": "numeric-margin",
                                "lane": "short_triage_ready",
                                "status": "ready_for_short_triage",
                                "existing_disposition": "",
                                "blockers": "no comparison package exists yet",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                binding_validation_root=validation_root,
                manifest_root=manifest_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "run_validated_matched_short_screen")
            self.assertTrue(task["runnable_now"])
            self.assertIn("scripts/run_magma_baselines.sh --target-id PHP003", task["command"])
            self.assertIn("scripts/run_formtrig_manifest_batch.sh --manifest-list", task["command"])
            self.assertIn(str(manifest_list), task["command"])
            self.assertIn(str(validation_path), task["evidence_paths"])

    def test_pretrigger_guidance_only_comparison_routes_to_terminal_repair(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            validation_root = root / "binding_validation"
            manifest_root = root / "manifests"
            comparison_dir = comparison_root / "php003_pretrigger_only"
            comparison_dir.mkdir(parents=True)
            validation_root.mkdir()
            manifest_root.mkdir()
            (manifest_root / "PHP003.current_1rep.list").write_text(
                "PHP003.native_b2_thumbnail_guard.600s.manifest\n",
                encoding="utf-8",
            )
            validation_path = validation_root / "PHP003.native_b2_thumbnail_guard_candidate.validation.json"
            validation_path.write_text(
                json.dumps(
                    {
                        "target_id": "PHP003",
                        "status": "needs_terminal_repair",
                        "ready_for_short_gate": False,
                        "benefit_readout": {
                            "pretrigger_lift_guidance_ready": True,
                            "non_trigger_progress_events": 4,
                            "saved_non_trigger_progress_events": 4,
                        },
                        "binding_signal": {
                            "status": "pass",
                            "accepted_non_trigger_progress_events": 4,
                        },
                        "checks": {
                            "native_site_map_validated": True,
                            "producer_constant_zero": True,
                        },
                        "producer_signal": {
                            "constant_zero_roles": ["desired_producer"],
                        },
                        "blockers": [
                            "producer role has no positive candidate signal: desired_producer",
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "PHP003",
                        "analysis": {
                            "verdict": "pretrigger_guidance_only",
                            "experiment_strength": {
                                "main_claim_strength": "not_supporting_main_claim"
                            },
                        },
                        "benefit_readout": {
                            "design_evidence": ["strict_pretrigger_guidance"],
                            "blocked_claims": [
                                "no FORMTRIG terminal success is established",
                            ],
                            "primary_benefits": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 2,
                                "target_id": "PHP003",
                                "source": "magma",
                                "project": "php",
                                "primary_category": "compound-sequence-lifecycle",
                                "secondary_category": "numeric-margin",
                                "lane": "short_triage_ready",
                                "status": "ready_for_short_triage",
                                "existing_disposition": "",
                                "blockers": "",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                binding_validation_root=validation_root,
                manifest_root=manifest_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "repair_guidance_to_terminal")
            self.assertFalse(task["runnable_now"])
            self.assertEqual(task["comparison_verdict"], "pretrigger_guidance_only")
            self.assertEqual(task["command"], "")
            self.assertIn(
                "producer role has no positive candidate signal: desired_producer",
                task["blocking_issue"],
            )
            self.assertIn("producer role constant-zero diagnosis", task["mechanism_evidence_required"])
            self.assertTrue(
                any(path.endswith("comparison.json") for path in task["evidence_paths"])
            )
            self.assertIn(str(validation_path), task["evidence_paths"])

    def test_ready_binding_validation_without_strict_guidance_stays_gated(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            validation_root = root / "binding_validation"
            comparison_root.mkdir()
            validation_root.mkdir()
            validation_path = validation_root / "PDF003.native_draft_magma_canary.validation.json"
            validation_path.write_text(
                json.dumps(
                    {
                        "target_id": "PDF003",
                        "status": "native_binding_validated",
                        "ready_for_short_gate": True,
                        "generated_at_utc": "2026-06-18T08:00:00+00:00",
                        "benefit_readout": {
                            "pretrigger_lift_guidance_ready": True,
                            "non_trigger_progress_events": 0,
                            "saved_non_trigger_progress_events": 0,
                            "terminal_triggered": False,
                        },
                        "binding_signal": {
                            "status": "pass",
                            "accepted_non_trigger_progress_events": 0,
                            "candidate_events": 569,
                        },
                        "checks": {
                            "native_site_map_validated": True,
                            "non_trigger_candidate_lift_delta": True,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 3,
                                "target_id": "PDF003",
                                "source": "magma",
                                "project": "poppler",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                binding_validation_root=validation_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "validate_binding_spec_then_short_screen")
            self.assertFalse(task["runnable_now"])
            self.assertIn(
                "validated BindingSpec lacks accepted non-trigger frontier progress",
                task["blocking_issue"],
            )
            self.assertIn(
                "only soft pre-trigger lifted signal is present",
                "; ".join(task["blocking_issue"]),
            )
            self.assertIn(str(validation_path), task["evidence_paths"])

    def test_terminal_only_validation_reports_real_blockers(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            validation_root = root / "binding_validation"
            comparison_root.mkdir()
            validation_root.mkdir()
            validation_path = validation_root / "PDF016.native_b3.validation.json"
            summary_path = root / "raw" / "pdf016_b3" / "summary.jsonl"
            summary_path.parent.mkdir(parents=True)
            summary_path.write_text("{}\n", encoding="utf-8")
            validation_path.write_text(
                json.dumps(
                    {
                        "target_id": "PDF016",
                        "status": "terminal_only_variable_semantic_roles_no_pretrigger_guidance",
                        "ready_for_short_gate": False,
                        "generated_at_utc": "2026-06-18T04:20:00+00:00",
                        "checks": {
                            "native_site_map_validated": True,
                            "lift_audit_pass": True,
                            "dynamic_binding_signal_pass": True,
                            "pretrigger_lift_guidance_ready": False,
                            "terminal_triggered": True,
                        },
                        "blockers": [
                            "pre-trigger lift guidance is not ready",
                            "terminal signal appeared without non-trigger guidance",
                            "semantic BindingSpec roles varied, but no accepted non-trigger frontier progress was observed",
                        ],
                        "source": {"summary_jsonl": str(summary_path)},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 5,
                                "target_id": "PDF016",
                                "source": "magma",
                                "project": "poppler",
                                "primary_category": "compound-sequence-lifecycle",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "BindingSpec candidate is not native-site-map validated",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                binding_validation_root=validation_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "validate_binding_spec_then_short_screen")
            self.assertFalse(task["runnable_now"])
            self.assertIn("pre-trigger lift guidance is not ready", task["blocking_issue"])
            self.assertIn(
                "terminal signal appeared without non-trigger guidance",
                task["blocking_issue"],
            )
            self.assertNotIn(
                "BindingSpec candidate is not native-site-map validated",
                task["blocking_issue"],
            )
            self.assertIn(str(validation_path), task["evidence_paths"])
            self.assertIn(str(summary_path), task["evidence_paths"])

    def test_validated_short_screen_reuses_manifest_afl_args_for_baselines(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_root = root / "manifests"
            manifest_root.mkdir()
            manifest = root / "PDF003.native_draft_magma_canary.600s.manifest"
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: PDF003",
                        "category: binary-null",
                        "afl_args: -t 5000",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (manifest_root / "PDF003.list").write_text(
                f"{manifest}\n",
                encoding="utf-8",
            )

            command, _followups = planner.validated_short_screen_command(
                "PDF003",
                600,
                4,
                1,
                manifest_root,
            )

            self.assertIn("--afl-arg -t --afl-arg 5000", command)
            self.assertIn("scripts/run_formtrig_manifest_batch.sh", command)

    def test_validated_short_screen_prefers_replicated_manifest_list(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_root = root / "manifests"
            manifest_root.mkdir()
            single = manifest_root / "PDF003.list"
            repeated = manifest_root / "PDF003.current_3rep.list"
            single.write_text("single.manifest\n", encoding="utf-8")
            repeated.write_text(
                "rep1.manifest\nrep2.manifest\nrep3.manifest\n",
                encoding="utf-8",
            )

            command, _followups = planner.validated_short_screen_command(
                "PDF003",
                600,
                3,
                3,
                manifest_root,
            )

            self.assertIn(str(repeated), command)
            self.assertNotIn(str(single), command)

    def test_completed_longrun_routes_to_cross_target_expansion(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "tif012"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "TIF012",
                        "analysis": {
                            "verdict": "positive_speedup_matched_comparison",
                            "matched_baseline_count": 9,
                            "experiment_strength": {
                                "main_claim_strength": "hard_speedup_or_reliability_candidate"
                            },
                            "baseline_groups": [
                                {
                                    "baseline": "aflplusplus_vanilla",
                                    "budget": 7200,
                                    "reps": 3,
                                    "success_rate": 1.0,
                                },
                                {
                                    "baseline": "aflplusplus_cmplog",
                                    "budget": 7200,
                                    "reps": 3,
                                    "success_rate": 0.33,
                                },
                            ],
                        },
                        "benefit_readout": {
                            "primary_benefits": ["FORMTRIG is faster by first _T"],
                            "design_evidence": ["formtrig_terminal_oracle_success"],
                            "blocked_claims": [],
                        },
                        "formtrig_runs": [
                            {"budget": 7200, "terminal_count": 1},
                            {"budget": 7200, "terminal_count": 1},
                            {"budget": 7200, "terminal_count": 1},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 5,
                                "target_id": "TIF012",
                                "source": "magma",
                                "project": "libtiff",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "expand_cross_target_hard_evidence")
            self.assertFalse(task["runnable_now"])
            self.assertIn("already complete", task["benefit_to_prove"])

    def test_endpoint_positive_comparison_overrides_stale_validation_lane(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "tif012_b5_endpoint"
            comparison_dir.mkdir(parents=True)
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "TIF012",
                        "analysis": {
                            "verdict": "positive_endpoint_matched_comparison",
                            "matched_baseline_count": 9,
                            "missing_required_baselines": [],
                            "best_formtrig_trigger_time_s": 0.035,
                            "baseline_groups": [
                                {
                                    "baseline": "aflplusplus_vanilla",
                                    "budget": 120,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                },
                                {
                                    "baseline": "aflplusplus_cmplog",
                                    "budget": 120,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                },
                                {
                                    "baseline": "redqueen_operand",
                                    "budget": 120,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                },
                            ],
                        },
                        "benefit_readout": {
                            "primary_benefits": [
                                "FORMTRIG reaches terminal success where matched baselines do not trigger"
                            ],
                            "design_evidence": [
                                "strict_pretrigger_guidance",
                                "matched_budget_endpoint_success",
                            ],
                            "blocked_claims": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 5,
                                "target_id": "TIF012",
                                "source": "magma",
                                "project": "libtiff",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "BindingSpec candidate is not native-site-map validated; no comparison package exists yet",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            self.assertEqual(payload["task_count"], 1)
            task = payload["tasks"][0]
            self.assertEqual(task["target_id"], "TIF012")
            self.assertEqual(task["action"], "extend_matched_longrun")
            self.assertEqual(task["priority"], "P0")
            self.assertTrue(task["runnable_now"])
            self.assertIn("scripts/run_tif012_b5_matched_longrun.sh", task["command"])
            self.assertIn("--duration 7200", task["command"])
            self.assertEqual(task["comparison_verdict"], "positive_endpoint_matched_comparison")
            self.assertIn("endpoint benefit", task["benefit_to_prove"])
            self.assertEqual(task["blocking_issue"], [])
            self.assertEqual(task["post_unblock_commands"], [])

    def test_active_matched_longrun_is_monitored_instead_of_relaunched(self):
        planner = load_planner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue_path = root / "queue.json"
            comparison_root = root / "comparisons"
            comparison_dir = comparison_root / "pdf003_short"
            comparison_dir.mkdir(parents=True)
            active_runs_path = root / "active_runs.json"
            run_root = "artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_live"
            guidance_out = "artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf003_matched_7200s_3rep_live"
            comparison_out = "artifacts/formtrig_native_readiness/comparisons/pdf003_matched_7200s_3rep_live"
            (comparison_dir / "comparison.json").write_text(
                json.dumps(
                    {
                        "target_id": "PDF003",
                        "analysis": {
                            "verdict": "positive_endpoint_matched_comparison",
                            "matched_baseline_count": 9,
                            "missing_required_baselines": [],
                            "baseline_groups": [
                                {
                                    "baseline": "aflplusplus_vanilla",
                                    "budget": 600,
                                    "reps": 3,
                                    "success_rate": 0.0,
                                }
                            ],
                        },
                        "benefit_readout": {
                            "primary_benefits": [
                                "FORMTRIG reaches terminal success where matched baselines do not trigger"
                            ],
                            "design_evidence": ["matched_budget_endpoint_success"],
                            "blocked_claims": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "rank": 3,
                                "target_id": "PDF003",
                                "source": "magma",
                                "project": "poppler",
                                "primary_category": "binary-state-null",
                                "secondary_category": "",
                                "lane": "binding_validation_first",
                                "status": "needs_binding_validation",
                                "existing_disposition": "",
                                "blockers": "BindingSpec candidate is not native-site-map validated",
                                "source_evidence": "magma.json",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            active_runs_path.write_text(
                json.dumps(
                    {
                        "runs": [
                            {
                                "target_id": "PDF003",
                                "duration_s": 7200,
                                "repetitions": 3,
                                "status": "running",
                                "run_root": run_root,
                                "guidance_out": guidance_out,
                                "comparison_out": comparison_out,
                                "baseline_roots": [
                                    f"{run_root}/baselines",
                                    "artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard",
                                ],
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = planner.build_worklist(
                queue_path,
                comparison_root,
                active_runs_path=active_runs_path,
                limit=10,
                use_all_targets=False,
                short_duration_s=600,
                longrun_duration_s=7200,
                jobs=4,
                reps=1,
                longrun_reps=3,
            )

            task = payload["tasks"][0]
            self.assertEqual(task["action"], "monitor_active_matched_longrun")
            self.assertFalse(task["runnable_now"])
            self.assertEqual(task["active_run_status"], "running")
            self.assertEqual(task["active_run_root"], run_root)
            self.assertEqual(task["command"], "")
            self.assertNotIn("run_magma_matched_longrun.sh", " ".join(task["post_unblock_commands"]))
            self.assertNotIn("--skip-incomplete-runs", " ".join(task["post_unblock_commands"]))
            self.assertIn("--duplicate-policy prefer-later", " ".join(task["post_unblock_commands"]))
            self.assertTrue(
                task["post_unblock_commands"][0].startswith(
                    "python3 tools/check_magma_matched_finalize_ready.py"
                )
            )
            self.assertIn("--fail-if-not-ready", task["post_unblock_commands"][0])
            self.assertIn(run_root, task["evidence_paths"])
            self.assertIn(guidance_out, task["evidence_paths"])
            self.assertTrue(
                any("finalize_magma_matched_run.sh" in step for step in task["post_unblock_commands"])
            )


if __name__ == "__main__":
    unittest.main()
