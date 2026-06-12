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
  --category binary-null --lift-spec formtrig.lift \
  --target-site-ids 12345,67890 --duration 1800 \
  -- ./target @@
```

The target must be linked with `formtrig/runtime/formtrig_runtime.c` and include
`formtrig/include` so it can publish `formtrig_shm_record_t` through the native
shared-memory ABI.

For source-line TC experiments, build the target with the LLVM pass and
`FORMTRIG_SITE_MAP=/path/to/site_map.tsv`. Then resolve known TC source
locations with the native helper:

```sh
cc -std=c11 -Iformtrig/include formtrig/tools/formtrig_site_map.c \
  -o formtrig_site_map
./formtrig_site_map --file bug.c --line 123 --kind cmp --emit env site_map.tsv
```

The printed `FORMTRIG_TARGET_SITE_IDS=...` value can be passed to
`run_formtrig_aflpp_campaign.sh --target-site-ids ...`. The same helper can emit
draft `FORMTRIG_LIFT_SPEC` rows with `--emit lift-spec`; those rows still need
the normal binding-tier audit before the campaign runs.

`run_native_formtrig_smoke.sh` checks the native runtime role signal, a
`FORMTRIG_LIFT_SPEC` role binding, native binding-tier audit, AFL++ queue
admission by FORMTRIG progress, source-line site-map resolution, generated
lift-spec audit, typed mutation execution, progress-summary generation,
separated accept/reject/stability reasons, campaign diagnosis fields, and that
`afl-fuzz` was built with `NO_PYTHON=1`.
