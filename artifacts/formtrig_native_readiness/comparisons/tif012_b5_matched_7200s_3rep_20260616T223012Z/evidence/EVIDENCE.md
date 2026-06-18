# TIF012 7200s x3 Matched Evidence Bundle

This directory contains the small, auditable evidence used by the matched
FORMTRIG-vs-baseline comparison. Full AFL++ raw queues are intentionally
left in the run directory and are not copied here.

## Comparison

- target: `TIF012`
- comparison id: `tif012_matched_7200s_3rep_20260618T022236Z`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `not_hard_pain_baseline_fast_enough`
- matched baseline runs: `9`
- best FORMTRIG first `_T`: `0.034`
- raw run root: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z`

## Primary Benefits

- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 6176.47x faster than the fastest matched successful baseline run

## FORMTRIG Guidance Capability

- unavailable; see missing optional files below

## Claim Boundary

- a matched faithful baseline reaches the trigger within the acceptable-time threshold, so this is not hard SOTA-pain evidence

## Files

- `baselines/`: baseline summaries and per-run monitor/run records.
- `formtrig/`: FORMTRIG batch summary, gate summary, and per-rep stats.
- `guidance_gap/`: baseline no-guidance analysis and per-run table.
- `live_status/`: non-final live snapshot of FORMTRIG and baseline `_R/_T` state.
- `formtrig_signal_path/`: strict path audit for calibrated frontier, typed-stage attribution, saved non-`_T`, and saved `_T` progress.
- `schedule_audit/`: baseline run-count, concurrency, and batch scheduling audit.

## Packaging Status

- copied files: `49`
- missing optional files: `28`

Missing optional files:
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/.batch_results/out/formtrig_mutation_hook.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/.batch_results/out/default/formtrig_summary.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/.batch_results/out/default/formtrig_diagnosis.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/.batch_results/out/default/formtrig_lift_feature_audit.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/.batch_results/out/default/formtrig_terminal_monitor.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/.batch_results/out/default/fuzzer_stats`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/001_TIF012/out/formtrig_mutation_hook.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/001_TIF012/out/default/formtrig_summary.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/001_TIF012/out/default/formtrig_diagnosis.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/001_TIF012/out/default/formtrig_lift_feature_audit.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/001_TIF012/out/default/formtrig_terminal_monitor.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/001_TIF012/out/default/fuzzer_stats`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/002_TIF012/out/formtrig_mutation_hook.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/002_TIF012/out/default/formtrig_summary.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/002_TIF012/out/default/formtrig_diagnosis.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/002_TIF012/out/default/formtrig_lift_feature_audit.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/002_TIF012/out/default/formtrig_terminal_monitor.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/002_TIF012/out/default/fuzzer_stats`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/003_TIF012/out/formtrig_mutation_hook.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/003_TIF012/out/default/formtrig_summary.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/003_TIF012/out/default/formtrig_diagnosis.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/003_TIF012/out/default/formtrig_lift_feature_audit.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/003_TIF012/out/default/formtrig_terminal_monitor.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig/003_TIF012/out/default/fuzzer_stats`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/live_status.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/live_status.md`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig_signal_path.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z/formtrig_signal_path.md`
