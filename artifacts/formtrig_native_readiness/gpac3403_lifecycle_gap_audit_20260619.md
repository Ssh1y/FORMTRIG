# GPAC_3403 Lifecycle Gap Audit - 2026-06-19

This is a diagnostic artifact, not endpoint success evidence.

Source run:

```text
artifacts/formtrig_native_readiness/raw/gpac3403_op24_samplefirst_hook_retain_smoke_30s_20260619T184146Z
```

Machine-readable audit:

```text
artifacts/formtrig_native_readiness/gpac3403_lifecycle_gap_audit_20260619.json
```

## Verdict

```text
status = parser_proximity_without_alias_terminal
primary_gap = same_object_relation_semantics_missing
parser_proximity_observed = true
terminal_observed_in_variants = false
same_object_relation_declared = true
same_object_signal_observed = true
same_object_signal_sparse = true
same_object_relation_runtime_proof = false
```

Interpretation: FORMTRIG typed mutation reaches GPAC HEVC/L-HEVC parser
neighborhoods, but current runtime evidence does not prove the same
`GF_ISOSample.data` pointer is later freed through `GF_BitStream->original`.
The remaining gap is actuation and lifecycle-alias construction, not absence of
all TC-rooted guidance.

## Endpoint Contrast

```text
retained candidates = 27
endpoint replayed variants = 24
variant ASAN/double-free files = 0
positive-control ASAN/double-free files = 1

top variant:
  matched positive signatures = 7
  HEVC import = 2 samples / 15 NALUs
  L-HEVC import = 0 I / 0 P / 1 B

positive control:
  HEVC import max = 172 samples / 413 NALUs
  L-HEVC import present
  ASAN double-free present
```

The top retained variants match parser-frontier signatures such as VPS
extension failure, NAL type 32 parsing, HEVC import, and L-HEVC import. They
still miss `layers_only_4`, `vps_max_layer_id`, `nal_type_49_not_handled`,
`asan`, and `asan_double_free`.

## Next Action

Do not spend the scarce 7200s x3 budget blindly while disk is nearly full and
the current GPAC path is still short of endpoint closure. The next engineering
step should add or tune relation-aware HEVC/lifecycle mutation:

```text
1. preserve multi-NAL VPS/SPS/PPS/slice references at PoC-like scale;
2. bias scheduling toward high-sample L-HEVC/access-unit candidates;
3. bind and score sample->data allocation/release against GF_BitStream->original cleanup;
4. require endpoint replay to move beyond the current 2-sample/15-NALU frontier before 2h x3.
```
