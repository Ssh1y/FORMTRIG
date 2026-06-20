# GPAC3403 B13 60s x3 Repaired Baseline Comparison

This package combines the earlier FORMTRIG/nohook/vanilla 60s x3 run with a
repaired CmpLog/Redqueen baseline rerun. Startup-only AFL++ cmplog forkserver
failures are marked invalid and retried; they are not counted as no-trigger
evidence.

## Sources

- FORMTRIG, nohook, vanilla:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_60s3rep_20260620T032730Z`
- CmpLog/Redqueen repaired baseline rerun:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_cmplog_redqueen_retry_60s3rep_20260620T034936Z`
- Combined comparison:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_60s3rep_repaired_baselines_20260620/comparison/comparison.json`

## Comparison

- verdict: `positive_endpoint_matched_comparison`
- main claim strength: `hard_endpoint_gap_candidate`
- matched valid baseline runs: `9`
- missing required baselines: none
- baseline no-guidance proof: `under_budgeted`
- baseline guidance gap:
  `artifacts/formtrig_native_readiness/baseline_guidance_gap/gpac3403_b13_scal_ref_payload_matched_screen_60s3rep_repaired_baselines_20260620/baseline_guidance_gap.json`

FORMTRIG with GPAC payload hook:

| rep | first `_T` | exec | terminal count | accepted/saved non-trigger | spec lifted |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2.390s | 8 | 2 | 5/5 | 70 |
| 2 | 2.422s | 8 | 2 | 5/5 | 70 |
| 3 | 2.605s | 8 | 2 | 5/5 | 70 |

FORMTRIG nohook:

| rep | first `_T` | exec | terminal count |
| ---: | ---: | ---: | ---: |
| 1 | 29.633s | 720 | 4 |
| 2 | 49.938s | 1801 | 1 |
| 3 | none | none | 0 |

Valid baselines:

| baseline | valid reps | attempted reps | success | execs |
| --- | ---: | ---: | ---: | --- |
| AFL++ vanilla | 3 | 3 | 0/3 | 1174, 971, 940 |
| AFL++ CmpLog | 3 | 4 | 0/3 valid | 1403, 1409, 1411 |
| Redqueen/operand | 3 | 3 | 0/3 | 1421, 1409, 1401 |

## Interpretation

Supported:

- FORMTRIG-hook has a clean 3/3 early endpoint result at about 2.4-2.6s.
- All required baseline families now have 3 valid 60s reps with no endpoint
  trigger.
- Post-reach seed contracts show pre-`_T` binary flatness for all valid
  baseline runs: every baseline starts from `_R=true,_T=false`, and the binary
  endpoint oracle remains false before any terminal hit.
- Nohook FORMTRIG is materially slower and less reliable on this screen.
- Baseline startup failures are handled as infrastructure noise, not as
  performance evidence.

Still not supported:

- hard SOTA-pain final claim
- long-budget baseline no-guidance proof: the current matched baseline runs are
  only 60s, below the 600s acceptable trigger threshold
- target-independent generality

Next step: repeat the B13 matched baseline screen at or beyond the 600s
acceptable trigger threshold, or move this proof path to another hard target.
