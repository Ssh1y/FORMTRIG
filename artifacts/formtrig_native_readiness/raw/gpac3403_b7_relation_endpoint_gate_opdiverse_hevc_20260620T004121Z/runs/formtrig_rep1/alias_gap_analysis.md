# GPAC_3403 Alias Gap Analysis

- Lift spec: `artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_opdiverse_hevc_20260620T004121Z/runs/formtrig_rep1/fuzzer_out/.formtrig/formtrig_lift.normalized`
- Runtime logs: 1
- Verdict: `variable_cleanup_alias_gap`
- Complete alias/free relation: `False`
- Stable nonzero cleanup offsets: `[]`

## Interpretation

Alias and cleanup values are both observed, but their difference is not stable or zero. More object/lifecycle correlation is needed before endpoint spending.

Next action: Add object-context instrumentation or split records by sample/lifecycle context.

Claim boundary: Pointer deltas are runtime diagnostics only. They must not be used as input-level optimization objectives because allocator addresses are not stable semantic trigger-state features.

## Runtime Summaries

| runtime | status | records | release=reassign | cleanup | alias+cleanup | unique release | unique cleanup | nonzero delta | top deltas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_opdiverse_hevc_20260620T004121Z/runs/formtrig_rep1/fuzzer_out/default/formtrig_progress.jsonl | `variable_cleanup_alias_gap` | 1922 | 19 | 19 | 19 | 4 | 3 | 19 | `[{'value': -28384, 'count': 11}, {'value': -33984, 'count': 4}, {'value': -34816, 'count': 2}, {'value': 9440, 'count': 2}]` |

## Top Records

### artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_opdiverse_hevc_20260620T004121Z/runs/formtrig_rep1/fuzzer_out/default/formtrig_progress.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 746 | `frontier_reject` | `high_priority_regression` | 1028 | 0 | 2 | `[94534924505328]` | `[94534924514768]` | `[9440]` | `06a82f6462325794` |
| 747 | `frontier_reject` | `high_priority_regression` | 1028 | 0 | 2 | `[94534924505328]` | `[94534924514768]` | `[9440]` | `06a82f6462325794` |
| 112 | `frontier_reject` | `high_priority_regression` | 296 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `053017bf88e381c7` |
| 113 | `frontier_reject` | `high_priority_regression` | 296 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `053017bf88e381c7` |
| 114 | `typed_retain` | `candidate_not_queued` | 296 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `053017bf88e381c7` |
| 209 | `frontier_reject` | `high_priority_regression` | 383 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `a6b98e765bcb37e4` |
| 210 | `typed_retain` | `candidate_not_queued` | 383 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `a6b98e765bcb37e4` |
| 299 | `frontier_reject` | `high_priority_regression` | 428 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `45902b8353bba59d` |
| 300 | `typed_retain` | `candidate_not_queued` | 428 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `45902b8353bba59d` |
| 389 | `frontier_reject` | `high_priority_regression` | 473 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `062715b1ae6e1431` |
| 390 | `typed_retain` | `candidate_not_queued` | 473 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `062715b1ae6e1431` |
| 479 | `frontier_reject` | `high_priority_regression` | 518 | 0 | 2 | `[94534924543152]` | `[94534924514768]` | `[-28384]` | `6e02897d2ae33ce8` |
