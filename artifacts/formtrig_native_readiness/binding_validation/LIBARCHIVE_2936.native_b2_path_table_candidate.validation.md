# LIBARCHIVE_2936 Binding Candidate Validation

- BindingSpec: `artifacts/binding_specs/LIBARCHIVE_2936.native_b2_path_table_candidate.yml`
- Status: `native_binding_validated`
- Ready for FORMTRIG short gate: `true`
- Native site-map validated: `true`
- TC-rooted static pass: `true`

## Benefit Evidence First

The FORMTRIG-instrumented `libarchive_write_replay` replayed the current RNT
seed as a reached, non-triggering input and produced spec-driven lifted
guidance:

- `status=pass`, `diagnosis=ready_single_rnt_seed`
- `reached=1`, `triggered=0`, `rnt=1`
- `spec_lifted=1`, `components=1`, `atom_signals=1`, `role_signals=1`
- runtime event: `D_T=1`, `D_F=2`, `D_F_spec_lifted=2`
- provenance flags: `uses_spec_lifted=true`, `uses_trigger_oracle=false`,
  `uses_runtime_heuristic=false`, `uses_manual_target=false`
- actionable input hints:
  - `range_start=18`, `range_len=12`, `hint=insert_byte('/')`
  - `range_start=3`, `range_len=12`, `hint=insert_byte('/')`

This is the expected pre-performance evidence: the intermediate FORMTRIG
products are not just instrumentation counters. They converted a binary
terminal condition into a non-trigger, spec-attributed, input-level mutation
signal.

## Mechanism Evidence

- Native site map: `/tmp/formtrig_libarchive_2936_native_env/site_map.tsv`,
  29,160 rows.
- Runtime event map:
  `artifacts/formtrig_native_readiness/binding_validation/LIBARCHIVE_2936.native_b2_path_table_candidate.runtime_event_map.csv`
- Normalized lift spec:
  `artifacts/formtrig_native_readiness/binding_validation/LIBARCHIVE_2936.native_b2_path_table_candidate.normalized.lift`
- Lift audit:
  `artifacts/formtrig_native_readiness/binding_validation/LIBARCHIVE_2936.native_b2_path_table_candidate.lift_audit.csv`
- Seed readiness:
  `artifacts/formtrig_native_readiness/binding_validation/LIBARCHIVE_2936.native_b2_path_table_candidate.seed_readiness.json`
- Runtime log:
  `artifacts/formtrig_native_readiness/binding_validation/LIBARCHIVE_2936.native_b2_path_table_candidate.seed_1.runtime.jsonl`

All six BindingSpec roles bind exactly to real native site-map rows. The atom
audits as `B4,true` for `binary-state-null`, and the harness admissibility audit
remains `admissible` with no flags.

## Boundary

This is not yet a TTE or win-rate result. With one RNT seed, signal entropy is
not a stability result. The next required step is a short FORMTRIG-vs-baseline
screen on LIBARCHIVE_2936, promoted to replicated long-run only if non-trigger
lifted progress converts into earlier terminal hits.
