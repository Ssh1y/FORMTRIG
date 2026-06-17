# libarchive_2936_matched_7200s_3rep_20260617T070307Z

- target: `LIBARCHIVE_2936`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `not_hard_pain_baseline_fast_enough`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget speedup benefit

Primary benefit statements:
- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 6.96x faster than the fastest matched successful baseline run

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 1.358s
- fastest matched successful baseline-run first `_T` upper bound is 9.456s
- fastest matched successful baseline-family median first `_T` upper bound is 32.517s

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

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| b4_7200s_3rep | 7207 | 10 | true | 161406 | 39964 | 4127 |
| b4_7200s_3rep | 7200 | 23 | true | 113983 | 30850 | 4108 |
| b4_7200s_3rep | 7203 | 46 | true | 138053 | 32418 | 4118 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 7200 | 3 | 1.000 | 52.977 |  | 0 |
| aflplusplus_vanilla | 7200 | 3 | 1.000 | 56.056 |  | 0 |
| redqueen_operand | 7200 | 3 | 1.000 | 32.517 |  | 0 |

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
