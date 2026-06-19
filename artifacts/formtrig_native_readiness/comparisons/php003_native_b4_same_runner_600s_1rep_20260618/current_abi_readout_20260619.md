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

## Existing 600s Same-Runner Comparison

- Source: `artifacts/formtrig_native_readiness/comparisons/php003_native_b4_same_runner_600s_1rep_20260618/comparison.json`
- Verdict: `speedup_but_under_replicated`
- FORMTRIG first `_T`: 1.985s
- FORMTRIG terminal `_T`: 21024
- Fastest successful baseline: AFL++ vanilla at 180s
- TTE speedup over fastest successful baseline: 90.68x

| Arm | Budget | Success | First `_T` | Terminal `_T` |
| --- | ---: | --- | ---: | ---: |
| FORMTRIG | 600s | true | 1.985s | 21024 |
| AFL++ CmpLog | 600s | false |  | 0 |
| AFL++ vanilla | 600s | true | 180s | 31 |
| Redqueen/operand | 600s | true | 330s | 11 |

## Claim Boundary

PHP003 is now a same-runner speedup/control candidate, not an unresolved
baseline-missing case. It still is not hard SOTA-pain evidence: the baseline
guidance-gap gate is `fail_fast_baseline` because AFL++ vanilla reaches `_T`
within the acceptable 600s threshold, even though baseline-visible pre-trigger
binary feedback is flat.

The existing 600s FORMTRIG arm used the older standalone AFL++ checkout. The
2026-06-19 current-ABI 20s validation confirms the same B4 repaired-runner path
still reaches terminal `_T` with accepted non-trigger lift guidance. Before
using PHP003 as a final performance result, rerun the 600s FORMTRIG arm with
the ABI-current AFL++ path and collect at least 3 repetitions for each matched
baseline family.
