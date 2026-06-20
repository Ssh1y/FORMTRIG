# GPAC_3403 B7 Relation Endpoint Gate With df-structure - 2026-06-19

Raw run:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_dfstructure_20260619T234925Z`

Runner:
`scripts/run_gpac3403_b7_relation_endpoint_gate.sh`

BindingSpec:
`artifacts/binding_specs/GPAC_3403.native_b7_relation_value_candidate.yml`

## Result

The 601s FORMTRIG-only B7 gate passed strict pre-trigger guidance with the new
`df-structure` endpoint-selection policy, but did not reach terminal endpoint
behavior.

```text
execs_done = 2902
reached_execs = 2903
terminal_triggered_execs = 0
queued_progress = 41
accepted_non_trigger = 41
saved_non_trigger = 41
typed_execs = 224
typed_finds = 38
spec_lifted_events = 1701
D_F_spec_lifted = 2..5
```

## Endpoint Replay

The full gate replayed 128 typed-retained variants selected by `df-structure`.
This confirms the offline selection repair inside the real gate:

```text
selection = df-structure
structure_profiled_records = 128
structure_score = 309..22012
variant HEVC import files = 60 / 128
variant max HEVC import scale = 8 samples / 26 NALUs
variant L-HEVC import files = 11 / 128
variant ASAN double-free files = 0

positive control max HEVC import scale = 172 samples / 413 NALUs
positive control L-HEVC slices = 30 I / 2 P / 87 B
positive control ASAN double-free files = 1
missing positive-control signatures = nal_type_49_not_handled, asan_double_free
```

Compared with the earlier op-diverse B7 gate, saved non-trigger progress
increased from 35 to 41, HEVC import files increased from 38 to 60, and L-HEVC
import files increased from 6 to 11. Terminal endpoint behavior did not improve.

## Alias Relation

The alias/free verdict remains:

```text
alias verdict = release_reassign_alias_observed_terminal_cleanup_missing
release value = 104535513085104
same_object value = 104535513085104
cleanup value = 104535513056720
release=same_object = yes
release=cleanup = no
same_object=cleanup = no
```

Claim boundary: this is a positive retained-selection repair and a stronger
mechanism baseline for GPAC_3403, not endpoint closure. Do not run matched
baselines or claim real-CVE endpoint benefit until the B7 gate reaches
ASAN/double-free or proves equivalent cleanup alias/free closure.
