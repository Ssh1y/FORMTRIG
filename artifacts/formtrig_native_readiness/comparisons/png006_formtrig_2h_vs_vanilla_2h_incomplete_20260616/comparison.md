# PNG006_formtrig_2h_vs_vanilla_2h_incomplete_20260616

- target: `PNG006`
- verdict: `incomplete_required_baseline_set`
- matched baselines: `1`

## Benefit Readout

- summary: current package supports a matched-budget terminal-success benefit, subject to replication

Allowed benefit statements:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Blocked or not-yet-supported statements:
- FORMTRIG first `_T`/TTE is not recorded for this run
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
| aflplusplus_vanilla | 7200 | 1 | 0.000 |  | 0 |

## Reasons

- `missing_required_baselines`
- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `low_replication`

## Required Next Steps

- collect at least 3 repetitions per matched baseline/budget
- run missing required baselines: aflplusplus_cmplog,redqueen_operand
