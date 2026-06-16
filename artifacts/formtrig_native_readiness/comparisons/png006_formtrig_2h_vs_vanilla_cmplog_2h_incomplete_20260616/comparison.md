# PNG006_formtrig_2h_vs_vanilla_cmplog_2h_incomplete_20260616

- target: `PNG006`
- verdict: `incomplete_required_baseline_set`
- matched baselines: `2`

## Benefit Readout

- summary: mechanism benefit is present, but performance advantage is not established on this target

Primary benefit statements:
- none

Endpoint observations:
- FORMTRIG terminal oracle success is observed

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- FORMTRIG first `_T`/TTE is not recorded for this run
- matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage
- required baseline families are still missing
- replication is too low for a final performance claim

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig_2h | 7200 | 17276659 | true | 29754905 | 26319188 | 3844204 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 1 | 1.000 | 120 | 2362 |
| aflplusplus_vanilla | 7200 | 1 | 0.000 |  | 0 |

## Reasons

- `missing_required_baselines`
- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `low_replication`
- `matched_baseline_also_triggers`

## Required Next Steps

- collect at least 3 repetitions per matched baseline/budget
- run missing required baselines: redqueen_operand
- do not claim SOTA advantage on this target without harder targets or stronger statistics
