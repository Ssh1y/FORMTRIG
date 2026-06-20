# GPAC_3403 SCAL Reference Preseed Probe

- status: `scal_ref_preseed_no_terminal_crash`
- preseed_class: `reference_scaffold_candidate`
- next_action: Use this non-terminal SCAL-reference scaffold as a candidate resumed corpus only after confirming replay stability and matched-baseline seed parity.
- claim_boundary: The preseed builds a SCAL-reference MP4 and replays without terminal crash or missing-reference diagnostics; it is a candidate scaffold, not endpoint success.

## Replay

| metric | value |
|---|---:|
| exit_code | 0 |
| native_crash | False |
| double_free_signature | False |
| no_reference_track_messages | 0 |
| corrupt_nal_messages | 0 |
| runtime_log_exists | True |
