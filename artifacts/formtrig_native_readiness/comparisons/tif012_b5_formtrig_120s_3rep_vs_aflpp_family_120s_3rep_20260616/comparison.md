# tif012_b5_formtrig_120s_3rep_vs_aflpp_family_120s_3rep_20260616

- target: `TIF012`
- verdict: `positive_endpoint_matched_comparison`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget primary endpoint benefit

Primary benefit statements:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 0.035s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- none

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`
- `matched_budget_endpoint_success`

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| b5_120s_3rep | 120 | 10870 | false | 34175 | 19422 | 6245 |
| b5_120s_3rep | 120 | 7971 | true | 49100 | 19919 | 5615 |
| b5_120s_3rep | 120 | 4604 | true | 59682 | 20142 | 4616 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 120 | 3 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 120 | 3 | 0.000 |  |  | 0 |
| redqueen_operand | 120 | 3 | 0.000 |  |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `formtrig_endpoint_where_matched_baselines_do_not_trigger`
