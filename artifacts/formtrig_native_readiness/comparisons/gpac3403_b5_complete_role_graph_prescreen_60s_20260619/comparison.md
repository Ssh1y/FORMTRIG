# GPAC_3403 B5 Complete-Role-Graph 60s Pre-Screen

Generated UTC: 2026-06-19T03:20:00Z

## Verdict

This is a short-gate result, not a long-run endpoint claim. B5 runs through the native AFL++ FORMTRIG path and produces spec-driven pre-trigger guidance, but no terminal `_T` in 60s.

## FORMTRIG B5 Result

| metric | value |
|---|---:|
| duration | 60s |
| execs_done | 7158 |
| corpus_count | 211 |
| terminal `_T` | 0 |
| queued progress | 1 |
| accepted non-trigger progress | 1 |
| saved non-trigger progress | 1 |
| typed execs | 109 |
| typed finds | 14 |
| `D_F_spec_lifted` min/max | 2/6 |
| candidate `D_F_spec_lifted` values | `[6, 2, 4, 5]` |
| variable TC-rooted roles | `['root_observe', 'use']` |
| sampled campaign roles | `['root_observe', 'desired_producer', 'use', 'lifecycle_event', 'input_influence']` |
| missing campaign roles | `['same_object']` |

## Baseline Context

Inherited from `artifacts/formtrig_native_readiness/comparisons/gpac3403_asan_baseline_prescreen_60s_20260618/comparison.json`.

| baseline | valid reps | endpoint successes | median execs | median corpus |
|---|---:|---:|---:|---:|
| `aflplusplus_vanilla` | 3 | 0 | 1467 | 58 |
| `aflplusplus_cmplog` | 3 | 0 | 1406 | 56 |
| `redqueen_operand` | 2 | 0 | 1000.5 | 32.0 |

Total valid baseline reps: 8; endpoint successes: 0.

## Lineage

| candidate | accepted non-trigger | typed execs/finds | candidate D_F values | variable roles | same_object samples |
|---|---:|---:|---|---|---:|
| B1 60s | 2 | 109/14 | `[4, 2, 3]` | `[]` | 0 |
| B5 60s | 1 | 109/14 | `[6, 2, 4, 5]` | `['root_observe', 'use']` | 0 |
| B5 full PoC replay | NA | NA | last `1` | full role graph | 51 |

## Interpretation

B5 improves the quality of the campaign guidance over B1: root/use roles vary in search candidates, and `D_F_spec_lifted` is non-constant over `[6, 2, 4, 5]`. That is useful pre-trigger ordering evidence. The short run still does not sample the `same_object` alias role during search, although full-PoC replay verifies that B5 can observe it on the aborting path.

Next action: run matched 10m/2h B5 FORMTRIG and ASAN AFL++ family endpoint campaigns, while tracking whether search reaches `same_object` and moves from campaign distance 2 toward the full-PoC pre-abort distance 1.
