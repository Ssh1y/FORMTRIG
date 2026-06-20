# gpac3403_typedops64_matched_60s_3rep_20260620T032732Z

- target: `GPAC_3403`
- verdict: `incomplete_required_baseline_set`
- main claim strength: `incomplete_matched_evidence`
- matched baselines: `5`

## Benefit Readout

- summary: current package supports a matched-budget primary benefit, subject to replication

Primary benefit statements:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 2.39s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- required baseline families are still missing
- replication is too low for a final performance claim

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`
- `matched_budget_endpoint_success`

## Experiment Strength

- main claim strength: `incomplete_matched_evidence`
- reasons:
  - `matched_baselines_do_not_trigger`
  - `required_baseline_families_missing`
  - `matched_baseline_replication_incomplete`
- required design actions:
  - promote to replicated long-run or cross-target confirmation if harness fidelity passes
  - complete the required faithful baseline set before hard SOTA-pain claims
  - complete the requested repetitions before hard SOTA-pain claims
- baseline no-guidance proof:
  - required for hard SOTA-pain: `false`
  - status: `not_required_for_current_strength`
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
| aflplusplus_cmplog | 60 | 2 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 60 | 3 | 0.000 |  |  | 0 |

## Reasons

- `missing_required_baselines`
- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `low_replication`
- `formtrig_endpoint_where_matched_baselines_do_not_trigger`

## Required Next Steps

- collect at least 3 repetitions per matched baseline/budget
- run missing required baselines: redqueen_operand
