# gpac3403_b13_60s3rep_repaired_baselines_20260620

- target: `GPAC_3403`
- verdict: `positive_endpoint_matched_comparison`
- main claim strength: `hard_endpoint_gap_candidate`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget primary endpoint benefit

Primary benefit statements:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 2.39s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- baseline no-guidance proof is not measured: hard SOTA-pain claims require flat/binary pre-_T baseline TC signal and late, missing, or high-variance baseline _T

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`
- `matched_budget_endpoint_success`
- `baseline_guidance_gap_required`

## Experiment Strength

- main claim strength: `hard_endpoint_gap_candidate`
- reasons:
  - `matched_baselines_do_not_trigger`
- required design actions:
  - promote to replicated long-run or cross-target confirmation if harness fidelity passes
- baseline no-guidance proof:
  - required for hard SOTA-pain: `true`
  - status: `not_measured`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| typedops64 | 60 | 2 | true | 147 | 146 | 70 |
| typedops64 | 60 | 2 | true | 147 | 146 | 70 |
| typedops64 | 60 | 2 | true | 147 | 146 | 70 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 60 | 3 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 60 | 3 | 0.000 |  |  | 0 |
| redqueen_operand | 60 | 3 | 0.000 |  |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `formtrig_endpoint_where_matched_baselines_do_not_trigger`
