# FORMTRIG Signal Path: PDF003

- analysis: `2026-06-18T04:05:46Z`
- verdict: `terminal_after_calibrated_frontier_only`
- typed attribution: `terminal_after_typed_lifted_nontrigger_stage`
- claim boundary: calibrated_frontier is reported for diagnosis only; strict gate still requires saved non-trigger progress before terminal _T; typed-stage attribution explains mutation activity but does not upgrade the strict gate

## Guidance Capability

- stable frontier runs: `3/3`
- sortable lifted D_F runs: `3/3`
- actionable typed non-T runs: `3/3`
- mutable typed-find runs: `3/3`
- total typed finds: `1933` / typed execs `4304`
- strict saved pre-trigger runs: `0/3`
- interpretation: FORMTRIG exposed stable/sortable/actionable/mutable intermediate signals before terminal _T, but strict saved non-trigger progress was not observed

## Runs

| run | time | execs | calibrated non-T | saved non-T | saved T | first non-T exec | first T exec | typed starts | typed before T | typed lifted non-T before T | typed finds | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| 001_PDF003 | 7200 | 33540 | 3 | 0 | 858 |  | 86 | 10 | yes | yes | 568 | terminal_after_calibrated_frontier |
| 002_PDF003 | 7200 | 33841 | 3 | 0 | 806 |  | 86 | 14 | yes | yes | 795 | terminal_after_calibrated_frontier |
| 003_PDF003 | 7201 | 29732 | 3 | 0 | 736 |  | 86 | 10 | yes | yes | 570 | terminal_after_calibrated_frontier |

## Per-Run First Signals

### 001_PDF003
- first calibrated non-T: exec `7`, D_F `1`, spec D_F `1`, reason `initial_frontier_seed`
- first typed stage: exec `78`, D_F `1`, spec D_F `1`, reason `planned`
- first typed lifted non-T before T: exec `78`, D_F `1`, spec D_F `1`, reason `planned`
- first saved non-T: none
- first saved T: exec `86`, D_F `2`, spec D_F `2`, reason `triggered`
- preterminal non-T D_F values: `[1, 3, 2]`

### 002_PDF003
- first calibrated non-T: exec `7`, D_F `1`, spec D_F `1`, reason `initial_frontier_seed`
- first typed stage: exec `78`, D_F `1`, spec D_F `1`, reason `planned`
- first typed lifted non-T before T: exec `78`, D_F `1`, spec D_F `1`, reason `planned`
- first saved non-T: none
- first saved T: exec `86`, D_F `2`, spec D_F `2`, reason `triggered`
- preterminal non-T D_F values: `[1, 3, 2]`

### 003_PDF003
- first calibrated non-T: exec `7`, D_F `1`, spec D_F `1`, reason `initial_frontier_seed`
- first typed stage: exec `78`, D_F `1`, spec D_F `1`, reason `planned`
- first typed lifted non-T before T: exec `78`, D_F `1`, spec D_F `1`, reason `planned`
- first saved non-T: none
- first saved T: exec `86`, D_F `2`, spec D_F `2`, reason `triggered`
- preterminal non-T D_F values: `[1, 3, 2]`
