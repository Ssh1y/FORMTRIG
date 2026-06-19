# PHP003 Current-ABI Readout - 2026-06-19

This readout links the current-ABI B4 validation to the existing same-runner
600s baseline comparison.

## Current-ABI FORMTRIG Validation

- Source: `artifacts/formtrig_native_readiness/binding_validation/PHP003.native_b4_thumbnail_length_hook_candidate.current_abi.validation.json`
- Runner: `exif_thumbnail`
- AFL++ path: `experiments/magma_workspace/magma/fuzzers/formtrig_native/repo/afl-fuzz`
- Budget: 20s
- Diagnosis: `triggered`
- Terminal `_T`: 43
- Accepted/saved non-trigger progress: 2/2
- `D_F_spec_lifted`: non-constant, values `{2,3}`
- Variable semantic role: `use`

## Current-ABI 600s FORMTRIG Arm

- Source: `artifacts/formtrig_native_readiness/raw/php003_native_b4_current_abi_600s_1rep_formtrig_20260619T204624Z/batch_summary.jsonl`
- Additional reps source: `artifacts/formtrig_native_readiness/raw/php003_native_b4_current_abi_600s_reps2_3_formtrig_20260619T210244Z/batch_summary.jsonl`
- AFL++ path: `experiments/magma_workspace/magma/fuzzers/formtrig_native/repo/afl-fuzz`
- Diagnosis: `triggered`
- First `_T`: 7.595s exact AFL++ queue time
- First `_T` queue file: `id:000083,src:000000,time:7595,execs:1815,op:havoc,rep:1,+cov`
- First `_T` monitor upper bound: 60s
- Terminal `_T`: 70678
- Accepted/saved non-trigger progress: 2/2
- Saved triggered progress: 7855
- `D_F_spec_lifted`: non-constant, values `{2,3}`
- Typed execs/finds: 242/44
- Stability failures: 0

### Current-ABI FORMTRIG 600s Replication

The FORMTRIG side is now 3/3 successful under the current AFL++ ABI. All three
runs preserve TC-rooted non-trigger progress before `_T` and use spec-driven
lift only (`D_F_spec_lifted` values `{2,3}`).

| Rep | First non-trigger progress | First `_T` exact queue time | Terminal `_T` | Saved non-trigger progress | Typed execs/finds | Stability failures |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 |  | 7.595s | 70678 | 2 | 242/44 | 0 |
| 2 | 1.880s | 1.942s | 37429 | 2 | 471/103 | 1 |
| 3 | 1.868s | 1.929s | 62258 | 2 | 360/70 | 0 |

Aggregate:

- Success rate: 3/3
- First `_T` exact queue time: min 1.929s, median 1.942s, max 7.595s
- Median exact first `_T` speedup over the fastest successful 1-rep baseline
  reference (AFL++ vanilla at 180s): 92.69x
- Slowest exact first `_T` speedup over the same baseline reference: 23.70x
- Total terminal `_T`: 170365
- Total saved non-trigger progress: 6
- Total spec-lifted events: 46382

## Existing 600s Same-Runner Comparison

- Source: `artifacts/formtrig_native_readiness/comparisons/php003_native_b4_same_runner_600s_1rep_20260618/comparison.json`
- Verdict: `speedup_but_under_replicated`
- FORMTRIG first `_T`: 1.985s
- FORMTRIG terminal `_T`: 21024
- Fastest successful baseline: AFL++ vanilla at 180s
- TTE speedup over fastest successful baseline: 90.68x
- Current-ABI FORMTRIG first `_T` speedup over fastest successful baseline: 23.70x by exact queue time, or 3.00x by monitor upper bound

| Arm | Budget | Success | First `_T` | Terminal `_T` |
| --- | ---: | --- | ---: | ---: |
| FORMTRIG old standalone AFL++ | 600s | true | 1.985s | 21024 |
| FORMTRIG current ABI AFL++ rep1 | 600s | true | 7.595s | 70678 |
| FORMTRIG current ABI AFL++ rep2 | 600s | true | 1.942s | 37429 |
| FORMTRIG current ABI AFL++ rep3 | 600s | true | 1.929s | 62258 |
| AFL++ CmpLog | 600s | false |  | 0 |
| AFL++ vanilla | 600s | true | 180s | 31 |
| Redqueen/operand | 600s | true | 330s | 11 |

## Claim Boundary

PHP003 is now a same-runner speedup/control candidate, not an unresolved
baseline-missing case. It still is not hard SOTA-pain evidence: the baseline
guidance-gap gate is `fail_fast_baseline` because AFL++ vanilla reaches `_T`
within the acceptable 600s threshold, even though baseline-visible pre-trigger
binary feedback is flat.

The original 600s FORMTRIG arm used the older standalone AFL++ checkout. The
2026-06-19 current-ABI 600s arms remove that ABI doubt for the FORMTRIG side:
they reach terminal `_T` in 3/3 runs and preserve accepted non-trigger lift
guidance before `_T`. Before using PHP003 as a final matched performance
result, collect reps 2-3 for each matched baseline family and assemble a
refreshed comparison package around the current-ABI FORMTRIG runs.
