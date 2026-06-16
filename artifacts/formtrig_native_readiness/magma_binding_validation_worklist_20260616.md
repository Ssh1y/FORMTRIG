# Magma Binding Validation Worklist

This is a validation worklist, not a performance-result table. A runnable
task executes a short BindingSpec candidate sweep and then summarizes it
into the existing `binding_validation` schema consumed by target planners.

Generated: `2026-06-16T18:37:31+00:00`
Tasks: `6`; runnable now: `1`; blocked: `5`

| target | category | runnable | blocker summary | validation record |
| --- | --- | --- | --- | --- |
| PDF003 | binary-state-null | blocked | site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF003.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF003; target_cmd is missing or still contains TODO | `artifacts/formtrig_native_readiness/binding_validation/PDF003.native_draft_magma_canary.validation.json` |
| SSL011 | binary-state-null | blocked | formal RNT seed corpus is not ready: excluded (No strict RNT seed is available under asn1: SSL011 is logged in PKCS7_dataDecode, but the selected asn1 runner decodes/prints/serializes ASN1 items and does not perform PKCS7 dataDecode workflows.); site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011; target_cmd is missing or still contains TODO | `artifacts/formtrig_native_readiness/binding_validation/SSL011.native_draft_magma_canary.validation.json` |
| SSL015 | binary-state-null | blocked | formal RNT seed corpus is not ready: excluded (No strict RNT seed is available under asn1: SSL015 is logged in PKCS7 data init/decode/final/verify workflows, but the selected asn1 runner decodes/prints/serializes ASN1 items and does not perform those PKCS7 workflows.); site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL015.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL015; target_cmd is missing or still contains TODO | `artifacts/formtrig_native_readiness/binding_validation/SSL015.native_draft_magma_canary.validation.json` |
| TIF012 | binary-state-null | yes | none | `artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.json` |
| PDF016 | compound-sequence-lifecycle | blocked | site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF016.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF016; target_cmd is missing or still contains TODO | `artifacts/formtrig_native_readiness/binding_validation/PDF016.native_draft_magma_canary.validation.json` |
| PHP009 | compound-sequence-lifecycle | blocked | site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PHP009.tsv; target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PHP009; target_cmd is missing or still contains TODO | `artifacts/formtrig_native_readiness/binding_validation/PHP009.native_draft_magma_canary.validation.json` |

## Runnable Commands

### TIF012

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/TIF012/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_binding_validation_600s --target-bug TIF012 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/TIF012.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer @@) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_binding_validation_600s/summary.jsonl --target-id TIF012 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/TIF012.native_draft_magma_canary.yml
```


## Blocked Tasks

### PDF003
- RNT status: `formal_ready`; seed files: `12`
- site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF003.tsv
- target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF003
- target_cmd is missing or still contains TODO

### SSL011
- RNT status: `excluded`; seed files: `0`
- formal RNT seed corpus is not ready: excluded (No strict RNT seed is available under asn1: SSL011 is logged in PKCS7_dataDecode, but the selected asn1 runner decodes/prints/serializes ASN1 items and does not perform PKCS7 dataDecode workflows.)
- site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv
- target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011
- target_cmd is missing or still contains TODO

### SSL015
- RNT status: `excluded`; seed files: `0`
- formal RNT seed corpus is not ready: excluded (No strict RNT seed is available under asn1: SSL015 is logged in PKCS7 data init/decode/final/verify workflows, but the selected asn1 runner decodes/prints/serializes ASN1 items and does not perform those PKCS7 workflows.)
- site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL015.tsv
- target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL015
- target_cmd is missing or still contains TODO

### PDF016
- RNT status: `formal_ready`; seed files: `20`
- site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF016.tsv
- target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF016
- target_cmd is missing or still contains TODO

### PHP009
- RNT status: `formal_ready`; seed files: `31`
- site_map is missing or unresolved: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PHP009.tsv
- target_cwd is missing or unresolved: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PHP009
- target_cmd is missing or still contains TODO
