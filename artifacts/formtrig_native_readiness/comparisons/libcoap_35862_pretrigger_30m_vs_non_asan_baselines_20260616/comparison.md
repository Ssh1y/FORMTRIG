# LIBCOAP_35862_pretrigger_30m_vs_non_asan_baselines_20260616

- target: `LIBCOAP_CVE_2023_35862`
- verdict: `pretrigger_guidance_only`
- matched baselines: `3`

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig_pretrigger_30m | 1800 | 0 | true | 4764811 | 2128534 | 8524 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 1800 | 1 | 0.000 |  | 0 |
| aflplusplus_vanilla | 1800 | 1 | 0.000 |  | 0 |
| redqueen_operand | 1800 | 1 | 0.000 |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_missing`
- `low_replication`

## Required Next Steps

- collect at least 3 repetitions per matched baseline/budget
- pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims
