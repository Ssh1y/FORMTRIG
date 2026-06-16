# PNG006 Magma Faithful Baseline Real Smoke - 2026-06-16

## Purpose

This note records the first real Magma/captain execution smoke for the PNG006
faithful baseline runner. It validates that the runner can execute Magma
`libpng_read_fuzzer`, harvest AFL++ `fuzzer_stats`, and use Magma monitor
`PNG006_T` as the terminal oracle.

This is not a 30-minute or 2-hour comparative result.

## Command

```bash
scripts/run_magma_png006_baselines.sh \
  --out /tmp/formtrig_png006_baselines_real_smoke_20260616T012458Z \
  --no-build \
  --durations 120 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --poll 30
```

The runner copies the host seed corpus into the Magma shared volume and passes
the container-visible path:

```text
MAGMA_INPUT_CORPUS=/magma_shared/input_corpus
```

It also passes:

```text
AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
```

so AFL++ does not abort when host `core_pattern` is configured as a pipe.

## Results

| baseline | run_time | execs_done | exec/s | corpus_count | PNG006_R | PNG006_T | saved_crashes | saved_hangs | result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aflplusplus_vanilla` | 117 | 261125 | 2214.03 | 362 | 336689 | 0 | 0 | 0 | no `_T` |
| `aflplusplus_cmplog` | 117 | 268226 | 2274.59 | 477 | 379517 | 0 | 0 | 0 | no `_T` |
| `redqueen_operand` | 117 | 264347 | 2241.08 | 528 | 510177 | 1 | 0 | 0 | `_T` observed |

The `redqueen_operand` `_T` appeared only in the final monitor snapshot, so the
recorded `trigger_time_s=117` is an upper bound with
`trigger_time_kind=magma_monitor_upper_bound`, not an exact first-trigger time.

Final monitor rows:

```text
aflplusplus_vanilla:  PNG006_R=336689, PNG006_T=0
aflplusplus_cmplog:   PNG006_R=379517, PNG006_T=0
redqueen_operand:     PNG006_R=510177, PNG006_T=1
```

## Interpretation

This smoke proves the PNG006 baseline path is executable and that the Magma
monitor oracle is wired correctly. It also shows why PNG006 is a better R2T
candidate than LIBCOAP: vanilla and CmpLog reach PNG006 hundreds of thousands
of times in 120 seconds without triggering it.

The result does not prove FORMTRIG superiority:

- one AFL++ Redqueen/CmpLog-path run observed one `_T` by 120 seconds;
- the run has no repetitions;
- the run budget is far shorter than the accepted FORMTRIG 30-minute and
  2-hour evidence;
- `redqueen_operand` is the AFL++ CmpLog/Redqueen implementation path, not the
  original Redqueen artifact.

The next evidence package must run at least 30-minute and 2-hour same-seed,
same-budget baselines and compare first `_T`, final `_T`, throughput, corpus,
hang/crash counters, and repetitions against the FORMTRIG PNG006 run.

## Preserved Evidence

Raw evidence is preserved at:

```text
artifacts/formtrig_native_readiness/raw/png006_baselines_real_smoke_120s_20260616T012458Z
```

The preserved directory contains:

- `run_metadata.txt`;
- per-baseline `run_config.json`, `events.jsonl`, `status.json`,
  `run_record.json`;
- per-baseline captain stdout/stderr logs;
- per-baseline Magma monitor snapshots;
- per-baseline AFL++ `fuzzer_stats`, `plot_data`, and command metadata where
  available.
