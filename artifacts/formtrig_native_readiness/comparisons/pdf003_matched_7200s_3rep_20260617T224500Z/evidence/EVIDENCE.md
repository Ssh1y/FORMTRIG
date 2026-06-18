# PDF003 7200s x3 Matched Evidence Bundle

This directory contains the small, auditable evidence used by the matched
FORMTRIG-vs-baseline comparison. Full AFL++ raw queues are intentionally
left in the run directory and are not copied here.

## Comparison

- target: `PDF003`
- comparison id: `pdf003_matched_7200s_3rep_20260618T040544Z`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `hard_speedup_or_reliability_candidate`
- matched baseline runs: `9`
- best FORMTRIG first `_T`: `0.31`
- raw run root: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z`

## Primary Benefits

- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 14612.90x faster than the fastest matched successful baseline run

## FORMTRIG Guidance Capability

- signal-path verdict: `terminal_after_calibrated_frontier_only`
- typed attribution: `terminal_after_typed_lifted_nontrigger_stage`
- stable frontier runs: `3/3`
- sortable lifted `D_F` runs: `3/3`
- actionable typed non-`_T` runs: `3/3`
- mutable typed-find runs: `3/3`
- total typed finds: `1933` / typed execs `4304`
- strict saved pre-trigger runs: `0/3`
- interpretation: FORMTRIG exposed stable/sortable/actionable/mutable intermediate signals before terminal _T, but strict saved non-trigger progress was not observed

## Claim Boundary

- no strict pre-trigger guidance benefit is established

## Files

- `baselines/`: baseline summaries and per-run monitor/run records.
- `formtrig/`: FORMTRIG batch summary, gate summary, and per-rep stats.
- `guidance_gap/`: baseline no-guidance analysis and per-run table.
- `live_status/`: non-final live snapshot of FORMTRIG and baseline `_R/_T` state.
- `formtrig_signal_path/`: strict path audit for calibrated frontier, typed-stage attribution, saved non-`_T`, and saved `_T` progress.
- `schedule_audit/`: baseline run-count, concurrency, and batch scheduling audit.

## Packaging Status

- copied files: `71`
- missing optional files: `6`

Missing optional files:
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/formtrig/.batch_results/out/formtrig_mutation_hook.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/formtrig/.batch_results/out/default/formtrig_summary.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/formtrig/.batch_results/out/default/formtrig_diagnosis.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/formtrig/.batch_results/out/default/formtrig_lift_feature_audit.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/formtrig/.batch_results/out/default/formtrig_terminal_monitor.json`
- `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/formtrig/.batch_results/out/default/fuzzer_stats`
