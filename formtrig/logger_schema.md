# FORMTRIG JSONL Schema

The runtime emits one JSON object per process execution when `FORMTRIG_LOG` is
set. Required fields:

- `reached`: whether the directed target was reached.
- `crash_predicate`: whether the benchmark/application crash predicate was
  satisfied.
- `D_T`: direct binary target/crash distance.
- `D_F`: synthesized FORMTRIG distance from generic runtime safety semantics.
  It is not derived from benchmark oracles such as Magma canaries.
- `D_F_lifted`: selected lifted distance used by the current runtime mode.
  FORMTRIG-main selects BindingSpec-driven lift by default.
- `D_F_spec_lifted`: BindingSpec/runtime-event-map generated lifted distance.
- `D_F_heuristic_lifted`: runtime-synthesized exploratory lift from generic
  event-ring heuristics. It is not FORMTRIG-main guidance unless
  `FORMTRIG_ALLOW_HEURISTIC_LIFT=1` is set.
- `D_F_manual_lifted`: explicit target/manual API lifted distance. It is
  disabled by default and is not FORMTRIG-main guidance.
- `lift_source_flags`: bitset over `FORMTRIG_SOURCE_*` source classes.
- `trace_signature`: 64-bit hex signature over post-reach events.
- `target_hit_count`: number of target hits in the execution.
- `hot_byte_ranges`: bounded list of byte ranges and finite-difference
  influence scores.
- `components`: TC-rooted native or lifted progress components. Each component
  includes `kind`, `atom_id`, semantic `role`, priority, direction/source flags,
  source id, context hash, value, and confidence.
- `feature_source_event_ids`: the component source ids used by lifted features.
  For normalized BindingSpecs these ids match `formtrig_runtime_event_map.csv`
  `event_id` values.
- `uses_trigger_oracle`: always `false` for feature computation. The terminal
  `crash_predicate` flag is reported separately and is not a non-trigger
  progress feature.
- `uses_target_id_specific_rule`: `true` only when explicit manual target lift
  APIs are enabled and used.
- `uses_runtime_heuristic`, `uses_spec_lifted`, and `uses_manual_target`:
  source-separation audit fields for lifted progress.
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
  Initial frontier admission does not count as `progress_queued`.
- `frontier_progress_accept_events`: accepted non-initial frontier updates.
  This excludes `initial_frontier_seed`, which is only setup state.
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

`formtrig/tools/formtrig_campaign_diagnose.c` consumes the campaign summary,
the runtime event map, and the lifted-feature provenance audit, then writes
`formtrig_diagnosis.json`. This is the experiment-readiness gate for result
interpretation. It reports:

- `experiment_ready`: true only when runtime signal reached the target,
  spec-driven lifted signal exists, actionable atom/role components are present,
  binding rows are exact/allowed, provenance passes, and heuristic/manual lifted
  sources did not enter FORMTRIG-main.
- `has_tc_rooted_progress`: true only for trigger or accepted non-initial
  progress, not for initial frontier seeds.
- `diagnosis`: a single primary explanation such as
  `seed_does_not_reach_target`, `insufficient_binding`,
  `semantic_role_collapse`, `no_spec_lifted_signal`, `constant_lift_signal`,
  `no_new_non_dominated_progress`, or `queued_tc_rooted_progress`.

## Seed Readiness

`scripts/run_formtrig_seed_readiness.sh` replays the initial seed corpus through
the native target before AFL++ starts. It writes `formtrig_seed_readiness.json`
with:

- per-seed `reached`, `triggered`, `rnt`, `spec_lifted`,
  `heuristic_lifted`, `manual_lifted`, `components`, `atom_signals`, and
  `role_signals`.
- aggregate `reached`, `triggered`, `rnt`, and lifted-source counters.
- `status` and `diagnosis`, such as `ready`, `no_seed_files`,
  `no_formtrig_runtime_signal`, `seed_does_not_reach_target`,
  `no_reached_non_trigger_seed`, `no_spec_lifted_signal`,
  `heuristic_lift_used`, or `manual_target_lift_used`.

Campaigns run this preflight by default in warning mode. Formal RNT-seeded
experiments should use `--seed-preflight require`; this fails before AFL++ if
the initial corpus cannot produce reached non-trigger, spec-driven,
BindingSpec-grounded runtime signal.

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
- `binding-spec`: a first-pass high-level BindingSpec manifest for the matched
  source event and requested atom/role.
