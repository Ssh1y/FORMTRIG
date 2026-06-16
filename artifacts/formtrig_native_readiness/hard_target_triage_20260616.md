# FORMTRIG Hard-Target Triage

This report is benefit-first. A target is promoted only when current
evidence supports a terminal/TTE benefit against matched faithful
baselines, or when it has mechanism evidence and a concrete terminal
oracle gap to close. Targets where matched baselines also trigger are
kept as controls or negative evidence, not main SOTA-gap cases.

Promoted hard-target candidates: `0`.

## Target Queue

| target | disposition | priority | baseline triggers | fastest baseline `_T` | next action |
| --- | --- | ---: | --- | ---: | --- |
| LIBARCHIVE_2936 | `short_gate_needs_signal_refinement` | 35 |  |  | refine BindingSpec/root-state guidance until non-trigger D_F variability appears, then rerun 10-30m FORMTRIG/baseline screen |
| LIBCOAP_CVE_2023_35862 | `demote_to_control_or_negative` | 90 | aflplusplus_cmplog,aflplusplus_vanilla,redqueen_operand | 1060.0 | do not spend main long-run budget here; use as control/evidence plumbing and search harder targets |
| PNG006 | `demote_to_control_or_negative` | 90 | aflplusplus_cmplog | 120.0 | do not spend main long-run budget here; use as control/evidence plumbing and search harder targets |
| LIBXML2_1107 | `demote_harness_artifact` | 99 |  |  | do not use as core evidence; keep only build, BindingSpec, and crash-accounting sanity checks |

## Package Evidence

| comparison | target | status | verdict | successful baselines | benefits | blocked claims |
| --- | --- | --- | --- | --- | --- | --- |
| LIBARCHIVE_2936_formtrig_10m_vs_aflpp_10m_20260616 | LIBARCHIVE_2936 | `needs_signal_refinement` | `short_gate_no_terminal_constant_lift_signal` |  | diagnostic triage benefit: exact native binding and typed mutation executed without endpoint success; diagnostic triage benefit: constant lifted D_F/D_F_spec_lifted identified as the current R2T blocker | no FORMTRIG terminal success is established; no time-to-_T or crash improvement is established; no accepted non-trigger frontier progress is established; D_F and D_F_spec_lifted are constant, so the present guidance is not an effective R2T gradient; replication is one run per arm and Redqueen/operand baseline is still missing |
| LIBCOAP_35862_asan_terminal_30m_vs_asan_baselines_20260616 | LIBCOAP_CVE_2023_35862 | `control_or_negative` | `baseline_also_triggers_not_sota_advantage` | aflplusplus_cmplog,aflplusplus_vanilla,redqueen_operand | FORMTRIG terminal oracle success is observed | no strict pre-trigger guidance benefit is established; FORMTRIG first `_T`/TTE is not recorded for this run; matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage; replication is too low for a final performance claim |
| LIBCOAP_35862_pretrigger_30m_vs_non_asan_baselines_20260616 | LIBCOAP_CVE_2023_35862 | `mechanism_only_needs_terminal_oracle` | `pretrigger_guidance_only` |  | binary or sparse trigger feedback was lifted into accepted non-trigger search progress | no FORMTRIG terminal success is established; FORMTRIG first `_T`/TTE is not recorded for this run; replication is too low for a final performance claim |
| PNG006_formtrig_2h_vs_baseline_30m_gap_20260616 | PNG006 | `incomparable_needs_matched_budget` | `not_comparable_missing_matched_budget` |  | FORMTRIG terminal oracle success is observed; binary or sparse trigger feedback was lifted into accepted non-trigger search progress | FORMTRIG first `_T`/TTE is not recorded for this run; no matched-budget baseline benefit comparison is available |
| PNG006_formtrig_2h_vs_vanilla_2h_incomplete_20260616 | PNG006 | `candidate_needs_required_baselines` | `incomplete_required_baseline_set` |  | FORMTRIG reaches terminal success where matched baselines do not trigger in this budget; FORMTRIG terminal oracle success is observed; binary or sparse trigger feedback was lifted into accepted non-trigger search progress | FORMTRIG first `_T`/TTE is not recorded for this run; required baseline families are still missing; replication is too low for a final performance claim |
| PNG006_formtrig_2h_vs_vanilla_cmplog_2h_incomplete_20260616 | PNG006 | `control_or_negative` | `incomplete_required_baseline_set` | aflplusplus_cmplog | FORMTRIG terminal oracle success is observed; binary or sparse trigger feedback was lifted into accepted non-trigger search progress | FORMTRIG first `_T`/TTE is not recorded for this run; matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage; required baseline families are still missing; replication is too low for a final performance claim |
