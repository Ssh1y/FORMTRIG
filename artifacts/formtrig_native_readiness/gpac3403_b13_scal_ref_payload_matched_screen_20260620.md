# GPAC3403 B13 SCAL-Reference Payload Matched Screen

This is a 5s, 1-rep matched smoke for the B13 GPAC_3403 path. It is useful
as endpoint-readiness and repair evidence, not as final hard SOTA-pain proof.

## Setup

- Raw directory:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z`
- Seed format: `mp4-scal-ref-scaffold`
- BindingSpec: `GPAC_3403.native_b10_extractor_return_candidate.yml`
- FORMTRIG typed config: `typed_ops=64`, `typed_op_start=52`, `typed_schedule=op-first`
- Mutation path: `gpac_scal_ref_mp4_hook.py` over the enhanced HEVC payload, then MP4Box endpoint replay
- Arms: `formtrig`, `formtrig_nohook`, `aflplusplus_vanilla`, `aflplusplus_cmplog`, `redqueen_operand`

## Benefit Readout

Tool-generated comparison after planned-budget normalization and invalid-run
filtering:

- verdict: `incomplete_required_baseline_set`
- main claim strength: `incomplete_matched_evidence`
- valid matched baseline runs: `2`
- missing required baseline family: `aflplusplus_vanilla`

FORMTRIG with the GPAC payload hook:

- budget: `5s` planned, `12s` recorded runtime
- terminal `_T`: `1`
- first `_T`: `2.369s`, crash filename exact, exec `8`
- total execs: `32`
- reached: `32`
- accepted/saved non-trigger: `3/3`
- spec-lifted events: `11`
- endpoint replay: `1/4` retained variants crashes natively, exit `-6`
- positive control: `1/1` native crash

FORMTRIG nohook ablation:

- budget: `5s` planned, `6s` recorded runtime
- terminal `_T`: `0`
- accepted/saved non-trigger: `2/2`
- spec-lifted events: `22`
- endpoint replay: `0/8` retained variants crash
- positive control: `1/1` native crash

Baselines:

| arm | budget | success | execs | note |
| --- | ---: | --- | ---: | --- |
| AFL++ vanilla | 5s | invalid | 0 | startup/preflight failure; not counted as a baseline no-trigger rep |
| AFL++ CmpLog | 5s | false | 127 | no endpoint crash |
| Redqueen/operand | 5s | false | 127 | no endpoint crash |

## Claim Boundary

Supported:

- The B13 target-specific GPAC payload hook closes the B12 SCAL-reference
  scaffold gap and reaches a real endpoint double-free signal.
- FORMTRIG records strict pre-trigger lifted guidance before endpoint success.
- Nohook retains lifted non-trigger progress but does not replay to endpoint
  `_T` in this smoke.
- CmpLog and Redqueen/operand valid reps do not trigger in the same planned 5s
  smoke.

Not supported yet:

- complete required baseline set
- final hard SOTA-pain claim
- baseline no-guidance proof
- repeated-run success-rate or TTE statistics
- target-independent FORMTRIG generality

Next required step: repeat this screen with more repetitions and longer budgets,
then add baseline-visible pre-`_T` flatness/high-variance evidence plus nohook and
generic-hook ablations before using GPAC3403 as a paper-level hard-target claim.
