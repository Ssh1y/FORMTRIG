# PNG006 eXIf Native FORMTRIG Long-Run Evidence - 2026-06-15

This note records the first completed 30-minute native FORMTRIG acceptance run
for Magma PNG006 with the eXIf insertion BindingSpec.

## Run

- Output: `/tmp/formtrig_png006_exif_longrun_20260615T1045Z`
- Runner: `scripts/run_formtrig_png006_native_longrun.sh`
- Binary: `/tmp/formtrig_png007_native_build_20260615T045038Z/libpng_read_fuzzer_env18`
- Site map: `/tmp/formtrig_png007_native_build_20260615T045038Z/native_env18/site_map.tsv`
- BindingSpec: `artifacts/binding_specs/PNG006.native_b2_exif_insert_candidate.yml`
- Seeds: `artifacts/rnt_corpus/PNG006/seeds`
- Duration: 1800 seconds

Command:

```bash
scripts/run_formtrig_png006_native_longrun.sh \
  --out /tmp/formtrig_png006_exif_longrun_20260615T1045Z \
  --durations 1800
```

Strict gate command:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite PNG006_30m_acceptance \
  --min-runtime 1800 \
  --out /tmp/formtrig_png006_exif_longrun_20260615T1045Z/gate_30m \
  --run PNG006_exif_30m=/tmp/formtrig_png006_exif_longrun_20260615T1045Z/png006_exif_1800s/candidates/001_PNG006.native_b2_exif_insert_candidate.yml/default
```

## Result

Gate result: pass.

Key counters:

- `run_time=1800`
- `execs_done=9527259`
- `execs_per_sec=5292.72`
- `formtrig_reached_execs=8726518`
- `formtrig_triggered_execs=5710408`
- `formtrig_queued_progress=634492`
- `accepted_non_trigger_progress_events=1`
- `saved_non_trigger_progress_events=1`
- `saved_triggered_progress_events=634491`
- `spec_lifted_events=1273466`
- `heuristic_lifted_events=0`
- `manual_lifted_events=0`
- `formtrig_typed_execs=15616`
- `formtrig_typed_finds=7`
- `formtrig_stability_failures=0`

Strict gate CSV:

```text
suite,run,status,reasons,run_time,execs_done,execs_per_sec,reached,terminal_triggered,queued_progress,accepted_non_trigger,saved_non_trigger,saved_triggered,spec_lifted,heuristic_lifted,manual_lifted,experiment_ready,pretrigger_lift_guidance_ready,non_trigger_candidate_lift_delta,lift_delta_only_on_triggered,binding_signal_status,binding_signal_diagnosis,out_dir
"PNG006_30m_acceptance","PNG006_exif_30m","pass","ok",1800,9527259,5292.72,8726518,5710408,634492,1,1,634491,1273466,0,0,"true","true","true","false","pass","triggered","/tmp/formtrig_png006_exif_longrun_20260615T1045Z/png006_exif_1800s/candidates/001_PNG006.native_b2_exif_insert_candidate.yml/default"
```

## Interpretation

This run is valid 30-minute positive evidence under the native acceptance gate:

- FORMTRIG did not rely on heuristic or manual lifted events.
- The BindingSpec produced spec-driven lifted `D_F` signal.
- There was accepted and saved non-trigger progress before terminal-only
  guidance would be sufficient.
- The binding-signal diagnosis reported both triggered and non-trigger
  candidate `D_F` delta, with `lift_delta_only_on_triggered_candidates=false`.

This completes the 30-minute PNG006 acceptance step. The 2-hour PNG006 run is
still pending before treating this case as long-horizon evidence.
