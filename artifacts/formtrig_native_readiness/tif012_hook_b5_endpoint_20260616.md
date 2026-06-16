# TIF012 Hook B5 Endpoint Note

Date: 2026-06-16

## Question

The B2 hook could reproduce the AFL++ vanilla parent-to-trigger mutation
locally, but the 600s FORMTRIG campaign still had no terminal `_T`. This note
records the B5 repair, its direct replay validation, and the first endpoint
positive FORMTRIG campaign for TIF012.

## Root Cause After B2

The B2 fallback inserted producer-like tags before `SamplesPerPixel`, but
libtiff reads `SamplesPerPixel` before the normal IFD pass whenever that tag is
present. The fallback therefore reached/use-side code without installing the
required producer state.

The B4 probe then omitted `SamplesPerPixel` and installed `SMaxSampleValue`.
This produced `producer_bits=2`, but still did not trigger because libtiff's
missing-`SamplesPerPixel` recovery is OJPEG-specific. The replayed vanilla
trigger had `Compression` low 16 bits equal to 6 (`COMPRESSION_OJPEG`).

## Hook Change

`scripts/formtrig_hooks/tiff_tif012_ifd_tag_hook.py` now has two paths:

- in-place path: when `ExtraSamples` already precedes `SamplesPerPixel`, rewrite
  the `SamplesPerPixel` tag to `SMaxSampleValue` or `SMinSampleValue`, and
  coerce the existing `Compression` entry to OJPEG;
- fallback path: append a new first IFD that coerces `Compression` to OJPEG,
  inserts `ExtraSamples` and `SMaxSampleValue`/`SMinSampleValue`, and omits
  `SamplesPerPixel`, letting libtiff's OJPEG recovery set `SamplesPerPixel=3`
  after the producer state exists.

Regression coverage:

- `tests/test_tiff_tif012_hook.py`
- `python3 -m unittest tests.test_tiff_tif012_hook`
- `python3 -m py_compile scripts/formtrig_hooks/tiff_tif012_ifd_tag_hook.py`

## Direct Replay Validation

The B5 hook was applied to all 20 TIF012 RNT corpus seeds:

- generated candidates:
  `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b5_probe_inputs`
- replay:
  `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b5_probe_replay_20260616.json`
- final hook SHA replay after the post-campaign robustness tweak:
  `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b5_final_probe_replay_20260616.json`

Result:

| seeds | reached | `_T` | spec lifted | role signal |
| ---: | ---: | ---: | ---: | --- |
| 20 | 20 | 20 | 20 | `producer_bits=2`, `use_bits=2` |

The replay readiness status is `fail` only because the candidate corpus has no
reached-non-trigger seeds after mutation; every generated candidate is terminal.
The final hook SHA validated by the second replay is:

`44743a1212bd044f8532bb6ed8bd034482fa1a0ccb0a3706a0a9a2dcd6e8d406`

## 120s FORMTRIG B5 Campaign

Manifest:

`artifacts/formtrig_native_readiness/manifests/TIF012.native_draft_magma_canary.hook_b5.120s.manifest`

Output:

`artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b5_120s_20260616`

Campaign summary:

| metric | value |
| --- | ---: |
| runtime | 120s |
| execs | 59,777 |
| corpus count | 2,339 |
| reached execs | 39,787 |
| terminal `_T` execs | 18,708 |
| queued FORMTRIG progress | 2,084 |
| saved triggered progress | 2,080 |
| saved non-trigger progress | 4 |
| typed stage starts | 3 |
| typed execs | 384 |
| typed finds | 384 |
| `D_F_spec_lifted` range | 1..2 |

The first terminal queue item was produced by the FORMTRIG typed stage:

`artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b5_120s_20260616/default/queue/id:000020,src:000013,time:35,execs:146,op:ftgtype,pos:4,+cov`

The progress log records the corresponding triggered save at exec 153:

- `typed_stage_start`: exec 145, source queue 13, `D_T=1`, `D_F=2`
- first `saved_progress` with `reason=triggered`: exec 153, queue 20,
  `D_T=0`, `D_F_spec_lifted=1`, `producer_bits=2`, `use_bits=2`

Hook provenance:

`artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b5_120s_20260616/formtrig_mutation_hook.json`

The campaign loaded the hook from the BindingSpec and recorded SHA-256:

`83fd1f8438a3f167955f03a78a88428989684754cd6982ad8961f80050e50c28`

That campaign SHA predates the final robustness-only hook edit above. The final
direct replay revalidated the current file and still converted 20/20 RNT seeds
to terminal `_T`.

## 30s Current-SHA Campaign

Manifest:

`artifacts/formtrig_native_readiness/manifests/TIF012.native_draft_magma_canary.hook_b5.final_30s.manifest`

Output:

`artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b5_final_30s_20260616`

This run revalidates the current hook file, SHA-256:

`44743a1212bd044f8532bb6ed8bd034482fa1a0ccb0a3706a0a9a2dcd6e8d406`

Campaign summary:

