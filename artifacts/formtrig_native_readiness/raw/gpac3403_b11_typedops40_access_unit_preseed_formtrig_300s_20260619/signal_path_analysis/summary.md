# FORMTRIG Signal Path: GPAC_3403

- analysis: `2026-06-19T17:01:14Z`
- verdict: `strict_pretrigger_guidance_observed`
- typed attribution: `no_typed_preterminal_attribution`
- claim boundary: calibrated_frontier is reported for diagnosis only; strict gate still requires saved non-trigger progress before terminal _T; typed-stage attribution explains mutation activity but does not upgrade the strict gate

## Guidance Capability

- stable frontier runs: `1/1`
- sortable lifted D_F runs: `1/1`
- actionable typed non-T runs: `1/1`
- mutable typed-find runs: `1/1`
- total typed finds: `43` / typed execs `218`
- strict saved pre-trigger runs: `1/1`
- interpretation: see per-run capability counts

## Runs

| run | time | execs | calibrated non-T | saved non-T | saved T | first non-T exec | first T exec | typed starts | typed before T | typed lifted non-T before T | typed finds | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| fuzzer_out | 301 | 2012 | 1 | 31 | 0 | 43 |  | 1 | no | no | 43 | strict_pretrigger_guidance_seen |

## Per-Run First Signals

### fuzzer_out
- first calibrated non-T: exec `35`, D_F `1`, spec D_F `1`, reason `initial_frontier_seed`
- first typed stage: exec `35`, D_F `1`, spec D_F `1`, reason `planned`
- first typed lifted non-T before T: exec `35`, D_F `1`, spec D_F `1`, reason `planned`
- first saved non-T: exec `43`, D_F `1`, spec D_F `1`, reason `root_aligned_state_transition`
- first saved T: none
- preterminal non-T D_F values: `[1, 4, 2]`

## R-to-T Terminal Gap

### fuzzer_out
- status: `saved_frontier_missing_binding_events`
- saved non-T frontier events: `31`; saved T events: `0`
- typed fallback without hot ranges: `0`; saved frontier hot-range events: `31`
- blocking reasons: `no_terminal_T_after_saved_non_trigger_frontier, missing_binding_events_at_latest_saved_frontier`
- missing binding events at latest saved frontier: `{'1': [{'binding_id': '4', 'role': 'lifecycle_event', 'event_id': '944c63fc04584807', 'function': 'gf_isom_nalu_sample_rewrite', 'file': 'isomedia/avc_ext.c', 'line': 672, 'column': 59, 'opcode': 'br', 'component_kind': 7, 'priority': 30, 'value_mode': 'hit'}]}`
- latest saved non-T: queue `180`, exec `1959`, trace `322f07e5fbf535ba`

| queue | exec | size | missing bound roles | missing binding events | observed unsatisfied roles | unsatisfied producers |
| ---: | ---: | ---: | --- | --- | --- | --- |
| 5 | 43 | 2956 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 7 | 59 | 2953 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 8 | 67 | 2928 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 12 | 99 | 3712 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 15 | 128 | 3357 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 26 | 217 | 3534 | `{'1': ['same_object']}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672', '7:same_object:gf_bs_reassign_buffer:122']}` | `{}` | `{}` |
| 33 | 275 | 5627 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 35 | 462 | 2956 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 37 | 479 | 1460 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 38 | 487 | 2970 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 46 | 556 | 3625 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 51 | 599 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 61 | 694 | 2944 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 65 | 733 | 2975 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 67 | 755 | 2998 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 68 | 766 | 2909 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 72 | 804 | 2974 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 79 | 869 | 2952 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 91 | 981 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 100 | 1063 | 2990 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 104 | 1107 | 2981 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 111 | 1188 | 2957 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 124 | 1325 | 2926 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 133 | 1407 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 152 | 1619 | 2981 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 158 | 1684 | 2968 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 164 | 1766 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 165 | 1774 | 2934 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 173 | 1879 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 174 | 1889 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 180 | 1959 | 3021 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
