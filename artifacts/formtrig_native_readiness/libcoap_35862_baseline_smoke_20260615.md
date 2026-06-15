# LIBCOAP_CVE_2023_35862 Faithful Baseline Smoke - 2026-06-15

This note records the first executable baseline smoke for
`LIBCOAP_CVE_2023_35862`. It is not comparative evidence by itself; it proves
that same-target faithful AFL++-family baseline runs can be built and launched.

## Baseline Policy

The accepted main-comparison baselines must follow
`artifacts/formtrig_native_readiness/baseline_faithfulness_policy_20260615.md`.
Representative signal-family stand-ins are rejected by
`tools/run_post_reach_baseline.py` with
`not_faithful_baseline_adapter`.

For this target, the currently runnable faithful baseline family is:

- `aflplusplus_vanilla`: local AFL++ coverage/reach-only control.
- `aflplusplus_cmplog`: local AFL++ CmpLog comparison-feedback artifact.
- `redqueen_operand`: AFL++ Redqueen/CmpLog operand mode, not a substitute for
  the original Redqueen artifact unless separately mapped.

## LLVM 18 / CmpLog Fix

Initial CmpLog builds failed because the local AFL++ LLVM pass sources used
`IntegerType::getInt8PtrTy`, which is removed in LLVM 18. The compatibility
patch is preserved as:

`patches/aflplusplus/formtrig_llvm18_cmplog_compat.patch`

After applying the patch and rebuilding the required AFL++ LLVM pass objects,
this preflight succeeded:

```bash
AFL_LLVM_CMPLOG=1 experiments/aflplusplus/AFLplusplus/afl-clang-fast \
  -c /tmp/formtrig_cmplog_probe.c -o /tmp/formtrig_cmplog_probe.o
```

Caveat: the full AFL++ LAF/split-switches self-test still fails on this host
with a `split-switches-pass.so` LLVM symbol mismatch. LAF is therefore not
counted as a faithful runnable baseline yet. The LIBCOAP CmpLog/Redqueen smoke
below does not enable LAF.

## Build Smoke

Command:

```bash
scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baseline_build_smoke2_20260615T185826Z \
  --durations 1 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog \
  --no-sweeps
```

Result: build completed and produced:

- `/tmp/formtrig_libcoap_35862_baseline_build_smoke2_20260615T185826Z/libcoap_oscore_conf_replay_aflpp`
- `/tmp/formtrig_libcoap_35862_baseline_build_smoke2_20260615T185826Z/libcoap_oscore_conf_replay_cmplog`

## Execute Smoke

Command:

```bash
scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baseline_exec_smoke_20260615T185844Z \
  --durations 1 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog
```

Result: both baselines launched through `tools/run_post_reach_baseline.py` and
preserved `run_config.json`, `events.jsonl`, `status.json`, and
`run_record.json`.

Observed one-second smoke stats:

- `aflplusplus_vanilla`: `execs_done=3284`, `execs_per_sec=1978.31`,
  `corpus_count=31`, `saved_hangs=1`, `saved_crashes=0`.
- `aflplusplus_cmplog`: `execs_done=3185`, `execs_per_sec=1837.85`,
  `corpus_count=24`, `saved_hangs=1`, `saved_crashes=0`.

## Next Required Evidence

Run the same baselines for the same budgets as FORMTRIG, using the same RNT
seed corpus and oracle policy:

```bash
scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baselines_20260615 \
  --durations 1800,7200 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
```

ASAN terminal-oracle comparisons should use the same script with `--asan`.
