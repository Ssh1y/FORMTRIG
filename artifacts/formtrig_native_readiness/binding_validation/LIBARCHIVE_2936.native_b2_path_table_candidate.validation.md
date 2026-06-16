# LIBARCHIVE_2936 Binding Candidate Validation

- BindingSpec: `artifacts/binding_specs/LIBARCHIVE_2936.native_b2_path_table_candidate.yml`
- Status: `candidate_static_validated`
- Ready for FORMTRIG short gate: `false`
- Native site-map validated: `false`

## What Passed

- `formtrig_binding_spec_compile.c` compiled with `-Wall -Wextra -Werror`.
- `formtrig_lift_spec_audit.c` compiled with `-Wall -Wextra -Werror`.
- The BindingSpec compiles against a temporary synthetic source map used only to test source-selector syntax.
- The generated lift spec audits as `B4,true` for `binary-state-null`.
- Harness admissibility audit reports `admissible` with no flags.

## What This Does Not Prove

The synthetic source map is not native runtime evidence. This artifact does not prove that the source selectors uniquely bind in a FORMTRIG-instrumented libarchive build, and it does not prove dynamic `D_F` variability or accepted non-trigger guidance.

## Required Next Action

Build a FORMTRIG-instrumented `libarchive_write_replay`, generate the native site map, compile this BindingSpec against that map, then run seed-readiness and binding-signal diagnosis before spending fuzzing budget.
