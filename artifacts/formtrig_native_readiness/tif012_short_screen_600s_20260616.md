# TIF012 600s Short Screen - 2026-06-16

## Benefit-First Conclusion

This is a negative endpoint screen for the current FORMTRIG TIF012
implementation. FORMTRIG produced strict pre-trigger mechanism evidence, but it
did not reach terminal `_T` within 600s. In the matched faithful baseline
screen, AFL++ vanilla did reach `_T` by the 300s Magma monitor snapshot and the
Redqueen/operand path reached `_T` by the 540s snapshot. CmpLog did not reach
`_T`.

Do not claim FORMTRIG performance advantage on TIF012 from this run. The valid
claim is narrower: the BindingSpec and typed TIFF hook create replay-stable
pre-trigger guidance, but the current lifted signal and mutation policy do not
close the R2T transition fast enough on this target.

## FORMTRIG Treatment

Command:

```bash
scripts/run_formtrig_native_manifest.sh \
  artifacts/formtrig_native_readiness/manifests/TIF012.native_draft_magma_canary.600s.manifest
```

Gate command:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite TIF012_formtrig_short_600s \
  --out artifacts/formtrig_native_readiness/raw/tif012_formtrig_short_600s_20260616/gate \
  --min-runtime 590 \
  --run TIF012_formtrig_600s=artifacts/formtrig_native_readiness/raw/tif012_formtrig_short_600s_20260616
```

Key result:

| field | value |
| --- | ---: |
| runtime | 600s |
| execs_done | 418805 |
| execs_per_sec | 697.96 |
| reached | 162101 |
| terminal `_T` | 0 |
| queued_progress | 2 |
| accepted_non_trigger | 2 |
| saved_non_trigger | 2 |
| spec_lifted | 4177 |
| binding_signal_status | pass |
| binding_signal_diagnosis | role_signal_progress_observed |

## Matched Faithful Baselines

Command:

```bash
scripts/run_magma_baselines.sh \
  --target-id TIF012 \
  --durations 600 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --reps 1 \
  --jobs 3 \
  --poll 30 \
  --out artifacts/formtrig_native_readiness/raw/tif012_baselines_short_600s_20260616_r6
```

Summary:

| baseline | runtime | execs_done | execs_per_sec | reached | terminal `_T` | first `_T` upper bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 597s | 1141857 | 1910.11 | 348663 | 0 | NA |
| aflplusplus_vanilla | 597s | 1159506 | 1939.66 | 186594 | 225 | 300s |
| redqueen_operand | 597s | 1129183 | 1888.87 | 722969 | 23 | 540s |

## Comparison Package

Command:

```bash
python3 tools/compare_formtrig_baselines.py \
  --comparison-id tif012_formtrig_600s_vs_aflpp_family_600s_20260616 \
  --target-id TIF012 \
  --formtrig-gate formtrig=artifacts/formtrig_native_readiness/raw/tif012_formtrig_short_600s_20260616/gate/gate_summary.csv \
  --baseline-summary aflpp_family=artifacts/formtrig_native_readiness/raw/tif012_baselines_short_600s_20260616_r6/summary.json \
  --out-dir artifacts/formtrig_native_readiness/comparisons/tif012_formtrig_600s_vs_aflpp_family_600s_20260616 \
  --required-baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --min-reps 1
```

Comparison verdict:

```text
baseline_also_triggers_not_sota_advantage
```

The comparison package preserves the separation between:

- strict FORMTRIG pre-trigger guidance;
- FORMTRIG terminal success;
- matched baseline terminal success.

This separation matters for TIF012 because the mechanism check passed while the
endpoint result failed.

## Engineering Fixes Made While Running This Screen

The faithful Magma baseline runner was repaired so that it can build and run
against the current FORMTRIG-aware Magma canary setup:

- sync `formtrig_runtime.h`, `formtrig_abi.h`, and `formtrig_runtime.c` into
  the Magma support tree when `magma/src/canary.h` includes the FORMTRIG
  runtime;
- patch Magma `prebuild.sh` and `build.sh` to include the FORMTRIG header path
  and link `formtrig_runtime.o`;
- protect dirty target repositories by moving them aside before Docker build
  and restoring them after the run;
- avoid network-dependent `config.guess`/`config.sub` downloads in libtiff
  `autogen.sh` by injecting a local `wget` wrapper for build-aux files;
- export the FORMTRIG include path into target `CFLAGS` and `CXXFLAGS`, so
  target configure/link probes compile with the modified canary header.

These are runner/reproducibility fixes. They do not improve FORMTRIG's TIF012
endpoint result.

## Next Repair Question

The immediate algorithm question is why strict pre-trigger guidance did not
translate into terminal `_T` while vanilla AFL++ did. The next inspection should
compare the FORMTRIG saved non-trigger progress queue against the vanilla
triggering queue entries, with attention to:

- whether the typed TIFF hook is mutating the right IFD/tag bytes;
- whether the accepted lifted delta rewards progress that is correlated with
  `_R` but anti-correlated or neutral with `_T`;
- whether FORMTRIG's lower exec/sec is consuming the short budget before the
  ordinary AFL++ mutations that solve TIF012 can occur;
- whether the current BindingSpec is missing a terminal-proximal role between
  tag parsing and the Magma canary condition.
