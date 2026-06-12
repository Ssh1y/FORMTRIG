# AFL++ FORMTRIG Native Integration

This patch wires FORMTRIG runtime signals into AFL++ without using the Python
prototype path.

Apply and build from the FORMTRIG repository:

```sh
./patches/aflplusplus/apply_formtrig_patch.sh
./scripts/run_native_formtrig_smoke.sh
```

Enable at fuzz time:

```sh
AFL_FORMTRIG=1 FORMTRIG_TARGET_BUG=<tc-label> afl-fuzz ...
```

Or use the repository campaign wrapper:

```sh
./scripts/run_formtrig_aflpp_campaign.sh \
  --in seeds --out results/run1 --target-bug <tc-label> \
  --category binary-null --binding-spec binding_spec.yaml \
  --site-map site_map.tsv --target-site-ids 12345,67890 --duration 1800 \
  -- ./target @@
```

The target must be linked with `formtrig/runtime/formtrig_runtime.c` and include
`formtrig/include` so it can publish `formtrig_shm_record_t` through the native
shared-memory ABI.

For real Make/CMake targets, prepare a source-able native build environment
instead of hand-copying compiler/linker flags:

```sh
./scripts/prepare_formtrig_native_env.sh --out build/formtrig-native \
  --clang /usr/bin/clang-18 --clang++ /usr/bin/clang++-18
. build/formtrig-native/formtrig_native_env.sh
# then configure/build the target with CC/CXX/CFLAGS/CXXFLAGS/LDFLAGS from env
```

The prepared environment pins AFL++'s backend clang to the same LLVM version
used to build the FORMTRIG pass, writes `FORMTRIG_SITE_MAP`, and links the
native runtime archive into the target.

For source-line TC experiments, build the target with the LLVM pass and
`FORMTRIG_SITE_MAP=/path/to/site_map.tsv`. Then resolve known TC source
locations with the native helper:

```sh
./scripts/build_formtrig_llvm_pass.sh build/formtrig_pass.so
./scripts/run_formtrig_source_site_smoke.sh
cc -std=c11 -Iformtrig/include formtrig/tools/formtrig_site_map.c \
  -o formtrig_site_map
./formtrig_site_map --file bug.c --line 123 --kind cmp --emit env site_map.tsv
./formtrig_site_map --file bug.c --line 123 --kind cmp \
  --emit binding-spec --tc-id BUG001 --tc-category numeric-margin \
  --tc-expr 'len > cap' --atom 1 --atom-kind numeric-margin \
  --atom-expr 'len > cap' --atom-root len \
  --role root_observe --component 3 --priority 10 --direction lower \
  --value-mode distance site_map.tsv > BUG001.binding.yaml
```

`build_formtrig_llvm_pass.sh` prints the clang arguments needed for the local
LLVM version. LLVM 11 uses legacy `-Xclang -load`; LLVM 12+ uses
`-fpass-plugin`.

The printed `FORMTRIG_TARGET_SITE_IDS=...` value can be passed to
`run_formtrig_aflpp_campaign.sh --target-site-ids ...`. Campaigns should use a
high-level BindingSpec manifest matching `formtrig/binding_specs/schema.json`.
The runner compiles that manifest with `formtrig_binding_spec_compile` into
runtime-facing `FORMTRIG_LIFT_SPEC` rows before any fuzzing starts. The same
site-map helper can emit a first-pass high-level BindingSpec with
`--emit binding-spec`; for binary/null and lifecycle targets this auto-generated
root-only manifest is intentionally insufficient until producer/use or
lifecycle-event bindings are added. It can also emit draft low-level rows with
`--emit lift-spec` for debugging, but those rows are not the first-class
experiment input.
BindingSpec `atoms[].kind` is emitted as low-level `atom_category` metadata, and
the binding gates use it per atom. The `--category` option is only a fallback for
legacy single-class specs.
FORMTRIG-main uses only BindingSpec-generated lifted components marked as
spec-driven. Runtime heuristic lift is available only as an explicit ablation
with `FORMTRIG_ALLOW_HEURISTIC_LIFT=1`; manual target lift APIs require
`FORMTRIG_ALLOW_MANUAL_LIFT=1` and are not part of main evaluation.

When `--binding-spec`/`--lift-spec` and `--site-map` are provided, the campaign
runner also builds `formtrig/tools/formtrig_binding_map.c` and writes
`formtrig_runtime_event_map.csv`. Missing runtime events, semantic role
collapse, and insufficient binding tiers fail the campaign before fuzzing. On a
passing map, the runner emits a normalized runtime lift spec under
`OUT/.formtrig/formtrig_lift.normalized` and exports that file as
`FORMTRIG_LIFT_SPEC`, so RuntimeSignal component `source_id`/`context_hash`
values match the runtime event-map `event_id`. After fuzzing, the runner writes
`OUT/default/formtrig_lift_feature_audit.json` and fails the campaign if
accepted non-trigger lifted progress cannot be traced back to a mapped runtime
event id. The runner also writes `OUT/default/formtrig_diagnosis.json`, which is
the preferred first file to inspect when a run has zero queued progress. It
separates target-not-reached, insufficient binding, role collapse, constant
lifted signal, dominance rejection, source leakage, and true queued TC-rooted
progress.

`run_native_formtrig_smoke.sh` checks the native runtime role signal, manual
lifted-component gating, high-level BindingSpec compilation, a
`FORMTRIG_LIFT_SPEC` role binding, native binding-tier audit, AFL++ queue
admission by FORMTRIG progress, LLVM pass build, source-line site-map
resolution, generated lift-spec audit, runtime event-map quality gate,
semantic-role collapse rejection, typed mutation execution, progress-summary
generation, lifted-feature provenance audit, separated accept/reject/stability
reasons, campaign diagnosis fields, spec/heuristic/manual source separation,
and that `afl-fuzz` was built with `NO_PYTHON=1`.
