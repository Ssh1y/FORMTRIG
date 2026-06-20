# GPAC_3403 Post-Reassign Path Audit

- status: `pre_detach_error_missing`
- interpretation: Inputs reach the lifecycle neighborhood but do not hit the modeled pre-detach HEVC error paths at avc_ext.c:809 or avc_ext.c:844.
- next_action: Bias typed mutation toward malformed HEVC extractor or nal_size<2 cases that remain parseable long enough to occur after sample-buffer reassign.

## Totals

| metric | value |
|---|---:|
| `fallback_reassign_records` | 0 |
| `normal_detach_absent_records` | 9 |
| `pre_detach_error_observed_records` | 1 |
| `pre_detach_error_records` | 0 |
| `reached_records` | 9 |
| `reassign_cleanup_same_records` | 0 |
| `release_reassign_same_records` | 9 |

## Runtime Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000000.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x6bffe2247a0917f9` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000001.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x1e7cd67c99a1ffd3` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000002.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xa60c9f3d75f05f94` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000004.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xc78abdafa214498c` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000005.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x3976b7abdee7ae9d` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000008.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `gpac_hevc_extractor_error_pre_detach_producer,gpac_invalid_nal_size_pre_detach_producer` | `` | `True` | `True` | `False` | `False` | `0x03da421585f11ae6` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000009.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x26a9f11c6a870a52` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000012.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x38b513ce9f261cb9` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b9_extractor_path_ops52_55_replay_20260620T021116Z/logs/variant_000013.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xf754f4345fbc3e52` |
