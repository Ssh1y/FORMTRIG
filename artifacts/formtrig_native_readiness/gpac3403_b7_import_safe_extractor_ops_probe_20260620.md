# GPAC_3403 B7 Import-Safe Extractor Ops Probe - 2026-06-20

Raw probe:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_import_safe_extractor_ops_probe_20260620T001443Z`

This probe validates four new bounded HEVC typed ops, `48..51`, before spending
another full B7 gate. The ops combine the import-safe output-layer-set train
with a small number of type49 extractor NALUs and VCL units.

## Result

```text
variants = 16
structural type49 variants = 16 / 16
Track Importing HEVC = 16 / 16
HEVC Import results = 16 / 16
HEVC L-HEVC Import results = 12 / 16
NAL Unit type 49 not handled = 12 / 16
ASAN double-free = 0 / 16
Wrong output layer sets = 16 / 16
layers-only-4 = 2 / 16
```

This repairs one concrete gap from the previous full B7 `df-structure` gate:
selected variants already contained structural type49 NALUs, but endpoint logs
never reached `NAL Unit type 49 not handled`. The new ops are bounded and keep
the input recognizable as importable HEVC while introducing extractor behavior.

Claim boundary: this is a direct endpoint probe, not a full FORMTRIG gate and
not endpoint closure. The next required evidence is a full B7 typedops52 gate
showing the new ops appear in retained candidates and improve endpoint
signatures under the standard fuzzing loop. ASAN/double-free is still 0.
