# tif012_b5_matched_7200s_3rep_20260617

- target: `TIF012`
- status: `fail_fast_baseline`
- interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence
- fastest successful baseline `_T`: `210.0`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `False`

## Reasons

- `pretrigger_binary_oracle_flat_before_T`
- `fast_successful_baseline_within_acceptable_threshold`
- `baseline_endpoint_cost_not_sufficient_for_hard_pain`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 0.333 | 4950.0 | 4950.0 | 4950.0 | 2 | 3/3 |
| aflplusplus_vanilla | 7200 | 3 | 1.000 | 930.0 | 1410.0 | 1560.0 | 0 | 3/3 |
| redqueen_operand | 7200 | 3 | 0.667 | 210.0 | 3375.0 | 6540.0 | 1 | 3/3 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
