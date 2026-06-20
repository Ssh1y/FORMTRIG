# GPAC_3403 B12 SCAL Reference Scaffold Runner Smoke

- status: `execute_smoke_passed`
- raw_dir: `artifacts/formtrig_native_readiness/raw/gpac3403_b12_scal_ref_scaffold_runner_smoke_20260620T024736Z`
- runner: `scripts/run_gpac3403_b12_scal_ref_scaffold_matched.sh`
- seed_format: `mp4-scal-ref-scaffold`
- BindingSpec: `GPAC_3403.native_b10_extractor_return_candidate.yml`
- mutation hook: `scripts/formtrig_hooks/mp4_box_structure_hook.py`

## Gate Result

| metric | value |
|---|---:|
| duration_s | 5 |
| execs_done | 78 |
| execs_per_sec | 15.26 |
| reached | 79 |
| terminal_triggered | 0 |
| queued_progress | 3 |
| accepted_non_trigger | 3 |
| saved_non_trigger | 3 |
| spec_lifted | 40 |
| pretrigger_lift_guidance_ready | true |
| non_trigger_candidate_lift_delta | true |
| lift_delta_only_on_triggered | false |

## Interpretation

The B12 wrapper is executable: it generated a SCAL-reference MP4 corpus, ran
FORMTRIG with B10 and the MP4 structure hook, and passed the strict pre-trigger
gate. This is not endpoint success. It is readiness evidence that the MP4
scaffold can now be used as a fair R-not-T start state for longer FORMTRIG and
matched baseline campaigns.

The retained-candidate audit observed 15 retained records with
`D_F_spec_lifted` in `[3.0, 6.0]`, but the alias/free relation is still
`release_reassign_alias_observed_terminal_cleanup_missing`. The next run should
enable endpoint replay and then add baseline arms with the same scaffold corpus.
