# GPAC_3403 SCAL Reference Preseed Probe

- status: `scal_ref_preseed_triggers_double_free`
- next_action: Promote SCAL-reference construction into the GPAC typed-mutation/preseed path, then compare against faithful baselines with the same endpoint oracle.

## Replay

| metric | value |
|---|---:|
| exit_code | -6 |
| native_crash | True |
| double_free_signature | True |
| no_reference_track_messages | 3 |
| corrupt_nal_messages | 2 |
| runtime_log_exists | False |
