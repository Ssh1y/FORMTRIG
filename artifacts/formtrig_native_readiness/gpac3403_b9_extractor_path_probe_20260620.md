# GPAC_3403 B9 Extractor Path Probe

## Verdict

- status: `diagnostic_progress_no_terminal_T`
- summary: B9 keeps the GPAC_3403 lifecycle/alias signal exact at B4 and adds process_extractor subpath events. Both typed windows still replay 9/16 reached/spec_lifted variants with D_F=3 and no _T. ops52-55 produces one process_extractor loop-entry record, but no modeled error or OK barrier is satisfied. ops56-59 reaches the outer lifecycle/alias neighborhood but never enters process_extractor.
- claim_boundary: This is repair/diagnostic evidence, not endpoint benefit evidence. The line-912 normal-detach absence probe remains weak because gf_bs_get_content_no_truncate is called before that line; B9 should be read as narrowing the missing R2T transition, not proving final double-free closure.
- next_action: Add the next internal process_extractor return/operand-distance binding for the observed op52 path, and separately repair malformed type49 preservation for ops56-59 before spending long-run endpoint budget.

## Static Lift Audit

| tier | lift_allowed | roles | event_count | collapsed | reason |
|---|---:|---:|---:|---:|---|
| B4 | true | `0x000001fb` | 22 | 0 | ok |

## Replay Cases

| case | generated/replayed | reached/spec_lifted | _T | D_F values | extractor status | post-reassign status | key totals |
|---|---:|---:|---:|---|---|---|---|
| ops52_55 | 16/16 | 9/9 | 0 | `[3.0]` | `extractor_path_incomplete` | `pre_detach_error_missing` | `{"error_satisfied": 0, "extractor_records": 1, "loop_observed": 1, "pre_detach_error": 0, "reassign_cleanup_same": 0, "release_reassign_same": 9}` |
| ops56_59 | 16/16 | 9/9 | 0 | `[3.0]` | `extractor_not_reached` | `pre_detach_error_missing` | `{"error_satisfied": 0, "extractor_records": 0, "loop_observed": 0, "pre_detach_error": 0, "reassign_cleanup_same": 0, "release_reassign_same": 9}` |
