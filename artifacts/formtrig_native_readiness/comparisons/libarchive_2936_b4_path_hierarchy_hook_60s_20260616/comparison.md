# LIBARCHIVE_2936_b4_path_hierarchy_hook_60s_20260616

- target: `LIBARCHIVE_2936`
- category: `binary-state-null`
- verdict: `positive_speedup_matched_comparison`
- key benefit: 3 matched 60s repetitions plus one matched 10m confirmation show FORMTRIG reaches first terminal SIGSEGV earlier and with far fewer executions than the fastest successful AFL++ vanilla/CmpLog/Redqueen-path baseline.

## Benefit First

Under the shared `-V 60 -t 5000+` oracle, FORMTRIG triggers in `3/3` reps with median first `_T` `1.326s / exec 32`. The fastest successful baseline family by median is AFL++ vanilla at `24.450s / exec 34379`, giving `18.44x` median time speedup and `1074.34x` median execution speedup.

The longer matched 10m confirmation preserves the direction. FORMTRIG reaches first terminal SIGSEGV at `1.220s / exec 32`; the fastest successful baseline in that run is AFL++ CmpLog at `20.671s / exec 28677`, giving `16.94x` wall-clock speedup and `896.16x` execution speedup to first terminal trigger.

This is replicated speedup and attribution evidence, not a baseline-impossibility package. Vanilla, CmpLog, and Redqueen/operand are all baseline-visible; the claim is that FORMTRIG converts the lifted path-hierarchy signal much earlier.

## Replicated 60s Result

| arm | reps | success | first `_T` values | median first `_T` | first exec values | median exec | note |
| --- | ---: | ---: | --- | ---: | --- | ---: | --- |
| FORMTRIG b4 + path-hierarchy hook | 3 | 3/3 | 1.196s, 2.000s, 1.326s | 1.326s | 32, 32, 32 | 32 | matched `-t 5000+` |
| AFL++ vanilla | 3 | 3/3 | 22.883s, 24.450s, 37.648s | 24.450s | 34379, 31216, 50549 | 34379 | matched `-t 5000+` |
| AFL++ CmpLog | 3 | 3/3 | 34.169s, 28.505s, 60.976s | 34.169s | 51119, 34515, 71727 | 51119 | matched `-t 5000+` |
| AFL++ Redqueen/operand path | 3 | 2/3 | 34.587s, 30.505s | 32.546s | 47776, 42539 | 45157 | matched `-t 5000+` |

## Matched 10m Confirmation

| arm | budget | success | first `_T` | first exec | saved crashes | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| FORMTRIG b4 + path-hierarchy hook | 600s | yes | 1.220s | 32 | 9 | `D_F_spec_lifted={0,1}`, 5 saved non-trigger progress events |
| AFL++ CmpLog | 600s | yes | 20.671s | 28677 | 25 | fastest successful baseline in this run |
| AFL++ vanilla | 600s | yes | 25.844s | 39789 | 25 | matched seed and `-t 5000+` |
| AFL++ Redqueen/operand path | 600s | yes | 62.335s | 102947 | 38 | matched seed and `-t 5000+` |

Benefit: FORMTRIG reaches first terminal SIGSEGV before every baseline family in this matched 10m point, with `16.94x` lower wall-clock time and `896.16x` fewer executions than the fastest successful baseline. This strengthens the 60s speedup result, but it is still one longer confirmation point rather than broad Magma/real-CVE generality.

## Design Attribution

The endpoint gain is attributable to FORMTRIG only through the benefit chain: non-constant `D_F_spec_lifted={0,1}`, accepted non-trigger progress, BindingSpec-selected path-hierarchy typed mutation, and terminal crash replay. The hook constructs slash-delimited path hierarchy candidates from the safe RNT seed (`a/b/file.txt`, `a/c/file.txt`); it does not copy PoC bytes.

## Blocked Claims

- This target does not prove that AFL++/CmpLog/Redqueen cannot solve the TC; all baseline families are visible in the 60s repeated package.
- The 10m confirmation strengthens the speedup direction but is still not the required long-run Magma and broad real-CVE evidence loop.
- The Redqueen/operand row is the local AFL++ CmpLog/Redqueen path, not the original Redqueen artifact unless separately mapped.

## Evidence

- Repetition summary: `evidence/repetition_summary.json`
- FORMTRIG rep1 summary: `evidence/b4_hook_formtrig_summary.json`
- FORMTRIG rep2/rep3 summaries: `evidence/reps/formtrig_rep2_summary.json`, `evidence/reps/formtrig_rep3_summary.json`
- Matched baseline run records: `evidence/*_60s_t5000_run_record.json`, `evidence/reps/*_run_record.json`
- Matched 10m confirmation: `evidence/longrun_10m/longrun_10m_summary.json`
- First crash inputs: `evidence/crashes/`, `evidence/baseline_first_crashes/`, `evidence/reps/first_crashes/`
