# GPAC_3403 Alias Gap Analysis

- Lift spec: `artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_spec_compile_20260620/.formtrig/formtrig_lift.normalized`
- Runtime logs: 9
- Verdict: `stable_nonzero_cleanup_offset`
- Complete alias/free relation: `False`
- Stable nonzero cleanup offsets: `[-377568, -358880, -344096, -330032, -224464, -190560, -146736, -46080, 40800]`

## Interpretation

Release and reassign-buffer pointers match, but cleanup consistently frees a different dynamic bitstream buffer. This narrows the blocker to lifecycle ownership closure, not HEVC importer routing or retained-candidate selection.

Next action: Repair typed mutation or BindingSpec correlation so the final GF_BitStream cleanup object is the same sample buffer that gf_isom_sample_del releases.

Claim boundary: Pointer deltas are runtime diagnostics only. They must not be used as input-level optimization objectives because allocator addresses are not stable semantic trigger-state features.

## Runtime Summaries

| runtime | status | records | release=reassign | cleanup | alias+cleanup | unique release | unique cleanup | nonzero delta | top deltas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000000.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -224464, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000001.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': 40800, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000002.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -146736, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000004.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -46080, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000005.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -190560, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000008.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -330032, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000009.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -358880, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000012.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -344096, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000013.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -377568, 'count': 1}]` |

## Top Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000000.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[101629917302016]` | `[101629917077552]` | `[-224464]` | `0x6578df7cf62a19c3` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000001.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[105383189356448]` | `[105383189397248]` | `[40800]` | `0x0abbb187a4816917` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000002.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[99329526312432]` | `[99329526165696]` | `[-146736]` | `0x4a82d03fe70d5532` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000004.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[103967556362480]` | `[103967556316400]` | `[-46080]` | `0xfacd1326a9a9fe67` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000005.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[94666548025232]` | `[94666547834672]` | `[-190560]` | `0xff95691bfa2f204f` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000008.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[103949230862928]` | `[103949230532896]` | `[-330032]` | `0x96039d31efa3d14d` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000009.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[108768498732288]` | `[108768498373408]` | `[-358880]` | `0xc1cbe80b9357d5da` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000012.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[94829820543760]` | `[94829820199664]` | `[-344096]` | `0xa00166ab37318c7d` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_malformed_extractor_ops56_59_endpoint_probe_20260620T023000Z/logs/variant_000013.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[108046990667008]` | `[108046990289440]` | `[-377568]` | `0xcd45a059acb999bc` |
