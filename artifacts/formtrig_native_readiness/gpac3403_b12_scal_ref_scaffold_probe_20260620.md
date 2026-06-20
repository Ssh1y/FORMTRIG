# GPAC_3403 B12 SCAL Reference Scaffold Probe

- status: `reference_scaffold_candidate_available`
- raw_dir: `artifacts/formtrig_native_readiness/raw/gpac3403_b12_scal_ref_scaffold_probe_20260620T023921Z`
- preseed_class: `reference_scaffold_candidate`
- enhanced_mode: `copy-base`

## Result

The probe builds a two-track MP4 from the original blackwhite HEVC as both base
and enhanced tracks, adds `2:scal:1`, and replays it through:

```text
/tmp/formtrig_gpac3403_src/bin/gcc/MP4Box -cat two_track_scal_ref.mp4 white.mp4 -out /dev/null
```

Replay exits cleanly:

| metric | value |
|---|---:|
| exit_code | 0 |
| native_crash | false |
| double_free_signature | false |
| no_reference_track_messages | 0 |
| corrupt_nal_messages | 0 |
| runtime_log_exists | true |

The runtime record is R-not-T and spec lifted:

| metric | value |
|---|---:|
| reached | true |
| crash_predicate | false |
| D_T | 1 |
| D_F_spec_lifted | 3 |
| uses_spec_lifted | true |
| uses_trigger_oracle | false |
| uses_target_id_specific_rule | false |
| uses_runtime_heuristic | false |

## Claim Boundary

This is a non-terminal SCAL-reference scaffold candidate for controlled resumed
GPAC experiments. It must stay separate from B11, where the enhanced track uses
the op52/sample2 payload and already triggers the double-free endpoint. Matched
baseline comparisons can only use this scaffold fairly if all arms receive the
same resumed corpus.
