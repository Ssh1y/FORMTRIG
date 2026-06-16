# FORMTRIG Benefit-First Experiment Worklist

Endpoint benefit and cost come first; D_F, BindingSpec, dominance frontier, and typed mutation are attribution gates, not cross-tool performance metrics.

Generated: `2026-06-16T22:12:03+00:00`
Tasks: `12`; runnable now: `1`; blocked/gated: `11`; demoted controls skipped: `4`; low-priority skipped: `93`.

## Budget Order

1. Spend long-run budget only on targets with endpoint benefit or validated short-screen readiness.
2. Treat `D_F`, BindingSpec, dominance frontier, and typed mutation as mechanism evidence after endpoint metrics.
3. Keep terminal-only or harness-shaped cases as control/negative evidence.

## Task Summary

| priority | rank | target | source | action | runnable | benefit to prove |
| --- | ---: | --- | --- | --- | --- | --- |
| P0 | 1 | LIBARCHIVE_2936 | real_cve | extend_matched_longrun | yes | Confirm that the current first-_T speedup and lower execution cost persist in 3 matched 7200s repetitions. |
| P1 | 2 | PDF003 | magma | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
| P1 | 3 | SSL011 | magma | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
| P1 | 4 | SSL015 | magma | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
| P0 | 5 | TIF012 | magma | extend_matched_longrun | blocked | Confirm that the current matched-budget endpoint benefit persists in 3 matched 7200s repetitions: FORMTRIG reaches _T while faithful baselines do not. |
| P1 | 6 | PDF016 | magma | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
| P1 | 7 | PHP009 | magma | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
| P1 | 8 | GPAC_3403 | real_cve | validate_replay_then_draft_binding_spec | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 9 | SQL013 | magma | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 10 | SSL009 | magma | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 11 | PHP003 | magma | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |
| P2 | 12 | PHP010 | magma | draft_binding_spec_then_short_screen | blocked | Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines. |

## Runnable Now

### P0 LIBARCHIVE_2936

- Benefit: Confirm that the current first-_T speedup and lower execution cost persist in 3 matched 7200s repetitions.
- Command: `scripts/run_libarchive_2936_matched_longrun.sh --duration 7200 --reps 3 --jobs 4`

## Gated Tasks

### P1 PDF003 - validate_binding_spec_then_short_screen

- Benefit to prove: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
- Endpoint metrics: binding audit pass/fail, accepted non-trigger progress count, short-screen first _T/TTE after validation
- Claim boundary: Validation is a gate, not an efficacy result.
- Blocking issue:
- BindingSpec candidate is not native-site-map validated
- no comparison package exists yet
- Mechanism evidence required after benefit:
- native site-map validation
- lift audit pass
- binding-signal diagnosis pass
- seed readiness with reached non-trigger seeds
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PDF003 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF003.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 SSL011 - validate_binding_spec_then_short_screen

- Benefit to prove: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
- Endpoint metrics: binding audit pass/fail, accepted non-trigger progress count, short-screen first _T/TTE after validation
- Claim boundary: Validation is a gate, not an efficacy result.
- Blocking issue:
- BindingSpec candidate is not native-site-map validated
- no comparison package exists yet
- Mechanism evidence required after benefit:
- native site-map validation
- lift audit pass
- binding-signal diagnosis pass
- seed readiness with reached non-trigger seeds
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL011 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL011.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 SSL015 - validate_binding_spec_then_short_screen

- Benefit to prove: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
- Endpoint metrics: binding audit pass/fail, accepted non-trigger progress count, short-screen first _T/TTE after validation
- Claim boundary: Validation is a gate, not an efficacy result.
- Blocking issue:
- BindingSpec candidate is not native-site-map validated
- no comparison package exists yet
- Mechanism evidence required after benefit:
- native site-map validation
- lift audit pass
- binding-signal diagnosis pass
- seed readiness with reached non-trigger seeds
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id SSL015 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL015.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P0 TIF012 - extend_matched_longrun

