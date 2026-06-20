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

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000000.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x6578df7cf62a19c3` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000001.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x0abbb187a4816917` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000002.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x4a82d03fe70d5532` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000004.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xfacd1326a9a9fe67` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000005.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xff95691bfa2f204f` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000008.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0x96039d31efa3d14d` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000009.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xc1cbe80b9357d5da` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000012.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xa00166ab37318c7d` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000013.runtime.jsonl

| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |
|---:|---:|---|---|---|---|---|---|---|
| 0 | 3 | `` | `` | `True` | `True` | `False` | `False` | `0xcd45a059acb999bc` |
