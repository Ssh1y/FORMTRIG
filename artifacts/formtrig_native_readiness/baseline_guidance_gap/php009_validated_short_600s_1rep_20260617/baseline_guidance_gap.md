# php009_validated_short_600s_1rep_20260617

- target: `PHP009`
- status: `fail_fast_baseline`
- interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence
- fastest successful baseline `_T`: `120.0`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `False`

## Reasons

- `low_replication`
- `pretrigger_binary_oracle_flat_before_T`
- `fast_successful_baseline_within_acceptable_threshold`
- `baseline_endpoint_cost_not_sufficient_for_hard_pain`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 1.000 | 300.0 | 300.0 | 300.0 | 0 | 1/1 |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 270.0 | 270.0 | 270.0 | 0 | 1/1 |
| redqueen_operand | 600 | 1 | 1.000 | 120.0 | 120.0 | 120.0 | 0 | 1/1 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
