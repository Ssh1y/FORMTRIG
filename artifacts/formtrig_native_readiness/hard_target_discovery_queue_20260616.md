# FORMTRIG Hard-Target Discovery Queue

This queue is benefit-first. It ranks targets by whether they can
plausibly expose a FORMTRIG advantage when terminal trigger feedback
is binary or otherwise uninformative, then states the shortest next
experiment needed to prove or discard that opportunity.

Top queued targets shown: `30`.
Real-CVE replacements in top queue: `2`.
Magma candidates in top queue: `28`.
Demoted controls retained outside the main queue: `9`.

## Top Queue

| rank | target | source | project | category | score | lane | comparison packages | next action |
| ---: | --- | --- | --- | --- | ---: | --- | ---: | --- |
| 1 | PDF003 | magma | poppler | binary-state-null+compound-sequence-lifecycle | 109 | `short_triage_ready` | 3 | run 2h matched repetitions if retained as a paper case; otherwise shift main budget to harder Magma/real-CVE targets |
| 2 | PHP003 | magma | php | compound-sequence-lifecycle+numeric-margin | 96 | `short_triage_ready` | 0 | run short FORMTRIG gate and same-seed AFL++ family baseline screen |
| 3 | LIBXML2_1107 | real_cve | libxml2 | binary-state-null | 74 | `binding_validation_first` | 0 | validate BindingSpec against native site map and dynamic binding signal before short gate |
| 4 | GPAC_3403 | real_cve | gpac | compound-sequence-lifecycle | 92 | `binding_spec_first` | 0 | validate vulnerable build/PoC replay, audit harness admissibility, then draft BindingSpec |
| 5 | SQL013 | magma | sqlite3 | compound-sequence-lifecycle | 75 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 6 | SSL009 | magma | openssl | compound-sequence-lifecycle | 75 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 7 | PHP010 | magma | php | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 8 | PHP011 | magma | php | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 9 | SQL015 | magma | sqlite3 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 10 | SSL005 | magma | openssl | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 11 | TIF011 | magma | libtiff | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 12 | TIF014 | magma | libtiff | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 13 | XML003 | magma | libxml2 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 14 | XML004 | magma | libxml2 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 15 | XML010 | magma | libxml2 | compound-sequence-lifecycle+numeric-margin | 74 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 16 | SSL008 | magma | openssl | binary-state-null+equality/magic | 72 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 17 | SSL012 | magma | openssl | binary-state-null+equality/magic | 72 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 18 | SSL017 | magma | openssl | binary-state-null+equality/magic | 72 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 19 | PDF010 | magma | poppler | binary-state-null | 71 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 20 | SSL002 | magma | openssl | binary-state-null | 71 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 21 | LUA002 | magma | lua | binary-state-null+numeric-margin | 70 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 22 | PHP001 | magma | php | binary-state-null+numeric-margin | 70 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 23 | TIF009 | magma | libtiff | binary-state-null+numeric-margin | 70 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 24 | LUA003 | magma | lua | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 25 | PDF013 | magma | poppler | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 26 | PDF015 | magma | poppler | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 27 | PDF018 | magma | poppler | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 28 | SND014 | magma | libsndfile | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 29 | SND022 | magma | libsndfile | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |
| 30 | SQL009 | magma | sqlite3 | compound-sequence-lifecycle | 68 | `binding_spec_first` | 0 | draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage |

## First Actions

### 1. PDF003

- Benefit hypothesis: binary terminal state is gated by parser/object lifecycle progress that CmpLog-style direct comparison feedback may not expose
- Comparison packages: 3
- Blockers: none recorded
- Short triage: positive speedup evidence already exists; run 2h matched FORMTRIG/AFL++ family repetitions only if this target remains in paper scope, otherwise shift budget to harder targets

### 2. PHP003

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no comparison package exists yet
- Short triage: run 10-30m FORMTRIG seed-readiness/gate, then same-seed AFL++ vanilla/CmpLog/Redqueen short baselines with `scripts/run_magma_baselines.sh --target-id PHP003 --durations 600,1800 --jobs N`

### 3. LIBXML2_1107

- Benefit hypothesis: native trigger feedback is likely 0/1, so FORMTRIG can test whether lifted producer/use or lifecycle features guide R2T
- Comparison packages: 0
- Blockers: no external PoC/input link recorded; no vulnerable/fix commit link recorded; BindingSpec candidate is not native-site-map validated
- Short triage: build FORMTRIG-instrumented target/site map, compile the BindingSpec against native site ids, then run seed-readiness and binding-signal diagnosis

### 4. GPAC_3403

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no BindingSpec candidate exists yet
- Short triage: validate vulnerable build and PoC replay, write harness admissibility note, then create BindingSpec before fuzzing budget is spent

### 5. SQL013

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no BindingSpec candidate exists yet; no comparison package exists yet
- Short triage: draft BindingSpec from Magma canary sites, pass static/dynamic binding audit, then run 10m FORMTRIG plus a 10m baseline screen with `scripts/run_magma_baselines.sh --target-id SQL013 --durations 600 --jobs N`

### 6. SSL009

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no BindingSpec candidate exists yet; no comparison package exists yet
- Short triage: draft BindingSpec from Magma canary sites, pass static/dynamic binding audit, then run 10m FORMTRIG plus a 10m baseline screen with `scripts/run_magma_baselines.sh --target-id SSL009 --durations 600 --jobs N`

### 7. PHP010

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no BindingSpec candidate exists yet; no comparison package exists yet
- Short triage: draft BindingSpec from Magma canary sites, pass static/dynamic binding audit, then run 10m FORMTRIG plus a 10m baseline screen with `scripts/run_magma_baselines.sh --target-id PHP010 --durations 600 --jobs N`

### 8. PHP011

- Benefit hypothesis: terminal success depends on event order, object identity, or parser state rather than one scalar branch distance
- Comparison packages: 0
- Blockers: no BindingSpec candidate exists yet; no comparison package exists yet
- Short triage: draft BindingSpec from Magma canary sites, pass static/dynamic binding audit, then run 10m FORMTRIG plus a 10m baseline screen with `scripts/run_magma_baselines.sh --target-id PHP011 --durations 600 --jobs N`

## Controls / Negative Evidence

| target | disposition | next action |
| --- | --- | --- |
| LIBARCHIVE_2936 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
| TIF012 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
| PHP009 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
| PNG006 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
| SSL011 | `do_not_promote` | keep as control or negative evidence; do not spend main long-run budget |
| SSL015 | `do_not_promote` | keep as control or negative evidence; do not spend main long-run budget |
| PNG007 | `do_not_promote` | keep as control or negative evidence; do not spend main long-run budget |
| PDF016 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
| LIBCOAP_CVE_2023_35862 | `demote_to_control_or_negative` | keep as control or negative evidence; do not spend main long-run budget |
