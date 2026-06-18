# Live Matched Status: PDF003

- snapshot: `2026-06-18T00:47:47Z`
- run root: `artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z`
- boundary: live_snapshot_only; final claims require formtrig_gate, baseline_guidance_gap, comparison, and evidence packaging

## Schedule

| verdict | expected baseline runs | observed baseline runs | missing | baseline jobs | batches | one-batch jobs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_batch_baseline_schedule | 9 | 6 | 3 | 3 | 3 | 9 |

## FORMTRIG

| run | time | execs | reached | triggered execs | saved T | saved non-T | frontier | typed finds | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 001_PDF003 | 7200 | 33540 | 13492 | 7693 | 858 | 0 | 3 | 568 | terminal_seen |
| 002_PDF003 | 7200 | 33841 | 18868 | 7246 | 806 | 0 | 3 | 795 | terminal_seen |
| 003_PDF003 | 7201 | 29732 | 14680 | 6607 | 736 | 0 | 3 | 570 | terminal_seen |

## Baselines

| baseline | runs | triggered runs | total R | total T | R without T | empirical T/R | zero-T 95% ub |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 2 | 0 | 576978 | 0 | 576978 | 0 | 5.19951e-06 |
| aflplusplus_vanilla | 2 | 0 | 255624 | 0 | 255624 | 0 | 1.1736e-05 |
| redqueen_operand | 2 | 0 | 663594 | 0 | 663594 | 0 | 4.52084e-06 |

The zero-T upper bound is a descriptive rule-of-three proxy for matched live runs with reached executions but no trigger events; it is not a proof that baseline mutations are independent.

## Baseline Runs

| run | time | execs | first R | latest monitor | R | T |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog_7200s_rep1 | 7175 | 1373920 | 90 |  | 548533 | 0 |
| aflplusplus_cmplog_7200s_rep2 | 122 | 14001 | 90 | 210 | 28445 | 0 |
| aflplusplus_vanilla_7200s_rep1 | 7175 | 487282 | 90 |  | 253025 | 0 |
| aflplusplus_vanilla_7200s_rep2 | 121 | 8883 | 90 | 210 | 2599 | 0 |
| redqueen_operand_7200s_rep1 | 7176 | 1650085 | 90 |  | 654054 | 0 |
| redqueen_operand_7200s_rep2 | 123 | 11486 | 90 | 210 | 9540 | 0 |
