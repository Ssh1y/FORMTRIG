# PHP003 Current-ABI Matched 600s 3rep Comparison

## Verdict

`replicated_speedup_control_not_hard_sota_pain`: FORMTRIG is much faster on this repaired runner, but PHP003 does not demonstrate a hard SOTA-pain endpoint gap because faithful baselines trigger within the 600s budget.

## FORMTRIG

| Reps | Success | First `_T` exact values | Median | Max | Terminal `_T` total | Saved non-trigger progress |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 3 | 3/3 | 7.595s, 1.942s, 1.929s | 1.942s | 7.595s | 170365 | 6 |

## Baselines

| Baseline | Success | First `_T` values | Median successful first `_T` | Terminal `_T` total |
| --- | ---: | --- | ---: | ---: |
| aflplusplus_cmplog | 2/3 | NA, 360s, 480s | 420s | 19 |
| aflplusplus_vanilla | 3/3 | 180s, 150s, 150s | 150s | 86 |
| redqueen_operand | 3/3 | 330s, 240s, 240s | 240s | 3936 |

## Benefit

- FORMTRIG median exact first `_T`: 1.942s
- Fastest baseline family median first `_T`: aflplusplus_vanilla at 150s
- Median TTE speedup: 77.24x
- Slowest FORMTRIG TTE speedup against that baseline median: 19.75x

## Claim Boundary

This is replicated speedup/control evidence, not a hard SOTA-pain result. AFL++ vanilla is 3/3 within 600s with first `_T` upper bounds 180s, 150s, and 150s; all baseline families trigger in at least 2/3 runs. The correct use of PHP003 is mechanism attribution and speedup control while hard-pain budget moves to targets where faithful baselines are late, missing, or high-variance.
