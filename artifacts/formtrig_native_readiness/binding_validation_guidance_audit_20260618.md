# Binding Validation Guidance Audit

Generated UTC: 2026-06-18T17:03:15+00:00

This audit separates native BindingSpec validity from evidence that FORMTRIG produced accepted pre-trigger frontier guidance.

## Summary

| disposition | targets |
|---|---:|
| `mechanism_and_endpoint_candidate` | 3 |
| `mechanism_only_needs_endpoint` | 1 |
| `native_binding_validated_no_guidance_readout` | 1 |
| `soft_signal_needs_frontier_evidence` | 1 |
| `terminal_only_control` | 3 |

## Target Triage

| target | disposition | TC-rooted static | strict pre-trigger | terminal | accepted non-trigger | next action |
|---|---|---|---:|---:|---:|---|
| PDF016 | `mechanism_and_endpoint_candidate` | `pass` | true | true | 4 | run matched baselines and baseline-guidance-gap analysis; promote only if baselines are late, missing, or high variance |
| PHP003 | `mechanism_and_endpoint_candidate` | `pass` | true | true | 1 | run matched baselines and baseline-guidance-gap analysis; promote only if baselines are late, missing, or high variance |
| PHP009 | `mechanism_and_endpoint_candidate` | `pass` | true | true | 2 | run matched baselines and baseline-guidance-gap analysis; promote only if baselines are late, missing, or high variance |
| TIF012 | `mechanism_only_needs_endpoint` | `pass` | true | false | 1 | run endpoint short screen against faithful AFL++ family baselines |
| PDF003 | `soft_signal_needs_frontier_evidence` | `pass` | false | false | 0 | collect accepted non-trigger frontier progress or a replayable signal path before efficacy claims |
| LIBARCHIVE_2936 | `native_binding_validated_no_guidance_readout` | `pass` | false | false | 0 | run or regenerate binding-signal diagnosis with benefit readout before endpoint spending |
| PNG007 | `terminal_only_control` | `pass` | false | true | 0 | keep as control or revise BindingSpec/seed distance; do not claim R-to-T guidance benefit |
| SSL011 | `terminal_only_control` | `pass` | false | true | 0 | keep as control or revise BindingSpec/seed distance; do not claim R-to-T guidance benefit |
| SSL015 | `terminal_only_control` | `pass` | false | true | 0 | keep as control or revise BindingSpec/seed distance; do not claim R-to-T guidance benefit |

## Claim Boundary

- `terminal_only_control` means `_T` appeared without accepted non-trigger guidance; it must not be used as R-to-T guidance evidence.
- `soft_signal_needs_frontier_evidence` means lifted signal moved before `_T`, but the current artifact lacks accepted/saved non-trigger frontier progress.
- `static_binding_not_tc_rooted` means dynamic movement exists only after the BindingSpec failed the static TC-rooted role gate.
- `mechanism_*` targets are candidates for matched baseline experiments, not final efficacy claims by themselves.
