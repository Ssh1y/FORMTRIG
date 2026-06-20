# GPAC_3403 B7 typedops52 Selection Gap - 2026-06-20

Raw full gate:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_typedops52_20260620T002044Z`

The 600s FORMTRIG-only gate passed strict pre-trigger guidance but did not
reach endpoint `_T`.

```text
execs_done = 2846
reached_execs = 2846
terminal_triggered_execs = 0
queued_progress = 22
accepted_non_trigger = 22
saved_non_trigger = 22
spec_lifted_events = 1941
D_F_spec_lifted = 2..5
```

The important diagnostic is that the new import-safe extractor ops were
retained but not replayed:

```text
retained records = 221
D_F distribution = 55 at D_F=2, 166 at D_F=5
retained op48/op49/op51 = 5 / 5 / 5
selected op48/op49/op51 = 0 / 0 / 0
selection = df-structure
selected records = 128
```

Endpoint replay therefore stayed short of the direct-probe behavior:

```text
Track Importing HEVC = 55 / 128
HEVC Import results = 55 / 128
HEVC L-HEVC Import results = 10 / 128
NAL Unit type 49 not handled = 0 / 128
Filter not found = 73 / 128
ASAN double-free = 0 / 128
positive-control native crash = 1
```

Diagnosis: this gate did not fail because FORMTRIG lacked retained candidates.
It failed because endpoint validation used a `D_F`-first selector that starved
op48/op49/op51, and replayed retained HEVC variants through `.bin` paths that
can send GPAC to `Filter not found` before the HEVC importer.

Claim boundary: this is a useful negative diagnostic and a strict pre-trigger
guidance pass, not endpoint closure. Do not run matched baselines for GPAC_3403
until endpoint replay selection and HEVC importer routing are repaired.
