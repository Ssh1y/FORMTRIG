# pdf003_matched_7200s_3rep_20260617T224500Z_partial_live_baseline_guidance_gap

- target: `PDF003`
- status: `under_replicated`
- interpretation: baseline no-guidance evidence needs more repetitions
- fastest successful baseline `_T`: `None`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `True`
- live snapshot input: `True`

## Reasons

- `low_replication`
- `pretrigger_binary_oracle_flat_before_T`
- `baseline_endpoint_cost_late_missing_or_high_variance`
- `live_snapshot_only`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs | total R | total T | empirical T/R | zero-T 95% upper bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 2 | 0.000 |  |  |  | 2 | 2/2 | 717602 | 0 | 0 | 4.18059e-06 |
| aflplusplus_vanilla | 7200 | 2 | 0.000 |  |  |  | 2 | 2/2 | 265138 | 0 | 0 | 1.13149e-05 |
| redqueen_operand | 7200 | 2 | 0.000 |  |  |  | 2 | 2/2 | 755339 | 0 | 0 | 3.97173e-06 |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.

| baseline | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 717602 | 2/2 runs | 4142.5 | 8285.0 |
| aflplusplus_vanilla | 265138 | 2/2 runs | 4142.5 | 8285.0 |
| redqueen_operand | 755339 | 2/2 runs | 4143.0 | 8286.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
