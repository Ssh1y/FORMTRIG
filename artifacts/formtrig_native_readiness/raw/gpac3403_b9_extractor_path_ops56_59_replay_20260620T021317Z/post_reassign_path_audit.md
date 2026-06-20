# GPAC_3403 Post-Reassign Path Audit

- status: `pre_detach_error_missing`
- interpretation: Inputs reach the lifecycle neighborhood but do not hit the modeled pre-detach HEVC error paths at avc_ext.c:809 or avc_ext.c:844.
- next_action: Bias typed mutation toward malformed HEVC extractor or nal_size<2 cases that remain parseable long enough to occur after sample-buffer reassign.

## Totals

| metric | value |
|---|---:|
| `fallback_reassign_records` | 0 |
| `normal_detach_absent_records` | 9 |
| `pre_detach_error_observed_records` | 0 |
| `pre_detach_error_records` | 0 |
| `reached_records` | 9 |
| `reassign_cleanup_same_records` | 0 |
| `release_reassign_same_records` | 9 |

## Runtime Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000000.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xfbdc5747a860e393` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000001.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x31c9b774231bf6dd` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000002.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xa54bedf5b8c70973` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000004.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x7c1060f370837c79` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000005.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xda128ad5f617933f` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000008.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xe79680620433b254` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000009.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x9d7cd0b04f5bb31f` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000012.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xbc8ce156ef51b0f7` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops56_59_replay_20260620T021317Z/logs/variant_000013.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xd90a28e28fe275bc` |
