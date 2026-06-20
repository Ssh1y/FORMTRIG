# gpac3403_b13_60s3rep_repaired_baselines_20260620

- target: `GPAC_3403`
- verdict: `positive_endpoint_matched_comparison`
- main claim strength: `hard_endpoint_gap_candidate`
- matched baselines: `9`

## Benefit Readout

- summary: current package supports a matched-budget primary endpoint benefit

Primary benefit statements:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget

Endpoint observations:
- FORMTRIG terminal oracle success is observed
- FORMTRIG first `_T` upper bound is recorded at 2.39s

Mechanism benefits:
- binary or sparse trigger feedback was lifted into accepted non-trigger search progress

Blocked or not-yet-supported statements:
- baseline no-guidance proof is under-budgeted: flat/binary pre-_T evidence is present, but the matched runs are shorter than the acceptable trigger threshold

Design evidence used for attribution:
- `strict_pretrigger_guidance`
- `formtrig_terminal_oracle_success`
- `matched_budget_endpoint_success`
- `baseline_guidance_gap_required`

## Experiment Strength

- main claim strength: `hard_endpoint_gap_candidate`
- reasons:
  - `matched_baselines_do_not_trigger`
- required design actions:
  - promote to replicated long-run or cross-target confirmation if harness fidelity passes
- baseline no-guidance proof:
  - required for hard SOTA-pain: `true`
  - status: `under_budgeted`
  - required evidence: baseline-visible TC signal is flat or binary before _T
  - required evidence: accepted non-trigger improvement under the baseline-visible signal is absent
  - required evidence: matched repeated endpoint runs are late, missing, or high-variance
  - source: `artifacts/formtrig_native_readiness/baseline_guidance_gap/gpac3403_b13_scal_ref_payload_matched_screen_60s3rep_repaired_baselines_20260620/baseline_guidance_gap.json`
  - interpretation: baseline runs are shorter than the acceptable trigger threshold, so missing triggers only support a short-screen gap

## FORMTRIG Runs

| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| formtrig | 60 | 2 | true | 147 | 146 | 70 |
| formtrig | 60 | 2 | true | 147 | 146 | 70 |
| formtrig | 60 | 2 | true | 147 | 146 | 70 |
| formtrig_nohook | 60 | 4 | true | 1899 | 1896 | 1233 |
| formtrig_nohook | 60 | 1 | true | 2118 | 2118 | 1551 |
| formtrig_nohook | 60 | 0 | true | 1622 | 1623 | 1020 |

## Matched Baseline Groups

| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aflplusplus_cmplog | 60 | 3 | 0.000 |  |  | 0 |
| aflplusplus_vanilla | 60 | 3 | 0.000 |  |  | 0 |
| redqueen_operand | 60 | 3 | 0.000 |  |  | 0 |

## Reasons

- `formtrig_strict_pretrigger_guidance_present`
- `formtrig_terminal_oracle_present`
- `formtrig_endpoint_where_matched_baselines_do_not_trigger`
