# GPAC_3403 Post-Reassign Path Audit

- status: `pre_detach_error_missing`
- interpretation: Inputs reach the lifecycle neighborhood but do not hit the modeled pre-detach HEVC error paths at avc_ext.c:809 or avc_ext.c:844.
- next_action: Bias typed mutation toward malformed HEVC extractor or nal_size<2 cases that remain parseable long enough to occur after sample-buffer reassign.

## Totals

| metric | value |
|---|---:|
| `fallback_reassign_records` | 0 |
| `normal_detach_absent_records` | 4 |
| `pre_detach_error_observed_records` | 1 |
| `pre_detach_error_records` | 0 |
| `reached_records` | 4 |
| `reassign_cleanup_same_records` | 0 |
| `release_reassign_same_records` | 4 |

## Runtime Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000000.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x3de5d520e3d0050a` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000001.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x1a0161bb5aa4a088` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000002.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `gpac_hevc_extractor_error_pre_detach_producer,gpac_invalid_nal_size_pre_detach_producer` | `` | `True` | `True` | `False` | `False` | `0x1805e692bdfb44c8` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_op52_replay_20260620T022321Z/logs/variant_000003.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x3fd3a41776d86a5c` |
