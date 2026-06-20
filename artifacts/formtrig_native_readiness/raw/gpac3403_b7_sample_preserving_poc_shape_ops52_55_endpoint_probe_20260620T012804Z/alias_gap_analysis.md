# GPAC_3403 Alias Gap Analysis

- Lift spec: `artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_opdiverse_hevc_20260620T004121Z/runs/formtrig_rep1/fuzzer_out/.formtrig/formtrig_lift.normalized`
- Runtime logs: 9
- Verdict: `stable_nonzero_cleanup_offset`
- Complete alias/free relation: `False`
- Stable nonzero cleanup offsets: `[-431440, -405568, -358880, -338304, -337776, -326752, -308128, -179696, -119360]`

## Interpretation

Release and reassign-buffer pointers match, but cleanup consistently frees a different dynamic bitstream buffer. This narrows the blocker to lifecycle ownership closure, not HEVC importer routing or retained-candidate selection.

Next action: Repair typed mutation or BindingSpec correlation so the final GF_BitStream cleanup object is the same sample buffer that gf_isom_sample_del releases.

Claim boundary: Pointer deltas are runtime diagnostics only. They must not be used as input-level optimization objectives because allocator addresses are not stable semantic trigger-state features.

## Runtime Summaries

| runtime | status | records | release=reassign | cleanup | alias+cleanup | unique release | unique cleanup | nonzero delta | top deltas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000000.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -358880, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000001.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -119360, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000002.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -308128, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000004.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -405568, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000005.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -338304, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000008.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -326752, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000009.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -431440, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000012.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -179696, 'count': 1}]` |
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000013.runtime.jsonl | `stable_nonzero_cleanup_offset` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | `[{'value': -337776, 'count': 1}]` |

## Top Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000000.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[94325213158656]` | `[94325212799776]` | `[-358880]` | `0x2d98b35f75d521d2` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000001.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[100599089499392]` | `[100599089380032]` | `[-119360]` | `0x6447afbe0e983bce` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000002.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[97695578156288]` | `[97695577848160]` | `[-308128]` | `0xfa311409d0742b9e` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000004.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[103894604520704]` | `[103894604115136]` | `[-405568]` | `0xf09ffb4362233346` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000005.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[105069399887104]` | `[105069399548800]` | `[-338304]` | `0x3da0c92428b39e2b` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000008.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[94608327864560]` | `[94608327537808]` | `[-326752]` | `0x9500fe6e839ea743` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000009.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[94788516760832]` | `[94788516329392]` | `[-431440]` | `0x8d79f087f73474d4` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000012.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[94300235978800]` | `[94300235799104]` | `[-179696]` | `0xad40b4152119fc82` |

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_sample_preserving_poc_shape_ops52_55_endpoint_probe_20260620T012804Z/logs/variant_000013.runtime.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `None` | `None` | None | None | 2 | `[110440473697536]` | `[110440473359760]` | `[-337776]` | `0x64b0354bd978c75b` |
