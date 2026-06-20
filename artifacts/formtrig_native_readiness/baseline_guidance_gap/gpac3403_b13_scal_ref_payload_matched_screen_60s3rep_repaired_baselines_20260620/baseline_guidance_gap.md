# gpac3403_b13_scal_ref_payload_matched_screen_60s3rep_repaired_baselines_20260620

- target: `GPAC_3403`
- status: `under_budgeted`
- interpretation: baseline runs are shorter than the acceptable trigger threshold, so missing triggers only support a short-screen gap
- fastest successful baseline `_T`: `None`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `False`
- live snapshot input: `False`
- invalid baseline runs excluded: `1`
- under-budget baselines: `aflplusplus_cmplog, aflplusplus_vanilla, redqueen_operand`

## Reasons

- `invalid_baseline_runs_excluded`
- `baseline_budget_below_acceptable_threshold`
- `pretrigger_binary_oracle_flat_before_T`
- `baseline_endpoint_cost_not_sufficient_for_hard_pain`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs | total R | total T | empirical T/R | zero-T 95% upper bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 60 | 3 | 0.000 |  |  |  | 3 | 3/3 | 3 | 0 |  |  |
| aflplusplus_vanilla | 60 | 3 | 0.000 |  |  |  | 3 | 3/3 | 3 | 0 |  |  |
| redqueen_operand | 60 | 3 | 0.000 |  |  |  | 3 | 3/3 | 3 | 0 |  |  |

## Random-Hit Proxy

The rates below are descriptive evidence for the matched runs, not a proof that all baseline mutations are independent Bernoulli trials.
When a baseline has many reached executions and zero trigger executions, the rule-of-three column gives an approximate 95% upper bound for a per-reached-execution hit rate under an independent random-hit model.
For real-CVE post-reach seed contracts without a Magma monitor, reached counts are seed-start evidence only; per-execution random-hit bounds are intentionally left blank.

| baseline | reach evidence | reached without T | zero-T reached runs | median post-reach window | total post-reach window |
| --- | --- | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | post_reach_seed_contract | 3 | 3/3 runs | 60.0 | 180.0 |
| aflplusplus_vanilla | post_reach_seed_contract | 3 | 3/3 runs | 60.0 | 180.0 |
| redqueen_operand | post_reach_seed_contract | 3 | 3/3 runs | 60.0 | 180.0 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
For non-Magma real-CVE runs, post-reach seed contracts can prove that the campaign starts from `_R=true,_T=false`; they do not replace longer endpoint budgets.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
