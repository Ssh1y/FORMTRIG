# LIBCOAP_CVE_2023_35862 ASAN Terminal Oracle Smoke

Date: 2026-06-15

## Purpose

This note records the first usable ASAN terminal-oracle campaign for the
admissible `LIBCOAP_CVE_2023_35862` native FORMTRIG target.

This is not a replacement for the strict pre-trigger guidance gate. It proves
that the ASAN terminal oracle can be run under AFL++ and counted as crashes
without being misclassified as hangs by the system `core_pattern` handler.

## Tooling Fix

The host uses an apport `core_pattern`, so ASAN `abort_on_error=1` can make AFL++
misclassify sanitizer crashes as timeouts/hangs. The fix is:

- set `ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0`
- set `UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0`
- set `AFL_CRASH_EXITCODE=86`
- patch AFL++'s `check_asan_opts()` to allow this mode only when
  `AFL_CRASH_EXITCODE` matches the ASAN `exitcode=`.

The FORMTRIG LIBCOAP runner now exports this ASAN mode automatically when
`--asan` is used.

## Evidence

Reused ASAN selective binary:

```text
/tmp/formtrig_libcoap_35862_asan_campaign_30s_20260615Tnow/libcoap_oscore_conf_replay_formtrig_selective
```

Exit-code ASAN sweep:

```bash
ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0 \
UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0 \
AFL_CRASH_EXITCODE=86 \
scripts/run_formtrig_binding_candidate_sweep.sh \
  --in artifacts/rnt_corpus/LIBCOAP_CVE_2023_35862/seeds \
  --out /tmp/formtrig_libcoap_35862_asan_exitcode_sweep_30s_after_aflpatch_20260615Tnow \
  --target-bug LIBCOAP_CVE_2023_35862 \
  --category equality \
  --site-map /tmp/formtrig_libcoap_35862_asan_campaign_30s_20260615Tnow/selective_native_env/site_map.tsv \
  --candidate artifacts/binding_specs/LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml \
  --duration 30 \
  --seed-preflight require \
  --seed-preflight-max 32 \
  --seed-preflight-timeout 2 \
  --target-site-ids 3854664882 \
  --aflpp-dir experiments/aflplusplus/AFLplusplus \
  --afl-arg -m --afl-arg none \
  -- /tmp/formtrig_libcoap_35862_asan_campaign_30s_20260615Tnow/libcoap_oscore_conf_replay_formtrig_selective @@
```

Result:

- `run_time=30`
- `execs_done=2303`
- `execs_per_sec=76.70`
- `saved_crashes=7`
- `saved_hangs=0`
- `terminal_triggered_execs=7`
- `formtrig_reached_execs=52`
- `spec_lifted_events=20`
- `heuristic_lifted_events=0`
- `manual_lifted_events=0`
- binding signal: `pass / no_new_non_dominated_progress`

Gate behavior:

- strict gate with `--require-terminal`: fails as expected with
  `no_accepted_non_trigger_progress;no_saved_non_trigger_progress`.
- terminal-oracle gate with `--terminal-oracle-only`: passes.

Terminal-only gate command:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBCOAP_CVE_2023_35862_asan_terminal_oracle \
  --min-runtime 30 \
  --terminal-oracle-only \
  --out /tmp/formtrig_libcoap_35862_asan_exitcode_sweep_30s_after_aflpatch_20260615Tnow/gate_terminal_oracle \
  --run asan30=/tmp/formtrig_libcoap_35862_asan_exitcode_sweep_30s_after_aflpatch_20260615Tnow/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml/default
```

End-to-end runner validation:

```bash
FORMTRIG_JOBS=8 scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_asan_runner_exitcode_5s_20260615Tnow \
  --asan \
  --durations 5
```

Runner-level result:

- `run_time=5`
- `execs_done=405`
- `saved_crashes=3`
- `saved_hangs=0`
- `terminal_triggered_execs=3`
- `spec_lifted_events=8`
- `heuristic_lifted_events=0`
- `manual_lifted_events=0`
- terminal-only gate: pass

## Interpretation

This closes a practical ASAN accounting gap: sanitizer terminal states are now
saved as AFL++ crashes instead of hangs under the current host `core_pattern`.

It does not by itself prove FORMTRIG guidance effectiveness. For acceptance, use
this terminal-oracle evidence together with a separate strict pre-trigger
guidance gate that has accepted and saved non-trigger progress.
