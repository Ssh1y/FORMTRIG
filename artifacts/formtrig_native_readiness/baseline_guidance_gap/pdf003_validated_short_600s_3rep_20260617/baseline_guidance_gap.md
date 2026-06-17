# pdf003_baseline_guidance_gap_600s_3rep_20260617

- target: `PDF003`
- status: `measured_pass`
- interpretation: baseline evidence supports a hard binary-TC no-guidance candidate
- fastest successful baseline `_T`: `None`
- pre-trigger binary flatness measured: `True`
- pre-trigger binary flatness pass: `True`
- endpoint cost pass: `True`

## Reasons

- `pretrigger_binary_oracle_flat_before_T`
- `baseline_endpoint_cost_late_missing_or_high_variance`

## Baseline Groups

| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 3 | 0.000 |  |  |  | 3 | 3/3 |
| aflplusplus_vanilla | 600 | 3 | 0.000 |  |  |  | 3 | 3/3 |
| redqueen_operand | 600 | 3 | 0.000 |  |  |  | 3 | 3/3 |

## Claim Boundary

This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.
It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.
