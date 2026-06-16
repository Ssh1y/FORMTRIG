# tif012_formtrig_600s_vs_aflpp_family_600s_20260616

- target: `TIF012`
- verdict: `baseline_also_triggers_not_sota_advantage`
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

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig | 600 | 0 | true | 418805 | 162101 | 4177 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 300 |  | 225 |
| redqueen_operand | 600 | 1 | 1.000 | 540 |  | 23 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_missing`
- `matched_baseline_also_triggers`

## Required Next Steps

- do not claim SOTA advantage on this target without harder targets or stronger statistics
- pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims
