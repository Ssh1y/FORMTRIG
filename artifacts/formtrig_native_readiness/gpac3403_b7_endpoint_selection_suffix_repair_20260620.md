# GPAC_3403 B7 Endpoint Selection and Suffix Repair - 2026-06-20

Source full gate:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_typedops52_20260620T002044Z`

Replay-only repair validation:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_typedops52_df_structure_op_diverse_hevc_replay_20260620T004004Z`

## Repair

Two endpoint-validation issues were fixed:

```text
selection = df-structure-op-diverse
  preserve D_F bucket priority
  within each D_F bucket, first cover retained operator ids
  then fill remaining budget by HEVC structure score

endpoint variant suffix = .hevc
  stage retained variants with HEVC extension before replay
  avoid GPAC routing valid HEVC candidates to Filter not found because they were named .bin
```

## Replay-Only Result

Using the same retained candidates from the failed typedops52 full gate:

```text
selected records = 128
D_F selected = 55 at D_F=2, 73 at D_F=5
selected op48/op49/op51 = 1 / 1 / 1
Track Importing HEVC = 124 / 128
HEVC Import results = 128 / 128
HEVC L-HEVC Import results = 71 / 128
NAL Unit type 49 not handled = 59 / 128
Filter not found = 0 / 128
ASAN double-free = 0 / 128
positive-control native crash = 1
```

Compared with the source full gate endpoint replay:

```text
selected op48/op49/op51: 0/0/0 -> 1/1/1
HEVC import files: 55 -> 128
L-HEVC import files: 10 -> 71
NAL Unit type 49 not handled: 0 -> 59
Filter not found: 73 -> 0
ASAN double-free: 0 -> 0
```

This is a real engineering repair: the endpoint replay now validates the type49
behavior that the direct op48..51 probe previously showed. It is still not
endpoint closure. The next full B7 gate must show this repair inside the
standard FORMTRIG loop and still needs to reach ASAN/double-free or equivalent
cleanup alias/free closure.
