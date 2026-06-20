# GPAC_3403 Alias Gap Analysis

- Lift spec: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z/runs/formtrig_rep1/fuzzer_out/.formtrig/formtrig_lift.normalized`
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
| /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z/runs/formtrig_rep1/fuzzer_out/default/formtrig_progress.jsonl | `variable_cleanup_alias_gap` | 12 | 5 | 11 | 5 | 2 | 4 | 5 | `[{'value': -20640, 'count': 3}, {'value': -5344, 'count': 2}]` |

## Top Records

### /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z/runs/formtrig_rep1/fuzzer_out/default/formtrig_progress.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `frontier_reject` | `not_replay_stable` | 7 | 0 | 3 | `[97945748852160]` | `[97945748846816]` | `[-5344]` | `8c1e0a7ae1d1ce69` |
| 1 | `typed_stage_start` | `planned` | 7 | 0 | 3 | `[97945748852160]` | `[97945748846816]` | `[-5344]` | `8c1e0a7ae1d1ce69` |
| 6 | `frontier_reject` | `not_replay_stable` | 24 | 0 | 4 | `[97945748879360]` | `[97945748858720]` | `[-20640]` | `a42c3be58f74049c` |
| 7 | `saved_progress` | `root_aligned_state_transition` | 24 | 2 | 4 | `[97945748879360]` | `[97945748858720]` | `[-20640]` | `a42c3be58f74049c` |
| 8 | `typed_retain` | `candidate_not_queued` | 24 | 0 | 4 | `[97945748879360]` | `[97945748858720]` | `[-20640]` | `a42c3be58f74049c` |
| 3 | `frontier_reject` | `not_replay_stable` | 16 | 0 | 4 | `[]` | `[97945748851472]` | `[]` | `932e75abdba91e5c` |
| 4 | `saved_progress` | `frontier_empty_seed` | 16 | 1 | 4 | `[]` | `[97945748851472]` | `[]` | `932e75abdba91e5c` |
| 5 | `typed_retain` | `candidate_not_queued` | 16 | 0 | 4 | `[]` | `[97945748851472]` | `[]` | `932e75abdba91e5c` |
| 9 | `frontier_reject` | `not_replay_stable` | 32 | 0 | 4 | `[]` | `[97945748851632]` | `[]` | `6769417fe601f9a4` |
| 10 | `saved_progress` | `root_aligned_state_transition` | 32 | 3 | 4 | `[]` | `[97945748851632]` | `[]` | `6769417fe601f9a4` |
| 11 | `typed_retain` | `candidate_not_queued` | 32 | 0 | 4 | `[]` | `[97945748851632]` | `[]` | `6769417fe601f9a4` |
