# FORMTRIG Benefit-First Experiment Worklist

Endpoint benefit and cost come first; D_F, BindingSpec, dominance frontier, and typed mutation are attribution gates, not cross-tool performance metrics.

Generated: `2026-06-16T16:59:05+00:00`
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
| P1 | 5 | TIF012 | magma | validate_binding_spec_then_short_screen | blocked | Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance. |
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
- scripts/run_magma_baselines.sh --target-id PDF003 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id SSL011 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id SSL015 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL015.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
- artifacts/magma_canary_inventory.json

### P1 TIF012 - validate_binding_spec_then_short_screen

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
- scripts/run_magma_baselines.sh --target-id TIF012 --durations 600 --jobs 4
- scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF012.list --duration 600 --jobs 4 --continue-on-fail
- Evidence paths:
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
- scripts/run_magma_baselines.sh --target-id PDF016 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id PHP009 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id PHP003 --durations 600 --jobs 4
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
- scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 4
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
