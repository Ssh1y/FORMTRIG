# RNT Corpus Status

Generated UTC: 2026-06-11T13:02:22Z

## Overall

| status | count |
|---|---:|
| excluded | 61 |
| formal_ready | 89 |

## By Suite

| suite | formal_ready | candidate_only | invalid | missing | excluded |
|---|---:|---:|---:|---:|---:|
| cve | 11 | 0 | 0 | 0 | 1 |
| magma | 78 | 0 | 0 | 0 | 60 |

## By TC Class

| TC class | formal_ready | candidate_only | invalid | missing | excluded |
|---|---:|---:|---:|---:|---:|
| binary-state-null | 10 | 0 | 0 | 0 | 7 |
| compound-sequence-lifecycle | 15 | 0 | 0 | 0 | 9 |
| equality/magic | 9 | 0 | 0 | 0 | 6 |
| numeric-margin | 55 | 0 | 0 | 0 | 39 |

## First Blockers

| target_id | suite | TC class | status | blocking reason |
|---|---|---|---|---|
| GPAC_3398 | cve | numeric-margin | excluded | No strict RNT seed found for target_location=sgpd_del_entry: code audit shows the validated av1s path reaches sgpd_del_entry only at the sanitizer-triggering default deleter, while local non-trigger MP4 samples and one-byte PoC-neighbor searches did not hit sgpd_del_entry. |
| LUA004 | magma | numeric-margin | excluded | No strict RNT seed is available under the current lua runner: source-guided line-hook seeds reach luaG_traceexec but also trigger LUA004, so no R=1,T=0 seed is admitted. |
| PDF004 | magma | numeric-margin | excluded | No strict RNT seed is available under pdftoppm: minimal page, vector path fill, and clipping-path candidates reached common Poppler canaries but did not produce PDF004_R in SplashXPathScanner::clipAALine. |
| PDF013 | magma | compound-sequence-lifecycle | excluded | No strict RNT seed is available under pdf_fuzzer's current workflow: PDF013 is logged in FileSpec::FileSpec, but pdf_fuzzer only loads pages, renders pages, and extracts text; it does not enumerate embedded-file name trees or construct FileSpec objects from them. |
| PDF015 | magma | compound-sequence-lifecycle | excluded | No strict RNT seed is available under pdf_fuzzer's current workflow: PDF015 is logged in EmbFile::save, but pdf_fuzzer never saves embedded files to disk; it only renders pages and extracts text. |
| PDF017 | magma | numeric-margin | excluded | No strict RNT seed is available under pdf_fuzzer: PDF017 is logged in FoFiTrueType::cvtSfnts vertical-metrics conversion, but minimal PDF/font candidates and full corpus replay did not produce PDF017_R. |
| PDF020 | magma | numeric-margin | excluded | No strict RNT seed is available under pdf_fuzzer: PDF020 is logged in FoFiType1C::cvtGlyph Type2 charstring conversion, but minimal PDF/font candidates and full corpus replay did not produce PDF020_R. |
| PHP001 | magma | binary-state-null | excluded | No strict RNT seed is available under php-fuzz-parser: PHP001 is logged in ext/phar runtime archive handling, but php-fuzz-parser only compiles PHP source with execute=false and does not parse phar archives. |
| PHP005 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-json: PHP005 is logged in ext/iconv MIME decoding, while php-fuzz-json directly invokes php_json_yyparse and does not call iconv MIME decode APIs. |
| PHP006 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-exif: PHP006 is logged in exif_scan_thumbnail, but fuzzer-exif calls exif_read_data with only the stream argument, leaving read_thumbnail=false, so thumbnail extraction/build is skipped and ImageInfo->Thumbnail.data is not populated for thumbnail scanning. |
| PHP007 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-parser: PHP007 is logged in ext/phar runtime archive parsing, but php-fuzz-parser only compiles PHP source with execute=false and does not parse phar archives. |
| PHP008 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-json: PHP008 is logged in ext/standard DNS response parsing, while php-fuzz-json directly invokes php_json_yyparse and does not call DNS APIs. |
| PHP010 | magma | compound-sequence-lifecycle | excluded | No strict RNT seed is available under php-fuzz-exif: PHP010 is logged in exif_scan_thumbnail's thumbnail length/size checks, but fuzzer-exif calls exif_read_data with only the stream argument, leaving read_thumbnail=false, so thumbnail extraction/build is skipped and the thumbnail scanner is not reached. |
| PHP012 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-json: PHP012 is logged in the HTTP stream wrapper response-header path, while php-fuzz-json directly invokes php_json_yyparse and does not open HTTP streams. |
| PHP013 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-json: PHP013 is logged in ext/intl MessageFormat parsing, while php-fuzz-json directly invokes php_json_yyparse and does not call intl APIs. |
| PHP014 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-json: PHP014 is logged in ext/intl locale display-name APIs, while php-fuzz-json directly invokes php_json_yyparse and does not call intl APIs. |
| PHP015 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-parser: PHP015 is logged in ext/phar runtime archive parsing, but php-fuzz-parser only compiles PHP source with execute=false and does not parse phar archives. |
| PHP016 | magma | numeric-margin | excluded | No strict RNT seed is available under php-fuzz-parser: PHP016 is logged in ext/phar signature verification/zip archive handling, but php-fuzz-parser only compiles PHP source with execute=false and does not parse phar archives. |
| PNG002 | magma | numeric-margin | excluded | No strict RNT seed is available under the current Magma program libpng_read_fuzzer: code audit shows PNG002 is logged in png_safe_execute, which belongs to the libpng simplified API cleanup path, while libpng_read_fuzzer uses the low-level png_create_read_struct/png_read_* API and does not call png_safe_execute. |
| SND002 | magma | numeric-margin | excluded | No strict RNT seed is available under sndfile_fuzzer: SND002 is logged in the SD2 resource-fork parser, but the current harness opens a single in-memory virtual file with SFM_READ and cannot provide the filesystem companion resource fork paths required by psf_open_rsrc. |
| SND004 | magma | numeric-margin | excluded | No strict RNT seed is available under sndfile_fuzzer: SND004 is logged in psf_fwrite, but the current harness opens input with sf_open_virtual(..., SFM_READ, ...) and only calls sf_readf_float; its virtual write callback returns 0. |
| SND010 | magma | numeric-margin | excluded | No strict RNT seed is available under sndfile_fuzzer: SND010 is logged in psf_binheader_writef while constructing output headers, but the current harness is read-only virtual IO and only calls sf_readf_float. |
| SND012 | magma | numeric-margin | excluded | No strict RNT seed is available under sndfile_fuzzer: SND012 is logged in psf_binheader_writef while constructing output headers, but the current harness is read-only virtual IO and only calls sf_readf_float. |
| SND013 | magma | numeric-margin | excluded | No strict RNT seed is available under sndfile_fuzzer: SND013 is logged in psf_binheader_writef while constructing output headers, but the current harness is read-only virtual IO and only calls sf_readf_float. |
| SND014 | magma | compound-sequence-lifecycle | excluded | No strict RNT seed is available under sndfile_fuzzer: SND014 is logged in A-law encode/write conversion code immediately before psf_fwrite, but the current harness is read-only and only exercises decode/read paths. |
| SND015 | magma | equality/magic | excluded | No strict RNT seed is available under sndfile_fuzzer: SND015 is logged in A-law encode/write conversion code immediately before psf_fwrite, but the current harness is read-only and only exercises decode/read paths. |
| SND022 | magma | compound-sequence-lifecycle | excluded | No strict RNT seed is available under sndfile_fuzzer: SND022 is logged in u-law encode/write conversion code immediately before psf_fwrite, but the current harness is read-only and only exercises decode/read paths. |
| SND023 | magma | equality/magic | excluded | No strict RNT seed is available under sndfile_fuzzer: SND023 is logged in u-law encode/write conversion code immediately before psf_fwrite, but the current harness is read-only and only exercises decode/read paths. |
| SND025 | magma | numeric-margin | excluded | No strict RNT seed is available under sndfile_fuzzer: SND025 is logged in wav_write_header, but the current harness opens a read-only virtual file and never writes WAV headers. |
| SQL001 | magma | numeric-margin | excluded | No strict RNT seed is available under the current sqlite3_fuzz build: SQL001 is logged in FTS5 fts5HashEntrySort, but FUZZCHECK_OPT comments out SQLITE_ENABLE_FTS5 and local compile options do not include ENABLE_FTS5; CREATE VIRTUAL TABLE ... USING fts5 reports no such module. |
| SQL004 | magma | numeric-margin | excluded | No strict RNT seed is available under sqlite3_fuzz: SQL004 is logged in ext/misc/zipfile.c, but the selected harness links ossfuzz.c with sqlite3.c and does not link/register the zipfile extension; source-guided zipfile SQL inputs do not produce SQL004_R. |
| SQL005 | magma | equality/magic | excluded | No strict RNT seed is available under sqlite3_fuzz: SQL005 is logged in ext/misc/zipfile.c's zipfileUpdate path, but the selected harness links ossfuzz.c with sqlite3.c and does not link/register the zipfile extension; source-guided zipfile SQL inputs do not produce SQL005_R. |
| SQL008 | magma | equality/magic | excluded | No strict RNT seed is available under sqlite3_fuzz: SQL008 is logged in src/shell.c.in tableColumnList, but sqlite3_fuzz executes input SQL through ossfuzz.c/sqlite3_exec and does not link or execute the CLI shell tableColumnList path. |
| SSL004 | magma | numeric-margin | excluded | No strict RNT seed is available under x509: SSL004 is guarded by CHARSET_EBCDIC in X509_NAME_oneline, and the current OpenSSL build is not an EBCDIC target. |
| SSL006 | magma | numeric-margin | excluded | No strict RNT seed is available under asn1: SSL006 is logged in EVP_EncodeUpdate, but the selected asn1 runner does not exercise the EVP base64 encoder and corpus/source-guided replays did not produce SSL006_R. |
| SSL007 | magma | numeric-margin | excluded | No strict RNT seed is available under asn1: SSL007 is logged in MDC2_Update, but the selected asn1 runner does not exercise MDC2 digest update and corpus/source-guided replays did not produce SSL007_R. |
| SSL008 | magma | binary-state-null | excluded | No strict RNT seed is available under server: SSL008 is logged in client key-exchange construction, while the selected server runner processes client bytes as a server and does not construct client key exchange messages. |
| SSL011 | magma | binary-state-null | formal_ready | pkcs7_decode formal RNT seed corpus: 1 CMS corpus seed replays as R=1,T=0 under the FORMTRIG-native pkcs7_decode runner. |
| SSL012 | magma | binary-state-null | excluded | No strict RNT seed is available under x509: SSL012 is logged in X509_to_X509_REQ, but the selected x509 runner parses/prints/hashes/serializes X509 certificates and does not convert X509 to certificate requests. |
| SSL013 | magma | numeric-margin | excluded | No strict RNT seed is available under asn1: SSL013 is logged in rsa_item_verify, but the selected asn1 runner does not perform RSA-PSS signature verification and corpus/source-guided replays did not produce SSL013_R. |
