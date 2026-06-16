#!/usr/bin/env bash
set -euo pipefail

# Generated FORMTRIG benefit-first runnable commands.
# Gated tasks are intentionally emitted as comments.

# P0 LIBARCHIVE_2936 extend_matched_longrun
# benefit: Confirm that the current first-_T speedup and lower execution cost persist in 3 matched 7200s repetitions.
scripts/run_libarchive_2936_matched_longrun.sh --duration 7200 --reps 3 --jobs 4

# P1 PDF003 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PDF003 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF003.list --duration 600 --jobs 4 --continue-on-fail

# P1 SSL011 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL011 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL011.list --duration 600 --jobs 4 --continue-on-fail

# P1 SSL015 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL015 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL015.list --duration 600 --jobs 4 --continue-on-fail

# P0 TIF012 extend_matched_longrun
# benefit: Confirm that the current matched-budget endpoint benefit persists in 3 matched 7200s repetitions: FORMTRIG reaches _T while faithful baselines do not.
scripts/run_tif012_b5_matched_longrun.sh --duration 7200 --reps 3 --jobs 4

# P1 PDF016 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PDF016 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF016.list --duration 600 --jobs 4 --continue-on-fail

# P1 PHP009 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP009 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP009.list --duration 600 --jobs 4 --continue-on-fail

# P1 GPAC_3403 validate_replay_then_draft_binding_spec
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet
# post-unblock: validate vulnerable build and PoC replay
# post-unblock: write harness admissibility note
# post-unblock: draft BindingSpec and run binding-signal sweep

# P2 SQL013 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL013.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL009 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL009.list --duration 600 --jobs 4 --continue-on-fail

# P2 PHP003 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP003 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP003.list --duration 600 --jobs 4 --continue-on-fail

# P2 PHP010 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 4 --reps 3
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP010.list --duration 600 --jobs 4 --continue-on-fail
