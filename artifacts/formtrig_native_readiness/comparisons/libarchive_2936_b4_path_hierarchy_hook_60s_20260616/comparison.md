# LIBARCHIVE_2936_b4_path_hierarchy_hook_60s_20260616

- target: `LIBARCHIVE_2936`
- category: `binary-state-null`
- verdict: `positive_but_under_replicated`
- key benefit: b4's pre-trigger guidance now converts into terminal `SIGSEGV` via BindingSpec-selected typed mutation.

## Result

| arm | budget | execs | `_T` / terminal | first `_T` | saved non-trigger | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| FORMTRIG b4 + path-hierarchy hook | 60s | 116 | 4 | 1.196s / exec 32 | 1 | first crash from `ftgtype`, `sig:11` |
| FORMTRIG b4 no hook | 600s | 305093 | 0 | n/a | 10 | pre-trigger guidance only |
| AFL++ vanilla | 600s | 531892 | 0 | n/a | n/a | no terminal |
| AFL++ CmpLog | 600s | 608906 | 0 | n/a | n/a | no terminal |

## Benefit Readout

This is the first LIBARCHIVE_2936 package where FORMTRIG turns the b4 lifted signal into endpoint success. The hook is selected by the BindingSpec and constructs slash-delimited path hierarchy candidates from the safe RNT seed (`a/b/file.txt`, `a/c/file.txt`); it does not copy PoC bytes. The first saved crash is `sig:11` at about `1.196s` and exec `32`.

The claim is still under-replicated: Redqueen/operand-aware baseline is missing, and final comparisons should rerun all arms with the same terminal timeout/oracle. The current package is strong endpoint-conversion evidence for FORMTRIG's middle products, not yet the final performance table.

## Evidence

- FORMTRIG hook summary: `evidence/b4_hook_formtrig_summary.json`
- FORMTRIG hook diagnosis: `evidence/b4_hook_formtrig_diagnosis.json`
- Hook provenance: `evidence/b4_hook_mutation_hook.json`
- Crash replay manifest: `evidence/b4_hook_crash_replay.json`
- Crash inputs: `evidence/crashes/`
- Previous b4 no-hook 10m summary: `evidence/b4_no_hook_10m_summary.json`
- AFL++ vanilla/CmpLog 10m stats: `evidence/aflplusplus_vanilla_10m_fuzzer_stats.txt`, `evidence/aflplusplus_cmplog_10m_fuzzer_stats.txt`
