# PNG006 Magma Faithful Baselines 30m - 2026-06-16

This note records the first 30-minute same-seed Magma baseline package for
PNG006. It also records a harvest-oracle correction made during the run:
for Magma monitor targets, terminal success is the target-specific
`PNG006_T > 0` signal. AFL `saved_crashes` is preserved as auxiliary evidence,
but it is not target success unless the Magma `_T` oracle also fires.

## Command

```bash
scripts/run_magma_png006_baselines.sh \
  --out /tmp/formtrig_png006_baselines_30m_20260616T013914Z \
  --no-build \
  --durations 1800 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --poll 30
```

Raw evidence subset:

```text
artifacts/formtrig_native_readiness/raw/png006_baselines_30m_20260616T013914Z
```

The preserved subset keeps run records, configs, events, captain logs, all
Magma monitor snapshots, AFL `fuzzer_stats`, `plot_data`, `fuzzer_setup`, and
`cmdline` files, plus generated `summary.json` and `summary.tsv`. Full AFL
queue directories were not copied.

## Harvester Correction

The first vanilla harvest initially reported `success=true` because AFL saved
two crashes even though the PNG006 Magma monitor showed `PNG006_T=0`. That was
wrong for a Magma bug-specific comparison.

`tools/run_post_reach_baseline.py` now uses this rule:

- with `--magma-monitor-dir`: `success = (magma_triggered > 0)`;
- without a Magma monitor: `success = (saved_crashes > 0)`;
- Magma first-trigger times are `magma_monitor_upper_bound`, not exact times;
- Magma harvest does not invent a precise `trigger_execs` value.

The vanilla and CmpLog records were re-harvested after this fix. Redqueen was
harvested by the fixed code path directly.

## Results

| baseline | run_time | execs_done | exec/s | corpus | PNG006_R | PNG006_T | first `_T` | saved_crashes | saved_hangs | target success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `aflplusplus_vanilla` | 1797 | 4313285 | 2399.00 | 704 | 7523009 | 0 | none | 2 | 0 | no |
| `aflplusplus_cmplog` | 1797 | 4167600 | 2317.97 | 1014 | 6951839 | 204 | `<=210s` | 0 | 0 | yes |
| `redqueen_operand` | 1797 | 4276691 | 2378.64 | 1017 | 7604252 | 1269 | `<=90s` | 0 | 0 | yes |

The `first _T` times are Magma monitor poll upper bounds. They are not exact
trigger timestamps.

## Comparison To FORMTRIG 30m

The existing FORMTRIG PNG006 30-minute run reported:

```text
run_time=1800
execs_done=9527259
execs_per_sec=5292.72
formtrig_reached_execs=8726518
formtrig_triggered_execs=5710408
formtrig_queued_progress=634492
accepted_non_trigger_progress_events=1
saved_non_trigger_progress_events=1
spec_lifted_events=1273466
heuristic_lifted_events=0
manual_lifted_events=0
```

That comparison is favorable to FORMTRIG on throughput and final target-state
volume, and the FORMTRIG run has the strict pre-trigger `D_F` guidance gate
evidence that the baselines do not have. However, PNG006 is not a target where
strong AFL++ comparison-feedback baselines cannot produce `_T`: CmpLog reached
`PNG006_T=204`, and the Redqueen/CmpLog path reached `PNG006_T=1269` in the
same 30-minute budget.

## Interpretation

This 30-minute package is useful comparative evidence, but it narrows the PNG006
claim:

- `aflplusplus_vanilla` is a clean high-`_R`, no-target-`_T` control:
  `PNG006_R=7523009`, `PNG006_T=0`.
- `aflplusplus_cmplog` and `redqueen_operand` both cross R2T quickly enough
  that PNG006 cannot support a broad "SOTA cannot trigger this" claim by
  itself.
- FORMTRIG still has stronger 30-minute final target-state volume on the
  current single run, but this must be validated with 2-hour baselines and
  repetitions before making a final comparative claim.
- The central FORMTRIG-specific evidence remains the strict gate: accepted,
  replay-stable non-trigger `D_F` progress with heuristic/manual lift disabled.

The next required step is the 2-hour baseline package and repetitions. PNG006
can remain in the comparison set, but it should not be the only target used to
argue that binary TC feedback remains unresolved for strong SOTA baselines.
