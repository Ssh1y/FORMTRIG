# pdf003_validated_short_600s_3rep_20260617

- target: `PDF003`
- verdict: `positive_endpoint_matched_comparison`
- main claim strength: `hard_endpoint_gap_candidate`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget primary endpoint benefit

Primary benefit statements:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 0.29s

Mechanism benefits:
- none

Blocked or not-yet-supported statements:
- no strict pre-trigger guidance benefit is established

Design evidence used for attribution:
- `formtrig_terminal_oracle_success`
- `matched_budget_endpoint_success`
- `baseline_guidance_gap_measured`

## Experiment Strength

- main claim strength: `hard_endpoint_gap_candidate`
- reasons:
  - `matched_baselines_do_not_trigger`
  - `baseline_guidance_gap_measured_pass`
- required design actions:
  - promote to replicated long-run or cross-target confirmation if harness fidelity passes
- baseline no-guidance proof:
  - required for hard SOTA-pain: `true`
  - status: `measured_pass`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance
  - source: `artifacts/formtrig_native_readiness/comparisons/pdf003_validated_short_600s_3rep_20260617/evidence/guidance_gap/baseline_guidance_gap.json`
  - interpretation: baseline evidence supports a hard binary-TC no-guidance candidate

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| typed_hook_600s_3rep | 602 | 502 | false | 926 | 812 | 180 |
| typed_hook_600s_3rep | 600 | 502 | false | 3480 | 1419 | 290 |
| typed_hook_600s_3rep | 601 | 502 | false | 3257 | 1995 | 474 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 3 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 600 | 3 | 0.000 |  |  | 0 |
| redqueen_operand | 600 | 3 | 0.000 |  |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_missing`
- `formtrig_terminal_oracle_present`
- `formtrig_endpoint_where_matched_baselines_do_not_trigger`
- `baseline_guidance_gap_measured_pass`
