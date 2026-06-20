# GPAC_3403 Alias Gap Analysis

- Lift spec: `artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_spec_compile_20260620/.formtrig/formtrig_lift.normalized`
- Runtime logs: 9
- Verdict: `stable_nonzero_cleanup_offset`
- Complete alias/free relation: `False`
- Stable nonzero cleanup offsets: `[-431440, -405568, -387888, -355872, -355472, -338304, -337776, -122624, -89440]`

## Interpretation

Release and reassign-buffer pointers match, but cleanup consistently frees a different dynamic bitstream buffer. This narrows the blocker to lifecycle ownership closure, not HEVC importer routing or retained-candidate selection.

Next action: Repair typed mutation or BindingSpec correlation so the final GF_BitStream cleanup object is the same sample buffer that gf_isom_sample_del releases.

Claim boundary: Pointer deltas are runtime diagnostics only. They must not be used as input-level optimization objectives because allocator addresses are not stable semantic trigger-state features.

## Runtime Summaries

| runtime | status | records | release=reassign | cleanup | alias+cleanup | unique release | unique cleanup | nonzero delta | top deltas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000000.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -387888, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000001.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -89440, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000002.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -355872, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000004.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -405568, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000005.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -338304, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000008.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -355472, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000009.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -431440, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000012.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -122624, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000013.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -337776, 'count': 1}]` |

## Top Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000000.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[107384825027840]` | `[107384824639952]` | `[-387888]` | `0xf734a80395b0ec82` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000001.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[97290858130688]` | `[97290858041248]` | `[-89440]` | `0x3e5bb9b87562418a` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000002.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[93857987596208]` | `[93857987240336]` | `[-355872]` | `0xafeb4861be2ede48` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000004.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[98155261558016]` | `[98155261152448]` | `[-405568]` | `0xe5e1a0230e41c860` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000005.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[101006343396608]` | `[101006343058304]` | `[-338304]` | `0xe65a2ef5dec8d340` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000008.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[96488943617536]` | `[96488943262064]` | `[-355472]` | `0x9f2d6f69ad7d6b30` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000009.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[95010795265280]` | `[95010794833840]` | `[-431440]` | `0x8a4f40fdf83e6242` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000012.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[103513504791808]` | `[103513504669184]` | `[-122624]` | `0xfbc89e7f845ad9c7` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b8_post_reassign_exit_guard_ops52_55_endpoint_probe_20260620T021500Z/logs/variant_000013.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 3 | `[93911674785024]` | `[93911674447248]` | `[-337776]` | `0xb5913dfa4522427d` |
