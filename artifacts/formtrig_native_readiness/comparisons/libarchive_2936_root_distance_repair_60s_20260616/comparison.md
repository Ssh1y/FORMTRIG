# LIBARCHIVE_2936_root_distance_repair_60s_20260616

- target: `LIBARCHIVE_2936`
- category: `binary-state-null`
- verdict: `scalar_guidance_repair_no_endpoint_success`
- benefit statement: the b4 BindingSpec converts the prior b3 producer/use-only role variation into an experiment-visible scalar/spec lift delta on the root-observe path.
- blocked claim: no endpoint or TTE benefit is established; both 60s arms have `_T=0`.

## Result

| arm | spec | execs | `_T` | saved non-trigger | queued progress | typed execs | typed finds | diagnosis | experiment ready | `D_F_spec_lifted` | non-trigger lift delta | variable roles |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| b3 | `LIBARCHIVE_2936.native_b3_path_table_count_candidate.yml` | 38914 | 0 | 3 | 3 | 256 | 8 | `queued_tc_rooted_progress` | false | constant `[2]` | false | `desired_producer,use` |
| b4 | `LIBARCHIVE_2936.native_b4_path_table_root_distance_candidate.yml` | 44607 | 0 | 3 | 3 | 512 | 8 | `queued_tc_rooted_progress` | true | variable `[1,0]` | true | `root_observe,desired_producer,use` |

## Interpretation

b3 already showed a mechanism benefit over the older hit-only spec: path-table producer/use values varied and FORMTRIG saved three non-trigger progress samples. Its remaining blocker was scalar collapse: `D_F_spec_lifted` stayed constant at `2`, so the signal was visible in components but not sortable as a lifted scalar.

b4 changes only the root binding from `binary/sub + outcome` to `_compare_path_table` `binary/sub + lower/distance`. This removes the scalar collapse: the root role now has values `[1,0]`, `D_F_spec_lifted` has candidate values `[1,0]`, and BindingSignal reports `non_trigger_candidate_lift_delta=true`.

The public `D_F` remains `1` because the runtime intentionally reserves zero for terminal TC confirmation. Therefore this package supports a benefit-first mechanism claim about scalar/spec guidance readiness, not a crash-performance claim.

## Evidence

- b3 summary: `evidence/b3_count_formtrig_summary.json`
- b3 diagnosis: `evidence/b3_count_formtrig_diagnosis.json`
- b3 binding signal: `evidence/b3_count_binding_signal_diagnosis.json`
- b3 runtime map: `evidence/b3_count_runtime_event_map.csv`
- b4 summary: `evidence/b4_root_distance_formtrig_summary.json`
- b4 diagnosis: `evidence/b4_root_distance_formtrig_diagnosis.json`
- b4 binding signal: `evidence/b4_root_distance_binding_signal_diagnosis.json`
- b4 runtime map: `evidence/b4_root_distance_runtime_event_map.csv`
- b4 lift audit: `evidence/b4_root_distance_lift_audit.csv`

## Next Gate

Promote b4 to a 10-30m screen only as a readiness candidate. The promotion criterion is endpoint or stronger pre-trigger advantage over faithful AFL++ vanilla/CmpLog baselines, not the presence of middle signals alone.
