# FORMTRIG Benefit-First Experiment Worklist

Endpoint benefit and cost come first; D_F, BindingSpec, dominance frontier, and typed mutation are attribution gates, not cross-tool performance metrics.

Generated: `2026-06-18T13:34:45+00:00`
Tasks: `24`; runnable now: `0`; blocked/gated: `24`; demoted controls skipped: `9`; low-priority skipped: `93`.

## Budget Order

1. Spend long-run budget only on targets with endpoint benefit or validated short-screen readiness.
2. Treat `D_F`, BindingSpec, dominance frontier, and typed mutation as mechanism evidence after endpoint metrics.
3. Keep terminal-only or harness-shaped cases as control/negative evidence.

## Task Summary

| priority | rank | target | source | SOTA pain | action | runnable | benefit to prove |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| P0 | 1 | PDF003 | magma | visible_hard_speedup_or_reliability | expand_cross_target_hard_evidence | blocked | The matched long-run budget is already complete for this target; spend new budget on cross-target hard evidence instead of rerunning the same campaign. |
| P1 | 2 | PHP003 | magma |  | repair_guidance_to_terminal | blocked | The matched short screen already showed strict pre-trigger FORMTRIG guidance and baseline no-guidance pain, but FORMTRIG did not reach terminal _T. Convert the saved non-trigger frontier into a terminal same-oracle outcome before spending another matched-baseline budget. |
| P0 | 3 | LIBXML2_1107 | real_cve |  | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
| P0 | 4 | GPAC_3403 | real_cve |  | validate_replay_then_draft_binding_spec | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P1 | 5 | SQL013 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P1 | 6 | SSL009 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P1 | 7 | PHP010 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P1 | 8 | PHP011 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 9 | SQL015 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 10 | SSL005 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 11 | TIF011 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 12 | TIF014 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 13 | XML003 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 14 | XML004 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 15 | XML010 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 16 | SSL008 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 17 | SSL012 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 18 | SSL017 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 19 | PDF010 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 20 | SSL002 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P3 | 21 | LUA002 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P3 | 22 | PHP001 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P3 | 23 | TIF009 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P3 | 24 | LUA003 | magma |  | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |

## Runnable Now

No main-budget FORMTRIG task is runnable without a gate/blocker being cleared.

## Gated Tasks

### P0 PDF003 - expand_cross_target_hard_evidence

- Benefit to prove: The matched long-run budget is already complete for this target; spend new budget on cross-target hard evidence instead of rerunning the same campaign.
- SOTA pain: `visible_hard_speedup_or_reliability`
- SOTA pain evidence: at least one strong baseline family is unstable or has low success under the matched budget; strength=hard_speedup_or_reliability_candidate; FORMTRIG first_T=0.31s; baseline fastest_T=4530s; baseline family_median_T=4530s; speedup=14612.9x; baseline_visible=aflplusplus_vanilla,redqueen_operand; baseline_guidance_gap.status=measured_pass; pre_T_binary_flat=true; baseline evidence supports a hard binary-TC no-guidance candidate
- Endpoint metrics: replicated matched-budget terminal success rate, first _T / terminal-crash wall-clock time, baseline R2T tail and success-rate variance across targets
- Claim boundary: Use this target as one hard-speedup data point; broad claims still require additional Magma and real-CVE targets.
- Blocking issue:
- none recorded
- Mechanism evidence required after benefit:
- formtrig_terminal_oracle_success
- baseline_guidance_gap_measured
- Current primary benefits:
- FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run
- FORMTRIG observed first-`_T` is 14612.90x faster than the fastest matched successful baseline run
- Post-unblock commands or steps:
- run the next hard Magma/real-CVE target with matched baselines
- prioritize targets where strong baselines have low success or long R2T tails
- add ablations for any target-specific typed hook before main-claim use
- Evidence paths:
- artifacts/formtrig_native_readiness/comparisons/pdf003_matched_7200s_3rep_20260617T224500Z/comparison.json
- artifacts/magma_canary_inventory.json
- artifacts/formtrig_native_readiness/magma_native_builds/PDF003/build_plan.json

### P1 PHP003 - repair_guidance_to_terminal

