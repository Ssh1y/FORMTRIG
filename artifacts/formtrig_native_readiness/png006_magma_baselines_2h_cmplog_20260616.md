# PNG006 Magma Faithful Baseline 2h CmpLog - 2026-06-16

This note records the first 2-hour same-seed AFL++ CmpLog baseline run for
PNG006. It is a matched-budget baseline for the existing FORMTRIG 2-hour run,
but it is not a final comparative package because Redqueen/CmpLog-path evidence
and repetitions are still missing.

Benefit-first conclusion: this run blocks a PNG006 performance-advantage claim
for FORMTRIG against CmpLog. The useful FORMTRIG benefit still visible on
PNG006 is mechanism/search-guidance evidence: binary or sparse trigger feedback
is lifted into accepted non-trigger progress. The CmpLog result shows that this
benefit is not enough, on this target, to claim better first-trigger performance.

## Command

```bash
scripts/run_magma_png006_baselines.sh \
  --out /tmp/formtrig_png006_baselines_2h_cmplog_20260616T053928Z \
  --no-build \
  --durations 7200 \
  --baselines aflplusplus_cmplog \
  --poll 30
```

Raw evidence subset:

```text
artifacts/formtrig_native_readiness/raw/png006_baselines_2h_cmplog_20260616T053928Z
```

The preserved subset keeps `summary.json`, `summary.tsv`, run metadata,
run record/config/status/events, captain logs, all Magma monitor snapshots,
and AFL `fuzzer_stats`, `plot_data`, `fuzzer_setup`, and `cmdline`. Full AFL
queue directories were not copied.

## Result

| baseline | budget | run_time | execs_done | exec/s | corpus | PNG006_R | PNG006_T | first `_T` | saved_crashes | saved_hangs | target success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aflplusplus_cmplog` | 7200 | 7197 | 17067952 | 2371.23 | 1201 | 27502106 | 2362 | <=120s | 0 | 0 | yes |

The first `_T` time is a Magma monitor upper bound from the 120-second poll
snapshot. The monitor first reached `PNG006_R` at 60 seconds and first observed
`PNG006_T>0` at 120 seconds.

## Matched-Budget Comparison Status

Generated package:

```text
artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_vanilla_cmplog_2h_incomplete_20260616
```

Verdict:

```text
incomplete_required_baseline_set
```

Reasons include `matched_baseline_also_triggers`: this 2-hour CmpLog baseline
does produce target-specific Magma `_T`, and it does so early. The package is
still incomplete because the required matched-budget `redqueen_operand` run is
missing and because there is only one repetition.

## Interpretation

PNG006 is not a hard CmpLog-negative target. FORMTRIG still has useful PNG006
evidence for native BindingSpec execution, strict pre-trigger `D_F` guidance,
typed mutation plumbing, and vanilla reach-only contrast, but PNG006 should not
carry the main SOTA-gap claim. Its role is now a control/native-readiness case
unless later repetitions show a different statistical pattern.
