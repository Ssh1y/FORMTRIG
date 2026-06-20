# gpac3403_typedops64_matched_5s_1rep_20260620T030129Z

- target: `GPAC_3403`
- verdict: `not_comparable_missing_matched_budget`
- main claim strength: `not_supporting_main_claim`
- matched baselines: `0`

## Benefit Readout

- summary: FORMTRIG endpoint success is observed, but matched-budget benefit is not comparable yet

Primary benefit statements:
- none

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 2.401s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- no matched-budget baseline benefit comparison is available

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`

## Experiment Strength

- main claim strength: `not_supporting_main_claim`
- reasons:
  - `no_endpoint_or_speedup_advantage_for_formtrig`
- required design actions:
  - repair BindingSpec/mutation design or move budget to a harder target
- baseline no-guidance proof:
  - required for hard SOTA-pain: `false`
  - status: `not_required_for_current_strength`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| typedops64 | 12 | 1 | true | 32 | 32 | 11 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

## Reasons

- `missing_matched_budget_baselines`
- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`

## Required Next Steps

- run faithful baselines at FORMTRIG budget(s): [12]
