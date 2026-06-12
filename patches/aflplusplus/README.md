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
  --category binary-null --lift-spec formtrig.lift --duration 1800 \
  -- ./target @@
```

The target must be linked with `formtrig/runtime/formtrig_runtime.c` and include
`formtrig/include` so it can publish `formtrig_shm_record_t` through the native
shared-memory ABI.

`run_native_formtrig_smoke.sh` checks the native runtime role signal, a
`FORMTRIG_LIFT_SPEC` role binding, native binding-tier audit, AFL++ queue
admission by FORMTRIG progress, typed mutation execution, progress-summary
generation, and that `afl-fuzz` was built with `NO_PYTHON=1`.
