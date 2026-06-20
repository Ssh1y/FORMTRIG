# GPAC3403 B13 600s Fast-Baseline Demotion

This package records why GPAC3403 B13 should not be used as hard SOTA-pain
main evidence under the current seedbank and harness.

## Source

- raw run:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_600s3rep_20260620`
- baseline summary:
  `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_matched_screen_600s3rep_20260620/baseline_summary.json`
- planned run: 600s x3, same `-t 5000+` endpoint oracle
- status: early stopped after fast successful baselines

This was an interrupted partial run, not a completed 3-rep matched comparison.

## Completed Baseline Evidence

| baseline | valid reps | success | first trigger | execs | saved crashes |
| --- | ---: | ---: | ---: | ---: | ---: |
| AFL++ CmpLog | 1 | 1/1 | 207.984s | 3073 | 7 |
| Redqueen/operand | 1 | 1/1 | 203.212s | 3045 | 4 |
| AFL++ vanilla | 0 | n/a | n/a | n/a | n/a |

The vanilla arm hit startup-only failures in two attempted reps. This exposed a
runner bug: `--startup-retries` was applied to CmpLog/Redqueen but not vanilla.
The runner is fixed in the same change so all baseline families receive the
configured startup retry budget.

## Partial FORMTRIG Context

The run was interrupted before the FORMTRIG arms produced a formal gate summary,
so these rows are context only and must not be used as FORMTRIG 600s performance
claims.

| arm | rep | run time | execs | saved crashes |
| --- | ---: | ---: | ---: | ---: |
| FORMTRIG hook | 1 | 621s | 363 | 7 |
| FORMTRIG hook | 2 | 624s | 363 | 7 |
| FORMTRIG hook | 3 | 39s | 48 | 1 |
| FORMTRIG nohook | 1 | 600s | 15869 | 9 |

## Interpretation

Supported:

- B13 remains useful as native-readiness, speedup/control, and runner-regression
  evidence.
- Strong faithful baselines can trigger under the current B13 seed/harness
  within the 600s acceptable threshold.
- The previous 60s hard-gap candidacy is demoted by the 600s screen.

Not supported:

- B13 as hard SOTA-pain main evidence.
- A completed 600s x3 matched comparison from this run.
- A FORMTRIG 600s endpoint-performance claim from this partial run.

Next:

- Use the fixed runner for future GPAC screens.
- Spend hard-pain budget on targets where faithful baselines show flat/binary
  pre-`_T` guidance and late/missing/high-variance endpoint behavior.
- Do not rerun B13 as a main hard-gap target unless the seedbank or harness is
  made materially farther from the terminal state.
