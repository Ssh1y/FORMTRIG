# PNG006 Magma Faithful Baseline Runner Update - 2026-06-16

## Purpose

PNG006 is the current positive Magma candidate for binary-state-null /
compound-lifecycle R2T guidance. FORMTRIG has 30-minute and 2-hour native
evidence, but it cannot support the final comparative claim until same-seed,
same-budget faithful baselines are run under the same Magma terminal oracle.

This update adds the missing runner path:

```bash
scripts/run_magma_png006_baselines.sh \
  --out /tmp/formtrig_png006_baselines_20260616 \
  --durations 1800,7200 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
```

The runner uses Magma captain to execute `libpng_read_fuzzer` and then harvests
the produced `findings/default/fuzzer_stats` plus `monitor/` snapshots through
`tools/run_post_reach_baseline.py --mode harvest`.

## Oracle

PNG006 is a Magma monitor bug, not necessarily an AFL crash. The baseline
terminal oracle must therefore be:

```text
PNG006_T > 0
```

not only:

```text
saved_crashes > 0
```

`tools/run_post_reach_baseline.py` now accepts:

```text
--magma-monitor-dir DIR
--magma-bug-id PNG006
--mode harvest
--existing-fuzzer-out DIR
```

and records:

- `magma_reached`
- `magma_triggered`
- first monitor snapshot where `PNG006_T > 0`
- `success=true` when the requested Magma bug has `_T > 0`

AFL `saved_crashes` remains in the run record, but it is auxiliary for Magma
bug-specific comparisons. A saved AFL crash for another Magma bug must not make
`PNG006` a success when `PNG006_T=0`.

## Baseline Mapping

The PNG006 runner maps accepted baseline IDs to executable Magma artifacts:

| baseline | Magma fuzzer | contract note |
| --- | --- | --- |
| `aflplusplus_vanilla` | `aflplusplus_plain` | coverage-only AFL++ control |
| `aflplusplus_cmplog` | `aflplusplus` | AFL++ CmpLog/operand feedback path |
| `redqueen_operand` | `aflplusplus` | AFL++ Redqueen/CmpLog implementation path, not the original Redqueen artifact |

The baseline contracts remain enforced by `tools/run_post_reach_baseline.py`:
accepted baselines require local paper anchors, local artifact anchors, and an
explicit information budget.

## Smoke Verification

A synthetic Magma monitor harvest was run to verify the oracle semantics. The
input had no AFL crash, but had `PNG006_T=3` in the monitor.

Command shape:

```bash
tools/run_post_reach_baseline.py \
  --baseline aflplusplus_vanilla \
  --target-id PNG006 \
  --tc-category binary-state-null \
  --seed-corpus artifacts/rnt_corpus/PNG006/seeds \
  --out-dir artifacts/formtrig_native_readiness/raw/magma_harvest_oracle_smoke_20260616/harvest \
  --budget-sec 120 \
  --mode harvest \
  --existing-fuzzer-out artifacts/formtrig_native_readiness/raw/magma_harvest_oracle_smoke_20260616/shared/findings \
  --magma-monitor-dir artifacts/formtrig_native_readiness/raw/magma_harvest_oracle_smoke_20260616/shared/monitor \
  --magma-bug-id PNG006
```

Harvest result:

```json
{
  "success": true,
  "trigger_time_s": 120,
  "trigger_time_kind": "magma_monitor_upper_bound",
  "stats": {
    "execs_done": 4242,
    "run_time": 120,
    "saved_crashes": 0,
    "saved_hangs": 0,
    "magma_reached": 20,
    "magma_triggered": 3
  }
}
```

Raw smoke evidence is preserved at:

```text
artifacts/formtrig_native_readiness/raw/magma_harvest_oracle_smoke_20260616
```

## Interpretation

This is a runner/oracle capability update, not a PNG006 comparative result.
The actual next evidence package must run the command above for at least the
30-minute and 2-hour budgets and compare first `_T`, final `_T`, throughput,
and corpus/crash/hang counters against the existing FORMTRIG PNG006 run.

## Real Smoke Follow-Up

A real 120-second Magma/captain smoke was subsequently completed and is recorded
in:

```text
artifacts/formtrig_native_readiness/png006_magma_baselines_real_smoke_20260616.md
```

That run validated the actual Docker/captain path and found:

- `aflplusplus_vanilla`: `PNG006_R=336689`, `PNG006_T=0`;
- `aflplusplus_cmplog`: `PNG006_R=379517`, `PNG006_T=0`;
- `redqueen_operand`: `PNG006_R=510177`, `PNG006_T=1`.

The `redqueen_operand` `_T` was observed only in the final monitor snapshot, so
the recorded trigger time is an upper bound. This reinforces that PNG006 still
needs same-seed 30-minute and 2-hour baseline campaigns before any comparative
claim is made.

## 30-Minute Follow-Up

A real same-seed 30-minute package was later completed and is recorded in:

```text
artifacts/formtrig_native_readiness/png006_magma_baselines_30m_20260616.md
```

That run also validated the corrected oracle rule. `aflplusplus_vanilla` saved
two AFL crashes but had `PNG006_T=0`, so it is recorded as `success=false` for
PNG006. `aflplusplus_cmplog` and `redqueen_operand` both produced target
`_T`, with final `PNG006_T=204` and `PNG006_T=1269`, respectively.
