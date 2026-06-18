# PHP003 Thumbnail Runner Repair - 2026-06-18

## Purpose

PHP003 requires both halves of this Magma canary:

```text
MAGMA_AND((bool)data, ImageInfo->Thumbnail.size < 4)
```

The stock `php-fuzz-exif` runner calls `exif_read_data` with one argument.
That keeps `read_thumbnail=false`, so `ImageInfo->Thumbnail.data` is not
populated even when the EXIF IFD1 thumbnail length is mutated below 4.

## New Native Asset Entry

Build plan:

```text
artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/build_plan.json
artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/build_plan.md
```

Expected validation asset:

```text
program = exif_thumbnail
target_cmd = artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/out/afl/exif_thumbnail @@
site_map = artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/out/formtrig_native/formtrig_sites.tsv
```

The generated runner instrumentation script derives a new PHP fuzzer:

```text
sapi/fuzzer/fuzzer-exif_thumbnail.c
php-fuzz-exif_thumbnail -> $OUT/exif_thumbnail
```

The derived runner calls:

```text
fuzzer_call_php_func_zval("exif_thumbnail", 3, args);
```

with `stream`, `width`, and `height` arguments. The third argument is important:
PHP's `exif_thumbnail` only calls `exif_scan_thumbnail` when width/height output
arguments are present, and PHP003's canary is inside `exif_scan_thumbnail`.

## Current Status

```text
status = executed
dependency_preflight = ok
build_plan_status = executed
binary = artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/out/afl/exif_thumbnail
site_map_lines = 284140
```

The build repaired the PHP fuzzer build system as well as the runner:

```text
config.m4:
  PHP_FUZZER_TARGET([exif_thumbnail], PHP_FUZZER_EXIF_THUMBNAIL_OBJS)

Makefile.frag:
  $(SAPI_FUZZER_PATH)/php-fuzz-exif_thumbnail: ...

build.sh:
  FUZZERS includes php-fuzz-exif_thumbnail
```

## New Runner Readiness And Short Screen

Seed readiness with the previous B4 thumbnail-length BindingSpec:

```text
artifact:
  artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_seed_readiness_20260618/formtrig_seed_readiness.json

status = pass
replayed_seeds = 5
reached = 5
triggered = 0
rnt = 5
spec_lifted = 5
heuristic_lifted = 0
manual_lifted = 0
spec_d_f_unique = 1
diagnosis = ready_constant_seed_spec_d_f_needs_mutation_calibration
```

The important delta versus the stock `exif` runner is that
`desired_producer` is now observed as `1`: the thumbnail producer lifecycle is
reachable. The seed corpus is still constant until mutation starts.

20-second B4 hook screen:

```text
artifact:
  artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_hook_20s_20260618/summary.tsv

diagnosis = queued_tc_rooted_progress
pretrigger_lift_guidance_ready = true
execs = 7355
reached = 307
typed_execs = 124
typed_finds = 11
queued_progress = 1
accepted_non_trigger_progress = 1
saved_non_trigger = 1
terminal _T = 0
variable role = use
```

120-second B4 hook screen:

```text
artifact:
  artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_hook_120s_20260618/summary.tsv

diagnosis = triggered
pretrigger_lift_guidance_ready = true
execs = 43516
reached = 7385
typed_execs = 490
typed_finds = 45
queued_progress = 32
accepted_non_trigger_progress = 1
saved_non_trigger = 1
saved_triggered = 31
terminal _T = 277
first _T monitor upper bound = 60s
```

This is endpoint smoke evidence for the repaired runner, not final matched
baseline evidence. It proves that PHP003 was previously blocked by harness/API
lifecycle and that the new runner can convert the B4 BindingSpec into
pre-trigger progress and terminal `_T`.

## Scalar Role-Graph Repair

The first repaired-runner screens exposed a real runtime aggregation bug: the
`root_observe` and `input_influence` components had lower-is-better value `0`,
so the scalar `D_F_spec_lifted` collapsed to `0` even while the `use` role still
varied. That defeated the intended sortable lifted signal.

The runtime now keeps single-component spec distance separate from role-graph
spec distance. When an atom has a multi-role TC-rooted graph, `D_F_spec_lifted`
uses the residual role-graph cost instead of the minimum single component.

Post-repair seed replay on the rebuilt `exif_thumbnail` binary:

```text
artifact = artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_seed_readiness_role_df_20260618_r2/formtrig_seed_readiness.json
replayed = 5
reached/RNT/spec_lifted = 5/5/5
triggered = 0
D_F_spec_lifted values = {2}
```

Post-repair 20s B4 sweep:

```text
artifact = artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_hook_20s_role_df_20260618/summary.tsv
diagnosis = triggered
pretrigger_lift_guidance_ready = true
execs = 5802
reached = 2667
queued_progress = 32
saved_non_trigger = 1
saved_triggered = 31
terminal _T = 277
D_F_spec_lifted constant = false
D_F_spec_lifted values = {2, 3}
non-trigger candidate D_F_spec_lifted values = {2, 3}
variable role = use
```

PHP003 can now be used as repaired-runner scalar-D_F smoke evidence. It is not
yet final endpoint evidence: faithful AFL++/CmpLog/related baselines still need
to be run on the same `exif_thumbnail` runner with replicated longer budgets.
