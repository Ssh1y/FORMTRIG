# pdf003_validated_short_600s_1rep_20260617

- target: `PDF003`
- verdict: `negative_formtrig_r2t_gap_with_sota_pain`
- main claim strength: `baseline_binary_tc_pain_observed_short_screen`
- matched baselines: `3`
- budget: `600s`

## Benefit Readout

- summary: PDF003 supports a SOTA-pain observation, but not a positive FORMTRIG endpoint result yet.

Primary supported statements:
- Matched faithful baselines repeatedly hit the Magma reach oracle but do not trigger the terminal oracle in this short screen.
- FORMTRIG's native instrumentation observes lifted BindingSpec signal on the same target.
- FORMTRIG diagnosis narrows the current miss to the R2T handoff: no valid hot range, no accepted non-trigger progress, and no typed mutation execution.

Blocked or not-yet-supported statements:
- FORMTRIG does not currently solve PDF003 within this 600s short screen.
- No endpoint speedup, endpoint success-rate benefit, or strict pre-trigger guidance benefit is supported by this PDF003 run.
- This single repetition is not enough for a final long-run paper claim; it is a hard-target screen and algorithm-debug artifact.

## Endpoint Observations

| arm | run | budget | run time | execs | `_R` / reached | `_T` / terminal |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | AFL++ CmpLog | 600 | 577 | 82301 | 41301 | 0 |
| baseline | AFL++ vanilla | 600 | 577 | 112842 | 110824 | 0 |
| baseline | Redqueen operand | 600 | 577 | 101717 | 42444 | 0 |
| FORMTRIG | native BindingSpec | 600 | 600 | 3611 | 2449 | 0 |

## Mechanism Diagnosis

FORMTRIG did create internal signal:
- `binding_signal_status=pass`
- `spec_lifted=396`
- `progress_events=396`
- `has_lifted_signal=true`
- `d_f_spec_lifted` varied over `[1, 2, 3]`

But the signal was not converted into guidance:
- `accepted_non_trigger_progress=0`
- `saved_non_trigger_progress=0`
- `queued_progress=0`
- `typed_execs=0`
- `typed_skips=1`
- `limiting_reason=no_valid_hot_range`
- `binding_signal_diagnosis=no_new_non_dominated_progress`
- `frontier_reject_events=394`, almost all due to `dominated_by_existing_frontier`

## Follow-up Repair Smoke

After the 600s negative run, the AFL++ native typed stage was patched to use a bounded full-input fallback when a stable reached lifted candidate has actionable BindingSpec components but no producer-provided hot range.

The follow-up smoke was intentionally short (`120s`) and is not endpoint evidence. It checks whether the previous typed-stage blocker was removed:

| run | budget | execs | reached | `_T` | typed execs | typed finds | diagnosis | limiting reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| FORMTRIG fallback smoke | 120 | 907 | 417 | 0 | 128 | 5 | `no_new_non_dominated_progress` | `dominance_rejected` |

This confirms the first repair step:
- before repair: `typed_execs=0`, `typed_skips=1`, limiting reason `no_valid_hot_range`
- after repair smoke: `typed_execs=128`, `typed_skips=0`, typed stage reason `fallback_no_hot_range`

It does not yet confirm R2T success. The remaining blocker is dominance/acceptance: 161 candidates were still rejected as `dominated_by_existing_frontier`, and accepted non-trigger progress remained zero.

## Interpretation

This run is useful because it separates two questions:

1. The pain point exists on PDF003 under the current faithful baselines: they spend the budget around `_R` without reaching `_T`.
2. The current FORMTRIG implementation has signal but does not yet deliver R2T benefit on this target.

The next engineering action is not to weaken the paper claim. It is to repair the acceptance and typed-mutation handoff so a non-trigger candidate with changed lifted state can be scheduled for mutation even when the current hot-range extractor returns no valid range.

## Evidence

- `evidence/baseline_summary.tsv`
- `evidence/baseline_summary.json`
- `evidence/*_monitor_final.csv`
- `evidence/formtrig_batch_summary.csv`
- `evidence/formtrig_summary.json`
- `evidence/formtrig_diagnosis.json`
- `evidence/formtrig_binding_signal_diagnosis.json`
- `evidence/formtrig_final.stats`
- `evidence/post_fallback_120s_*`
