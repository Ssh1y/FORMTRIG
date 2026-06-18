# tif012_matched_7200s_3rep_20260618T022236Z_baseline_guidance_gap

- target: `TIF012`
- status: `fail_fast_baseline`
- interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence
- fastest successful baseline `_T`: `210.0`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `False`
- live snapshot input: `False`

## Reasons

- `pretrigger_binary_oracle_flat_before_T`
- `fast_successful_baseline_within_acceptable_threshold`
- `baseline_endpoint_cost_not_sufficient_for_hard_pain`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs | total R | total T | empirical T/R | zero-T 95% upper bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 0.333 | 4950.0 | 4950.0 | 4950.0 | 2 | 3/3 | 4205348 | 7615 | 0.00181079 |  |
| aflplusplus_vanilla | 7200 | 3 | 1.000 | 930.0 | 1410.0 | 1560.0 | 0 | 3/3 | 2478927 | 123220 | 0.049707 |  |
| redqueen_operand | 7200 | 3 | 0.667 | 210.0 | 3375.0 | 6540.0 | 1 | 3/3 | 4636890 | 8011 | 0.00172767 |  |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.

| baseline | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 4197733 | 2/3 runs | 7137.0 | 19164.0 |
| aflplusplus_vanilla | 2355707 | 0/3 runs | 1350.0 | 3720.0 |
| redqueen_operand | 4628879 | 1/3 runs | 6480.0 | 13767.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
