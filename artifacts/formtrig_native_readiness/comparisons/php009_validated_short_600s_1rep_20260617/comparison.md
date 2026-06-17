# php009_validated_short_600s_1rep_20260617

- target: `PHP009`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `not_hard_pain_baseline_fast_enough`
- matched baselines: `3`

## Benefit Readout

- summary: current package supports a matched-budget speedup benefit

Primary benefit statements:
- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 1.38x faster than the fastest matched successful baseline run

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 87.04s
- fastest matched successful baseline-run first `_T` upper bound is 120s
- fastest matched successful baseline-family median first `_T` upper bound is 120s

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
  - status: `not_required_for_current_strength`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| php009_formtrig_600s | 600 | 37120 | true | 243121 | 54959 | 12362 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 1.000 | 300 |  | 9 |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 270 |  | 43 |
| redqueen_operand | 600 | 1 | 1.000 | 120 |  | 20 |

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
