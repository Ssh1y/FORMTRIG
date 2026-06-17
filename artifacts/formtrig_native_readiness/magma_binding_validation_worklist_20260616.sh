#!/usr/bin/env bash
set -euo pipefail

# Generated Magma BindingSpec validation commands.
# Blocked tasks are emitted as comments until native assets are provided.

# PDF003 run_binding_candidate_sweep_then_summarize_validation
# benefit: Validate that this BindingSpec creates replay-stable, non-terminal pre-trigger guidance before spending endpoint comparison budget.
# blocked: site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF003.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF003; target_cmd is missing or still contains TODO
# next: provide site_map, target_cwd, and target_cmd in a validation assets JSON

# SSL011 run_binding_candidate_sweep_then_summarize_validation
# benefit: Validate that this BindingSpec creates replay-stable, non-terminal pre-trigger guidance before spending endpoint comparison budget.
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/SSL011/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/ssl011_binding_validation_600s --target-bug SSL011 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/SSL011.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/afl/pkcs7_decode -) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/ssl011_binding_validation_600s/summary.jsonl --target-id SSL011 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/SSL011.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/SSL011.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/SSL011.native_draft_magma_canary.yml

# SSL015 run_binding_candidate_sweep_then_summarize_validation
# benefit: Validate that this BindingSpec creates replay-stable, non-terminal pre-trigger guidance before spending endpoint comparison budget.
# blocked: formal RNT seed corpus is not ready: excluded (No strict RNT seed is available under asn1: SSL015 is logged in PKCS7 data init/decode/final/verify workflows, but the selected asn1 runner decodes/prints/serializes ASN1 items and does not perform those PKCS7 workflows.); site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL015.tsv
# next: provide site_map, target_cwd, and target_cmd in a validation assets JSON

# TIF012 run_binding_candidate_sweep_then_summarize_validation
# benefit: Validate that this BindingSpec creates replay-stable, non-terminal pre-trigger guidance before spending endpoint comparison budget.
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/TIF012/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_binding_validation_600s --target-bug TIF012 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/TIF012.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer @@) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_binding_validation_600s/summary.jsonl --target-id TIF012 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/TIF012.native_draft_magma_canary.yml

# PDF016 run_binding_candidate_sweep_then_summarize_validation
# benefit: Validate that this BindingSpec creates replay-stable, non-terminal pre-trigger guidance before spending endpoint comparison budget.
# blocked: site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF016.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF016; target_cmd is missing or still contains TODO
# next: provide site_map, target_cwd, and target_cmd in a validation assets JSON

# PHP009 run_binding_candidate_sweep_then_summarize_validation
# benefit: Validate that this BindingSpec creates replay-stable, non-terminal pre-trigger guidance before spending endpoint comparison budget.
# blocked: site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PHP009.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PHP009; target_cmd is missing or still contains TODO
# next: provide site_map, target_cwd, and target_cmd in a validation assets JSON
