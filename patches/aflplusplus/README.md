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

For ASAN/UBSAN terminal-oracle fuzzing on hosts where `core_pattern` routes
crashes through apport/systemd-coredump, prefer exit-code crash accounting over
`abort_on_error=1`:

```sh
ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0 \
UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0 \
AFL_CRASH_EXITCODE=86 \
AFL_FORMTRIG=1 FORMTRIG_TARGET_BUG=<tc-label> afl-fuzz ...
```

The FORMTRIG AFL++ patch accepts this mode only when `AFL_CRASH_EXITCODE`
matches the ASAN `exitcode=` value; otherwise AFL++ keeps its default
`abort_on_error=1` safety check. Use
`scripts/formtrig_experiment_gate.sh --terminal-oracle-only` to validate this
oracle separately from the strict pre-trigger guidance gate.

Faithful AFL++-family baselines use the same local AFL++ artifact. The
FORMTRIG patch installer also applies
`formtrig_llvm18_cmplog_compat.patch`, which updates older AFL++ pass sources
that used the removed LLVM `IntegerType::getInt8PtrTy` API. This is required
for CmpLog/Redqueen baseline builds on LLVM 18 hosts. Rebuild the LLVM pass
objects with the matching LLVM toolchain before running those baselines:

```sh
LLVM_CONFIG=llvm-config-18 \
  make -C experiments/aflplusplus/AFLplusplus -f GNUmakefile.llvm \
  cmplog-routines-pass.so cmplog-instructions-pass.so \
  cmplog-switches-pass.so compare-transform-pass.so \
  afl-llvm-dict2file.so SanitizerCoveragePCGUARD.so afl-llvm-pass.so
```

The LIBCOAP baseline wrapper checks this with a tiny
`AFL_LLVM_CMPLOG=1 afl-clang-fast` compile before accepting CmpLog or
Redqueen-mode runs. Do not count AFL++ LAF/split-switches as a faithful
baseline until its LLVM pass self-test is fixed separately; the current
verified baseline path does not enable LAF.

Or use the repository campaign wrapper:

```sh
./scripts/run_formtrig_aflpp_campaign.sh \
  --in seeds --out results/run1 --target-bug <tc-label> \
  --category binary-null --binding-spec binding_spec.yaml \
  --site-map site_map.tsv --target-site-ids 12345,67890 \
  --seed-preflight require --duration 1800 \
  -- ./target @@
```

For repeatable experiments, prefer a small line-oriented manifest and let the
repository runner assemble BindingSpec compilation, seed readiness, AFL++,
summary, and diagnosis:

```text
target_id: BUG001
category: numeric
seed_dir: seeds
out_dir: results/BUG001/formtrig
duration: 1800
seed_preflight: require
binding_spec: BUG001.binding.yaml
site_map: build/formtrig-native/site_map.tsv
target_site_ids: 12345
target_cmd: ./build/target @@
```

Run it with:

```sh
./scripts/run_formtrig_native_manifest.sh BUG001.manifest
```

The manifest also supports generating a first-pass high-level BindingSpec from
one source site using `source_file`, `source_line`, `source_kind`, `tc_expr`,
`atom_*`, `role`, `component`, `priority`, `direction`, and `value_mode`.

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

Before fuzzing, the runner also executes
`scripts/run_formtrig_seed_readiness.sh` unless `--seed-preflight off` is set.
The preflight writes `OUT/default/formtrig_seed_readiness.json` after the run
starts, and always leaves the same JSON under `OUT/.formtrig/` even if
`--seed-preflight require` aborts before AFL++. For formal RNT-seeded
experiments, use `--seed-preflight require` so a campaign fails fast when the
seed corpus has no reached non-trigger seed, no spec-driven lifted signal, or
manual/heuristic lifted source leakage.

`run_native_formtrig_smoke.sh` checks the native runtime role signal, manual
lifted-component gating, high-level BindingSpec compilation, a
`FORMTRIG_LIFT_SPEC` role binding, native binding-tier audit, AFL++ queue
admission by FORMTRIG progress, LLVM pass build, source-line site-map
resolution, generated lift-spec audit, runtime event-map quality gate,
semantic-role collapse rejection, typed mutation execution, progress-summary
generation, lifted-feature provenance audit, separated accept/reject/stability
reasons, campaign diagnosis fields, spec/heuristic/manual source separation,
seed readiness preflight, and that `afl-fuzz` was built with `NO_PYTHON=1`.
