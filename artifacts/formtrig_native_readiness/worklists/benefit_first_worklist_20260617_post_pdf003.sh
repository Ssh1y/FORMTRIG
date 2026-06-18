#!/usr/bin/env bash
set -euo pipefail

# Generated FORMTRIG benefit-first runnable commands.
# Gated tasks are intentionally emitted as comments.

# P0 PDF003 monitor_active_matched_longrun
# benefit: Confirm that the current matched-budget endpoint benefit persists in 3 matched 7200s repetitions: FORMTRIG reaches _T while faithful baselines do not.
# blocked: active matched longrun status=running; wait for all expected baseline run_record.json files before final claims; active run root: artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z
# post-unblock: python3 tools/merge_magma_baseline_roots.py --out artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/merged_baselines --source artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/baselines --source artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard_7200s_20260618T014149Z --duplicate-policy prefer-later
# post-unblock: scripts/finalize_magma_matched_run.sh --run-root artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z --baseline-dir artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/merged_baselines --guidance-out artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf003_matched_7200s_3rep_20260617T224500Z --comparison-out artifacts/formtrig_native_readiness/comparisons/pdf003_matched_7200s_3rep_20260617T224500Z

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
