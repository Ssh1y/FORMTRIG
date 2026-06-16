# PNG006 Magma Faithful Baseline 2h Vanilla - 2026-06-16

This note records the first 2-hour same-seed Magma baseline run for PNG006.
It covers only the faithful AFL++ vanilla coverage/reach-only control. It is a
matched-budget control for the existing FORMTRIG 2-hour PNG006 run, but it is
not a complete baseline package because AFL++ CmpLog and Redqueen/CmpLog-path
2-hour runs were still missing when this note was generated. The later CmpLog
2-hour run is recorded separately and does trigger PNG006.

Benefit-first conclusion: against the vanilla reach-only control, FORMTRIG has
a matched-budget terminal-success benefit and strict pre-trigger search-guidance
evidence. This benefit must be scoped to vanilla only; the later matched CmpLog
run blocks a broader SOTA-performance claim on PNG006.

## Command

```bash
scripts/run_magma_png006_baselines.sh \
  --out /tmp/formtrig_png006_baselines_2h_vanilla_20260616T033317Z \
  --no-build \
  --durations 7200 \
  --baselines aflplusplus_vanilla \
  --poll 30
```

Raw evidence subset:

```text
artifacts/formtrig_native_readiness/raw/png006_baselines_2h_vanilla_20260616T033317Z
```

The preserved subset keeps `summary.json`, `summary.tsv`, run metadata,
run record/config/status/events, captain logs, all Magma monitor snapshots,
AFL `fuzzer_stats`, `plot_data`, `fuzzer_setup`, `cmdline`, and the auxiliary
AFL crash entry. Full AFL queue directories were not copied.

## Result

| baseline | budget | run_time | execs_done | exec/s | corpus | PNG006_R | PNG006_T | first `_T` | saved_crashes | saved_hangs | target success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `aflplusplus_vanilla` | 7200 | 7197 | 16126501 | 2240.43 | 902 | 23144616 | 0 | none | 1 | 0 | no |

The AFL saved crash is auxiliary evidence only. Because the Magma
target-specific oracle remained `PNG006_T=0`, this run is recorded as
`success=false` for PNG006.

## Matched-Budget Comparison Status

Generated package:

```text
artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_vanilla_2h_incomplete_20260616
```

Verdict:

```text
incomplete_required_baseline_set
```

The comparison package records that FORMTRIG has 2-hour strict pre-trigger
guidance and terminal oracle evidence, and that the matched 2-hour vanilla
baseline has `PNG006_T=0`. It also records that this is not a complete
comparison package because the required matched-budget `aflplusplus_cmplog` and
`redqueen_operand` runs are still missing, and because there is only one
repetition.

## Interpretation

This run strengthens the PNG006 control evidence:

- Vanilla AFL++ can sustain high target reach (`PNG006_R=23144616`) over the
  same 2-hour budget without reaching the target trigger (`PNG006_T=0`).
- FORMTRIG's existing 2-hour run has strict pre-trigger `D_F` evidence and
  terminal oracle evidence. This is mechanism evidence for FORMTRIG; it is not
  a cross-tool ranking metric.
- This does not prove a SOTA advantage. The 30-minute package already showed
  that CmpLog and the Redqueen/CmpLog path can produce `PNG006_T`, and the
  later matched-budget 2-hour CmpLog run triggers within the 120-second monitor
  upper bound. PNG006 should stay in the control/native-readiness bucket while
  harder targets receive long-run budget.
