# GPAC_3403 Extractor Path Audit

- status: `extractor_returns_ok_without_reference_track_inferred`
- interpretation: process_extractor reaches the no-reference-track return site and no modeled downstream post-reference event is observed; branch outcome polarity is therefore treated as ambiguous, but the path is consistent with the GF_OK no-ref-track early return.
- next_action: Mutate toward an imported L-HEVC/SCAL reference relation, then require downstream post-reference probes before endpoint replay.

## Totals

| metric | value |
|---|---:|
| `constructor_mode_observed_records` | 1 |
| `extractor_loop_entry_observed_records` | 1 |
| `extractor_loop_entry_satisfied_records` | 1 |
| `no_reference_track_ok_return_observed_records` | 1 |
| `outer_hevc_extractor_error_observed_records` | 1 |
| `outer_invalid_nal_size_observed_records` | 1 |
| `records_with_extractor_components` | 1 |

## Runtime Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000000.runtime.jsonl

| idx | D_F | observed | satisfied | error | ok barrier | trace |
|---:|---:|---|---|---|---|---|

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000001.runtime.jsonl

| idx | D_F | observed | satisfied | error | ok barrier | trace |
|---:|---:|---|---|---|---|---|

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000002.runtime.jsonl

| idx | D_F | observed | satisfied | error | ok barrier | trace |
|---:|---:|---|---|---|---|---|
| 0 | 3 | `constructor_mode,extractor_loop_entry,no_reference_track_ok_return,outer_hevc_extractor_error,outer_invalid_nal_size` | `extractor_loop_entry` | `` | `` | `0x1805e692bdfb44c8` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000003.runtime.jsonl

| idx | D_F | observed | satisfied | error | ok barrier | trace |
|---:|---:|---|---|---|---|---|
