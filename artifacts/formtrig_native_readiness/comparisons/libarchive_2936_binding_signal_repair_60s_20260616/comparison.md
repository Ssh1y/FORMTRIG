# LIBARCHIVE_2936_binding_signal_repair_60s_20260616

- target: `LIBARCHIVE_2936`
- verdict: `mechanism_benefit_no_endpoint_success`
- budget: `60s` per FORMTRIG arm
- purpose: same-budget BindingSpec/signal repair check, not fuzzer-vs-baseline performance comparison

## Benefit Readout

- summary: No endpoint performance benefit is established: both FORMTRIG arms have terminal_triggered_execs=0 in 60s. The observed benefit is a mechanism/search-readiness benefit: the count-based BindingSpec turns saturated hit roles into variable producer/use roles and yields saved non-trigger progress.

Primary benefits:
- same-budget saved non-trigger progress improved from `0` to `3`
- binding-signal status improved from `fail/constant_lift_signal` to `pass/role_signal_progress_observed`
- `pretrigger_lift_guidance_ready` improved from `false` to `true`

Endpoint observations:
- old B2 hit-role spec: `_T=0` in 60s
- new B3 path-table-count spec: `_T=0` in 60s
- this package establishes no TTE/crash-speedup claim

Mechanism benefits:
- `desired_producer` candidate values widened from `[1]` to `[2, 3, 4, 7]`
- `use` candidate values widened from `[1]` to `[1, 16, 24, 32, 56]`
- runtime event-map binding remains exact/B4 for the exercised rows
- accepted non-trigger progress is spec-lifted and uses no heuristic/manual lift

Blocked or not-yet-supported statements:
- no endpoint/TTE benefit is established
- scalar `D_F_spec_lifted` is still constant at `2`, so the next repair should expose a lower-is-better scalar or root-proximal value
- single 60s repetition is not final efficacy evidence
- no faithful AFL++/CmpLog/Redqueen performance comparison is made in this mechanism package

## FORMTRIG Arms

| arm | spec | execs | _T | queued progress | saved non-trigger | typed execs | typed finds | BindingSignal | variable roles | producer values | use values | diagnosis |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| `old_b2_hit_roles_60s` | `LIBARCHIVE_2936.native_b2_path_table_candidate.yml` | 43254 | 0 | 0 | 0 | 256 | 10 | `fail/constant_lift_signal` | `none` | `[1]` | `[1]` | `constant_lift_signal` |
| `count_b3_path_table_count_60s` | `LIBARCHIVE_2936.native_b3_path_table_count_candidate.yml` | 38914 | 0 | 3 | 3 | 256 | 8 | `pass/role_signal_progress_observed` | `desired_producer,use` | `[2, 3, 4, 7]` | `[1, 16, 24, 32, 56]` | `queued_tc_rooted_progress` |

## Interpretation

The old BindingSpec had exact native bindings but all non-root roles were saturated hit bits, so the fuzzer could not rank R2T candidates before `_T`. The count-based BindingSpec keeps the same TC root but binds producer/use progress to path-table cardinality and allocation scale. That creates variable, TC-rooted role signals and lets FORMTRIG save non-trigger progress within the same 60s budget.

This is a real mechanism benefit, but not the final claim. The next step is to turn the variable role vector into stronger root-proximal guidance and typed mutation, then rerun 10-30m screens and faithful baselines.