- Benefit to prove: The matched short screen already showed strict pre-trigger FORMTRIG guidance and baseline no-guidance pain, but FORMTRIG did not reach terminal _T. Convert the saved non-trigger frontier into a terminal same-oracle outcome before spending another matched-baseline budget.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: FORMTRIG terminal success after the saved non-trigger frontier, first _T / execution count after the repair, same Magma/CVE oracle as the matched baseline screen
- Claim boundary: This is a repair target, not a performance target. Do not rerun the same matched short screen until FORMTRIG terminal success or a revised BindingSpec/typed mutation is available.
- Blocking issue:
- no FORMTRIG terminal success is established
- FORMTRIG first `_T`/TTE is not recorded for this run
- Mechanism evidence required after benefit:
- strict_pretrigger_guidance
- Post-unblock commands or steps:
- replay FORMTRIG saved non-trigger queue entries and inspect which role blocks _T
- repair BindingSpec or typed mutation so the non-trigger frontier can cross R2T
- run a FORMTRIG-only terminal gate before repeating faithful baselines
- Evidence paths:
- artifacts/formtrig_native_readiness/comparisons/php003_validated_short_600s_1rep_r2/comparison.json
- artifacts/magma_canary_inventory.json

### P0 LIBXML2_1107 - validate_binding_spec_then_short_screen

- Benefit to prove: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: binding audit pass/fail, accepted non-trigger progress count, short-screen first _T/TTE after validation
- Claim boundary: Validation is a gate, not an efficacy result.
- Blocking issue:
- no external PoC/input link recorded
- no vulnerable/fix commit link recorded
- BindingSpec candidate is not native-site-map validated
- Mechanism evidence required after benefit:
- native site-map validation
- lift audit pass
- binding-signal diagnosis pass
- seed readiness with reached non-trigger seeds
- Post-unblock commands or steps:
- run short FORMTRIG gate and same-budget AFL++ family baselines
- Evidence paths:
- artifacts/cve_bench_candidate_audit.json

### P0 GPAC_3403 - validate_replay_then_draft_binding_spec

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- validate vulnerable build and PoC replay
- write harness admissibility note
- draft BindingSpec and run binding-signal sweep
- Evidence paths:
- artifacts/cve_bench_candidate_audit.json

### P1 SQL013 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL013.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 SSL009 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL009.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 PHP010 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP010.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 PHP011 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PHP011 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP011.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SQL015 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SQL015 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL015.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SSL005 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL005 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL005.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 TIF011 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id TIF011 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF011.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 TIF014 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id TIF014 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF014.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 XML003 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id XML003 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/XML003.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 XML004 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id XML004 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/XML004.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 XML010 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id XML010 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/XML010.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SSL008 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL008 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL008.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SSL012 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL012 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL012.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SSL017 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL017 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL017.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 PDF010 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PDF010 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF010.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SSL002 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL002 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL002.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P3 LUA002 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id LUA002 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/LUA002.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P3 PHP001 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PHP001 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP001.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P3 TIF009 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id TIF009 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF009.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P3 LUA003 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
- SOTA pain: `not recorded`
- SOTA pain evidence: not recorded
- Endpoint metrics: 10m same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, baseline-visible vs FORMTRIG-only endpoint behavior
- Claim boundary: Do not spend 2h budget or make performance claims until the short screen has endpoint benefit; use failed screens as negative/control evidence.
- Blocking issue:
- no BindingSpec candidate exists yet
- no comparison package exists yet
- Mechanism evidence required after benefit:
- BindingSpec compiles against native site ids
- D_F_spec_lifted is non-constant before _T
- saved non-trigger progress is replay-stable
- typed mutation, if used, is BindingSpec-provenance tagged
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id LUA003 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/LUA003.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

## Skipped Controls

| rank | target | lane | disposition/status | SOTA pain | reason |
| ---: | --- | --- | --- | --- | --- |
| 139 | LIBARCHIVE_2936 | control_or_negative | demote_to_control_or_negative | not_visible_baseline_time_cost_acceptable | sota_pain_triage_not_main_budget |
| 140 | TIF012 | control_or_negative | demote_to_control_or_negative | not_visible_baseline_time_cost_acceptable | sota_pain_triage_not_main_budget |
| 141 | PHP009 | control_or_negative | demote_to_control_or_negative | not_visible_baseline_time_cost_acceptable | sota_pain_triage_not_main_budget |
| 142 | PNG006 | control_or_negative | demote_to_control_or_negative | not_visible_baseline_visible_no_formtrig_advantage | sota_pain_triage_not_main_budget |
| 143 | SSL011 | control_or_negative | do_not_promote |  | control_or_negative_not_main_budget |
| 144 | SSL015 | control_or_negative | do_not_promote |  | control_or_negative_not_main_budget |
| 145 | PNG007 | control_or_negative | do_not_promote |  | control_or_negative_not_main_budget |
| 146 | PDF016 | control_or_negative | demote_to_control_or_negative | not_visible_baseline_visible_no_formtrig_advantage | sota_pain_triage_not_main_budget |
| 147 | LIBCOAP_CVE_2023_35862 | control_or_negative | demote_to_control_or_negative | not_visible_baseline_visible_no_formtrig_advantage | sota_pain_triage_not_main_budget |