- `lift-spec`: draft `role_component` rows for `FORMTRIG_LIFT_SPEC`.

Source-line generated BindingSpecs are intended to remove the site-id handoff
from experiment setup. They still represent only the roles requested on the
command line: a generated root-only BindingSpec can satisfy B1 numeric/equality
binding, but binary/null and lifecycle targets remain blocked until explicit
producer/use or lifecycle-event bindings are added. Draft lift-spec rows are
only binding inputs. They must still pass the native binding-tier audit before a
lifted plan is trusted.

## BindingSpec And Runtime Event Map

The first-class experiment input is a high-level BindingSpec manifest matching
`formtrig/binding_specs/schema.json`. It names the TC, atoms, root expressions,
semantic binding roles, role expressions, and `observe_at` source locations.
The native runtime does not parse this manifest in the fuzzing hot path.
Campaign setup compiles it once into the lower-level `FORMTRIG_LIFT_SPEC` row
format:

```sh
formtrig_binding_spec_compile --site-map site_map.tsv \
  --out formtrig.lift binding_spec.yaml
```

`FORMTRIG_LIFT_SPEC` is the runtime-facing probe-spec format. It binds TC atoms
to runtime-observable roles through instrumented event kinds and resolved site
ids. The runtime consumes this file directly, but campaigns should first map it
against the LLVM site map:

```sh
formtrig_binding_map --category binary-null \
  --site-map site_map.tsv --normalized-spec formtrig.normalized.lift \
  formtrig.lift > formtrig_runtime_event_map.csv
```

Low-level specs may include per-atom category metadata:

```text
atom_category 1 equality-magic
atom_category 2 binary-state-null
```

The high-level BindingSpec compiler emits these rows from `atoms[].kind`.
`--category` remains only a fallback for legacy single-class specs. Binding
quality gates compute minimum tier per atom, so mixed TCs such as
`equality/magic && binary-state-null` do not incorrectly apply one global tier
to every atom.

The resulting runtime event map includes:

- `binding_id`, `atom_id`, semantic `role`, event kind, site id, and stable
  `event_id`.
- source mapping fields from `FORMTRIG_SITE_MAP`.
- `mapping_status`: `exact`, `ambiguous`, or `missing`.
- `binding_tier`: B0 through B4.
- `lift_allowed` and `reason`.
- `semantic_role_collapse` when multiple semantic roles for an atom collapse
  onto the same runtime site.

When `--normalized-spec` is used, the tool writes the runtime-facing
`FORMTRIG_LIFT_SPEC` whose component `source_id` and `context_hash` are the
stable `event_id` from the runtime event map. AFL++ progress logs can therefore
trace each lifted component back to a specific BindingSpec row and LLVM site.

The campaign runner treats missing runtime events, role collapse, and
insufficient binding tier as hard failures for lifted plans. This is the
runtime-grounded quality gate between BindingSpec and the AFL++ RuntimeSignal
ABI; it is intentionally separate from target-specific repair or format logic.

## Lifted Feature Audit

When a campaign has both `--lift-spec` and `--site-map`, the runner also emits:

```text
OUT/default/formtrig_lift_feature_audit.json
```

This audit reads `formtrig_runtime_event_map.csv` and
`formtrig_progress.jsonl`. It verifies that nonzero-atom lifted components in
AFL++ progress logs use `source_id` values present in the runtime event map. For
non-trigger accepted lifted progress, at least one lifted component must map
back to a BindingSpec/runtime event id. Unmapped lifted progress fails the
campaign because it is not runtime-grounded FORMTRIG progress.

## Lift Source Separation

Runtime and AFL++ logs separate lifted signal sources:

- `FORMTRIG_SOURCE_SPEC_LIFTED`: BindingSpec/event-map generated components.
- `FORMTRIG_SOURCE_HEURISTIC_LIFTED`: generic runtime synthesized lift.
- `FORMTRIG_SOURCE_MANUAL_TARGET`: explicit target/manual API lift.

FORMTRIG-main uses only nonzero-atom lifted components marked
`FORMTRIG_COMPONENT_SPEC_LIFTED`. `FORMTRIG_COMPONENT_HEURISTIC_LIFTED` is
enabled only by `FORMTRIG_ALLOW_HEURISTIC_LIFT=1`; manual target lift is enabled
only by `FORMTRIG_ALLOW_MANUAL_LIFT=1`. Scalar atom-0 lifted distances are
logged for diagnosis but are not actionable frontier components.
