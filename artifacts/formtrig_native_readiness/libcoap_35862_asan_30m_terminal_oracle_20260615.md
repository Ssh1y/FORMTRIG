# LIBCOAP_CVE_2023_35862 30m ASAN Terminal-Oracle Evidence

Date: 2026-06-15

## Purpose

This note records a 30-minute FORMTRIG ASAN terminal-oracle campaign for the
admissible `LIBCOAP_CVE_2023_35862` native target.

This is terminal vulnerability evidence, not a replacement for the strict
pre-trigger guidance gate. The terminal signal here comes from AFL++ crash
accounting under ASAN exit-code mode. The FORMTRIG runtime `_T` counter stayed
at zero in this run.

## Command

```bash
FORMTRIG_JOBS=8 scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z \
  --asan \
  --durations 1800
```

Terminal-only gate:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBCOAP_CVE_2023_35862_asan_30m_terminal_oracle \
  --min-runtime 1800 \
  --terminal-oracle-only \
  --out /tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z/gate_30m_terminal_oracle \
  --run asan30m=/tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z/selective_sweep_1800s/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml/default
```

## Result

The terminal-only gate passed.

| field | value |
| --- | ---: |
| `run_time` | 1800 |
| `execs_done` | 130010 |
| `execs_per_sec` | 72.23 |
| `corpus_count` | 83 |
| `reached` | 46370 |
| `terminal_triggered` | 17 |
| `saved_crashes` | 17 |
| `saved_hangs` | 0 |
| `formtrig_triggered_execs` | 0 |
| `spec_lifted` | 4213 |
| `heuristic_lifted` | 0 |
| `manual_lifted` | 0 |

Gate summary:

- status: `pass`
- mode: `terminal_oracle_only`
- `experiment_ready=true`
- `pretrigger_lift_guidance_ready=true`
- `non_trigger_candidate_lift_delta=true`
- `binding_signal_status=pass`
- `binding_signal_diagnosis=no_new_non_dominated_progress`

## Replay Verification

The first saved crash was replayed manually against the ASAN selective binary
with:

```bash
ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0 \
UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0 \
/tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z/libcoap_oscore_conf_replay_formtrig_selective \
  /tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z/selective_sweep_1800s/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml/default/crashes/id:000000,sig:00,src:000000,time:1938,execs:143,op:havoc,rep:2
```

The replay exited with ASAN exit code `86`. `replay_stderr.txt` reports
`AddressSanitizer: global-buffer-overflow`, a `READ of size 13`, and the
overflow adjacent to `master_salt`, `sender_id`, and `id_context` strings in
`coap_oscore.c`.

## Interpretation

This confirms that the ASAN terminal oracle is usable for this real-CVE target
and that the 30-minute FORMTRIG ASAN campaign reaches a sanitizer-confirmed
terminal vulnerability state.

It does not mean the runtime `_T` signal fired. The relevant distinction is:

- terminal oracle: `terminal_triggered=17` and `saved_crashes=17`;
- FORMTRIG runtime trigger counter: `formtrig_triggered_execs=0`.

The strongest current LIBCOAP guidance evidence remains the separate 30-minute
and 2-hour non-ASAN strict pre-trigger runs, which accepted replay-stable
non-trigger progress with spec-driven lifted `D_F`. This ASAN run adds terminal
vulnerability confirmation, not an additional accepted non-trigger frontier
event.

## Caveats

- ASAN throughput is much lower than the non-ASAN runs: `72.23` exec/s here
  versus about `2.6k` exec/s in the non-ASAN FORMTRIG long runs.
- `formtrig_progress_log_dropped=41853`, so the progress JSONL is sampled; the
  gate relies on summaries, replayable artifacts, and binding diagnostics.
- This is one 30-minute repetition. Full acceptance still needs 2-hour ASAN
  repetitions and same-seed, same-budget ASAN faithful baselines.
- Faithful SOTA comparison must follow
  `artifacts/formtrig_native_readiness/baseline_faithfulness_policy_20260615.md`;
  representative paper-family stand-ins are not accepted.

## Preserved Evidence

Raw evidence is preserved at:

`artifacts/formtrig_native_readiness/raw/libcoap_35862_asan_30m_20260615T225016Z`

The preserved directory includes gate summaries, fuzzer stats, FORMTRIG summary
and binding diagnostics, harness admissibility output, replay stderr/stdout, a
replay status note, and all 17 AFL++ crash inputs.
