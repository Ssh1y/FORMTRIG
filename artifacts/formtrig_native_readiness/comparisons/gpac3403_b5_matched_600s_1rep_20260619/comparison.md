# GPAC_3403 B5 Matched 600s Single-Rep Pre-Screen

Generated UTC: 2026-06-19T03:55:00Z

## Verdict

This is a 10m single-repetition matched pre-screen, not a replicated long-run proof. FORMTRIG B5 remains experiment-ready and produces pre-trigger lifted guidance; no arm reaches terminal `_T` / endpoint crash.

## FORMTRIG B5

| metric | value |
|---|---:|
| duration | 600s |
| gate status | pass |
| execs_done | 49444 |
| reached execs | 47320 |
| corpus_count | 523 |
| terminal `_T` | 0 |
| queued progress | 1 |
| accepted non-trigger progress | 1 |
| typed execs/finds | 431/24 |
| `D_F_spec_lifted` min/max | 2/6 |
| candidate `D_F_spec_lifted` values | `[6, 2, 4, 5]` |
| variable roles | `['root_observe', 'use']` |
| missing campaign roles | `['same_object']` |

## Baselines

| baseline | valid | execs | corpus | crashes | hangs | endpoint success |
|---|---:|---:|---:|---:|---:|---:|
| `aflplusplus_cmplog` | yes | 6907 | 247 | 0 | 1 | 0 |
| `aflplusplus_vanilla` | yes | 6900 | 226 | 0 | 0 | 0 |
| `redqueen_operand` | yes | 13654 | 308 | 0 | 0 | 0 |
| `redqueen_operand default-map` | no | 0 | 0 | 0 | 0 | 0 |


Redqueen default-map startup failed before fuzzing. The `AFL_MAP_SIZE=10000000` retry is the valid Redqueen/CmpLog operand arm above.

## Interpretation

The useful signal here is not endpoint success. It is that B5 preserves TC-rooted, spec-driven ordering for 600s while faithful AFL++ family baselines do not hit the endpoint in the same budget. The remaining R2T gap is clear: campaign search reaches distance 2 but does not sample `same_object`; full-PoC replay has complete role graph and distance 1.

Next action: run replicated 2h GPAC_3403 B5 matched campaigns, or add a same-object-reaching seed/mutation stage before spending the full 2h budget.
