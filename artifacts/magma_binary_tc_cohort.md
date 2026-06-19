# Magma Binary-State TC Cohort

Generated UTC: 2026-06-19T02:02:48Z

## Summary

| metric | value |
|---|---:|
| inventory_binary_total | 14 |
| main_experiment_eligible | 9 |
| excluded_or_blocked | 5 |
| strict_clean_binary | 3 |
| ambiguous_or_secondary | 11 |

## Formal-Ready Binary Targets

| target | project | program | confidence | secondary | expression |
|---|---|---|---|---|---|
| PNG006 | libpng | libpng_read_fuzzer | heuristic | compound-sequence-lifecycle | `MAGMA_AND(info_ptr->eXIf_buf != NULL, (mask & info_ptr->free_me & PNG_FREE_EXIF) == 0)` |
| PNG007 | libpng | libpng_read_fuzzer | known_manifest |  | `png_ptr->palette == NULL` |
| TIF012 | libtiff | tiff_read_rgba_fuzzer | heuristic | compound-sequence-lifecycle | `MAGMA_AND(td->td_transferfunction[0] != NULL, MAGMA_AND(td->td_samplesperpixel - *v > 1, !(td->td_samplesperpixel - td->td_extrasamples > 1))) ; MAGMA_OR(td->td_sminsamplevalue != NULL, MAGMA_OR(td->td_smaxsamplevalue != NULL, MAGMA_AND(td->td_transferfunction[0] != NULL, MAGMA_AND(v - td->td_extrasamples > 1, !(td->td_samplesperpixel - td->td_extrasamples > 1)))))` |
| LUA002 | lua | lua | heuristic | numeric-margin | `p->lineinfo == NULL` |
| SSL002 | openssl | server | known_manifest |  | `s->init_msg != (s->init_buf->data + msg_offset)` |
| SSL011 | openssl | asn1 | heuristic | compound-sequence-lifecycle | `MAGMA_AND(data_body == NULL, in_bio == NULL)` |
| SSL015 | openssl | asn1 | heuristic | compound-sequence-lifecycle | `MAGMA_OR(p7 == NULL, p7->d.ptr) ; MAGMA_OR(p7 == NULL, p7->d.ptr == NULL)` |
| PDF003 | poppler | pdfimages | heuristic | compound-sequence-lifecycle | `MAGMA_AND(colorMap->getColorSpace2() == nullptr, (size_t)colorMap->getNumPixelComps() > sizeof(zero))` |
| PDF010 | poppler | pdf_fuzzer | known_manifest |  | `t3GlyphStack == nullptr` |

## Excluded Harness/Runner Gaps

| target | project | program | reason |
|---|---|---|---|
| TIF009 | libtiff | tiff_read_rgba_fuzzer | No strict RNT seed is available under tiff_read_rgba_fuzzer: TIF009 is logged in TIFFWriteDirectoryTagTransferfunction, but the current harness only reads RGBA pixels and never writes TIFF directories. |
| SSL008 | openssl | server | No strict RNT seed is available under server: SSL008 is logged in client key-exchange construction, while the selected server runner processes client bytes as a server and does not construct client key exchange messages. |
| SSL012 | openssl | x509 | No strict RNT seed is available under x509: SSL012 is logged in X509_to_X509_REQ, but the selected x509 runner parses/prints/hashes/serializes X509 certificates and does not convert X509 to certificate requests. |
| SSL017 | openssl | x509 | No strict RNT seed is available under x509: SSL017 is logged in CRL selection get_crl_sk, but the x509 runner does not run certificate path validation with CRL stores and corpus/source-guided replays did not produce SSL017_R. |
| PHP001 | php | parser | No strict RNT seed is available under php-fuzz-parser: PHP001 is logged in ext/phar runtime archive handling, but php-fuzz-parser only compiles PHP source with execute=false and does not parse phar archives. |

## Strict Clean Binary Subset

| target | project | expression |
|---|---|---|
| PNG007 | libpng | `png_ptr->palette == NULL` |
| SSL002 | openssl | `s->init_msg != (s->init_buf->data + msg_offset)` |
| PDF010 | poppler | `t3GlyphStack == nullptr` |

## Methodology Notes

- Use main_experiment_eligible targets for Magma binary-state claims; they have formal RNT seeds with R>0,T=0 and can support R2T long runs.
- Excluded targets remain useful harness-repair opportunities, but they should not be counted as FORMTRIG failures or baseline wins until the runner reaches the target path.
- strict_clean_binary keeps only non-ambiguous known-manifest null/pointer-state predicates; the broader eligible cohort includes compound binary-rooted cases needed for generality.
