# php003_validated_short_600s_1rep_r2

- target: `PHP003`
- verdict: `pretrigger_guidance_only`
- main claim strength: `not_supporting_main_claim`
- matched baselines: `3`

## Benefit Readout

- summary: current package supports mechanism/search-guidance benefit, subject to remaining blockers

Primary benefit statements:
- none

Endpoint observations:
- none

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- no FORMTRIG terminal success is established
- FORMTRIG first `_T`/TTE is not recorded for this run

Design evidence used for attribution:
- `strict_pretrigger_guidance`

## Experiment Strength

- main claim strength: `not_supporting_main_claim`
- reasons:
  - `no_endpoint_or_speedup_advantage_for_formtrig`
  - `baseline_guidance_gap_measured_pass`
- required design actions:
  - repair BindingSpec/mutation design or move budget to a harder target
- baseline no-guidance proof:
  - required for hard SOTA-pain: `false`
  - status: `measured_pass`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance
  - source: `artifacts/formtrig_native_readiness/baseline_guidance_gap/php003_validated_short_600s_1rep_r2/baseline_guidance_gap.json`
  - interpretation: baseline evidence supports a hard binary-TC no-guidance candidate

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig_600s_1rep | 600 | 0 | true | 205673 | 121014 | 4203 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 600 | 1 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 600 | 1 | 0.000 |  |  | 0 |
| redqueen_operand | 600 | 1 | 0.000 |  |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_missing`
- `baseline_guidance_gap_measured_pass`

## Required Next Steps

- pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims
