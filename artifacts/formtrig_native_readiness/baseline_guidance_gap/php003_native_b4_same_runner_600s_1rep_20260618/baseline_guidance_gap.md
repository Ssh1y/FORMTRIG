# php003_native_b4_same_runner_600s_1rep_20260618

- target: `PHP003`
- status: `fail_fast_baseline`
- interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence
- fastest successful baseline `_T`: `180.0`
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
| aflplusplus_cmplog | 600 | 1 | 0.000 |  |  |  | 1 | 1/1 | 24946 | 0 | 0 | 0.00012026 |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 180.0 | 180.0 | 180.0 | 0 | 1/1 | 2518 | 31 | 0.0123114 |  |
| redqueen_operand | 600 | 1 | 1.000 | 330.0 | 330.0 | 330.0 | 0 | 1/1 | 24944 | 11 | 0.000440988 |  |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.

| baseline | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 24946 | 1/1 runs | 507.0 | 507.0 |
| aflplusplus_vanilla | 2487 | 0/1 runs | 90.0 | 90.0 |
| redqueen_operand | 24933 | 0/1 runs | 240.0 | 240.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
