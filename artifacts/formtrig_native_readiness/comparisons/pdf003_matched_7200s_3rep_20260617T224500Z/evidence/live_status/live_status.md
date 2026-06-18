# Live Matched Status: PDF003

- snapshot: `2026-06-18T04:05:46Z`
- run root: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z`
- baseline roots: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/merged_baselines`
- boundary: live_snapshot_only; final claims require formtrig_gate, baseline_guidance_gap, comparison, and evidence packaging

## Schedule

| verdict | expected baseline runs | observed baseline runs | missing | baseline jobs | batches | one-batch jobs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_batch_baseline_schedule | 9 | 0 | 9 | 3 | 3 | 9 |

## FORMTRIG

| run | time | execs | reached | triggered execs | saved T | saved non-T | frontier | typed finds | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 001_PDF003 | 7200 | 33540 | 13492 | 7693 | 858 | 0 | 3 | 568 | terminal_seen |
| 002_PDF003 | 7200 | 33841 | 18868 | 7246 | 806 | 0 | 3 | 795 | terminal_seen |
| 003_PDF003 | 7201 | 29732 | 14680 | 6607 | 736 | 0 | 3 | 570 | terminal_seen |

## Baselines

| baseline | runs | triggered runs | total R | total T | R without T | empirical T/R | zero-T 95% ub |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

The zero-T upper bound is a descriptive rule-of-three proxy for matched live runs with reached executions but no trigger events; it is not a proof that baseline mutations are independent.

## Baseline Runs

| run | time | execs | first R | latest monitor | R | T |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
