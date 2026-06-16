# LIBARCHIVE_2936_b4_formtrig_10m_vs_aflpp_10m_20260616

- target: `LIBARCHIVE_2936`
- category: `binary-state-null`
- budget: 600 seconds per arm
- verdict: `pretrigger_guidance_improved_no_endpoint_success`

## Result

| arm | execs | `_T` | saved non-trigger | reached | binding signal | `D_F_spec_lifted` | note |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| old FORMTRIG b2 10m | 393966 | 0 | 0 | 108141 | `fail/constant_lift_signal` | constant `[2]` | no accepted pre-trigger progress |
| FORMTRIG b4 10m | 305093 | 0 | 10 | 162849 | `pass/role_signal_progress_observed` | variable `[1,0]` | scalar guidance improved |
| AFL++ vanilla 10m | 531892 | 0 | n/a | n/a | n/a | n/a | no terminal |
| AFL++ CmpLog 10m | 608906 | 0 | n/a | n/a | n/a | n/a | no terminal |

## Benefit Readout

b4 does not solve endpoint R2T on this target within 600 seconds: no arm reaches `_T` or saves a crash. It does show a real FORMTRIG-side mechanism benefit over the old native FORMTRIG run: saved non-trigger progress improves from `0` to `10`, `D_F_spec_lifted` changes from constant `[2]` to `[1,0]`, and the campaign diagnosis changes from `not_ready/typed_mutation_no_lift_delta` to `ready/queued_tc_rooted_progress`.

This is the benefit-first interpretation: FORMTRIG's middle products are now paying off as stable pre-trigger search guidance, but the claim stops there. The next blocker is endpoint conversion, likely requiring typed mutation that changes RNT entry count/path hierarchy or a closer producer for null-parent creation.

## Evidence

- b4 summary: `evidence/b4_formtrig_summary.json`
- b4 diagnosis: `evidence/b4_formtrig_diagnosis.json`
- b4 binding signal: `evidence/b4_binding_signal_diagnosis.json`
- old FORMTRIG summary: `evidence/old_formtrig_summary.json`
- old FORMTRIG diagnosis: `evidence/old_formtrig_diagnosis.json`
- old FORMTRIG binding signal: `evidence/old_binding_signal_diagnosis.json`
- AFL++ vanilla stats: `evidence/aflplusplus_vanilla_fuzzer_stats.txt`
- AFL++ CmpLog stats: `evidence/aflplusplus_cmplog_fuzzer_stats.txt`

## Next Gate

Do not promote this as endpoint evidence. Promote b4 only as the current LIBARCHIVE readiness candidate, and spend the next engineering step on structure-aware typed mutation or a closer null-parent producer signal before longer replicated runs.
