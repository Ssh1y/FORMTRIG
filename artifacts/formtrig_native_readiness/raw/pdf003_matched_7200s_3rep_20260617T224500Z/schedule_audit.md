# Magma Matched Schedule Audit

- analysis: `2026-06-18T04:05:44Z`
- target: `PDF003`
- verdict: `multi_batch_baseline_schedule`
- claim boundary: schedule audit only explains expected wall-clock shape; endpoint and guidance claims still require gate, guidance-gap, comparison, and evidence

| metric | value |
| --- | ---: |
| reps | 3 |
| baselines | 3 |
| baseline runs | 9 |
| FORMTRIG jobs | 3 |
| baseline jobs | 3 |
| baseline batches | 3 |
| longest duration s | 7200 |
| total baseline budget s | 64800 |
| ideal baseline wall s | 21600 |
| one-batch baseline jobs | 9 |

## Scheduling Note

Baseline wall-clock is expected to expand because the baseline run count exceeds `baseline_jobs`. For a 3 baseline x 3 rep matched run, use `--baseline-jobs 9` when the machine can support that concurrency.
