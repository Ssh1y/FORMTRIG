# Magma Binding Validation Worklist

This is a validation worklist, not a performance-result table. A runnable
task executes a short BindingSpec candidate sweep and then summarizes it
into the existing `binding_validation` schema consumed by target planners.

Generated: `2026-06-18T08:33:36+00:00`
Tasks: `6`; runnable now: `6`; blocked: `0`

| target | category | runnable | blocker summary | validation record |
| --- | --- | --- | --- | --- |
| PDF003 | binary-state-null | yes | none | `artifacts/formtrig_native_readiness/binding_validation/PDF003.native_draft_magma_canary.validation.json` |
| SSL011 | binary-state-null | yes | none | `artifacts/formtrig_native_readiness/binding_validation/SSL011.native_draft_magma_canary.validation.json` |
| SSL015 | binary-state-null | yes | none | `artifacts/formtrig_native_readiness/binding_validation/SSL015.native_b2_pkcs7_decode_candidate.validation.json` |
| TIF012 | binary-state-null | yes | none | `artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.json` |
| PDF016 | compound-sequence-lifecycle | yes | none | `artifacts/formtrig_native_readiness/binding_validation/PDF016.native_draft_magma_canary.validation.json` |
| PHP009 | numeric-margin | yes | none | `artifacts/formtrig_native_readiness/binding_validation/PHP009.native_draft_magma_canary.validation.json` |

## Runnable Commands

### PDF003

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/PDF003/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_binding_validation_600s --target-bug PDF003 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/PDF003.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus --afl-arg -t --afl-arg 5000 -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl/pdfimages @@ /tmp/out) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf003_binding_validation_600s/summary.jsonl --target-id PDF003 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/PDF003.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/PDF003.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/PDF003.native_draft_magma_canary.yml
```

### SSL011

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/SSL011/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/ssl011_binding_validation_600s --target-bug SSL011 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/SSL011.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/afl/pkcs7_decode -) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/ssl011_binding_validation_600s/summary.jsonl --target-id SSL011 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/SSL011.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/SSL011.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/SSL011.native_draft_magma_canary.yml
```

### SSL015

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/SSL015/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/ssl015_binding_validation_600s --target-bug SSL015 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/SSL015.native_b2_pkcs7_decode_candidate.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/afl/pkcs7_decode -) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/ssl015_binding_validation_600s/summary.jsonl --target-id SSL015 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/SSL015.native_b2_pkcs7_decode_candidate.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/SSL015.native_b2_pkcs7_decode_candidate.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/SSL015.native_b2_pkcs7_decode_candidate.yml
```

### TIF012

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/TIF012/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_binding_validation_600s --target-bug TIF012 --category binary-null --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/TIF012.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer @@) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/tif012_binding_validation_600s/summary.jsonl --target-id TIF012 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/TIF012.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/TIF012.native_draft_magma_canary.yml
```

### PDF016

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/PDF016/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf016_binding_validation_600s --target-bug PDF016 --category lifecycle --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/PDF016.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/afl/pdf_fuzzer @@) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/pdf016_binding_validation_600s/summary.jsonl --target-id PDF016 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/PDF016.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/PDF016.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/PDF016.native_draft_magma_canary.yml
```

### PHP009

```bash
(cd /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/afl && /home/cwh/FORMTRIG/scripts/run_formtrig_binding_candidate_sweep.sh --in /home/cwh/FORMTRIG/artifacts/rnt_corpus/PHP009/seeds --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/php009_binding_validation_600s --target-bug PHP009 --category numeric --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/formtrig_native/formtrig_sites.tsv --candidate /home/cwh/FORMTRIG/artifacts/binding_specs/PHP009.native_draft_magma_canary.yml --candidate-kind binding-spec --duration 600 --seed-preflight require --seed-preflight-max 32 --seed-preflight-timeout 5 --aflpp-dir /home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus -- /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/afl/exif @@) && python3 /home/cwh/FORMTRIG/tools/summarize_binding_candidate_sweep.py --summary-jsonl /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/raw/php009_binding_validation_600s/summary.jsonl --target-id PHP009 --out /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/PHP009.native_draft_magma_canary.validation.json --out-md /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/binding_validation/PHP009.native_draft_magma_canary.validation.md --site-map /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/formtrig_native/formtrig_sites.tsv --binding-spec /home/cwh/FORMTRIG/artifacts/binding_specs/PHP009.native_draft_magma_canary.yml
```


## Blocked Tasks
