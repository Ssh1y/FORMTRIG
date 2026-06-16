# LIBARCHIVE_2936_formtrig_10m_vs_aflpp_10m_20260616

- target: `LIBARCHIVE_2936`
- verdict: `short_gate_no_terminal_constant_lift_signal`
- matched baselines: `2`
- budget: `600s` per arm

## Benefit Readout

- summary: No endpoint/performance benefit is established in this 600s screen. The observed FORMTRIG benefit is diagnostic: exact native binding, spec-lifted roles, and typed mutation were exercised, and the run localizes the R2T failure to a constant lifted signal rather than to missing reachability or an invalid harness.

Primary benefit statements:
- none established in this screen

Endpoint observations:
- FORMTRIG did not reach _T or a terminal crash within 600s
- AFL++ vanilla did not reach a terminal crash within 600s
- AFL++ CmpLog did not reach a terminal crash within 600s
- LIBARCHIVE_2936 is therefore not a seconds-easy target for these faithful 600s screens

Mechanism/diagnostic benefits:
- native BindingSpec/site-map binding is exact for the exercised sites
- spec-lifted/actionable atom and role signals were observed at scale
- typed mutation executed on FORMTRIG-selected byte ranges and produced coverage finds
- binding-signal diagnosis isolated the current failure to constant D_F/D_F_spec_lifted values

Blocked or not-yet-supported statements:
- no FORMTRIG terminal success is established
- no time-to-_T or crash improvement is established
- no accepted non-trigger frontier progress is established
- D_F and D_F_spec_lifted are constant, so the present guidance is not an effective R2T gradient
- replication is one run per arm and Redqueen/operand baseline is still missing

Design evidence used for attribution:
- `runtime_event_map_exact`
- `spec_lifted_events`
- `typed_mutation_executed`
- `constant_lift_signal_diagnosis`

## FORMTRIG Run

| label | budget | terminal | reached | spec lifted | accepted non-trigger | typed execs | typed finds | D_F range | diagnosis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| formtrig_short_10m | 600 | 0 | 108141 | 4182 | 0 | 5632 | 8 | 2-2 | `constant_lift_signal` |

## Matched Baselines

| baseline | budget | terminal | execs | exec/s | corpus found | edges | bitmap coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_vanilla | 600 | 0 | 531892 | 886.48 | 851 | 1648 | 20.49% |
| aflplusplus_cmplog | 600 | 0 | 608906 | 1014.83 | 796 | 1695 | 21.08% |

## Reasons
- `no_arm_reached_terminal_in_600s`
- `formtrig_spec_lifted_signal_present`
- `formtrig_typed_stage_executed`
- `formtrig_constant_lift_signal`
- `formtrig_no_accepted_frontier_progress`
- `faithful_aflpp_vanilla_and_cmplog_screen_complete`
- `low_replication`

## Required Next Steps
- refine LIBARCHIVE_2936 BindingSpec/root-state observability before long-run promotion
- add a producer/root signal that varies before _T, such as path-table cardinality, parent-link creation, or hierarchy ordering
- extend typed mutation toward RNT entry count and path hierarchy instead of only byte-local slash insertion
- rerun a 10-30m FORMTRIG/baseline screen only after non-trigger D_F variability appears
- add Redqueen/operand-aware baseline before any final performance claim
