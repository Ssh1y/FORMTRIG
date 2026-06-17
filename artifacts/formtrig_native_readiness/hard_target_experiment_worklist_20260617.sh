#!/usr/bin/env bash
set -euo pipefail

# Generated FORMTRIG benefit-first runnable commands.
# Gated tasks are intentionally emitted as comments.

# P0 LIBARCHIVE_2936 improve_experiment_design
# benefit: Make the experiment hard enough to expose SOTA R2T pain: current speedup is real, but matched baselines trigger too early for this package to serve as main binary-TC gap evidence.
# blocked: main_claim_strength=weak_near_seed_or_harness_shaped_speedup; current comparison is not hard enough for SOTA-gap evidence
# post-unblock: do not spend main hard-evidence budget on this harness shape alone
# post-unblock: rerun with a higher-fidelity/raw-format harness or a farther RNT seed
# post-unblock: add no-hook and generic-hook FORMTRIG ablations to measure target-specific hook contribution
# post-unblock: prioritize targets where at least one strong baseline family has low success rate or long median R2T

# P1 PDF003 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PDF003 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF003.list --duration 600 --jobs 4 --continue-on-fail

# P1 SSL011 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL011 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL011.list --duration 600 --jobs 4 --continue-on-fail

# P1 SSL015 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL015 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL015.list --duration 600 --jobs 4 --continue-on-fail

# P0 TIF012 expand_cross_target_hard_evidence
# benefit: The matched long-run budget is already complete for this target; spend new budget on cross-target hard evidence instead of rerunning the same campaign.
# blocked: blocked
# post-unblock: run the next hard Magma/real-CVE target with matched baselines
# post-unblock: prioritize targets where strong baselines have low success or long R2T tails
# post-unblock: add ablations for any target-specific typed hook before main-claim use

# P1 PDF016 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PDF016 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF016.list --duration 600 --jobs 4 --continue-on-fail

# P1 PHP009 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP009 --durations 600 --jobs 4
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
# post-unblock: scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL013.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL009 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL009.list --duration 600 --jobs 4 --continue-on-fail

# P2 PHP003 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP003 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP003.list --duration 600 --jobs 4 --continue-on-fail

# P2 PHP010 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP010.list --duration 600 --jobs 4 --continue-on-fail
