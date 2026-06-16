# tif012_b5_matched_1s_2rep_20260616T222404Z

- target: `TIF012`
- verdict: `positive_endpoint_matched_comparison`
- matched baselines: `6`

## Benefit Readout

- summary: current package supports a matched-budget primary endpoint benefit

Primary benefit statements:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 0.034s

Mechanism benefits:
- none

Blocked or not-yet-supported statements:
- no strict pre-trigger guidance benefit is established

Design evidence used for attribution:
- `formtrig_terminal_oracle_success`
- `matched_budget_endpoint_success`

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| b5_1s_2rep | 3 | 305 | false | 449 | 450 | 87 |
| b5_1s_2rep | 3 | 314 | false | 458 | 459 | 89 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 1 | 2 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 1 | 2 | 0.000 |  |  | 0 |
| redqueen_operand | 1 | 2 | 0.000 |  |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_missing`
- `formtrig_terminal_oracle_present`
- `formtrig_endpoint_where_matched_baselines_do_not_trigger`
