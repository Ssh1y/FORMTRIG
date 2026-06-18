# pdf016_validated_short_600s_1rep_baseline_guidance_gap

- target: `PDF016`
- status: `fail_fast_baseline`
- interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence
- fastest successful baseline `_T`: `90.0`
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
| aflplusplus_cmplog | 600 | 1 | 1.000 | 150.0 | 150.0 | 150.0 | 0 | 1/1 | 1306930 | 137 | 0.000104826 |  |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 120.0 | 120.0 | 120.0 | 0 | 1/1 | 1169034 | 178 | 0.000152262 |  |
| redqueen_operand | 600 | 1 | 1.000 | 90.0 | 90.0 | 90.0 | 0 | 1/1 | 2388575 | 122 | 5.10765e-05 |  |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.

| baseline | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 1306793 | 0/1 runs | 90.0 | 90.0 |
| aflplusplus_vanilla | 1168856 | 0/1 runs | 60.0 | 60.0 |
| redqueen_operand | 2388453 | 0/1 runs | 30.0 | 30.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
