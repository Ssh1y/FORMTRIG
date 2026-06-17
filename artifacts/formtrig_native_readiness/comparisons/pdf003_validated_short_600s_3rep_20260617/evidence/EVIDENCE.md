# PDF003 600s x3 Evidence Bundle

This directory contains the small, auditable evidence used by
`../comparison.json` and `../comparison.md`. The full AFL++ raw queues are not
included because they are large local run artifacts.

## Claim Supported

- target: `PDF003`
- budget: 600 seconds per run
- FORMTRIG: 3/3 runs reached `_T`; exact first queue-trigger upper bound is
  0.29-0.306 seconds, best 0.29 seconds.
- matched baselines: AFL++ vanilla, AFL++ CmpLog, and Redqueen operand, 3 runs
  each; all 9/9 runs had `_R` but 0 `_T` in 600 seconds.
- baseline guidance gap: `measured_pass`; monitor-visible binary `_T` feedback
  stayed flat before trigger while endpoint cost was missing in all matched
  baseline runs.

## Claim Boundary

This bundle supports a matched endpoint R2T benefit and a measured baseline
no-guidance gap for PDF003. It does not establish strict FORMTRIG pre-trigger
frontier guidance on this target, because accepted/saved non-trigger progress is
0 in the FORMTRIG gate summary.

## Files

- `baselines/summary.json` and `baselines/summary.tsv`: aggregate baseline
  results.
- `baselines/runs/*/{run_record.json,events.jsonl}`: per-run baseline monitor
  records used by the guidance-gap analysis.
- `formtrig/batch_summary.*`: FORMTRIG batch-level summary for the 3 reps.
- `formtrig/gate_summary.*` and `formtrig/gate_report.md`: FORMTRIG experiment
  gate result and first-trigger evidence.
- `formtrig/runs/*`: per-rep FORMTRIG summary, diagnosis, typed hook config,
  terminal monitor, lift-feature audit, and AFL++ fuzzer stats.
- `guidance_gap/baseline_guidance_gap.*`: baseline no-guidance analysis and
  per-run table.
