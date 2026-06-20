# GPAC_3403 Post-Reassign Path Audit

- status: `pre_detach_error_missing`
- interpretation: Inputs reach the lifecycle neighborhood but do not hit the modeled pre-detach HEVC error paths at avc_ext.c:809 or avc_ext.c:844.
- next_action: Bias typed mutation toward malformed HEVC extractor or nal_size<2 cases that remain parseable long enough to occur after sample-buffer reassign.

## Totals

| metric | value |
|---|---:|
| `fallback_reassign_records` | 1 |
| `normal_detach_absent_records` | 9 |
| `pre_detach_error_observed_records` | 1 |
| `pre_detach_error_records` | 0 |
| `reached_records` | 9 |
| `reassign_cleanup_same_records` | 0 |
| `release_reassign_same_records` | 9 |

## Runtime Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000000.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xf734a80395b0ec82` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000001.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x3e5bb9b87562418a` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000002.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xafeb4861be2ede48` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000004.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xe5e1a0230e41c860` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000005.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xe65a2ef5dec8d340` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000008.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `gpac_hevc_extractor_error_pre_detach_producer,gpac_invalid_nal_size_pre_detach_producer` | `` | `True` | `True` | `False` | `True` | `0x9f2d6f69ad7d6b30` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000009.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x8a4f40fdf83e6242` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000012.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xfbc89e7f845ad9c7` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000013.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xb5913dfa4522427d` |
