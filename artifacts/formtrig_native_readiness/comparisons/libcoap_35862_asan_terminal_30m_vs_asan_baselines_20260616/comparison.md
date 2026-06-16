# LIBCOAP_35862_asan_terminal_30m_vs_asan_baselines_20260616

- target: `LIBCOAP_CVE_2023_35862`
- verdict: `baseline_also_triggers_not_sota_advantage`
- matched baselines: `3`

## Benefit Readout

- summary: no benefit claim is supported by the current package

Allowed benefit statements:
- none

Blocked or not-yet-supported statements:
- no strict pre-trigger guidance benefit is established
- FORMTRIG first `_T`/TTE is not recorded for this run
- matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage
- replication is too low for a final performance claim

Design evidence used for attribution:
- `formtrig_terminal_oracle_success`

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig_asan_terminal_30m | 1800 | 17 | false | 130010 | 46370 | 4213 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 1800 | 1 | 1.000 | 1060 | 20 |
| aflplusplus_vanilla | 1800 | 1 | 1.000 | 1484 | 22 |
| redqueen_operand | 1800 | 1 | 1.000 | 1327 | 24 |

## Reasons

- `formtrig_strict_pretrigger_guidance_missing`
- `formtrig_terminal_oracle_present`
- `low_replication`
- `matched_baseline_also_triggers`

## Required Next Steps

- collect at least 3 repetitions per matched baseline/budget
- do not claim SOTA advantage on this target without harder targets or stronger statistics
