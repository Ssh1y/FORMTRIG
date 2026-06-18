# Live Matched Status: PDF003

- snapshot: `2026-06-18T02:09:16Z`
- run root: `artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z`
- baseline roots: `artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/baselines, artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard_7200s_20260618T014149Z`
- boundary: live_snapshot_only; final claims require formtrig_gate, baseline_guidance_gap, comparison, and evidence packaging

## Schedule

| verdict | expected baseline runs | observed baseline runs | missing | baseline jobs | batches | one-batch jobs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_batch_baseline_schedule | 9 | 9 | 0 | 3 | 3 | 9 |

## FORMTRIG

| run | time | execs | reached | triggered execs | saved T | saved non-T | frontier | typed finds | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 001_PDF003 | 7200 | 33540 | 13492 | 7693 | 858 | 0 | 3 | 568 | terminal_seen |
| 002_PDF003 | 7200 | 33841 | 18868 | 7246 | 806 | 0 | 3 | 795 | terminal_seen |
| 003_PDF003 | 7201 | 29732 | 14680 | 6607 | 736 | 0 | 3 | 570 | terminal_seen |

## Baselines

| baseline | runs | triggered runs | total R | total T | R without T | empirical T/R | zero-T 95% ub |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 3 | 0 | 1124010 | 0 | 1124010 | 0 | 2.66902e-06 |
| aflplusplus_vanilla | 3 | 0 | 441564 | 0 | 441564 | 0 | 6.79403e-06 |
| redqueen_operand | 3 | 1 | 973746 | 18 | 973728 | 1.84853e-05 |  |

The zero-T upper bound is a descriptive rule-of-three proxy for matched live runs with reached executions but no trigger events; it is not a proof that baseline mutations are independent.

## Baseline Runs

| run | time | execs | first R | latest monitor | R | T |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog_7200s_rep1 | 7175 | 1373920 | 90 |  | 548533 | 0 |
| aflplusplus_cmplog_7200s_rep2 | 5002 | 1122220 | 90 | 5100 | 474684 | 0 |
| aflplusplus_vanilla_7200s_rep1 | 7175 | 487282 | 90 |  | 253025 | 0 |
| aflplusplus_vanilla_7200s_rep2 | 4995 | 83847 | 90 | 5100 | 19923 | 0 |
| redqueen_operand_7200s_rep1 | 7176 | 1650085 | 90 |  | 654054 | 0 |
| redqueen_operand_7200s_rep2 | 5018 | 979183 | 90 | 5100 | 212464 | 18 |
| aflplusplus_cmplog_7200s_rep3 | 1578 | 401894 | 90 | 1650 | 100793 | 0 |
| aflplusplus_vanilla_7200s_rep3 | 1593 | 188550 | 90 | 1650 | 168616 | 0 |
| redqueen_operand_7200s_rep3 | 1588 | 405167 | 90 | 1650 | 107228 | 0 |
