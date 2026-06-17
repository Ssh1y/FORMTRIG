# pdf003_validated_short_600s_1rep_20260617

- target: `PDF003`
- verdict: `positive_format_typed_r2t_smoke_with_sota_pain_not_longrun`
- main claim strength: `format_aware_typed_r2t_smoke_not_matched_longrun`
- matched baselines: `3`
- budget: `600s`

## Benefit Readout

- summary: PDF003 supports a SOTA-pain observation and now has a positive FORMTRIG format-aware typed R2T smoke, but not yet a matched long-run or strict pre-trigger guidance claim.

Primary supported statements:
- Matched faithful baselines repeatedly hit the Magma reach oracle but do not trigger the terminal oracle in this short screen.
- FORMTRIG's native instrumentation observes lifted BindingSpec signal on the same target.
- The earlier FORMTRIG runs narrowed the miss to the R2T handoff: no accepted non-trigger progress and insufficient typed mutation structure.
- A BindingSpec-provenance PDF image typed hook now generates valid multi-component image PDFs and reaches `_T` from an `op:ftgtype` queue entry in the 30s smoke.

Blocked or not-yet-supported statements:
- The 30s typed-hook smoke is not a matched long-run endpoint comparison.
- Strict pre-trigger frontier guidance is not proven on PDF003 because `saved_non_trigger_progress=0`.
- This single smoke is not enough for a final paper claim; it is positive R2T engineering evidence that needs replicated matched runs.

## Endpoint Observations

| arm | run | budget | run time | execs | `_R` / reached | `_T` / terminal |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | AFL++ CmpLog | 600 | 577 | 82301 | 41301 | 0 |
| baseline | AFL++ vanilla | 600 | 577 | 112842 | 110824 | 0 |
| baseline | Redqueen operand | 600 | 577 | 101717 | 42444 | 0 |
| FORMTRIG | native BindingSpec | 600 | 600 | 3611 | 2449 | 0 |
| FORMTRIG | PDF image typed hook smoke | 30 | 31 | 214 | 176 | 89 |

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

## Semantic Frontier Repair Smoke

The next repair changed frontier admission so a BindingSpec-generated semantic state transition is not collapsed solely because a coarse lifted `D_F=1` frontier entry already exists. The main frontier still prefers non-regressing candidates, but a bounded semantic escape can keep a different atom role/producer/use state for follow-up mutation.

This follow-up smoke was also short (`180s`) and is not endpoint evidence:

| run | budget | execs | reached | `_T` | typed execs | typed finds | frontier updates | semantic transition accepts | saved non-trigger | diagnosis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| FORMTRIG semantic escape smoke | 180 | 1361 | 683 | 0 | 128 | 5 | 3 | 2 | 0 | `no_new_non_dominated_progress` |

This confirms a second repair step:
- before semantic repair: changed lifted states were still rejected as `dominated_by_existing_frontier`
- after semantic repair: two `root_aligned_state_transition` candidates entered the calibration frontier, and `formtrig_frontier_updates` increased to 3

It still does not confirm R2T success. In this 180s run, the semantic transitions came from calibration/frontier maintenance and no FORMTRIG-only non-trigger seed was saved:
- `saved_non_trigger_progress=0`
- `queued_progress=0`
- `formtrig_triggered_execs=0`
- `limiting_reason=dominance_rejected`

## PDF Image Typed Hook Smoke

The next repair adds a BindingSpec-provenance typed mutation hook for PDF image color-space structure. The hook emits small valid image PDFs with standard multi-component color spaces such as `/DeviceRGB`; it does not read the Magma canary value, but it does use PDF-format knowledge derived from the BindingSpec role that image color-space dictionaries influence the PDF003 state.

This follow-up smoke is short (`30s`) and is endpoint R2T evidence, not a matched long-run comparison:

| run | budget | run time | execs | reached | `_T` | first `_T` queue | typed execs | saved triggered | saved non-trigger | diagnosis |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| FORMTRIG PDF image typed hook smoke | 30 | 31 | 214 | 176 | 89 | `time:287,execs:79,op:ftgtype` | 24 | 10 | 0 | `triggered` |

This confirms the R2T engineering path:
- The first saved trigger came from `op:ftgtype`, not from a startup seed.
- Direct replay of the saved queue entry logs `crash_predicate=true`.
- `binding_signal_status=pass`, `spec_lifted_events=33`, and `d_f_spec_lifted` varied over `[1, 3]`.

It does not prove strict pre-trigger guidance on PDF003:
- `saved_non_trigger_progress=0`
- `frontier_progress_accept_events=0`
- The positive result is typed endpoint conversion, not a gradual non-trigger frontier chain.

## Interpretation

This run is useful because it separates two questions:

1. The pain point exists on PDF003 under the current faithful baselines: they spend the budget around `_R` without reaching `_T`.
2. The current FORMTRIG implementation now has a positive R2T path when BindingSpec typed mutation can create valid PDF image structure.
3. The remaining unproven part is strict pre-trigger guidance: the successful PDF003 smoke goes directly to `_T` and does not save non-trigger progress.

The next engineering action is to run matched repetitions with this hook enabled and to add a fair comparison against format-aware or grammar-aware baselines where appropriate. In parallel, FORMTRIG still needs the non-trigger save/frontier handoff for targets where direct typed endpoint conversion is not enough.

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
- `evidence/post_semantic_escape_180s_*`
- `evidence/post_pdf_image_hook_30s_*`
