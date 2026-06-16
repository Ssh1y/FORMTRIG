# FORMTRIG Hard-Target Discovery Queue

This queue is benefit-first. It ranks targets by whether they can
plausibly expose a FORMTRIG advantage when terminal trigger feedback
is binary or otherwise uninformative, then states the shortest next
experiment needed to prove or discard that opportunity.

Top queued targets shown: `30`.
Real-CVE replacements in top queue: `2`.
Magma candidates in top queue: `28`.
Demoted controls retained outside the main queue: `4`.

## Top Queue

| rank | target | source | project | category | score | lane | comparison packages | next action |
| ---: | --- | --- | --- | --- | ---: | --- | ---: | --- |
| 1 | LIBARCHIVE_2936 | real_cve | libarchive | binary-state-null | 115 | `real_cve_replacement` | 5 | run 2h matched repetitions if retained as a paper case; otherwise shift main budget to harder Magma/real-CVE targets |
| 2 | PDF003 | magma | poppler | binary-state-null+compound-sequence-lifecycle | 90 | `binding_validation_first` | 0 | validate BindingSpec against native site map and binding-signal diagnosis before short gate |
| 3 | SSL011 | magma | openssl | binary-state-null+compound-sequence-lifecycle | 90 | `binding_validation_first` | 0 | validate BindingSpec against native site map and binding-signal diagnosis before short gate |
| 4 | SSL015 | magma | openssl | binary-state-null+compound-sequence-lifecycle | 90 | `binding_validation_first` | 0 | validate BindingSpec against native site map and binding-signal diagnosis before short gate |
| 5 | TIF012 | magma | libtiff | binary-state-null+compound-sequence-lifecycle | 90 | `binding_validation_first` | 0 | validate BindingSpec against native site map and binding-signal diagnosis before short gate |
| 6 | PDF016 | magma | poppler | compound-sequence-lifecycle | 81 | `binding_validation_first` | 0 | validate BindingSpec against native site map and binding-signal diagnosis before short gate |
| 7 | PHP009 | magma | php | compound-sequence-lifecycle | 81 | `binding_validation_first` | 0 | validate BindingSpec against native site map and binding-signal diagnosis before short gate |
| 8 | GPAC_3403 | real_cve | gpac | compound-sequence-lifecycle | 92 | `binding_spec_first` | 0 | validate vulnerable build/PoC replay, audit harness admissibility, then draft BindingSpec |
| 9 | SQL013 | magma | sqlite3 | compound-sequence-lifecycle | 75 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 10 | SSL009 | magma | openssl | compound-sequence-lifecycle | 75 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 11 | PHP003 | magma | php | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 12 | PHP010 | magma | php | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 13 | PHP011 | magma | php | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 14 | SQL015 | magma | sqlite3 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 15 | SSL005 | magma | openssl | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 16 | TIF011 | magma | libtiff | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 17 | TIF014 | magma | libtiff | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 18 | XML003 | magma | libxml2 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 19 | XML004 | magma | libxml2 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 20 | XML010 | magma | libxml2 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 21 | SSL008 | magma | openssl | binary-state-null+equality/magic | 72 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 22 | SSL012 | magma | openssl | binary-state-null+equality/magic | 72 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 23 | SSL017 | magma | openssl | binary-state-null+equality/magic | 72 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 24 | PDF010 | magma | poppler | binary-state-null | 71 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 25 | SSL002 | magma | openssl | binary-state-null | 71 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 26 | LUA002 | magma | lua | binary-state-null+numeric-margin | 70 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 27 | PHP001 | magma | php | binary-state-null+numeric-margin | 70 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 28 | TIF009 | magma | libtiff | binary-state-null+numeric-margin | 70 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 29 | LUA003 | magma | lua | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 30 | PDF013 | magma | poppler | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |

## First Actions

### 1. LIBARCHIVE_2936

- Benefit hypothesis: native trigger feedback is likely 0/1, so FORMTRIG can test whether lifted producer/use or lifecycle features guide R2T
- Comparison packages: 5
- Blockers: none recorded
- Short triage: positive speedup evidence already exists; run 2h matched FORMTRIG/AFL++ family repetitions only if this target remains in paper scope, otherwise shift budget to harder targets

### 2. PDF003

- Benefit hypothesis: binary terminal state is gated by parser/object lifecycle progress that CmpLog-style direct comparison feedback may not expose
- Comparison packages: 0
- Blockers: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
- Short triage: compile BindingSpec against the native site map, pass lift audit and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen

### 3. SSL011

- Benefit hypothesis: binary terminal state is gated by parser/object lifecycle progress that CmpLog-style direct comparison feedback may not expose
- Comparison packages: 0
- Blockers: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
- Short triage: compile BindingSpec against the native site map, pass lift audit and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen

### 4. SSL015

- Benefit hypothesis: binary terminal state is gated by parser/object lifecycle progress that CmpLog-style direct comparison feedback may not expose
- Comparison packages: 0
- Blockers: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
- Short triage: compile BindingSpec against the native site map, pass lift audit and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen

### 5. TIF012

- Benefit hypothesis: binary terminal state is gated by parser/object lifecycle progress that CmpLog-style direct comparison feedback may not expose
- Comparison packages: 0
- Blockers: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
- Short triage: compile BindingSpec against the native site map, pass lift audit and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen

### 6. PDF016

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
- Short triage: compile BindingSpec against the native site map, pass lift audit and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen

### 7. PHP009

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: BindingSpec candidate is not native-site-map validated; no comparison package exists yet
- Short triage: compile BindingSpec against the native site map, pass lift audit and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen

### 8. GPAC_3403

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no BindingSpec candidate exists yet
- Short triage: validate vulnerable build and PoC replay, write harness admissibility note, then create BindingSpec before fuzzing budget is spent

## Controls / Negative Evidence

| target | disposition | next action |
| --- | --- | --- |
| PNG006 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
| PNG007 | `do_not_promote` | keep as control or negative evidence; do not spend main long-run budget |
| LIBXML2_1107 | `demote_harness_artifact` | keep as control or negative evidence; do not spend main long-run budget |
| LIBCOAP_CVE_2023_35862 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
