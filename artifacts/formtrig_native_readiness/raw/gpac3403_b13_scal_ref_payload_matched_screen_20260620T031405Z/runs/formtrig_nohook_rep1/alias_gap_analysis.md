# GPAC_3403 Alias Gap Analysis

- Lift spec: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z/runs/formtrig_nohook_rep1/fuzzer_out/.formtrig/formtrig_lift.normalized`
- Runtime logs: 1
- Verdict: `stable_nonzero_cleanup_offset`
- Complete alias/free relation: `False`
- Stable nonzero cleanup offsets: `[-5344]`

## Interpretation

Release and reassign-buffer pointers match, but cleanup consistently frees a different dynamic bitstream buffer. This narrows the blocker to lifecycle ownership closure, not HEVC importer routing or retained-candidate selection.

Next action: Repair typed mutation or BindingSpec correlation so the final GF_BitStream cleanup object is the same sample buffer that gf_isom_sample_del releases.

Claim boundary: Pointer deltas are runtime diagnostics only. They must not be used as input-level optimization objectives because allocator addresses are not stable semantic trigger-state features.

## Runtime Summaries

| runtime | status | records | release=reassign | cleanup | alias+cleanup | unique release | unique cleanup | nonzero delta | top deltas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z/runs/formtrig_nohook_rep1/fuzzer_out/default/formtrig_progress.jsonl | `stable_nonzero_cleanup_offset` | 22 | 2 | 16 | 2 | 1 | 2 | 2 | `[{'value': -5344, 'count': 2}]` |

## Top Records

### /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_20260620T031405Z/runs/formtrig_nohook_rep1/fuzzer_out/default/formtrig_progress.jsonl

| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |
|---:|---|---|---:|---:|---:|---|---|---|---|
| 0 | `frontier_reject` | `not_replay_stable` | 7 | 0 | 3 | `[108384546196928]` | `[108384546191584]` | `[-5344]` | `1a0ae4fc8210f67a` |
| 1 | `typed_stage_start` | `planned` | 7 | 0 | 3 | `[108384546196928]` | `[108384546191584]` | `[-5344]` | `1a0ae4fc8210f67a` |
| 2 | `frontier_reject` | `not_replay_stable` | 15 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `a03a623833b1ebed` |
| 3 | `saved_progress` | `frontier_empty_seed` | 15 | 1 | 5 | `[]` | `[108384546165424]` | `[]` | `a03a623833b1ebed` |
| 4 | `typed_retain` | `candidate_not_queued` | 15 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `a03a623833b1ebed` |
| 5 | `frontier_reject` | `dominated_by_existing_frontier` | 16 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `70f3f3124b53b428` |
| 6 | `typed_retain` | `candidate_not_queued` | 16 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `70f3f3124b53b428` |
| 7 | `frontier_reject` | `dominated_by_existing_frontier` | 24 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `e3c006292cace410` |
| 8 | `frontier_reject` | `dominated_by_existing_frontier` | 24 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `e3c006292cace410` |
| 9 | `typed_retain` | `candidate_not_queued` | 24 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `e3c006292cace410` |
| 10 | `frontier_reject` | `dominated_by_existing_frontier` | 25 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `70f3f3124b53b428` |
| 11 | `typed_retain` | `candidate_not_queued` | 25 | 0 | 5 | `[]` | `[108384546165424]` | `[]` | `70f3f3124b53b428` |
