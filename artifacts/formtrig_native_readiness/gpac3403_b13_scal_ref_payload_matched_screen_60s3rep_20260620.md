# GPAC3403 B13 SCAL-Reference Payload Matched Screen, 60s x3

This run is stronger than the 5s smoke, but it is still not a final hard
SOTA-pain result because the required CmpLog/Redqueen baseline set is incomplete.

## Setup

- Raw directory:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_60s3rep_20260620T032730Z`
- Budget: `60s`
- Reps: `3`
- Seed format: `mp4-scal-ref-scaffold`
- BindingSpec: `GPAC_3403.native_b10_extractor_return_candidate.yml`
- FORMTRIG config: `typed_ops=64`, `typed_op_start=52`, `typed_schedule=op-first`
- Hook arm: `gpac_scal_ref_mp4_hook.py`

## Result

Comparison after excluding invalid baseline runs:

- verdict: `incomplete_required_baseline_set`
- main claim strength: `incomplete_matched_evidence`
- valid matched baseline runs: `5`
- missing required baseline family: `redqueen_operand`

FORMTRIG with GPAC payload hook:

| rep | first `_T` | exec | terminal count | accepted/saved non-trigger | spec lifted | endpoint replay |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 2.390s | 8 | 2 | 5/5 | 70 | 1/28 native crashes |
| 2 | 2.422s | 8 | 2 | 5/5 | 70 | 1/28 native crashes |
| 3 | 2.605s | 8 | 2 | 5/5 | 70 | 1/28 native crashes |

FORMTRIG nohook:

| rep | first `_T` | exec | terminal count | accepted/saved non-trigger | spec lifted | endpoint replay |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 29.633s | 720 | 4 | 17/17 | 1233 | 0/32 native crashes |
| 2 | 49.938s | 1801 | 1 | 14/14 | 1551 | 0/32 native crashes |
| 3 | none | none | 0 | 14/14 | 1020 | 0/32 native crashes |

Valid baseline runs:

| baseline | valid reps | invalid reps | success | execs |
| --- | ---: | ---: | ---: | --- |
| AFL++ vanilla | 3 | 0 | 0/3 | 1174, 971, 940 |
| AFL++ CmpLog | 2 | 1 | 0/2 valid | 949, 1257 |
| Redqueen/operand | 0 | 3 | not comparable | none |

The invalid CmpLog/Redqueen runs aborted early with AFL++ cmplog forkserver
signal 11. They must not be counted as normal non-triggering baseline reps.

## Claim Boundary

Supported:

- The target-specific GPAC payload hook is stable on this B13 path: `3/3` early
  endpoint `_T`, all at exec `8`.
- Nohook FORMTRIG also produces TC-rooted lifted progress and can reach `_T`, but
  in this screen it is slower and less reliable: `2/3`, first `_T` at
  `29.633s` and `49.938s`.
- Vanilla AFL++ has a clean `3/3` 60s no-trigger result on this seed/harness.
- Hook retained endpoint replay produces native crashes in all reps; nohook
  retained endpoint replay does not.

Not supported:

- hard SOTA-pain claim
- complete matched SOTA comparison
- baseline no-guidance proof
- target-independent generality

Next action: repair or rerun CmpLog/Redqueen startup failures, then repeat the
same 60s/longer screen with valid baseline reps and add baseline-visible pre-`_T`
flatness measurement.
