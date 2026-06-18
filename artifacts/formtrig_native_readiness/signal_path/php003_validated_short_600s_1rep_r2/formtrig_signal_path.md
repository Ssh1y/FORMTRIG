# FORMTRIG Signal Path: PHP003

- analysis: `2026-06-18T13:51:42Z`
- verdict: `strict_pretrigger_guidance_observed`
- typed attribution: `no_typed_preterminal_attribution`
- claim boundary: calibrated_frontier is reported for diagnosis only; strict gate still requires saved non-trigger progress before terminal _T; typed-stage attribution explains mutation activity but does not upgrade the strict gate

## Guidance Capability

- stable frontier runs: `1/1`
- sortable lifted D_F runs: `1/1`
- actionable typed non-T runs: `1/1`
- mutable typed-find runs: `1/1`
- total typed finds: `8` / typed execs `6412`
- strict saved pre-trigger runs: `1/1`
- interpretation: see per-run capability counts

## Runs

| run | time | execs | calibrated non-T | saved non-T | saved T | first non-T exec | first T exec | typed starts | typed before T | typed lifted non-T before T | typed finds | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| 001_PHP003 | 600 | 205673 | 2 | 6 | 0 | 142 |  | 52 | no | no | 8 | strict_pretrigger_guidance_seen |

## Per-Run First Signals

### 001_PHP003
- first calibrated non-T: exec `12`, D_F `1`, spec D_F `1`, reason `initial_frontier_seed`
- first typed stage: exec `40`, D_F `1`, spec D_F `1`, reason `fallback_no_hot_range`
- first typed lifted non-T before T: exec `40`, D_F `1`, spec D_F `1`, reason `fallback_no_hot_range`
- first saved non-T: exec `142`, D_F `1`, spec D_F `1`, reason `root_aligned_state_transition`
- first saved T: none
- preterminal non-T D_F values: `[1]`

## R-to-T Terminal Gap

### 001_PHP003
- status: `saved_frontier_blocked_on_producer`
- saved non-T frontier events: `6`; saved T events: `0`
- typed fallback without hot ranges: `52`; saved frontier hot-range events: `0`
- blocking reasons: `no_terminal_T_after_saved_non_trigger_frontier, missing_bound_roles_at_latest_saved_frontier, producer_roles_not_satisfied_at_latest_saved_frontier, observed_bound_roles_not_goal_satisfied_at_latest_saved_frontier, producer_roles_constant_zero_in_candidates, typed_mutation_has_no_hot_ranges_for_saved_frontier`
- missing bound roles at latest saved frontier: `{'1': ['desired_producer']}`
- observed roles not goal-satisfied at latest saved frontier: `{'1': ['root_observe', 'use']}`
- unsatisfied producer roles at latest saved frontier: `{'1': ['desired_producer']}`
- latest saved non-T: queue `466`, exec `119606`, trace `6ed559e280b60e5d`

| queue | exec | size | missing bound roles | observed unsatisfied roles | unsatisfied producers |
| ---: | ---: | ---: | --- | --- | --- |
| 8 | 142 | 1240 | `{'1': ['guard', 'desired_producer', 'use']}` | `{'1': ['root_observe']}` | `{'1': ['desired_producer']}` |
| 12 | 221 | 1259 | `{'1': ['guard', 'desired_producer']}` | `{'1': ['root_observe', 'use']}` | `{'1': ['desired_producer']}` |
| 147 | 3554 | 1240 | `{'1': ['guard', 'desired_producer']}` | `{'1': ['root_observe']}` | `{'1': ['desired_producer']}` |
| 227 | 11959 | 92 | `{'1': ['desired_producer', 'use']}` | `{'1': ['root_observe']}` | `{'1': ['desired_producer']}` |
| 238 | 13198 | 91 | `{'1': ['desired_producer', 'use']}` | `{'1': ['root_observe', 'guard']}` | `{'1': ['desired_producer']}` |
| 466 | 119606 | 1240 | `{'1': ['desired_producer']}` | `{'1': ['root_observe', 'use']}` | `{'1': ['desired_producer']}` |