| metric | value |
| --- | ---: |
| runtime | 30s |
| execs | 8,202 |
| corpus count | 288 |
| reached execs | 6,136 |
| terminal `_T` execs | 1,150 |
| queued FORMTRIG progress | 132 |
| saved triggered progress | 128 |
| saved non-trigger progress | 4 |
| typed execs | 128 |
| typed finds | 128 |
| `D_F_spec_lifted` range | 1..2 |

The first terminal queue item was again produced by the FORMTRIG typed stage:

`artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b5_final_30s_20260616/default/queue/id:000020,src:000013,time:36,execs:146,op:ftgtype,pos:4,+cov`

The progress log records the first triggered save at exec 153 with `D_T=0`,
`D_F_spec_lifted=1`, `producer_bits=2`, and `use_bits=2`.

Gate:

`artifacts/formtrig_native_readiness/gates/tif012_hook_b5_final_30s_20260616/gate_report.md`

The current-SHA 30s run also has endpoint and binding readiness:

- `experiment_ready=true`
- `pretrigger_lift_guidance_ready=true`
- `binding_signal_status=pass`
- `terminal_triggered=1,150`

The strict pre-trigger gate still reports:

- status: `fail`
- reasons: `no_non_trigger_lift_delta;lift_delta_only_on_triggered`

## Gate Result

Gate:

`artifacts/formtrig_native_readiness/gates/tif012_hook_b5_120s_20260616/gate_report.md`

The run satisfies endpoint and binding readiness:

- `experiment_ready=true`
- `pretrigger_lift_guidance_ready=true`
- `binding_signal_status=pass`
- `terminal_triggered=18,708`

The strict pre-trigger gate still reports:

- status: `fail`
- reasons: `no_non_trigger_lift_delta;lift_delta_only_on_triggered`

This is expected for the B5 repair. The evidence is not a continuous
non-trigger `D_F` gradient claim. It is a typed-repair endpoint claim: FORMTRIG
uses the lifted input-influence hook to synthesize the missing producer/use
state and directly closes R2T.

## Matched 120s Baseline Comparison

Comparison package:

`artifacts/formtrig_native_readiness/comparisons/tif012_b5_formtrig_120s_vs_aflpp_family_120s_20260616`

Replicated comparison package:

`artifacts/formtrig_native_readiness/comparisons/tif012_b5_formtrig_120s_3rep_vs_aflpp_family_120s_3rep_20260616`

Baseline input:

`artifacts/formtrig_native_readiness/raw/tif012_baselines_b5_matched_120s_20260616/summary.json`

Replicated baseline input:

`artifacts/formtrig_native_readiness/raw/tif012_baselines_b5_matched_120s_3rep_20260616/summary.json`

Replicated FORMTRIG input:

`artifacts/formtrig_native_readiness/raw/tif012_b5_formtrig_120s_3rep_20260616/batch_summary.csv`

Replicated first-trigger evidence:

`artifacts/formtrig_native_readiness/raw/tif012_b5_formtrig_120s_3rep_20260616/first_trigger_events.jsonl`

Same-budget 120s result:

| arm | budget | `_R`/reached | `_T` | first `_T` |
| --- | ---: | ---: | ---: | ---: |
| FORMTRIG B5 | 120s | 39,787 | 18,708 | 0.035s / exec 146 |
| AFL++ vanilla | 120s | 37,505 | 0 | n/a |
| AFL++ CmpLog | 120s | 63,036 | 0 | n/a |
| Redqueen/operand | 120s | 52,228 | 0 | n/a |

The comparison verdict is `positive_endpoint_but_under_replicated`: it supports
a same-budget endpoint benefit for this short screen, but not a final
performance claim. Required next step is at least three repetitions per
matched baseline/budget and matching FORMTRIG repetitions.

The replicated 3x120s result upgrades this short-screen evidence:

| arm | success | terminal `_T` counts | first `_T` |
| --- | ---: | --- | --- |
| FORMTRIG B5 current SHA | 3/3 | 10,870; 7,971; 4,604 | 0.036s, 0.035s, 0.035s / exec 146 |
| AFL++ vanilla | 0/3 | 0; 0; 0 | n/a |
| AFL++ CmpLog | 0/3 | 0; 0; 0 | n/a |
| Redqueen/operand | 0/3 | 0; 0; 0 | n/a |

The replicated comparison verdict is `positive_endpoint_matched_comparison`.
This is now a real short-screen endpoint benefit, not only a single-run smoke
signal. It is still not a final long-run or cross-target claim.

## Interpretation

TIF012 has moved from negative endpoint evidence under B2 to positive endpoint
evidence under B5 for a 120s native FORMTRIG screen. The benefit is visible
before the mechanism details: first `_T` appears in 35 ms of AFL time at queue
20 and exec 153, with 18,708 terminal executions by 120s. The current file hash
also reproduces the endpoint in a 30s campaign, with first `_T` at queue 20 and
exec 153 and 1,150 terminal executions by 30s.

This result should be compared against faithful baselines in matched repeated
runs before it becomes a main performance claim. The right claim today is
narrower and stronger than the B2 note:

- B5 fixes the concrete R2T implementation gap for TIF012;
- the advantage comes from structured typed repair, not from scalar `D_F`
  gradually separating many non-trigger candidates;
- future long-run comparisons should report first `_T`, total `_T`, typed-stage
  provenance, exec/sec cost, and repetition rate.
