# gpac3403_typedops40_matched_300s_1rep_20260619T165543Z

- target: `GPAC_3403`
- verdict: `not_comparable_missing_matched_budget`
- main claim strength: `not_supporting_main_claim`
- matched baselines: `0`

## Benefit Readout

- summary: current package supports mechanism/search-guidance benefit, subject to remaining blockers

Primary benefit statements:
- none

Endpoint observations:
- none

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- no FORMTRIG terminal success is established
- FORMTRIG first `_T`/TTE is not recorded for this run
- no matched-budget baseline benefit comparison is available

Design evidence used for attribution:
- `strict_pretrigger_guidance`

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
| typedops40 | 301 | 0 | true | 2012 | 1696 | 589 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

## Reasons

- `missing_matched_budget_baselines`
- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_missing`

## Required Next Steps

- run faithful baselines at FORMTRIG budget(s): [301]
- pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims
