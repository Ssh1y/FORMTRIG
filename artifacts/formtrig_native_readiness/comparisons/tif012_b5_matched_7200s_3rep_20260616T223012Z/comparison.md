# tif012_matched_7200s_3rep_20260618T022236Z

- target: `TIF012`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `not_hard_pain_baseline_fast_enough`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget speedup benefit

Primary benefit statements:
- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 6176.47x faster than the fastest matched successful baseline run

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 0.034s
- fastest matched successful baseline-run first `_T` upper bound is 210s
- fastest matched successful baseline-family median first `_T` upper bound is 1410s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- a matched faithful baseline reaches the trigger within the acceptable-time threshold, so this is not hard SOTA-pain evidence

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`
- `experiment_strength_gate`

## Experiment Strength

- main claim strength: `not_hard_pain_baseline_fast_enough`
- reasons:
  - `baseline_fastest_trigger_time_is_under_acceptable_threshold`
- required design actions:
  - treat as speedup/control evidence, not hard SOTA-pain evidence
  - move main budget to targets where no faithful baseline triggers within the acceptable-time threshold
  - if retained, report only FORMTRIG TTE speedup and mechanism attribution
- baseline no-guidance proof:
  - required for hard SOTA-pain: `false`
  - status: `fail_fast_baseline`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance
  - source: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/baseline_guidance_gap/tif012_b5_matched_7200s_3rep_20260616T223012Z/baseline_guidance_gap.json`
  - interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| typed_hook_7200s_3rep | 7200 | 1379546 | false | 2749423 | 1647188 | 165507 |
| typed_hook_7200s_3rep | 7200 | 1234445 | true | 3993820 | 1893870 | 149750 |
| typed_hook_7200s_3rep | 7200 | 2045147 | false | 3947580 | 2518098 | 239540 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 0.333 | 4950 |  | 0 |
| aflplusplus_vanilla | 7200 | 3 | 1.000 | 1410 |  | 28536 |
| redqueen_operand | 7200 | 3 | 0.667 | 3375 |  | 3841 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `matched_baseline_also_triggers`
- `formtrig_faster_than_successful_baselines`
- `not_hard_pain_baseline_fast_enough`

## Required Next Steps

- treat as speedup/control evidence, not hard SOTA-pain evidence
- move main budget to targets where no faithful baseline triggers within the acceptable-time threshold
- if retained, report only FORMTRIG TTE speedup and mechanism attribution
