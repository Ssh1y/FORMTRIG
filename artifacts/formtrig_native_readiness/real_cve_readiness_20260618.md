# FORMTRIG Real-CVE Readiness Audit

This audit checks whether the real-CVE candidates are executable enough
to enter FORMTRIG short-gate work. It separates the RNT/binary-D_T
benefit opportunity from missing engineering assets such as BindingSpec
or terminal validation.

| rank | target | category | readiness | RNT | binary `D_T` gap | terminal | BindingSpec candidate | BindingSpec validated | short-gate packages | next action |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | GPAC_3403 | compound-sequence-lifecycle | `short_gate_triaged` | yes | yes | yes | yes | yes | 3 | extend latest complete-role-graph short-gate package to matched 10m/2h endpoint runs |
| 2 | LIBARCHIVE_2935 | numeric-margin | `ready_for_binding_spec` | yes | yes | yes | no | no | 0 | draft BindingSpec from TCIR/atoms and validate static/dynamic binding signal |
| 3 | LIBARCHIVE_2937 | numeric-margin | `ready_for_binding_spec` | yes | yes | yes | no | no | 0 | draft BindingSpec from TCIR/atoms and validate static/dynamic binding signal |
| 4 | LIBARCHIVE_2938 | numeric-margin | `ready_for_binding_spec` | yes | yes | yes | no | no | 0 | draft BindingSpec from TCIR/atoms and validate static/dynamic binding signal |
| 5 | LIBARCHIVE_2925 | numeric-margin | `ready_for_binding_spec` | yes | yes | yes | no | no | 0 | draft BindingSpec from TCIR/atoms and validate static/dynamic binding signal |
| 6 | GPAC_3398 | numeric-margin | `not_ready` | no | no | yes | no | no | 0 | collect formal RNT seed before spending fuzzing budget |
| 7 | LIBXML2_1107 | binary-state-null | `control_or_negative` | yes | yes | yes | yes | no | 0 | keep as control/sanity evidence; do not spend main real-CVE long-run budget |
| 8 | LIBARCHIVE_2936 | binary-state-null | `control_or_negative` | yes | yes | yes | yes | yes | 6 | keep as control/sanity evidence; do not spend main real-CVE long-run budget |

## Details

### 1. GPAC_3403

- Discovery rank: 4
- Source locations: src/utils/bitstream.c:372#gf_bs_del
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: AddressSanitizer: double-free (/home/cwh/FORMTRIG/benchmarks/cve_build/gpac-3403-src/bin/gcc/MP4Box+0x194f48a) (BuildId: da5c3e139317cf0e2b8580968246bc6803e86243) in free
- Binding validation status: native_binding_validated@artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.binding_validation_60s_20260618.json; same_object_binding_not_on_crash_path@artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.native_b2_poc_snapshot_triage_20260619.validation.json; partial_mechanism_missing_role_coverage@artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.native_b2_same_object_repair_60s_20260618.validation.json; alias_role_repaired_cleanup_use_not_captured@artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.native_b3_nalu_reassign_alias_20260619.validation.json; complete_role_graph_preabort_verified@artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.native_b5_gfbsdel_use_root_polarity_20260619.validation.json; native_site_map_validated@artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.native_site_map_validation_20260618.json
- Short-gate comparison packages: 3
- Current speedup package: none
- Current benefit: 600s short-gate pre-screen: FORMTRIG pre-trigger lifted guidance with 1 accepted / 1 saved non-trigger progress events; variable TC-rooted roles: root_observe,use; spec D_F candidate values {6,5,4,2}; ASAN AFL++ family valid baseline reps 3 with 0 endpoint successes
- Blockers: none
- Program: `benchmarks/cve_build/gpac-3403-src/bin/gcc/MP4Box`
- RNT manifest: `artifacts/rnt_corpus/GPAC_3403/manifest.json`

### 2. LIBARCHIVE_2935

- Discovery rank: 47
- Source locations: libarchive/archive_write_set_format_iso9660.c:5913#idr_extend_identifier
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: AddressSanitizer: heap-buffer-overflow (/home/cwh/FORMTRIG/benchmarks/cve_build/libarchive-a819-asan/libarchive_write_replay+0x191878) (BuildId: 8c400a70b41c909bb4562a98f2e8133b3820b542) in __asan_memmove
- Binding validation status: none
- Short-gate comparison packages: 0
- Current speedup package: none
- Current benefit: none
- Blockers: no executable BindingSpec candidate
- Program: `benchmarks/cve_build/libarchive-a819-asan/libarchive_write_replay`
- RNT manifest: `artifacts/rnt_corpus/LIBARCHIVE_2935/manifest.json`

### 3. LIBARCHIVE_2937

