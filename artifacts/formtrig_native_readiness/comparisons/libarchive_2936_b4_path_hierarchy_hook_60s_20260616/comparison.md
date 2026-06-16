# LIBARCHIVE_2936_b4_path_hierarchy_hook_60s_20260616

- target: `LIBARCHIVE_2936`
- category: `binary-state-null`
- verdict: `speedup_but_under_replicated`
- key benefit: same-timeout matched 60s run shows FORMTRIG reaches first terminal SIGSEGV earlier than successful AFL++ vanilla/CmpLog baselines, while Redqueen/operand does not trigger.

## Benefit First

Under the shared `-V 60 -t 5000+` oracle, FORMTRIG first `_T` is `1.196s / exec 32`. The fastest matched successful baseline is AFL++ vanilla at `22.883s / exec 34379`, so the observed first-`_T` gap is `19.13x` by time and `1074.34x` by executions. AFL++ CmpLog also triggers, but later; Redqueen/operand does not trigger in this 60s run.

This is a speedup and attribution package, not a baseline-impossibility package. It remains under-replicated and needs repeated/longer matched runs before final paper efficacy claims.

## Matched 60s Result

| arm | budget | execs | terminal/crashes | first `_T` | saved non-trigger | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| FORMTRIG b4 + path-hierarchy hook | 60s | 116 | 4 | 1.196s / exec 32 | 1 | first crash from `ftgtype`, `sig:11` |
| aflplusplus_vanilla | 60s | 65592 | 13 | 22.883s / exec 34379 | n/a | matched `-t 5000+` baseline |
| aflplusplus_cmplog | 60s | 56512 | 12 | 34.169s / exec 51119 | n/a | matched `-t 5000+` baseline |
| redqueen_operand | 60s | 102222 | 0 | n/a | n/a | matched `-t 5000+` baseline |

## Historical Context

| arm | budget | execs | `_T` / terminal | first `_T` | saved non-trigger | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| FORMTRIG b4 no hook | 600s | 305093 | 0 | n/a | 10 | pre-trigger guidance only; unmatched older screen |
| AFL++ vanilla old screen | 600s | 531892 | 0 | n/a | n/a | old screen retained as context, not the matched result |
| AFL++ CmpLog old screen | 600s | 608906 | 0 | n/a | n/a | old screen retained as context, not the matched result |

## Design Attribution

The endpoint gain is attributable to FORMTRIG only through the benefit chain: non-constant `D_F_spec_lifted=[0,1]`, accepted non-trigger progress, BindingSpec-selected path-hierarchy typed mutation, and terminal crash replay. The hook constructs slash-delimited path hierarchy candidates from the safe RNT seed (`a/b/file.txt`, `a/c/file.txt`); it does not copy PoC bytes.

## Blocked Claims

- Single repetition is not final efficacy evidence.
- AFL++ vanilla and CmpLog also trigger, so this target supports speedup/attribution rather than an unsolved-by-CmpLog claim.
- The Redqueen/operand row is the local AFL++ CmpLog/Redqueen path, not the original Redqueen artifact unless separately mapped.
- This 60s package must be followed by repeated long-run Magma and real-CVE experiments.

## Evidence

- FORMTRIG hook summary: `evidence/b4_hook_formtrig_summary.json`
- FORMTRIG hook diagnosis: `evidence/b4_hook_formtrig_diagnosis.json`
- Hook provenance: `evidence/b4_hook_mutation_hook.json`
- Crash replay manifest: `evidence/b4_hook_crash_replay.json`
- Matched vanilla run record: `evidence/aflplusplus_vanilla_60s_t5000_run_record.json`
- Matched CmpLog run record: `evidence/aflplusplus_cmplog_60s_t5000_run_record.json`
- Matched Redqueen/operand run record: `evidence/redqueen_operand_60s_t5000_run_record.json`
- First crash inputs: `evidence/crashes/`, `evidence/baseline_first_crashes/`
