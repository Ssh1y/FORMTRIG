# GPAC_3403 B7 Endpoint Gate With op-diverse `.hevc` Replay - 2026-06-20

Raw run:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_opdiverse_hevc_20260620T004121Z`

Runner:
`scripts/run_gpac3403_b7_relation_endpoint_gate.sh`

BindingSpec:
`artifacts/binding_specs/GPAC_3403.native_b7_relation_value_candidate.yml`

## Result

The 600s FORMTRIG-only B7 gate passed strict pre-trigger guidance and carried
the repaired endpoint replay policy into the standard gate. It still did not
reach terminal endpoint behavior.

```text
execs_done = 2892
reached_execs = 2893
terminal_triggered_execs = 0
queued_progress = 22
accepted_non_trigger = 22
saved_non_trigger = 22
spec_lifted_events = 1922
D_F_spec_lifted = 2..5
```

## Endpoint Replay

The gate replayed 128 retained variants with:

```text
selection = df-structure-op-diverse
endpoint variant suffix = .hevc
selected op48/op49/op51 = 1 / 1 / 1
selected D_F = 55 at D_F=2, 73 at D_F=5
```

This repairs both endpoint-validation gaps from the previous typedops52 full
gate:

```text
Track Importing HEVC = 124 / 128
HEVC Import results = 128 / 128
HEVC L-HEVC Import results = 71 / 128
NAL Unit type 49 not handled = 59 / 128
Filter not found = 0 / 128
ASAN double-free = 0 / 128

positive-control native crash = 1
positive-control ASAN double-free signature = 1 file
missing positive-control signature from variants = asan_double_free
```

Compared with the source typedops52 full gate:

```text
selected op48/op49/op51: 0/0/0 -> 1/1/1
HEVC import files: 55 -> 128
L-HEVC import files: 10 -> 71
NAL Unit type 49 not handled: 0 -> 59
Filter not found: 73 -> 0
ASAN double-free: 0 -> 0
```

## Alias Relation

The alias/free verdict remains the blocker:

```text
alias verdict = release_reassign_alias_observed_terminal_cleanup_missing
release value = 94534924543152
same_object value = 94534924543152
cleanup value = 94534924514768
release=same_object = yes
release=cleanup = no
same_object=cleanup = no
complete alias/free records = 0
```

Interpretation: endpoint selection and HEVC importer routing are now repaired
inside the real gate. GPAC_3403 is closer to the positive-control endpoint
behavior, but not closed. The next repair should target cleanup
GF_BitStream->original ownership/free aliasing; matched baselines are still
premature for GPAC_3403.
