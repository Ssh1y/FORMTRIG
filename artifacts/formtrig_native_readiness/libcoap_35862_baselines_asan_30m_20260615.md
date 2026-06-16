# LIBCOAP_CVE_2023_35862 30m ASAN Faithful Baseline Evidence

Date: 2026-06-15

## Purpose

This package records same-seed, same-budget, same-ASAN-oracle baseline runs for
`LIBCOAP_CVE_2023_35862`. It closes the main fairness gap left by the earlier
non-ASAN baseline package.

These results are important because they are negative for a strong FORMTRIG
terminal-advantage claim on this target: all three AFL++-family baselines also
triggered the ASAN terminal oracle quickly. LIBCOAP remains useful as a real-CVE
pipeline and oracle-validation target, but it should not be used as main
evidence that FORMTRIG outperforms faithful AFL++-family baselines.

## Command

```bash
FORMTRIG_JOBS=8 scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baselines_asan_30m_20260615T233518Z \
  --asan \
  --durations 1800 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
```

The runner used ASAN exit-code oracle mode:

- `AFL_CRASH_EXITCODE=86`
- `ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0`
- `UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0`

Each run wrote `baseline_contract` metadata with `paper_anchors`,
`artifact_anchors`, and an explicit `information_budget`.

## Results

| baseline | run_time | execs_done | exec/s | corpus_count | saved_crashes | saved_hangs | first crash | first crash execs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `aflplusplus_vanilla` | 1800 | 137840 | 76.58 | 111 | 22 | 0 | 0.200s | 22 |
| `aflplusplus_cmplog` | 1800 | 140244 | 77.91 | 96 | 20 | 0 | 0.227s | 25 |
| `redqueen_operand` | 1800 | 138452 | 76.92 | 115 | 24 | 0 | 0.226s | 25 |

The first-crash values come from AFL++ crash filenames:

- `aflplusplus_vanilla`: `time:200,execs:22`
- `aflplusplus_cmplog`: `time:227,execs:25`
- `redqueen_operand`: `time:226,execs:25`

The raw `run_record.json` files in this package were generated before
`tools/run_post_reach_baseline.py` was fixed to report first-crash timing. In
those raw records, `trigger_time_s` is last-crash-derived. The table above is
the authoritative first-trigger interpretation for this run.

## Replay Verification

The first saved crash from each baseline was replayed with the same ASAN
exit-code oracle. All three replays exited `86` and reported
`AddressSanitizer: global-buffer-overflow`.

| baseline | first crash op | replay exit | ASAN summary |
| --- | --- | ---: | --- |
| `aflplusplus_vanilla` | `havoc` | 86 | `global-buffer-overflow`, `READ of size 7` |
| `aflplusplus_cmplog` | `colorization` | 86 | `global-buffer-overflow`, `READ of size 13` |
| `redqueen_operand` | `colorization` | 86 | `global-buffer-overflow`, `READ of size 13` |

## Interpretation

This is faithful executable baseline evidence, not a representative stand-in.
It proves that the current LIBCOAP ASAN target is easy for the AFL++ family
under the same seed corpus and terminal oracle.

Consequences for the FORMTRIG claim:

- The 30-minute FORMTRIG ASAN run remains valid terminal-oracle evidence:
  `saved_crashes=17`, `terminal_triggered=17`, and replayed ASAN
  `global-buffer-overflow`.
- The 30-minute and 2-hour non-ASAN FORMTRIG runs remain valid pre-trigger
  lifted-guidance evidence: replay-stable non-trigger progress, spec-lifted
  `D_F`, and no heuristic/manual lifted signal.
- LIBCOAP should not be used to claim terminal TTE superiority over faithful
  AFL++-family baselines. All three baselines trigger in less than one second
  according to AFL crash filename time fields.
- For the final SOTA comparison, the main positive targets must be harder
  binary/state/sequence/lifecycle TCs where native `D_T` collapses and where
  faithful baselines do not receive FORMTRIG-only lifted `D_F` or typed
  mutation information.

`redqueen_operand` is still the AFL++ CmpLog/Redqueen implementation path, not
the original Redqueen artifact. It is useful as an operand/value-feedback
baseline for this equality/magic target, but it must not be described as the
original Redqueen artifact without a separate equivalence mapping.

## Preserved Evidence

Raw evidence is preserved at:

`artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_asan_30m_20260615T233518Z`

The preserved directory includes:

- baseline build logs and CmpLog compiler preflight log;
- `run_metadata.txt`;
- per-baseline `run_config.json`;
- per-baseline `events.jsonl`;
- per-baseline `status.json`;
- per-baseline `run_record.json`;
- per-baseline `fuzzer_stats`;
- per-baseline AFL++ crash inputs;
- per-baseline first-crash replay stdout/stderr/status files.