- Benefit to prove: Confirm that the current matched-budget endpoint benefit persists in 3 matched 7200s repetitions: FORMTRIG reaches _T while faithful baselines do not.
- Endpoint metrics: same-budget terminal success rate, first _T / terminal-crash wall-clock time, first _T / terminal-crash execution count, PRET/TTE under the same seed corpus and oracle
- Claim boundary: Report as speedup/attribution unless long-run matched baselines stop triggering while FORMTRIG remains successful.
- Blocking issue:
- no single reusable matched long-run runner currently coordinates this Magma target and rebuilds the comparison package
- use the recorded TIF012 b5 manifest list and regenerate the comparison package after both arms finish
- Mechanism evidence required after benefit:
- strict_pretrigger_guidance
- formtrig_terminal_oracle_success
- matched_budget_endpoint_success
- Current primary benefits:
- FORMTRIG reaches terminal success where matched baselines do not trigger in this budget
- Post-unblock commands or steps:
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF012.b5_current_3rep.list --duration 7200 --jobs 4 --continue-on-fail --out-root 'artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_formtrig'
- scripts/run_magma_baselines.sh --target-id TIF012 --durations 7200 --jobs 4 --out 'artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_baselines' --reps 3
- scripts/formtrig_experiment_gate.sh --suite TIF012_b5_7200s_3rep --out 'artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_formtrig/gate' --min-runtime 7200 --run 'rep1=artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_formtrig/001_TIF012/out' --run 'rep2=artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_formtrig/002_TIF012/out' --run 'rep3=artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_formtrig/003_TIF012/out'
- python3 tools/compare_formtrig_baselines.py --comparison-id 'tif012_b5_matched_7200s_3rep_<UTC>' --target-id TIF012 --formtrig-gate 'b5_7200s_3rep=artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_formtrig/gate/gate_summary.csv' --baseline-summary 'aflpp_family_7200s_3rep=artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_<UTC>_baselines/summary.json' --out-dir 'artifacts/formtrig_native_readiness/comparisons/tif012_b5_matched_7200s_3rep_<UTC>' --min-reps 3 --required-baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
- Evidence paths:
- artifacts/formtrig_native_readiness/comparisons/tif012_b5_formtrig_120s_3rep_vs_aflpp_family_120s_3rep_20260616/comparison.json
- artifacts/magma_canary_inventory.json

### P1 PDF016 - validate_binding_spec_then_short_screen

- Benefit to prove: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
- Endpoint metrics: binding audit pass/fail, accepted non-trigger progress count, short-screen first _T/TTE after validation
- Claim boundary: Validation is a gate, not an efficacy result.
- Blocking issue:
- BindingSpec candidate is not native-site-map validated
- no comparison package exists yet
- Mechanism evidence required after benefit:
- native site-map validation
- lift audit pass
- binding-signal diagnosis pass
- seed readiness with reached non-trigger seeds
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PDF016 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF016.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 PHP009 - validate_binding_spec_then_short_screen

- Benefit to prove: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
- Endpoint metrics: binding audit pass/fail, accepted non-trigger progress count, short-screen first _T/TTE after validation
- Claim boundary: Validation is a gate, not an efficacy result.
- Blocking issue:
- BindingSpec candidate is not native-site-map validated
- no comparison package exists yet
- Mechanism evidence required after benefit:
- native site-map validation
- lift audit pass
- binding-signal diagnosis pass
- seed readiness with reached non-trigger seeds
- Post-unblock commands or steps:
- scripts/run_magma_baselines.sh --target-id PHP009 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP009.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 GPAC_3403 - validate_replay_then_draft_binding_spec

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
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

### P2 SQL013 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
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
- scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL013.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 SSL009 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
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
- scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL009.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 PHP003 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
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
- scripts/run_magma_baselines.sh --target-id PHP003 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP003.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P2 PHP010 - draft_binding_spec_then_short_screen

- Benefit to prove: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
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
- scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 4 --reps 3
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP010.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

## Skipped Controls

| rank | target | lane | disposition/status | reason |
| ---: | --- | --- | --- | --- |
| 144 | PNG006 | control_or_negative | demote_to_control_or_negative | control_or_negative_not_main_budget |
| 145 | PNG007 | control_or_negative | do_not_promote | control_or_negative_not_main_budget |
| 146 | LIBXML2_1107 | control_or_negative | demote_harness_artifact | control_or_negative_not_main_budget |
| 147 | LIBCOAP_CVE_2023_35862 | control_or_negative | demote_to_control_or_negative | control_or_negative_not_main_budget |