- Discovery rank: 48
- Source locations: libarchive/archive_write_set_format_iso9660.c:5634#isoent_tree
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /home/cwh/FORMTRIG/benchmarks/cve_build/libarchive-a819-src/libarchive/archive_write_set_format_iso9660.c:5634:8
- Binding validation status: none
- Short-gate comparison packages: 0
- Current speedup package: none
- Current benefit: none
- Blockers: no executable BindingSpec candidate
- Program: `benchmarks/cve_build/libarchive-a819-asan/libarchive_write_replay`
- RNT manifest: `artifacts/rnt_corpus/LIBARCHIVE_2937/manifest.json`

### 4. LIBARCHIVE_2938

- Discovery rank: 49
- Source locations: libarchive/archive_write_set_format_iso9660.c:5969#idr_set_num_beutf16
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: AddressSanitizer: heap-buffer-overflow /home/cwh/FORMTRIG/benchmarks/cve_build/libarchive-a819-src/libarchive/archive_endian.h:140:7 in archive_be16enc
- Binding validation status: none
- Short-gate comparison packages: 0
- Current speedup package: none
- Current benefit: none
- Blockers: no executable BindingSpec candidate
- Program: `benchmarks/cve_build/libarchive-a819-asan/libarchive_write_replay`
- RNT manifest: `artifacts/rnt_corpus/LIBARCHIVE_2938/manifest.json`

### 5. LIBARCHIVE_2925

- Discovery rank: 50
- Source locations: libarchive/archive_write_set_format_zip.c:2306#copy_path
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /home/cwh/FORMTRIG/benchmarks/cve_build/libarchive-a819-src/libarchive/archive_write_set_format_zip.c:2306:29
- Binding validation status: none
- Short-gate comparison packages: 0
- Current speedup package: none
- Current benefit: none
- Blockers: no executable BindingSpec candidate
- Program: `benchmarks/cve_build/libarchive-a819-asan/libarchive_zip_empty_dir_replay`
- RNT manifest: `artifacts/rnt_corpus/LIBARCHIVE_2925/manifest.json`

### 6. GPAC_3398

- Discovery rank: 46
- Source locations: none
- Native D_T values in RNT metadata: `none`
- Terminal validation signal: SUMMARY: AddressSanitizer: heap-buffer-overflow /home/cwh/FORMTRIG/benchmarks/cve_build/gpac-3398-src/src/isomedia/box_code_base.c:10568:12 in sgpd_del_entry
- Binding validation status: none
- Short-gate comparison packages: 0
- Current speedup package: none
- Current benefit: none
- Blockers: no formal RNT seed with R=1,T=0; binary native D_T gap is not established; no executable BindingSpec candidate; no TCIR file; no atom file
- Program: `benchmarks/cve_build/gpac-3398-src/bin/gcc/MP4Box`
- RNT manifest: `artifacts/rnt_corpus/GPAC_3398/manifest.json`

### 7. LIBXML2_1107

- Discovery rank: 3
- Source locations: xmlregexp.c:740#xmlRegNewParserCtxt
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /home/cwh/FORMTRIG/benchmarks/cve_build/libxml2-a7511af0-src/xmlregexp.c:740:20
- Binding validation status: none
- Short-gate comparison packages: 0
- Current speedup package: none
- Current benefit: none
- Blockers: harness admissibility rejects core evidence: inadmissible_core_evidence@artifacts/formtrig_native_readiness/raw/libxml2_1107_harness_admissibility_20260615.json: Not admissible as core FORMTRIG R2T evidence because the harness exposes an artificial trigger-control knob.; BindingSpec candidate is not native-site-map validated
- Program: `benchmarks/cve_build/libxml2-a7511af0-asan/libxml2_regexp_strdup_fail_replay`
- RNT manifest: `artifacts/rnt_corpus/LIBXML2_1107/manifest.json`

### 8. LIBARCHIVE_2936

- Discovery rank: 139
- Source locations: libarchive/archive_write_set_format_iso9660.c:6823#_compare_path_table
- Native D_T values in RNT metadata: `1`
- Terminal validation signal: SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /home/cwh/FORMTRIG/benchmarks/cve_build/libarchive-a819-src/libarchive/archive_write_set_format_iso9660.c:6823:45
- Binding validation status: native_binding_validated@artifacts/formtrig_native_readiness/binding_validation/LIBARCHIVE_2936.native_b2_path_table_candidate.validation.json
- Short-gate comparison packages: 6
- Current speedup package: `artifacts/formtrig_native_readiness/comparisons/libarchive_2936_b4_path_hierarchy_hook_60s_20260616/comparison.json`
- Current benefit: replicated 60s first-_T speedup: FORMTRIG median 1.326s versus fastest baseline median 24.45s; 18.44x wall-clock and 1074.34x execution speedup by median; matched 10m confirmation: FORMTRIG 1.22s / exec 32 versus fastest baseline 20.671s / exec 28677
- Blockers: existing discovery triage demotes this target: demote_to_control_or_negative
- Program: `benchmarks/cve_build/libarchive-a819-asan/libarchive_write_replay`
- RNT manifest: `artifacts/rnt_corpus/LIBARCHIVE_2936/manifest.json`
