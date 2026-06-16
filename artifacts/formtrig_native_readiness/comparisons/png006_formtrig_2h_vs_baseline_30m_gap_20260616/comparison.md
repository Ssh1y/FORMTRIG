# PNG006_formtrig_2h_vs_baseline_30m_gap_20260616

- target: `PNG006`
- verdict: `not_comparable_missing_matched_budget`
- matched baselines: `0`

## Benefit Readout

- summary: current package supports mechanism/search-guidance benefit, subject to remaining blockers

Allowed benefit statements:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- FORMTRIG first `_T`/TTE is not recorded for this run
- no matched-budget baseline benefit comparison is available

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

## Reasons

- `missing_matched_budget_baselines`
- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`

## Required Next Steps

- run faithful baselines at FORMTRIG budget(s): [7200]
