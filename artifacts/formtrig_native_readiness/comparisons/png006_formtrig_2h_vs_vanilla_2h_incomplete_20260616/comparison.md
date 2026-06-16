# PNG006_formtrig_2h_vs_vanilla_2h_incomplete_20260616

- target: `PNG006`
- verdict: `incomplete_required_baseline_set`
- matched baselines: `1`

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
