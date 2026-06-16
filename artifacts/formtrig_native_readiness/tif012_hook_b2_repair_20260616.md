# TIF012 Hook B2 Repair Note

Date: 2026-06-16

## Question

After the 600s TIF012 matched short-screen, FORMTRIG had strict pre-trigger
activity but no terminal `_T`, while AFL++ vanilla and the local
Redqueen/operand path reached `_T`. This note records the repair analysis for
the TIFF typed mutation hook and the follow-up 600s result.

## Baseline Replay Evidence

Full queue replay of the 600s baseline run shows that terminal seeds exist in
the AFL++ family queues:

| queue | seeds | reached | `_T` | RNT | spec lifted | spec D_F unique |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AFL++ vanilla | 741 | 480 | 1 | 479 | 481 | 2 |
| Redqueen/operand | 671 | 445 | 2 | 443 | 449 | 2 |
| FORMTRIG pre-B2 | 518 | 362 | 0 | 362 | 363 | 2 |

Evidence:

- `artifacts/formtrig_native_readiness/runner_validation/tif012_vanilla_queue_replay_full_20260616.json`
- `artifacts/formtrig_native_readiness/runner_validation/tif012_redqueen_queue_replay_full_20260616.json`
- `artifacts/formtrig_native_readiness/runner_validation/tif012_formtrig_queue_replay_full_20260616.json`

The vanilla terminal seed is:

`artifacts/formtrig_native_readiness/raw/tif012_baselines_short_600s_20260616_r6/magma/aflplusplus_vanilla_600s/findings/default/queue/id:000535,src:000501,time:232357,op:havoc,rep:4,+cov`

Its parent RNT seed is:

`artifacts/formtrig_native_readiness/raw/tif012_baselines_short_600s_20260616_r6/magma/aflplusplus_vanilla_600s/findings/default/queue/id:000501,src:000418,time:195765,op:havoc,rep:2,+cov`

The parent-to-trigger transition is a minimal TIFF IFD tag substitution:
`SamplesPerPixel` (tag 277) becomes `SMaxSampleValue` (tag 341) while the
surrounding directory context is preserved. In byte terms, the B2 candidate
differs from the parent by one byte at offset 1911 (`0x15 -> 0x55`), changing
little-endian tag `0x0115` to `0x0155`.

## Hook Change

`scripts/formtrig_hooks/tiff_tif012_ifd_tag_hook.py` now tries the replayed
in-place substitution first when the seed already has the vulnerable
`ExtraSamples` then `SamplesPerPixel` IFD shape:

- if `ExtraSamples` appears before `SamplesPerPixel`, rewrite the
  `SamplesPerPixel` tag to `SMaxSampleValue` or `SMinSampleValue`;
- otherwise fall back to appended-IFD synthesis;
- in the fallback path, state tags are placed before inserted
  `SamplesPerPixel`, fixing the previous ordering bug.

Regression coverage:

- `tests/test_tiff_tif012_hook.py`
- `python3 -m unittest tests.test_tiff_tif012_hook`
- `python3 -m py_compile scripts/formtrig_hooks/tiff_tif012_ifd_tag_hook.py`

## Local Probe

The B2 hook can close the observed vanilla parent-to-trigger gap when applied
directly to the vanilla RNT parent:

- candidate:
  `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b2_probe_inputs/vanilla_parent_hook_b2_candidate.tif`
- replay:
  `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b2_vanilla_parent_probe_20260616.json`
- runtime log:
  `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b2_vanilla_parent_probe_20260616.logs/seed_1.runtime.jsonl`

Probe result:

- reached: true
- triggered: true
- `D_T`: 0
- `D_F_spec_lifted`: 1
- observed producer role bit: present in the runtime atom signal

The replay JSON has readiness `status=fail` only because this single probe
corpus has no reached-non-trigger seed; the seed itself is terminal.

## 600s FORMTRIG B2 Run

The patched hook was run under the same TIF012 native BindingSpec for 600s:

- manifest:
  `artifacts/formtrig_native_readiness/manifests/TIF012.native_draft_magma_canary.hook_b2.600s.manifest`
- output:
  `artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b2_600s_20260616`

Campaign summary:

- runtime: 600s
- execs: 465,793
- corpus count: 627
- reached execs: 178,995
- terminal `_T` execs: 0
- typed execs: 7,646
- typed finds: 2
- queued replay-stable non-trigger progress: 9
- binding-signal diagnosis: pass, `role_signal_progress_observed`
- desired producer samples in binding diagnosis: 0
- campaign diagnosis: `not_ready`, `queued_tc_rooted_progress`

Gate result:

- `artifacts/formtrig_native_readiness/raw/tif012_formtrig_hook_b2_600s_20260616/gate/gate_report.md`
- status: fail
- reasons: `experiment_not_ready;no_non_trigger_lift_delta`
- terminal `_T`: 0

Full queue replay confirms the monitor:

| queue | seeds | reached | `_T` | RNT | spec lifted | spec D_F unique |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FORMTRIG B2 600s | 627 | 482 | 0 | 482 | 483 | 1 |

Evidence:

- `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b2_queue_replay_full_20260616.json`
- `artifacts/formtrig_native_readiness/runner_validation/tif012_hook_b2_queue_replay_full_20260616.signal_entropy.json`

## Interpretation

This is not a TIF012 endpoint success. The repaired typed operator is locally
valid: it can turn the baseline's observed terminal-proximal parent into `_T`
with a one-byte structured rewrite. The full FORMTRIG campaign still does not
generate or preserve the required parent shape within 600s, and its scalar
spec `D_F` collapses to constant 2 across replayed RNT seeds. The current
guidance reaches the use side of the canary but does not create enough
producer-state signal for the scheduler to close R2T.

The next repair should therefore target the search loop, not only the hook:

- prioritize or synthesize seeds with the `ExtraSamples -> SamplesPerPixel`
  directory context;
- add producer-role scoring so `desired_producer` absence is visible to the
  frontier instead of collapsing into constant `D_F=2`;
- treat this case as a hard binary-null/lifecycle-state target until a
  same-budget terminal result exists.

Until that repair lands, TIF012 remains negative evidence for FORMTRIG endpoint
benefit and positive evidence for a concrete implementation gap.
