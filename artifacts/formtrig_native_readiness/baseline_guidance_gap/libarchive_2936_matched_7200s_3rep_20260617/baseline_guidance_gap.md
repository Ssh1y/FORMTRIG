# libarchive_2936_matched_7200s_3rep_20260617

- target: `LIBARCHIVE_2936`
- status: `fail_fast_baseline`
- interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence
- fastest successful baseline `_T`: `9.456`
- pre-trigger binary flatness measured: `False`
- pre-trigger binary flatness pass: `False`
- endpoint cost pass: `False`

## Reasons

- `pretrigger_binary_flatness_not_measured_for_all_runs`
- `fast_successful_baseline_within_acceptable_threshold`
- `baseline_endpoint_cost_not_sufficient_for_hard_pain`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 1.000 | 51.275 | 52.977 | 537.231 | 0 | 0/3 |
| aflplusplus_vanilla | 7200 | 3 | 1.000 | 42.154 | 56.056 | 369.432 | 0 | 0/3 |
| redqueen_operand | 7200 | 3 | 1.000 | 9.456 | 32.517 | 39.068 | 0 | 0/3 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
