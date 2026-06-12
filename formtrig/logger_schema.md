# FORMTRIG JSONL Schema

The runtime emits one JSON object per process execution when `FORMTRIG_LOG` is
set. Required fields:

- `reached`: whether the directed target was reached.
- `crash_predicate`: whether the benchmark/application crash predicate was
  satisfied.
- `D_T`: direct binary target/crash distance.
- `D_F`: synthesized FORMTRIG distance from generic runtime safety semantics.
  It is not derived from benchmark oracles such as Magma canaries.
- `D_F_lifted`: producer/slice-based lifted post-reach distance, or `null` if
  no bounded dynamic lift was available.
- `trace_signature`: 64-bit hex signature over post-reach events.
- `target_hit_count`: number of target hits in the execution.
- `hot_byte_ranges`: bounded list of byte ranges and finite-difference
  influence scores.
- `components`: TC-rooted native or lifted progress components. Each component
  includes `kind`, `atom_id`, semantic `role`, priority, direction/source flags,
  source id, context hash, value, and confidence.
- `atom_signals`: per-atom role summary for the AFL++ fast path. Role bits
  distinguish root observation, guard, producer, desired/opposite producer,
  use, lifecycle event, same-object, and input-influence evidence.
- `df_source`: optional object explaining the selected FORMTRIG distance source.
  `mode=1` means producer-linked lifted comparison, `mode=2` manual direct
  margin, `mode=3` manual lifted distance, `mode=4` direct binary sink,
  `mode=5` bounded pre-reach control candidate, and `mode=6` null-pointer
  sink lifted through a bounded producer/store slice.
- `lift_stats`: candidate and rejection counters for binary lifting.
- `lift_candidates`: optional debug-only candidate list when
  `FORMTRIG_DEBUG_EVENTS=1`; debug candidates include `input_start` and
  `input_len` when runtime provenance links the candidate to input bytes.
- `debug_events`: optional debug-only bounded event list when
  `FORMTRIG_DEBUG_EVENTS=1`; debug events also include input provenance when
  known.

For crash-predicate binary sinks, null-pointer sink discovery is restricted to
the target/crash-predicate window. `FORMTRIG_SINK_LOOKBACK` allows a small
lookback before the target marker to tolerate compiler scheduling of the sink
comparison. For non-crashing null-pointer sinks, producer/store lifting treats
the last field write before the sink load as the causal boundary. Generic
comparisons after that last write are not used as null-lift sources because
they cannot change the already-written pointer unless a later write exists in
the dynamic trace.

`FORMTRIG_LIFT_WINDOW` controls the bounded dynamic lifting window. The default
is large enough for post-reach structure-state sinks but remains capped by the
runtime ring buffer. `FORMTRIG_DEBUG_EVENT_WINDOW` controls how many recent
events are emitted when `FORMTRIG_DEBUG_EVENTS=1`.

Example:

```json
{"reached":true,"crash_predicate":false,"D_T":1,"D_F":7,"D_F_lifted":7,"trace_signature":"0x31f4b20e0b9c8a1d","target_hit_count":1,"hot_byte_ranges":[{"start":0,"len":1,"influence":1}],"df_source":{"mode":1,"kind":7,"site_id":123,"predicate":37,"outcome":0,"after_reach":true,"distance":7,"a":15,"b":8,"linked_count":1},"lift_stats":{"candidates":2,"linked":1,"reject_pointer":0,"reject_zero":0,"reject_noslice":1,"reject_prereach":0}}
```

## AFL++ Progress Summary

`formtrig/tools/formtrig_progress_summary.c` consumes AFL++ `fuzzer_stats` and
`formtrig_progress.jsonl` and emits one campaign-level JSON object. The summary
keeps aggregate counters from AFL++ and adds experiment-facing diagnostics:

- `progress_status`: `triggered`, `progress_queued`, or `not_progressing`.
- `limiting_reason`: first coarse explanation when no FORMTRIG progress was
  queued, such as `no_formtrig_signal`, `target_not_reached`,
  `no_actionable_component`, `constant_d_f`, `dominance_rejected`, or
  `progress_not_replay_stable`.
- `d_f_constant`: whether all observed finite `D_F` values were identical.
- `has_lifted_signal`, `has_actionable_component`, `has_atom_signal`,
  `has_role_signal`: quick checks for the native lift signal chain.
- `reason_counts`: all logged reasons.
- `accept_reason_counts`, `reject_reason_counts`, `stability_reason_counts`:
  reasons split by queue admission, frontier rejection, and replay stability.

These summary diagnostics are audit data. They do not feed back into fuzzing
decisions and they do not use trigger-oracle state to score non-trigger inputs.

## LLVM Site Map

When `FORMTRIG_SITE_MAP` is set at compile time, the LLVM pass appends one TSV
row for each instrumented site:

```text
site_id kind function inst_no opcode file line column
```

`formtrig/tools/formtrig_site_map.c` filters this map by file, function, kind,
and source line. It can emit:

- `csv`: matching rows plus `mapping_status` (`exact`, `ambiguous`, `missing`).
- `ids`: comma-separated site ids.
- `env`: `FORMTRIG_TARGET_SITE_IDS=...` for source-line TC campaigns.
- `lift-spec`: draft `role_component` rows for `FORMTRIG_LIFT_SPEC`.

Draft lift-spec rows are only binding inputs. They must still pass the native
binding-tier audit before a lifted plan is trusted.

## Binding And Runtime Event Map

`FORMTRIG_LIFT_SPEC` is the current native BindingSpec input format. It binds
TC atoms to runtime-observable roles through instrumented event kinds and site
ids. The runtime consumes this file directly, but campaigns should first map it
against the LLVM site map:

```sh
formtrig_binding_map --category binary-null \
  --site-map site_map.tsv formtrig.lift > formtrig_runtime_event_map.csv
```

The resulting runtime event map includes:

- `binding_id`, `atom_id`, semantic `role`, event kind, site id, and stable
  `event_id`.
- source mapping fields from `FORMTRIG_SITE_MAP`.
- `mapping_status`: `exact`, `ambiguous`, or `missing`.
- `binding_tier`: B0 through B4.
- `lift_allowed` and `reason`.
- `semantic_role_collapse` when multiple semantic roles for an atom collapse
  onto the same runtime site.

The campaign runner treats missing runtime events, role collapse, and
insufficient binding tier as hard failures for lifted plans. This is the
runtime-grounded quality gate between BindingSpec and the AFL++ RuntimeSignal
ABI; it is intentionally separate from target-specific repair or format logic.
