#!/usr/bin/env bash
set -euo pipefail

# Generated FORMTRIG benefit-first runnable commands.
# Gated tasks are intentionally emitted as comments.

# P0 PDF003 expand_cross_target_hard_evidence
# benefit: The matched long-run budget is already complete for this target; spend new budget on cross-target hard evidence instead of rerunning the same campaign.
# blocked: blocked
# post-unblock: run the next hard Magma/real-CVE target with matched baselines
# post-unblock: prioritize targets where strong baselines have low success or long R2T tails
# post-unblock: add ablations for any target-specific typed hook before main-claim use

# P1 PHP003 run_validated_matched_short_screen
# benefit: Now that BindingSpec guidance is validated, test endpoint benefit against faithful AFL++ family baselines under the same budget. Promote only if baseline binary TC remains flat before _T and FORMTRIG improves terminal success, TTE, or execution cost.
scripts/run_magma_baselines.sh --target-id PHP003 --durations 600 --jobs 4 --out artifacts/formtrig_native_readiness/raw/php003_validated_short_600s_1rep_baselines --program exif_thumbnail --args-template @@ && scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP003.current_1rep.list --duration 600 --jobs 4 --continue-on-fail --out-root artifacts/formtrig_native_readiness/raw/php003_validated_short_600s_1rep_formtrig

# P0 LIBXML2_1107 validate_binding_spec_then_short_screen
# benefit: Before comparing performance, prove that the candidate BindingSpec creates replay-stable pre-trigger guidance.
# blocked: no external PoC/input link recorded; no vulnerable/fix commit link recorded; BindingSpec candidate is not native-site-map validated
# post-unblock: run short FORMTRIG gate and same-budget AFL++ family baselines

# P0 GPAC_3403 validate_replay_then_draft_binding_spec
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet
# post-unblock: validate vulnerable build and PoC replay
# post-unblock: write harness admissibility note
# post-unblock: draft BindingSpec and run binding-signal sweep

# P1 SQL013 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL013.list --duration 600 --jobs 4 --continue-on-fail

# P1 SSL009 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL009.list --duration 600 --jobs 4 --continue-on-fail

# P1 PHP010 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP010.list --duration 600 --jobs 4 --continue-on-fail

# P1 PHP011 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP011 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP011.list --duration 600 --jobs 4 --continue-on-fail

# P2 SQL015 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SQL015 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SQL015.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL005 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL005 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL005.list --duration 600 --jobs 4 --continue-on-fail

# P2 TIF011 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id TIF011 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF011.list --duration 600 --jobs 4 --continue-on-fail

# P2 TIF014 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id TIF014 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF014.list --duration 600 --jobs 4 --continue-on-fail

# P2 XML003 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id XML003 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/XML003.list --duration 600 --jobs 4 --continue-on-fail

# P2 XML004 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id XML004 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/XML004.list --duration 600 --jobs 4 --continue-on-fail

# P2 XML010 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id XML010 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/XML010.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL008 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL008 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL008.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL012 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL012 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL012.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL017 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL017 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL017.list --duration 600 --jobs 4 --continue-on-fail

# P2 PDF010 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PDF010 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PDF010.list --duration 600 --jobs 4 --continue-on-fail

# P2 SSL002 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id SSL002 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/SSL002.list --duration 600 --jobs 4 --continue-on-fail

# P3 LUA002 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id LUA002 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/LUA002.list --duration 600 --jobs 4 --continue-on-fail

# P3 PHP001 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id PHP001 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/PHP001.list --duration 600 --jobs 4 --continue-on-fail

# P3 TIF009 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id TIF009 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/TIF009.list --duration 600 --jobs 4 --continue-on-fail

# P3 LUA003 draft_binding_spec_then_short_screen
# benefit: Find whether a binary or lifecycle TC can be converted into accepted non-trigger progress and then a faster terminal outcome than faithful baselines.
# blocked: no BindingSpec candidate exists yet; no comparison package exists yet
# post-unblock: scripts/run_magma_baselines.sh --target-id LUA003 --durations 600 --jobs 4
# post-unblock: scripts/run_formtrig_manifest_batch.sh --manifest-list artifacts/formtrig_native_readiness/manifests/LUA003.list --duration 600 --jobs 4 --continue-on-fail
