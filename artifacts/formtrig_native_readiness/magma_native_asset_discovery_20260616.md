# Magma Native Asset Discovery

This report only records discovered validation inputs. It is not endpoint
performance evidence. A target is runnable only when formal RNT seeds, a
source-matching `site_map.tsv`, and an executable target command are all present.

Generated: `2026-06-17T18:26:10+00:00`
Scanned files: `73668`; site maps: `6`; runnable candidates: `4`
Assets JSON: `artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json`

| target | program | runnable | best site map | executables | blockers |
| --- | --- | --- | --- | ---: | --- |
| PDF003 | pdfimages | yes | `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv` | 2 | none |
| SSL011 | pkcs7_decode | yes | `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011_pkcs7_decode/out/formtrig_native/formtrig_sites.tsv` | 2 | none |
| SSL015 | asn1 | blocked | `` | 4 | formal RNT seed corpus is not ready: excluded; no site_map.tsv matched the BindingSpec source selectors |
| TIF012 | tiff_read_rgba_fuzzer | yes | `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv` | 1 | none |
| PDF016 | pdf_fuzzer | blocked | `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv` | 0 | no executable found for program pdf_fuzzer |
| PHP009 | exif | yes | `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/formtrig_native/formtrig_sites.tsv` | 1 | none |
