# php003_native_b4_same_runner_600s_1rep_20260618

- target: `PHP003`
- verdict: `speedup_but_under_replicated`
- main claim strength: `not_hard_pain_baseline_fast_enough`
- matched baselines: `3`

## Benefit Readout

- summary: current package supports a matched-budget speedup benefit, subject to replication

Primary benefit statements:
- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 90.68x faster than the fastest matched successful baseline run

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 1.985s
- fastest matched successful baseline-run first `_T` upper bound is 180s
- fastest matched successful baseline-family median first `_T` upper bound is 180s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- replication is too low for a final performance claim
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
  - source: `artifacts/formtrig_native_readiness/baseline_guidance_gap/php003_native_b4_same_runner_600s_1rep_20260618/baseline_guidance_gap.json`
  - interpretation: a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence

## Current-ABI Follow-Up

- Readout: `artifacts/formtrig_native_readiness/comparisons/php003_native_b4_same_runner_600s_1rep_20260618/current_abi_readout_20260619.md`
- Current-ABI validation: `artifacts/formtrig_native_readiness/binding_validation/PHP003.native_b4_thumbnail_length_hook_candidate.current_abi.validation.json`
- Current-ABI 20s validation confirms the same B4 repaired-runner path still reaches terminal `_T` with accepted non-trigger lift guidance.
- The 600s FORMTRIG arm in this package used the older standalone AFL++ checkout, so rerun the 600s FORMTRIG arm with the ABI-current AFL++ path before treating PHP003 as final performance evidence.

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig_600s | 600 | 21024 | true | 190828 | 52269 | 8721 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 600 | 1 | 1.000 | 180 |  | 31 |
| redqueen_operand | 600 | 1 | 1.000 | 330 |  | 11 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `low_replication`
- `matched_baseline_also_triggers`
- `formtrig_faster_than_successful_baselines`
- `not_hard_pain_baseline_fast_enough`

## Required Next Steps

- collect at least 3 repetitions per matched baseline/budget
- treat as speedup/control evidence, not hard SOTA-pain evidence
- move main budget to targets where no faithful baseline triggers within the acceptable-time threshold
- if retained, report only FORMTRIG TTE speedup and mechanism attribution
