# php003_validated_short_600s_1rep_r2_baseline_guidance_gap

- target: `PHP003`
- status: `measured_pass`
- interpretation: baseline evidence supports a hard binary-TC no-guidance candidate
- fastest successful baseline `_T`: `None`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `True`
- live snapshot input: `False`

## Reasons

- `pretrigger_binary_oracle_flat_before_T`
- `baseline_endpoint_cost_late_missing_or_high_variance`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs | total R | total T | empirical T/R | zero-T 95% upper bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 0.000 |  |  |  | 1 | 1/1 | 29955 | 0 | 0 | 0.00010015 |
| aflplusplus_vanilla | 600 | 1 | 0.000 |  |  |  | 1 | 1/1 | 10711 | 0 | 0 | 0.000280086 |
| redqueen_operand | 600 | 1 | 0.000 |  |  |  | 1 | 1/1 | 7816 | 0 | 0 | 0.000383828 |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.

| baseline | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 29955 | 1/1 runs | 507.0 | 507.0 |
| aflplusplus_vanilla | 10711 | 1/1 runs | 507.0 | 507.0 |
| redqueen_operand | 7816 | 1/1 runs | 507.0 | 507.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
