# pdf003_matched_7200s_3rep_20260618T040544Z

- target: `PDF003`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `hard_speedup_or_reliability_candidate`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget speedup benefit

Primary benefit statements:
- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 14612.90x faster than the fastest matched successful baseline run

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 0.31s
- fastest matched successful baseline-run first `_T` upper bound is 4530s
- fastest matched successful baseline-family median first `_T` upper bound is 4530s

Mechanism benefits:
- none

Blocked or not-yet-supported statements:
- no strict pre-trigger guidance benefit is established

Design evidence used for attribution:
- `formtrig_terminal_oracle_success`
- `baseline_guidance_gap_measured`

## Experiment Strength

- main claim strength: `hard_speedup_or_reliability_candidate`
- reasons:
  - `some_required_baseline_families_fail_or_are_unstable`
  - `baseline_guidance_gap_measured_pass`
- required design actions:
  - quantify success-rate and TTE-tail improvement with additional repetitions
- baseline no-guidance proof:
  - required for hard SOTA-pain: `true`
  - status: `measured_pass`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance
  - source: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf003_matched_7200s_3rep_20260617T224500Z/baseline_guidance_gap.json`
  - interpretation: baseline evidence supports a hard binary-TC no-guidance candidate

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| typed_hook_7200s_3rep | 7200 | 7693 | false | 33540 | 13492 | 3758 |
| typed_hook_7200s_3rep | 7200 | 7246 | false | 33841 | 18868 | 4563 |
| typed_hook_7200s_3rep | 7201 | 6607 | false | 29732 | 14680 | 4621 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 7200 | 3 | 0.333 | 5670 |  | 0 |
| redqueen_operand | 7200 | 3 | 0.333 | 4530 |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_missing`
- `formtrig_terminal_oracle_present`
- `matched_baseline_also_triggers`
- `formtrig_faster_than_successful_baselines`
- `baseline_guidance_gap_measured_pass`

## Required Next Steps

- treat this as a speedup claim and complete repetitions/longer runs before final performance claims
