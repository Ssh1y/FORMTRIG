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
