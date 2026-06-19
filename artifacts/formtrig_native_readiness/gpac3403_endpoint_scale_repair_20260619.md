# GPAC_3403 Endpoint-Scale Repair - 2026-06-19

This is repair evidence, not endpoint success evidence.

## Result

- Operator window: `op44-op47`
- Variants replayed: 16
- Reached variants: 12
- Terminal / ASAN double-free variants: 0 / 0
- Variant HEVC import max: 221 samples / 550 NALUs
- Positive-control HEVC import: 172 samples / 413 NALUs
- L-HEVC import files: 16 / 16
- Positive-control signatures still absent from variants: `asan, asan_double_free`

## Interpretation

The previous GPAC blocker included a format-scale gap: retained variants imported only 2 samples / 15 NALUs while the positive control imported 172 samples / 413 NALUs. The endpoint-scale typed operators repair that part of the gap: the best variant now imports 221 samples / 550 NALUs and the signature audit matches all positive-control parser/import signatures except ASAN and ASAN double-free.

The remaining GPAC blocker is therefore narrower: prove or create the sample-data to GF_BitStream->original alias/free terminal relation. Do not promote GPAC_3403 to matched 2h baseline long-run until endpoint ASAN/double-free or equivalent lifecycle-alias proof appears.

## Evidence

- `artifacts/formtrig_native_readiness/raw/gpac3403_op44_47_endpoint_scale_sweep_20260619T224231Z/summary.json`
- `artifacts/formtrig_native_readiness/raw/gpac3403_op44_47_endpoint_scale_sweep_20260619T224231Z/endpoint_signature_audit.json`
