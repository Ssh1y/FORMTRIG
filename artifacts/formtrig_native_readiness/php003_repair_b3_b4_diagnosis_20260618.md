# PHP003 B3/B4 Repair Diagnosis - 2026-06-18

## Verdict

Current PHP003 B3/B4 repair is **observation lift only**, not effective
R-to-T guidance.

The important distinction is:

```text
FORMTRIG can observe lifted PHP003-side state.
B4 can mutate IFD1 JPEGInterchangeFormatLength below 4.
But terminal _T remains 0 because the active php-fuzz-exif runner does not
populate ImageInfo->Thumbnail.data under exif_read_data's default path.
```

Therefore PHP003 is not a positive endpoint result yet.

Update: this verdict applies to the stock `php-fuzz-exif` runner. The repaired
`exif_thumbnail(stream,width,height)` runner has now been built and short
screened in:

```text
artifacts/formtrig_native_readiness/php003_thumbnail_runner_repair_20260618.md
artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_hook_120s_20260618/summary.tsv
```

On that runner, the same B4 BindingSpec reaches pre-trigger guidance and
terminal `_T` in a 120-second smoke. The remaining limitation moves from
harness/API lifecycle to scalar `D_F_spec_lifted` aggregation.

2026-06-18 follow-up: the scalar aggregation blocker was repaired by separating
single-component spec distance from multi-role residual role-graph distance.
After rebuilding the `exif_thumbnail` binary, the same B4 BindingSpec now
produces non-constant scalar lifted distance before/alongside `_T`:

```text
artifact = artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_hook_20s_role_df_20260618/summary.tsv
diagnosis = triggered
D_F_spec_lifted values = {2,3}
non-trigger candidate D_F_spec_lifted values = {2,3}
terminal _T = 277
```

The remaining PHP003 gap is no longer scalar aggregation; it is faithful
same-runner baseline comparison and replicated longer endpoint evidence.

## Current Lift Degree

B4 hook run:

```text
artifact:
  artifacts/formtrig_native_readiness/raw/php003_binding_repair_b4_hook_20s_20260618/summary.tsv

status = not_ready
diagnosis = constant_lift_signal
execs = 4805
reached = 1565
corpus = 157
progress_events = 1210
spec_lifted_events = 1210
role_signal_events = 1210
typed_execs = 120
typed_finds = 7
d_f_spec_lifted_min = 0
d_f_spec_lifted_max = 0
d_f_spec_lifted_constant = true
accepted_non_trigger_progress = 0
saved_non_trigger_progress = 0
saved_triggered_progress = 0
terminal _T = 0
```

This means the current repair produces FORMTRIG-visible events, but the
spec-driven distance is constant. It does not rank inputs by closeness to
terminal `_T`.

## B3 Result

The B3 sweep moved candidate bindings into local `exif_scan_thumbnail` sites.
All three candidates failed the readiness gate:

```text
artifact:
  artifacts/formtrig_native_readiness/raw/php003_binding_repair_b3_sweep_20s_20260618/summary.tsv

candidates = 3
status = not_ready
diagnosis = constant_lift_signal
accepted_non_trigger_progress = 0
saved_non_trigger_progress = 0
saved_triggered_progress = 0
terminal _T = 0
```

So simply rebinding near the local thumbnail guard is not enough.

## B4 Hook Result

The B4 hook is wired and does mutate the expected EXIF field:

```text
hook:
  scripts/formtrig_hooks/php_exif_thumbnail_length_hook.py

binding:
  artifacts/binding_specs/php003_repair_candidates/PHP003.native_b4_thumbnail_length_hook_candidate.yml

hook enabled = true
source = binding_spec
typed_execs = 120
typed_finds = 7
```

Queue probe found six saved queue files with IFD1
`JPEGInterchangeFormatLength < 4`:

```text
id:000005...op:ftgtype,pos:0,+cov       length=1 prefix=ffd8ffe0
id:000009...op:ftgtype,pos:85,+cov      length=0 prefix=ffd8ffe0
id:000011...op:ftgtype,pos:170          length=2 prefix=ffd8ffe0
```

These inputs satisfy the `Thumbnail.size < 4` half of PHP003, yet terminal
`_T` remains zero.

## Why `_T` Still Does Not Appear

PHP003's canary is:

```text
MAGMA_AND((bool)data, ImageInfo->Thumbnail.size < 4)
```

The B4 queue evidence shows the size half is reachable. The missing half is
`data != NULL`.

Existing runner audit:

```text
artifacts/rnt_collection_logs/php_exif_thumbnail_runner_mismatch.log
```

states that `fuzzer-exif.c` creates a memory stream and calls:

```text
fuzzer_call_php_func_zval("exif_read_data", 1, &stream_zv)
```

In PHP `exif_read_data`, the fourth optional argument is `read_thumbnail`,
defaulting to `false`. The thumbnail extraction/build paths return early when
`ImageInfo->read_thumbnail` is false, so `ImageInfo->Thumbnail.data` is not
populated for the thumbnail scanner under the current runner.

This matches the current observation: length can be driven below 4, but
`data` remains false, so `MAGMA_AND(data, size < 4)` never becomes `_T`.

## Decision

Do not spend matched endpoint baseline budget on PHP003 under the current
`php-fuzz-exif` runner.

Next valid options:

```text
1. Build the new PHP003_exif_thumbnail native asset:
   artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/build_plan.json
2. Rebuild native FORMTRIG and rerun BindingSpec validation.
3. Only if accepted non-trigger progress and non-constant D_F appear, move
   PHP003 back toward matched baseline comparison.
4. If the runner must stay unchanged, keep PHP003 as a harness-lifecycle
   negative/control, not as a FORMTRIG positive result.
```
