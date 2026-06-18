# pdf016_validated_short_600s_1rep_20260618

- target: `PDF016`
- verdict: `baseline_also_triggers_not_sota_advantage`
- main claim strength: `not_supporting_main_claim`
- matched baselines: `3`

## Benefit Readout

- summary: mechanism benefit is present, but performance advantage is not established on this target

Primary benefit statements:
- none

Endpoint observations:
- none

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- no FORMTRIG terminal success is established
- FORMTRIG first `_T`/TTE is not recorded for this run
- matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage

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
  - status: `fail_fast_baseline`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance
  - source: `artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf016_validated_short_600s_1rep/baseline_guidance_gap.json`
  - interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| b4_600s_1rep | 602 | 0 | true | 1702 | 1661 | 414 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 1.000 | 150 |  | 137 |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 120 |  | 178 |
| redqueen_operand | 600 | 1 | 1.000 | 90 |  | 122 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_missing`
- `matched_baseline_also_triggers`

## Required Next Steps

- do not claim SOTA advantage on this target without harder targets or stronger statistics
- pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims
