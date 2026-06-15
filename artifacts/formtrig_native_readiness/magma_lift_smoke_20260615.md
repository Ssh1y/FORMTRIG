# FORMTRIG Native Lift Smoke Evidence - 2026-06-15

Scope:

- Backend: patched AFL++ native FORMTRIG runtime.
- Target binary: `/tmp/formtrig_png007_native_build_20260615T045038Z/libpng_read_fuzzer_env18`.
- Site map: `/tmp/formtrig_png007_native_build_20260615T045038Z/native_env18/site_map.tsv`.
- Runtime mode: `FORMTRIG_ALLOW_HEURISTIC_LIFT=0`, `FORMTRIG_OBSERVE_HEURISTIC_LIFT=0`,
  `FORMTRIG_ALLOW_MANUAL_LIFT=0`.
- Interpretation rule: trigger counts are terminal evidence only. A useful
  lift smoke requires non-trigger `D_F_spec_lifted` movement and accepted
  TC-rooted progress.

## PNG006: Baseline BindingSpec Without Input Influence

BindingSpec:

- `artifacts/binding_specs/PNG006.native_b2_candidate.yml`

Static gate:

- BindingSpec compile: pass.
- `formtrig_lift_spec_audit`: atom 1 `binary-state-null` B2, atom 2
  `equality-magic` B1.
- `formtrig_binding_map`: all rows exact, no semantic role collapse.

Dynamic smoke:

- Command output: `/tmp/formtrig_png006_candidate_sweep_30s/summary.jsonl`.
- Duration: 30s.
- Executions: 223073.
- Reached: 200352.
- Triggered: 0.
- Queued progress: 0.
- Accepted non-trigger progress: 0.
- `D_F_spec_lifted`: constant 2.
- Diagnosis: `constant_lift_signal`, limiting reason `no_valid_hot_range`.

Conclusion:

- Runtime binding is not enough by itself. Root/use are observed, but the
  eXIf producer is not reached and no input-influence range is available, so
  typed mutation cannot push execution toward the producer.

## PNG006: BindingSpec Plus External eXIf Input Influence Hook

BindingSpec:

- `artifacts/binding_specs/PNG006.native_b2_exif_insert_candidate.yml`

External mutation hook:

- `scripts/formtrig_hooks/png_exif_insert_hook.py`

Static gate:

- BindingSpec compile: pass.
- `formtrig_lift_spec_audit`: atom 1 `binary-state-null` B4, atom 2
  `equality-magic` B1.
- `formtrig_binding_map`: 6 exact rows, 0 ambiguous, 0 missing, no semantic
  role collapse.

30s dynamic smoke:

- Command output: `/tmp/formtrig_png006_exif_insert_sweep_30s/summary.jsonl`.
- Executions: 58304.
- Reached: 54296.
- Triggered: 476.
- Queued progress: 54.
- Accepted non-trigger progress: 1.
- Accepted triggered progress: 53.
- `D_F_spec_lifted`: non-trigger values `[2, 1]`.
- Accepted non-trigger reason: `root_aligned_state_transition`.
- Runtime lift provenance: spec lifted only; heuristic/manual counts 0.
- Lift feature audit: pass; no unmapped spec lifted components.

120s dynamic smoke:

- Command output: `/tmp/formtrig_png006_exif_insert_sweep_120s/summary.jsonl`.
- Executions: 235465.
- Reached: 215286.
- Triggered: 3373.
- Queued progress: 376.
- Accepted non-trigger progress: 1.
- Accepted triggered progress: 375.
- `D_F_spec_lifted`: non-trigger values `[2, 1]`.
- Typed stages: 45 starts, 5760 typed execs.
- Stability failures: 0.
- Runtime lift provenance: spec lifted only; heuristic/manual counts 0.

Conclusion:

- This is a valid pre-trigger lift smoke. `D_T` remains 1 for the accepted
  non-trigger seed, while `D_F_spec_lifted` improves from 2 to 1 because the
  `desired_producer` role becomes observed. The accepted reason is TC-rooted
  and replay-stable, not R preservation.

## PNG007: PLTE Deletion BindingSpec

BindingSpec:

- `artifacts/binding_specs/PNG007.native_b2_plte_multi_delete_candidate.yml`

Static gate:

- BindingSpec compile: pass.
- Runtime event map: 8 exact rows, 0 ambiguous, 0 missing, no semantic role
  collapse.

120s dynamic smoke:

- Command output: `/tmp/formtrig_png007_plte_multi_sweep_120s/summary.jsonl`.
- Executions: 383233.
- Reached: 261018.
- Triggered: 225868.
- Queued progress: 25039.
- Accepted non-trigger progress: 0.
- Accepted triggered progress: 25039.
- `D_F_spec_lifted`: candidate values `[3, 2]`.
- Non-trigger candidate `D_F_spec_lifted`: `[3]`.
- Triggered candidate `D_F_spec_lifted`: `[2]`.
- Diagnosis flag: `lift_delta_only_on_triggered_candidates=true`.
- Runtime lift provenance: spec lifted only; heuristic/manual counts 0.

Additional root-orientation check:

- Temporary variant: `/tmp/PNG007.root_notoutcome_candidate.yml`.
- Seed readiness: pass but RNT non-trigger seeds already have root value 1 and
  `D_F_spec_lifted=2`.
- This contradicts the intended root predicate as a pre-trigger signal, so
  simply changing `value_mode` to `not_outcome` is not a valid fix.

Conclusion:

- PNG007 is a strong terminal-trigger smoke but not yet a valid pre-trigger
  lift smoke. Current BindingSpec/hook mostly jumps from non-trigger state to
  trigger state; no accepted non-trigger `D_F` improvement was observed.

## LIBXML2_1107: Real CVE Binary-Null Alloc-Fail BindingSpec

BindingSpec:

- `artifacts/binding_specs/LIBXML2_1107.native_b2_alloc_fail_candidate.yml`

Target:

- CVE harness: `benchmarks/cve_harnesses/libxml2_regexp_strdup_fail_replay.c`.
- TC root: `ret->string == NULL` before `strlen(ret->string)` in
  `xmlRegNewParserCtxt`.
- Instrumented binary:
  `/tmp/formtrig_libxml2_1107_full_20260615T090425Z/libxml2_regexp_strdup_fail_replay_formtrig_full`.
- Site map:
  `/tmp/formtrig_libxml2_1107_full_20260615T090425Z/native_env/site_map.tsv`.

Engineering fix required to run this target:

- Full instrumentation produced 212715 site-map rows. The BindingSpec compiler
  and runtime event-map gate previously truncated site maps at 65536 rows.
- `formtrig_binding_spec_compile.c` and `formtrig_binding_map.c` now use
  dynamically grown site-map storage.

Static gate:

- BindingSpec compile: pass.
- `formtrig_lift_spec_audit`: atom 1 `binary-state-null` B4.
- `formtrig_binding_map`: 5 exact rows, 0 ambiguous, 0 missing, no semantic
  role collapse.
- Bound roles: root_observe, guard, desired_producer, use, input_influence.

Seed readiness:

- Output: `/tmp/formtrig_libxml2_1107_binding_check_strict/seed_readiness.json`.
- RNT seed: reached, non-trigger, spec lifted.
- `D_F_spec_lifted`: 4.
- Hot range: byte `[0, 1]`, `set_byte=2`.
- Runtime lift provenance: spec lifted only; heuristic/manual counts 0.

30s dynamic smoke:

- Output: `/tmp/formtrig_libxml2_1107_full_strict_sweep_30s/summary.jsonl`.
- Executions: 22051.
- Reached: 19467.
- AFL saved crashes: 2.
- Terminal triggered execs: 2.
- Queued progress: 1.
- Accepted non-trigger progress: 1.
- Accepted triggered progress: 0.
- `D_F_spec_lifted`: calibration value `[4]`, non-trigger candidate values
  `[1, 3, 2, 4]`, minimum 1.
- Accepted non-trigger reason: `root_aligned_state_transition`.
- Runtime lift provenance: spec lifted only; heuristic/manual counts 0.
- Lift feature audit: pass; no unmapped spec lifted components.

Important interpretation:

- The accepted non-trigger progress is not R preservation. `D_T` remains 1,
  while `D_F_spec_lifted` improves from 4 to 1 because the input-selected
  allocation-failure count moves close to the target `xmlStrdup` allocation.
- The terminal crash input is the expected `02 61`; AFL stores it under
  `default/crashes/`, so CVE terminal success must include AFL crash oracle.
- The first broader BindingSpec variant bound `desired_producer` to the generic
  `xmlStrndup` failure branch and was too weak because it could observe
  non-target strdup failures. The current BindingSpec binds producer progress
  to distance from the harness fail-count operand to the target allocation
  index 2.
- This is a valid real-CVE binary-null lift smoke, but it currently uses
  `FORMTRIG_INSTRUMENT_LEVEL=full`. The next engineering step is selective or
  slice-level instrumentation for only BindingSpec-referenced load/cmp sites so
  the same signal moves closer to native AFL++ throughput.

## Current Engineering Takeaways

- Binding quality is necessary but not sufficient. Static B2/B4 passing only
  proves roles are runtime-grounded, not that mutation will create useful
  pre-trigger ordering.
- Large real-target site maps must not be silently truncated. Dynamic site-map
  storage is required for full/slice instrumentation on real projects.
- Input influence is decisive for binary/null targets. PNG006 without an
  external influence/hook is constant; the same target with an external hook
  shows non-trigger `D_F` improvement.
- CVE crash targets need AFL crash oracle in terminal success accounting.
  Runtime `T` remains terminal-only and must not enter non-trigger `D_F`.
- `lift_delta_only_on_triggered_candidates=true` must not be reported as
  FORMTRIG pre-trigger guidance. PNG007 currently falls into this category.
- Root operand orientation needs dynamic validation. Static site matching
  cannot prove that `outcome`/`not_outcome` matches the TC predicate.
