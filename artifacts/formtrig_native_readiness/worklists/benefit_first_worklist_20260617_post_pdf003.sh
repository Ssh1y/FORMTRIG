#!/usr/bin/env bash
set -euo pipefail

# Generated FORMTRIG benefit-first runnable commands.
# Gated tasks are intentionally emitted as comments.

# P0 PDF003 extend_matched_longrun
# benefit: Confirm that the current matched-budget endpoint benefit persists in 3 matched 7200s repetitions: FORMTRIG reaches _T while faithful baselines do not.
scripts/run_magma_baselines.sh --target-id PDF003 --durations 7200 --jobs 3 --out artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_baselines --afl-arg -t --afl-arg 5000 --reps 3 && scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF003.current_3rep.list --duration 7200 --jobs 3 --continue-on-fail --out-root artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_formtrig && scripts/formtrig_experiment_gate.sh --suite PDF003_7200s_3rep --out artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_formtrig/gate --min-runtime 7200 --run rep1=artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_formtrig/001_PDF003/out --run rep2=artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_formtrig/002_PDF003/out --run rep3=artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_formtrig/003_PDF003/out && python3 tools/analyze_baseline_guidance_gap.py --analysis-id pdf003_matched_7200s_3rep_20260617T222410Z_baseline_guidance_gap --target-id PDF003 --baseline-summary aflpp_family_7200s_3rep=artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_baselines/summary.json --out-dir artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf003_matched_7200s_3rep_20260617T222410Z --required-baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand --min-reps 3 --acceptable-trigger-s 600 --hard-trigger-s 1800 && python3 tools/compare_formtrig_baselines.py --comparison-id pdf003_matched_7200s_3rep_20260617T222410Z --target-id PDF003 --formtrig-gate typed_hook_7200s_3rep=artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_formtrig/gate/gate_summary.csv --baseline-summary aflpp_family_7200s_3rep=artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T222410Z_baselines/summary.json --baseline-guidance-gap artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf003_matched_7200s_3rep_20260617T222410Z --out-dir artifacts/formtrig_native_readiness/comparisons/pdf003_matched_7200s_3rep_20260617T222410Z --min-reps 3 --required-baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand

# P1 SSL015 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL015 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL015.list --duration 600 --jobs 3 --continue-on-fail

# P1 PDF016 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PDF016 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF016.list --duration 600 --jobs 3 --continue-on-fail

# P1 LIBXML2_1107 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: no external PoC/input link recorded; no vulnerable/fix commit link recorded; BindingSpec candidate is not native-site-map validated
# post-unblock: run short FORMTRIG gate and same-budget AFL++ family baselines

# P1 GPAC_3403 validate_replay_then_draft_binding_spec
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet
# post-unblock: validate vulnerable build and PoC replay
# post-unblock: write harness admissibility note
# post-unblock: draft BindingSpec and run binding-signal sweep

# P2 SQL013 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL013.list --duration 600 --jobs 3 --continue-on-fail

# P2 SSL009 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL009.list --duration 600 --jobs 3 --continue-on-fail

# P2 PHP003 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP003 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP003.list --duration 600 --jobs 3 --continue-on-fail

# P2 PHP010 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP010.list --duration 600 --jobs 3 --continue-on-fail

# P2 PHP011 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP011 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP011.list --duration 600 --jobs 3 --continue-on-fail

# P2 SQL015 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SQL015 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL015.list --duration 600 --jobs 3 --continue-on-fail

# P2 SSL005 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL005 --durations 600 --jobs 3 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL005.list --duration 600 --jobs 3 --continue-on-fail
