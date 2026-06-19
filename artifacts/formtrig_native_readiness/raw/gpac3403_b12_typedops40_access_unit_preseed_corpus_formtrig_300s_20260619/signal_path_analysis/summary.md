# FORMTRIG Signal Path: GPAC_3403

- analysis: `2026-06-19T17:15:00Z`
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
| fuzzer_out | 300 | 1900 | 1 | 32 | 0 | 36 |  | 1 | no | no | 43 | strict_pretrigger_guidance_seen |

## Per-Run First Signals

### fuzzer_out
- first calibrated non-T: exec `28`, D_F `1`, spec D_F `1`, reason `initial_frontier_seed`
- first typed stage: exec `28`, D_F `1`, spec D_F `1`, reason `planned`
- first typed lifted non-T before T: exec `28`, D_F `1`, spec D_F `1`, reason `planned`
- first saved non-T: exec `36`, D_F `1`, spec D_F `1`, reason `root_aligned_state_transition`
- first saved T: none
- preterminal non-T D_F values: `[1, 4, 2]`

## R-to-T Terminal Gap

### fuzzer_out
- status: `saved_frontier_missing_binding_events`
- saved non-T frontier events: `32`; saved T events: `0`
- typed fallback without hot ranges: `0`; saved frontier hot-range events: `32`
- blocking reasons: `no_terminal_T_after_saved_non_trigger_frontier, missing_binding_events_at_latest_saved_frontier`
- missing binding events at latest saved frontier: `{'1': [{'binding_id': '4', 'role': 'lifecycle_event', 'event_id': '944c63fc04584807', 'function': 'gf_isom_nalu_sample_rewrite', 'file': 'isomedia/avc_ext.c', 'line': 672, 'column': 59, 'opcode': 'br', 'component_kind': 7, 'priority': 30, 'value_mode': 'hit'}]}`
- latest saved non-T: queue `152`, exec `1884`, trace `f2587b40c2b37a34`

| queue | exec | size | missing bound roles | missing binding events | observed unsatisfied roles | unsatisfied producers |
| ---: | ---: | ---: | --- | --- | --- | --- |
| 4 | 36 | 2956 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 6 | 52 | 2953 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 7 | 60 | 2928 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 11 | 92 | 3712 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 14 | 121 | 3357 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 25 | 210 | 3534 | `{'1': ['same_object']}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672', '7:same_object:gf_bs_reassign_buffer:122']}` | `{}` | `{}` |
| 32 | 273 | 5627 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 34 | 460 | 2956 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 36 | 477 | 1460 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 37 | 485 | 2970 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 45 | 554 | 3625 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 60 | 704 | 2985 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 62 | 726 | 2950 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 69 | 812 | 2953 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 71 | 830 | 2979 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 76 | 879 | 2929 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 86 | 989 | 2999 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 92 | 1072 | 2944 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 93 | 1090 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 95 | 1108 | 2929 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 96 | 1120 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 101 | 1169 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 102 | 1185 | 2972 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 106 | 1229 | 2927 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 107 | 1245 | 2981 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 115 | 1356 | 2979 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 128 | 1536 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 130 | 1555 | 2977 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 134 | 1621 | 2970 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 147 | 1823 | 2949 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 148 | 1838 | 2963 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
| 152 | 1884 | 2973 | `{}` | `{'1': ['4:lifecycle_event:gf_isom_nalu_sample_rewrite:672']}` | `{}` | `{}` |
