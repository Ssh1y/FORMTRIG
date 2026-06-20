# GPAC3403 B13 Readiness Delta

This delta updates the GPAC3403 real-CVE readiness state after the B13 SCAL
payload experiments.

## Updated Fact

The 2026-06-19 readiness file says GPAC3403 endpoint closure is still absent.
That is now superseded for the B13 path:

- B13 smoke reaches a real endpoint double-free at `2.401s / exec 8`.
- Endpoint replay confirms one retained variant exits `-6` with
  `free(): double free detected in tcache 2`.
- The repaired 60s x3 screen has FORMTRIG-hook `3/3` endpoint success at
  about `2.4-2.6s`, with accepted/saved non-trigger progress before `_T`.

## Boundary

This does not promote GPAC3403 B13 to hard SOTA-pain evidence.

The 600s screen was stopped after two strong baselines already triggered within
the acceptable threshold:

| baseline | first trigger | execs | saved crashes |
| --- | ---: | ---: | ---: |
| Redqueen/operand | 203.212s | 3045 | 4 |
| AFL++ CmpLog | 207.984s | 3073 | 7 |

So the correct status is:

```text
endpoint closure: present for B13 target-specific SCAL payload hook
hard SOTA-pain: demoted under the current B13 seed/harness
use: native readiness, repair-hook, speedup/control, runner regression evidence
do not use: main hard-gap proof or target-independent generality proof
```

## Next Action

Keep B13 out of the main hard-pain budget unless a materially farther seedbank
or less endpoint-revealing harness is built. For GPAC3403 as main real-CVE
evidence, continue either with the generic lifecycle/alias path or use B13 only
as a control and ablation case.

The canonical readiness/worklist generator still needs to learn how to ingest
this delta or top-level `formtrig_native_readiness_result_v1` artifacts before a
new 2026-06-20 readiness file is generated.
