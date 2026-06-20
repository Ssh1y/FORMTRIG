# GPAC_3403 B7 Sample-Preserving PoC-Shape Probe

- Raw dir: `artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z`
- Reached/spec-lifted/triggered: `9/9/0`
- D_F_spec_lifted range: `2.0` to `2.0`
- Endpoint probes: `16`; sanitizer/native crashes: `0/0`

## Repair effect versus previous op52-55

- Previous op52-55 HEVC import files: `8`; max samples: `0`; L-HEVC files: `0`
- New sample-preserving op52-55 HEVC import files: `16`; max samples: `223`; L-HEVC files: `16`
- Previous missing positive signatures: `['nal_type_49_not_handled', 'track_importing_hevc', 'lhevc_import_results', 'asan_double_free']`
- New missing positive signatures: `['asan_double_free']`

## Alias Gap

- Previous alias verdict: `no_alias_relation_progress`
- New alias verdict: `stable_nonzero_cleanup_offset`
- Interpretation: Release and reassign-buffer pointers match, but cleanup consistently frees a different dynamic bitstream buffer. This narrows the blocker to lifecycle ownership closure, not HEVC importer routing or retained-candidate selection.

## Claim Boundary

The sample-preserving PoC-shape operators repair the previous 0-sample import failure and recover HEVC/L-HEVC/type49/layer-pressure endpoint behavior, but this is still a repair probe rather than terminal success: no ASAN/double-free endpoint crash was observed, and the remaining gap is lifecycle ownership closure between release/reassign and final cleanup.

Next action: Bias the next GPAC typed mutation or BindingSpec correlation toward the post-reassign pre-get_content error path so the final GF_BitStream cleanup frees the same sample buffer observed in release/reassign.
