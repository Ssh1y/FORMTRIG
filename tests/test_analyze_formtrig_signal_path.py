import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class AnalyzeFormtrigSignalPathTest(unittest.TestCase):
    def write_run(
        self,
        root: Path,
        name: str,
        events: list[dict],
        binding_signal: dict | None = None,
        queue_files: dict[int, bytes] | None = None,
        runtime_event_map: str | None = None,
    ) -> Path:
        default_dir = root / "formtrig" / name / "out" / "default"
        default_dir.mkdir(parents=True)
        (default_dir / "fuzzer_stats").write_text(
            "\n".join(
                [
                    "run_time          : 60",
                    "execs_done        : 100",
                    "execs_per_sec     : 1.66",
                    "formtrig_reached_execs   : 90",
                    "formtrig_triggered_execs : 1",
                    "formtrig_queued_progress : 2",
                    "formtrig_frontier_updates: 1",
                    "formtrig_typed_execs     : 10",
                    "formtrig_typed_finds     : 3",
                    "formtrig_saved_non_trigger_log_seen: 0",
                    "formtrig_saved_triggered_log_seen: 1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (default_dir / "formtrig_progress.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events) + "\n",
            encoding="utf-8",
        )
        if binding_signal is not None:
            (default_dir / "formtrig_binding_signal_diagnosis.json").write_text(
                json.dumps(binding_signal) + "\n",
                encoding="utf-8",
            )
        if queue_files:
            queue_dir = default_dir / "queue"
            queue_dir.mkdir()
            for queue_id, content in queue_files.items():
                (queue_dir / f"id:{queue_id:06d},src:000000").write_bytes(content)
        if runtime_event_map is not None:
            (default_dir.parent / "formtrig_runtime_event_map.csv").write_text(
                runtime_event_map,
                encoding="utf-8",
            )
        return root / "formtrig" / name

    def run_tool(self, root: Path) -> dict:
        output = subprocess.check_output(
            [
                "python3",
                str(REPO_ROOT / "tools" / "analyze_formtrig_signal_path.py"),
                "--target-id",
                "TGT",
                "--formtrig-dir",
                str(root / "formtrig"),
                "--run-root",
                str(root),
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
        )
        return json.loads(output)

    def test_terminal_after_calibrated_frontier_is_not_strict_pretrigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "calibrated_frontier",
                        "reason": "initial_frontier_seed",
                        "triggered": False,
                        "execs_done": 7,
                        "d_f": 3,
                        "d_f_spec_lifted": 3,
                        "source_flags": 2,
                    },
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "triggered": True,
                        "execs_done": 9,
                        "d_f": 0,
                        "d_f_spec_lifted": 0,
                        "source_flags": 2,
                    },
                ],
            )

            payload = self.run_tool(root)

        self.assertEqual(payload["verdict"], "terminal_after_calibrated_frontier_only")
        run = payload["runs"][0]["progress_path"]
        self.assertFalse(run["strict_pretrigger_guidance_seen"])
        self.assertEqual(run["calibrated_non_trigger_events"], 1)
        self.assertEqual(run["saved_non_trigger_events"], 0)
        self.assertEqual(run["saved_trigger_events"], 1)

    def test_saved_non_trigger_before_trigger_is_strict_pretrigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "saved_progress",
                        "reason": "lifted-feature improvement",
                        "triggered": False,
                        "execs_done": 5,
                        "d_f": 2,
                        "d_f_spec_lifted": 2,
                        "source_flags": 2,
                    },
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "triggered": True,
                        "execs_done": 9,
                        "d_f": 0,
                        "d_f_spec_lifted": 0,
                        "source_flags": 2,
                    },
                ],
            )

            payload = self.run_tool(root)

        self.assertEqual(payload["verdict"], "strict_pretrigger_guidance_observed")
        run = payload["runs"][0]["progress_path"]
        self.assertTrue(run["strict_pretrigger_guidance_seen"])
        self.assertEqual(run["first_saved_non_trigger"]["execs_done"], 5)

    def test_typed_lifted_stage_before_trigger_is_attribution_not_strict_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "calibrated_frontier",
                        "reason": "initial_frontier_seed",
                        "triggered": False,
                        "execs_done": 5,
                        "d_f": 2,
                        "d_f_spec_lifted": 2,
                        "lifted": True,
                        "stable": 1,
                        "source_flags": 2,
                    },
                    {
                        "event": "typed_stage_start",
                        "reason": "planned",
                        "triggered": False,
                        "lifted": True,
                        "execs_done": 7,
                        "queue_id": 3,
                        "d_t": 1,
                        "d_f": 1,
                        "d_f_spec_lifted": 1,
                        "source_flags": 2,
                        "first_actionable": {
                            "kind": 6,
                            "role": 4,
                            "priority": 30,
                            "value": 1,
                        },
                    },
                    {
                        "event": "typed_stage_end",
                        "reason": "completed",
                        "triggered": False,
                        "lifted": True,
                        "execs_done": 8,
                        "queue_id": 3,
                        "d_f": 1,
                        "d_f_spec_lifted": 1,
                    },
                    {
                        "event": "saved_progress",
                        "reason": "triggered",
                        "triggered": True,
                        "execs_done": 9,
                        "d_f": 0,
                        "d_f_spec_lifted": 0,
                        "source_flags": 2,
                    },
                ],
            )

            payload = self.run_tool(root)

        self.assertEqual(payload["verdict"], "terminal_after_calibrated_frontier_only")
        self.assertEqual(payload["typed_attribution"], "terminal_after_typed_lifted_nontrigger_stage")
        self.assertEqual(payload["typed_stage_before_terminal_runs"], 1)
        self.assertEqual(payload["typed_lifted_nontrigger_before_terminal_runs"], 1)
        capability = payload["guidance_capability"]
        self.assertEqual(capability["stable_frontier_runs"], 1)
        self.assertEqual(capability["sortable_lifted_df_runs"], 1)
        self.assertEqual(capability["actionable_typed_nontrigger_runs"], 1)
        self.assertEqual(capability["mutable_typed_find_runs"], 1)
        self.assertEqual(capability["total_typed_finds"], 3)
        self.assertEqual(capability["strict_saved_pretrigger_runs"], 0)
        run = payload["runs"][0]["progress_path"]
        self.assertFalse(run["strict_pretrigger_guidance_seen"])
        self.assertTrue(run["stable_frontier_before_first_saved_trigger"])
        self.assertTrue(run["sortable_lifted_df_before_first_saved_trigger"])
        self.assertTrue(run["actionable_typed_nontrigger_before_first_saved_trigger"])
        self.assertTrue(run["first_saved_trigger_after_typed_stage"])
        self.assertTrue(run["typed_lifted_nontrigger_before_first_saved_trigger"])
        self.assertEqual(run["typed_stage_start_events"], 1)
        self.assertEqual(run["typed_stage_end_events"], 1)
        self.assertEqual(run["first_typed_stage_start"]["execs_done"], 7)
        self.assertEqual(
            run["first_typed_lifted_nontrigger_before_first_saved_trigger"]["queue_id"],
            3,
        )

    def test_terminal_gap_reports_unsatisfied_producer_on_saved_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "saved_progress",
                        "reason": "root_aligned_state_transition",
                        "triggered": False,
                        "execs_done": 17,
                        "queue_id": 5,
                        "d_f": 1,
                        "d_f_spec_lifted": 1,
                        "lifted": True,
                        "atom_signal_values": [
                            {
                                "atom_id": 1,
                                "role_bits": 35,
                                "producer_bits": 0,
                                "guard_bits": 2,
                                "use_bits": 1,
                                "flags": 3,
                            }
                        ],
                    }
                ],
                binding_signal={
                    "atoms": [
                        {
                            "atom_id": 1,
                            "category": "binary-state-null",
                            "bound_roles": [
                                "root_observe",
                                "guard",
                                "desired_producer",
                                "use",
                            ],
                            "roles": [
                                {
                                    "role": "root_observe",
                                    "bound": True,
                                    "candidate_values": [1],
                                },
                                {
                                    "role": "guard",
                                    "bound": True,
                                    "candidate_values": [1],
                                },
                                {
                                    "role": "desired_producer",
                                    "bound": True,
                                    "candidate_values": [0],
                                },
                                {
                                    "role": "use",
                                    "bound": True,
                                    "candidate_values": [0, 1],
                                },
                            ],
                        }
                    ]
                },
                queue_files={5: b"abc"},
            )

            payload = self.run_tool(root)

        gap = payload["runs"][0]["terminal_gap"]
        self.assertEqual(gap["status"], "saved_frontier_blocked_on_producer")
        self.assertEqual(gap["saved_non_trigger_frontier_events"], 1)
        self.assertIn(
            "no_terminal_T_after_saved_non_trigger_frontier",
            gap["blocking_reasons"],
        )
        self.assertEqual(
            gap["unsatisfied_producer_roles_at_latest_saved"],
            {"1": ["desired_producer"]},
        )
        self.assertEqual(
            gap["constant_zero_producer_roles"],
            {"1": ["desired_producer"]},
        )
        self.assertEqual(
            gap["missing_bound_roles_at_latest_saved"],
            {"1": ["desired_producer"]},
        )
        self.assertEqual(
            gap["latest_saved_non_trigger"]["queue_file_size"],
            3,
        )

    def test_terminal_gap_reports_missing_specific_binding_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(
                root,
                "001_TGT",
                [
                    {
                        "event": "saved_progress",
                        "reason": "root_aligned_state_transition",
                        "triggered": False,
                        "execs_done": 17,
                        "queue_id": 5,
                        "d_f": 1,
                        "d_f_spec_lifted": 1,
                        "lifted": True,
                        "atom_signal_values": [
                            {
                                "atom_id": 1,
                                "role_bits": 65,
                                "producer_bits": 0,
                                "guard_bits": 0,
                                "use_bits": 0,
                                "flags": 3,
                            }
                        ],
                        "component_values": [
                            {
                                "atom_id": 1,
                                "role": 1,
                                "flags": 2,
                                "value": 1,
                                "context_hash": "root",
                            },
                            {
                                "atom_id": 1,
                                "role": 7,
                                "flags": 2,
                                "value": 1,
                                "context_hash": "life_a",
                            },
                            {
                                "atom_id": 1,
                                "role": 7,
                                "flags": 2,
                                "value": 1,
                                "context_hash": "life_b",
                            },
                        ],
                    }
                ],
                binding_signal={
                    "atoms": [
                        {
                            "atom_id": 1,
                            "category": "compound-sequence-lifecycle",
                            "bound_roles": ["root_observe", "lifecycle_event"],
                            "roles": [
                                {"role": "root_observe", "bound": True},
                                {"role": "lifecycle_event", "bound": True},
                            ],
                        }
                    ]
                },
                runtime_event_map=(
                    "binding_id,atom_id,role,event_id,lift_allowed,function,file,line,column,opcode,component_kind,priority,value_mode\n"
                    "1,1,root_observe,root,true,root_fn,a.c,10,1,icmp,3,50,hit\n"
                    "2,1,lifecycle_event,life_a,true,life_a_fn,a.c,20,1,br,7,20,hit\n"
                    "3,1,lifecycle_event,life_b,true,life_b_fn,a.c,30,1,br,7,25,hit\n"
                    "4,1,lifecycle_event,life_c,true,life_c_fn,a.c,40,1,br,7,30,hit\n"
                ),
                queue_files={5: b"abc"},
            )

            payload = self.run_tool(root)

        gap = payload["runs"][0]["terminal_gap"]
        self.assertEqual(gap["status"], "saved_frontier_missing_binding_events")
        self.assertEqual(gap["missing_bound_roles_at_latest_saved"], {})
        self.assertEqual(
            gap["missing_binding_events_at_latest_saved"]["1"][0]["event_id"],
            "life_c",
        )
        self.assertIn(
            "missing_binding_events_at_latest_saved_frontier",
            gap["blocking_reasons"],
        )

    def test_accepts_direct_fuzzer_out_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self.write_run(root, "001_TGT", [])
            out_dir = run / "out"
            output = subprocess.check_output(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "analyze_formtrig_signal_path.py"),
                    "--target-id",
                    "TGT",
                    "--formtrig-dir",
                    str(out_dir),
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
            )
            payload = json.loads(output)

        self.assertEqual(payload["run_count"], 1)
        self.assertEqual(payload["runs"][0]["run"], "out")

    def test_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_run(root, "001_TGT", [])
            out_md = root / "signal_path.md"
            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "analyze_formtrig_signal_path.py"),
                    "--target-id",
                    "TGT",
                    "--formtrig-dir",
                    str(root / "formtrig"),
                    "--out-md",
                    str(out_md),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            text = out_md.read_text(encoding="utf-8")

        self.assertIn("FORMTRIG Signal Path: TGT", text)
        self.assertIn("claim boundary", text)
        self.assertIn("typed attribution", text)
        self.assertIn("Guidance Capability", text)
        self.assertIn("stable frontier runs", text)


if __name__ == "__main__":
    unittest.main()
