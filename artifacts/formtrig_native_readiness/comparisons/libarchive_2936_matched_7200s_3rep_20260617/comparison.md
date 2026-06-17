# libarchive_2936_matched_7200s_3rep_20260617T070307Z

- target: `LIBARCHIVE_2936`
- verdict: `positive_speedup_matched_comparison`
- main claim strength: `weak_near_seed_or_harness_shaped_speedup`
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
- current experiment is too near-trigger or harness-shaped to serve as main SOTA-gap evidence

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`
- `experiment_strength_gate`

## Experiment Strength

- main claim strength: `weak_near_seed_or_harness_shaped_speedup`
- reasons:
  - `all_required_baseline_families_trigger_in_replicated_runs`
  - `baseline_family_median_trigger_time_is_under_60s`
- required design actions:
  - do not spend main hard-evidence budget on this harness shape alone
  - rerun with a higher-fidelity/raw-format harness or a farther RNT seed
  - add no-hook and generic-hook FORMTRIG ablations to measure target-specific hook contribution
  - prioritize targets where at least one strong baseline family has low success rate or long median R2T

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig | 7207 | 10 | true | 161406 | 39964 | 4127 |
| formtrig | 7200 | 23 | true | 113983 | 30850 | 4108 |
| formtrig | 7203 | 46 | true | 138053 | 32418 | 4118 |

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
- `weak_near_seed_or_harness_shaped_speedup`

## Required Next Steps

- treat this as a speedup claim and complete repetitions/longer runs before final performance claims
- do not spend main hard-evidence budget on this harness shape alone
- rerun with a higher-fidelity/raw-format harness or a farther RNT seed
- add no-hook and generic-hook FORMTRIG ablations to measure target-specific hook contribution
- prioritize targets where at least one strong baseline family has low success rate or long median R2T
