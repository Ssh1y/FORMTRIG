# GPAC_3403 B11 SCAL Reference Preseed Probe

## Verdict

- status: `reference_relation_closes_gpac3403_r2t_endpoint_gap`
- summary: B10 showed the typed HEVC path entering process_extractor but stopping at the no-reference-track return site. B11 constructs a two-track MP4 preseed from the same typed op52/sample2 HEVC mutation, adds an explicit track-2 -> track-1 SCAL reference, and replays it through the GPAC -cat endpoint. The replay aborts with SIGABRT/subprocess return -6 and stderr contains the glibc double-free signature.
- claim_boundary: This is a repair/positive-control endpoint proof for the GPAC R2T gap, not yet a FORMTRIG fuzzing campaign result. No FORMTRIG runtime JSONL was flushed before abort, so the current evidence is endpoint/native-crash evidence plus the B10 diagnostic chain.
- next_action: Promote SCAL-reference preseed construction into a controlled GPAC typed-mutation or seed-preparation stage, then run matched FORMTRIG/baseline campaigns with this endpoint oracle.

## Replay

| metric | value |
|---|---:|
| exit_code | `-6` |
| native_crash | `True` |
| double_free_signature | `True` |
| no_reference_track_messages | `3` |
| corrupt_nal_messages | `2` |
| runtime_log_exists | `False` |

## Link To B10

- B10 blocker: `extractor_returns_ok_without_reference_track_inferred`
- B11 probe status: `scal_ref_preseed_triggers_double_free`
