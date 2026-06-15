# LIBXML2_1107 Selective Native Evidence - 2026-06-15

This note records the first selective-instrumentation run for the native
FORMTRIG `LIBXML2_1107` BindingSpec line.

## Inputs

- BindingSpec: `artifacts/binding_specs/LIBXML2_1107.native_b2_alloc_fail_candidate.yml`
- Full site map used for binding: `/tmp/formtrig_libxml2_1107_full_20260615T090425Z/native_env/site_map.tsv`
- Selective work dir: `/tmp/formtrig_libxml2_1107_selective_20260615T100923Z`
- Selective binary: `/tmp/formtrig_libxml2_1107_selective_20260615T100923Z/libxml2_regexp_strdup_fail_replay_formtrig_selective`
- Selective site map: `/tmp/formtrig_libxml2_1107_selective_20260615T100923Z/native_env/site_map.tsv`

## Selective Allowlist

The compile-time allowlist contains five site ids:

```text
787463692
820871835
921684644
1816698454
1900586549
```

The selective rebuild emitted exactly five instrumented site-map rows:

```text
820871835  branch  xmlRegNewParserCtxt  xmlregexp.c:738
921684644  load    xmlRegNewParserCtxt  xmlregexp.c:740
787463692  cmp     xmlRegNewParserCtxt  xmlregexp.c:741
1816698454 cmp     hook_malloc          libxml2_regexp_strdup_fail_replay.c:15
1900586549 cmp     hook_malloc          libxml2_regexp_strdup_fail_replay.c:15
```

This confirms the pass-level `FORMTRIG_INSTRUMENT_SITE_ID_FILE` filter was
effective for the target build.

## Campaign Results

| run | exec/s | execs | reached | queued progress | accepted non-trigger progress | saved crashes | saved hangs | diagnosis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| full 30s baseline | 734.76 | 22051 | 19467 | 1 | 1 | 2 | 0 | triggered |
| selective 30s | 1874.70 | 56258 | 54307 | 1 | 1 | 0 | 2 | queued_tc_rooted_progress |
| selective 120s | 2016.13 | 242020 | 236972 | 1 | 1 | 0 | 2 | queued_tc_rooted_progress |
| selective 30s, `-t 3000+` | 3.49 | 106 | 55 | 1 | 1 | 1 | 0 | triggered |
| selective 120s, `-t 3000+` | 102.11 | 12317 | 11370 | 1 | 1 | 2 | 0 | triggered |

The normal selective runs preserve the main pre-trigger evidence while improving
throughput by about 2.55x to 2.74x over the full 30s baseline. The timeout-
adjusted runs confirm the same selective binary reaches terminal crash
accounting, but their throughput should not be used as the instrumentation
performance comparison because the terminal path takes about 1.1s to reach
SIGSEGV on direct replay.

## Lift Signal

For selective 120s:

```json
{
  "experiment_ready": true,
  "pretrigger_lift_guidance_ready": true,
  "accepted_non_trigger_progress_events": 1,
  "non_trigger_candidate_lift_delta": true,
  "lift_delta_only_on_triggered_candidates": false,
  "binding_signal_diagnosis": "role_signal_progress_observed",
  "spec_d_f_non_trigger_candidate_values": [1, 3, 2, 4],
  "spec_d_f_calibration_values": [4]
}
```

Seed readiness passed with:

```text
reached=1
triggered=0
rnt=1
spec_lifted=1
heuristic_lifted=0
manual_lifted=0
observed_heuristic_lifted=0
observed_manual_lifted=0
shm_abi_ok=1
```

The accepted saved progress event remains non-trigger:

```text
d_t=1
d_f_spec_lifted=1
d_f_heuristic_lifted=-1
d_f_manual_lifted=-1
reason=root_aligned_state_transition
```

## Terminal Accounting Note

With AFL++'s auto-selected `exec_timeout=20ms`, the selective 120s campaign
generated the terminal inputs but classified them as hangs:

```text
hangs/id:000000... = 02 61
hangs/id:000001... = 02 00
```

Direct replay of `02 61` on the selective binary exits with SIGSEGV but takes
about 1.1s. Re-running with `-t 3000+` moves the typed `02 61` input into
`crashes/` and yields `saved_crashes > 0`.

## Reproduction Helper

The flow has been scripted in:

```text
scripts/run_formtrig_libxml2_1107_selective.sh
```

Use `--no-terminal-sweeps` when measuring normal selective instrumentation
throughput, and use the terminal timeout sweeps only to validate crash
classification for this slow terminal path.
