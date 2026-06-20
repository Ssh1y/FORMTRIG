# GPAC_3403 B10 Extractor Return Probe

## Verdict

- status: `repair_target_identified_no_terminal_T`
- summary: B10 expands B9 with internal process_extractor return/progress probes after the no-reference-track guard. The op52 minimal replay remains 4/4 reached/spec_lifted with D_F=3 and no _T. The only extractor-internal record reaches the no-reference-track return site, observes no downstream post-reference probes, and is now classified as an inferred GF_OK no-reference-track early return.
- claim_boundary: This is diagnostic repair evidence, not endpoint benefit evidence. It narrows the missing GPAC_3403 R2T step to constructing or importing a valid L-HEVC/SCAL reference relation for type49 extractors before spending long-run endpoint budget.
- next_action: Repair typed mutation toward a valid dependent/reference track relation so process_extractor progresses beyond line 154; then require B10 downstream probes such as lines 179/186/207/209/252 before endpoint replay.

## Static Lift Audit

| tier | lift_allowed | roles | event_count | collapsed | reason |
|---|---:|---:|---:|---:|---|
| B4 | true | `0x000001fb` | 34 | 0 | ok |

## Replay And Path Audit

| generated/replayed | reached/spec_lifted | _T | D_F values | extractor status | post-reassign status | key totals |
|---:|---:|---:|---|---|---|---|
| 4/4 | 4/4 | 0 | `[3.0]` | `extractor_returns_ok_without_reference_track_inferred` | `pre_detach_error_missing` | `{"extractor_records": 1, "loop_observed": 1, "no_ref_observed": 1, "post_ref_observed": 0, "pre_detach_error": 0, "reassign_cleanup_same": 0, "release_reassign_same": 4}` |
