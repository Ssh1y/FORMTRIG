# pdf003_matched_7200s_3rep_combined_live_baseline_guidance_gap

- target: `PDF003`
- status: `live_snapshot_only`
- interpretation: live baseline evidence is provisional and cannot support a final hard-pain claim
- fastest successful baseline `_T`: `None`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `True`
- live snapshot input: `True`

## Reasons

- `pretrigger_binary_oracle_flat_before_T`
- `baseline_endpoint_cost_late_missing_or_high_variance`
- `live_snapshot_only`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs | total R | total T | empirical T/R | zero-T 95% upper bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 0.000 |  |  |  | 3 | 3/3 | 973831 | 0 | 0 | 3.08062e-06 |
| aflplusplus_vanilla | 7200 | 3 | 0.000 |  |  |  | 3 | 3/3 | 328755 | 0 | 0 | 9.12534e-06 |
| redqueen_operand | 7200 | 3 | 0.000 |  |  |  | 3 | 3/3 | 854855 | 0 | 0 | 3.50937e-06 |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.

| baseline | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 973831 | 3/3 runs | 3900.0 | 11465.0 |
| aflplusplus_vanilla | 328755 | 3/3 runs | 3900.0 | 11465.0 |
| redqueen_operand | 854855 | 3/3 runs | 3900.0 | 11466.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
