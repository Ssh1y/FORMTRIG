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

For source-line TC experiments, build the target with the LLVM pass and
`FORMTRIG_SITE_MAP=/path/to/site_map.tsv`. Then resolve known TC source
locations with the native helper:

```sh
./scripts/build_formtrig_llvm_pass.sh build/formtrig_pass.so
./scripts/run_formtrig_source_site_smoke.sh
cc -std=c11 -Iformtrig/include formtrig/tools/formtrig_site_map.c \
  -o formtrig_site_map
./formtrig_site_map --file bug.c --line 123 --kind cmp --emit env site_map.tsv
```

`build_formtrig_llvm_pass.sh` prints the clang arguments needed for the local
LLVM version. LLVM 11 uses legacy `-Xclang -load`; LLVM 12+ uses
`-fpass-plugin`.

The printed `FORMTRIG_TARGET_SITE_IDS=...` value can be passed to
`run_formtrig_aflpp_campaign.sh --target-site-ids ...`. Campaigns should use a
high-level BindingSpec manifest matching `formtrig/binding_specs/schema.json`.
The runner compiles that manifest with `formtrig_binding_spec_compile` into
runtime-facing `FORMTRIG_LIFT_SPEC` rows before any fuzzing starts. The same
site-map helper can still emit draft low-level rows with `--emit lift-spec` for
debugging, but those rows are not the first-class experiment input.
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
event id.

`run_native_formtrig_smoke.sh` checks the native runtime role signal, manual
lifted-component gating, high-level BindingSpec compilation, a
`FORMTRIG_LIFT_SPEC` role binding, native binding-tier audit, AFL++ queue
admission by FORMTRIG progress, LLVM pass build, source-line site-map
resolution, generated lift-spec audit, runtime event-map quality gate,
semantic-role collapse rejection, typed mutation execution, progress-summary
generation, lifted-feature provenance audit, separated accept/reject/stability
reasons, campaign diagnosis fields, spec/heuristic/manual source separation,
and that `afl-fuzz` was built with `NO_PYTHON=1`.
