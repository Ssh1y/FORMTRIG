# FORMTRIG JSONL Schema

The runtime emits one JSON object per process execution when `FORMTRIG_LOG` is
set. Required fields:

- `reached`: whether the directed target was reached.
- `crash_predicate`: whether the benchmark/application crash predicate was
  satisfied.
- `D_T`: direct binary target/crash distance.
- `D_F`: selected FORMTRIG distance for the current run mode. In
  FORMTRIG-main this comes from BindingSpec-driven TC-rooted components, not
  benchmark oracles such as Magma canaries.
- `D_F_lifted`: selected lifted distance used by the current runtime mode.
  FORMTRIG-main selects BindingSpec-driven lift by default.
- `D_F_spec_lifted`: BindingSpec/runtime-event-map generated lifted distance.
  For multi-role TC atoms, this is the residual role-graph distance; a single
  lower-is-better component with value `0` must not collapse the whole lifted
  atom to terminal distance before the TC oracle confirms `_T`.
- `D_F_heuristic_lifted`: runtime-synthesized exploratory lift from generic
  event-ring heuristics. It is not FORMTRIG-main guidance unless
  `FORMTRIG_ALLOW_HEURISTIC_LIFT=1` is set.
- `D_F_manual_lifted`: explicit target/manual API lifted distance. It is
  disabled by default and is not FORMTRIG-main guidance.
- `lift_source_flags`: bitset over `FORMTRIG_SOURCE_*` source classes that were
  eligible for guidance in the current run mode.
- `observed_lift_source_flags`: bitset over all lifted source classes observed
  by the runtime, including heuristic/manual sources that were not allowed to
  guide FORMTRIG-main.
- AFL++ progress JSON mirrors this split as `source_flags` and
  `observed_source_flags`; summary/diagnosis report used and observed source
  counts separately.
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
  source-separation audit fields for guidance actually used by the current run
  mode.
- `observed_runtime_heuristic` and `observed_manual_target`: raw-source audit
  fields showing whether disabled exploratory/manual sources were observed.
- `atom_signals`: per-atom role summary for the AFL++ fast path. Role bits
  distinguish root observation, guard, producer, desired/opposite producer,
  use, lifecycle event, same-object, input-influence evidence, and external
  repair hooks.
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

`FORMTRIG_SNAPSHOT_LOG` is an opt-in diagnostic sink for targets that may abort
before the normal `atexit` finalizer writes `FORMTRIG_LOG`. When set, the
runtime appends the same JSON object format during the publish path. It is off
by default. `FORMTRIG_SNAPSHOT_INTERVAL` controls the publish cadence, defaulting
to `1`; finalized or crash-predicate states are written regardless of the
interval so crash triage keeps the last observed lifted state.

Example:

```json
{"reached":true,"crash_predicate":false,"D_T":1,"D_F":7,"D_F_lifted":7,"trace_signature":"0x31f4b20e0b9c8a1d","target_hit_count":1,"hot_byte_ranges":[{"start":0,"len":1,"influence":1}],"df_source":{"mode":1,"kind":7,"site_id":123,"predicate":37,"outcome":0,"after_reach":true,"distance":7,"a":15,"b":8,"linked_count":1},"lift_stats":{"candidates":2,"linked":1,"reject_pointer":0,"reject_zero":0,"reject_noslice":1,"reject_prereach":0}}
```

## AFL++ Progress Summary

`formtrig/tools/formtrig_progress_summary.c` consumes AFL++ `fuzzer_stats` and
`formtrig_progress.jsonl` and emits one campaign-level JSON object. The summary
keeps aggregate counters from AFL++ and adds experiment-facing diagnostics:

- `progress_status`: `triggered`, `progress_queued`,
  `frontier_progress_observed`, or `not_progressing`.
  Initial frontier admission does not count as `progress_queued`.
- `calibrated_frontier_events`: initial corpus calibration events that build
  the starting frontier. These are setup state, not search progress.
- `frontier_progress_accept_events`: accepted non-initial `frontier_accept`
  updates from search. This excludes `calibrated_frontier` and
  `initial_frontier_seed`, which are only setup state.
- `saved_triggered_progress_events`: `saved_progress` events whose runtime
  signal already fired the TC. These are terminal successes, not evidence of a
  non-trigger frontier step.
- `saved_non_trigger_progress_events`: `saved_progress` events that preserve
  reachability without firing the TC and are therefore evidence of non-trigger
  lifted progress.
- `formtrig_saved_progress_log_seen`: number of `saved_progress` candidates
  observed by AFL++ before JSONL sampling.
- `formtrig_saved_triggered_log_seen` and
  `formtrig_saved_non_trigger_log_seen`: triggered and non-trigger splits for
  the saved-progress candidates seen before sampling.
- `formtrig_progress_log_events` and `formtrig_progress_log_dropped`: JSONL
  entries written and entries skipped by logging caps. `saved_progress` uses
  a separate triggered/non-trigger sampler so long runs keep diagnostic
  examples without writing one JSON object for every queued trigger.
- `non_trigger_progress_events`: `saved_non_trigger_progress_events` plus
  non-initial `frontier_progress_accept_events`.
- `has_tc_rooted_progress`: true when the run triggered, saved FORMTRIG
  progress, or observed non-initial frontier progress.
- `has_queued_progress`: true only when FORMTRIG progress was saved into the
  fuzzing queue.
- `has_frontier_progress`: true when dominance/frontier accepted non-initial
  TC-rooted progress, even if that progress was not saved into the queue.
- `has_non_trigger_progress`: true when the run produced replay-stable,
  non-trigger TC-rooted progress. This is the field to use when evaluating
  whether FORMTRIG moved through lifted states before terminal trigger.
- `limiting_reason`: first coarse explanation when no FORMTRIG progress was
  queued, such as `no_formtrig_signal`, `target_not_reached`,
  `no_actionable_component`, `constant_d_f`, `frontier_progress_not_queued`,
  `typed_stage_parent_not_replay_stable`, `dominance_rejected`, or
  `progress_not_replay_stable`.
- `d_f_constant`: whether all observed finite `D_F` values were identical.
- `has_lifted_signal`, `has_actionable_component`, `has_atom_signal`,
  `has_role_signal`: quick checks for the native lift signal chain.
- `reason_counts`: all logged reasons.
- `accept_reason_counts`, `reject_reason_counts`, `stability_reason_counts`:
  reasons split by queue admission, frontier rejection, and replay stability.

These summary diagnostics are audit data. They do not feed back into fuzzing
decisions and they do not use trigger-oracle state to score non-trigger inputs.

Long AFL++ campaigns cap progress logging without disabling diagnostics.
`FORMTRIG_PROGRESS_LOG_LIMIT` caps ordinary non-critical progress events
defaulting to 4096. `FORMTRIG_SAVED_PROGRESS_LOG_LIMIT` keeps the first N
triggered and first N non-trigger `saved_progress` entries per run, defaulting
to 8192 per class. `FORMTRIG_SAVED_PROGRESS_LOG_SAMPLE_RATE` then keeps one
additional saved-progress sample per class every N candidates, defaulting to
1024. Stability rejects and typed-stage boundary events remain critical audit
events and bypass the ordinary event cap.

`formtrig/tools/formtrig_binding_signal_diagnose.c` consumes the runtime event
map and `formtrig_progress.jsonl`, then writes
`formtrig_binding_signal_diagnosis.json`. This is a dynamic BindingSpec quality
diagnostic, separate from provenance. It reports per-atom/per-role samples,
candidate-only samples, unique values, variable roles, and candidate `D_F`
values. For binary/null and lifecycle atoms, it flags cases such as
`guard_only_lift_signal`, `producer_root_use_constant`,
`producer_not_observed_in_candidates`, and
`mutations_lose_best_lifted_state`. These diagnoses prevent a statically valid
BindingSpec from being interpreted as effective lifted guidance when mutation
children do not move TC-rooted producer/use/root or lifecycle roles.

`formtrig/tools/formtrig_campaign_diagnose.c` consumes the campaign summary,
the runtime event map, the lifted-feature provenance audit, and the binding
signal diagnosis, then writes `formtrig_diagnosis.json`. This is the
experiment-readiness gate for result interpretation. It reports:

- `experiment_ready`: true only when runtime signal reached the target,
  spec-driven lifted signal exists, actionable atom/role components are present,
  binding rows are exact/allowed, provenance passes, and heuristic/manual lifted
  sources did not enter FORMTRIG-main.
- `has_tc_rooted_progress`: true only for trigger or accepted non-initial
  progress, not for initial frontier seeds.
- `has_non_trigger_progress`: true only when replay-stable non-trigger lifted
  progress was saved or accepted by the frontier. A run can be `triggered` while
  this remains false.
- `pretrigger_lift_guidance_ready`: true when the run produced either
  non-trigger progress or a non-trigger candidate-side lifted `D_F` delta. This
  is stricter than `experiment_ready` and is the campaign-level indicator for
  whether lifted guidance moved before the terminal trigger.
- `diagnosis`: a single primary explanation such as
  `seed_does_not_reach_target`, `insufficient_binding`,
  `semantic_role_collapse`, `no_spec_lifted_signal`, `constant_lift_signal`,
  `guard_only_lift_signal`, `producer_root_use_constant`,
  `mutations_lose_best_lifted_state`, `no_new_non_dominated_progress`, or
  `queued_tc_rooted_progress`.

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

`scripts/run_formtrig_native_manifest.sh` is a thin experiment wrapper around
the same artifacts. It reads a line-oriented manifest, optionally generates a
first-pass BindingSpec from a source site, then invokes the campaign runner. It
does not change runtime semantics; all authoritative evidence remains in
`formtrig_seed_readiness.json`, `formtrig_runtime_event_map.csv`,
`formtrig_lift_feature_audit.json`, `formtrig_summary.json`,
`formtrig_binding_signal_diagnosis.json`, and `formtrig_diagnosis.json`.

`scripts/run_formtrig_binding_candidate_sweep.sh` evaluates a set of external
BindingSpec or low-level lift-spec candidates without embedding target-specific
rules in FORMTRIG core. For each candidate it runs the same static event-map
gate, seed readiness replay, short AFL++ campaign, provenance audit, and
binding-signal diagnosis. It writes `summary.tsv` and `summary.jsonl` with a
deterministic score plus the candidate's final diagnosis, dynamic
binding-signal diagnosis, queued progress count, trigger count, reached execs,
candidate event count, non-trigger progress counts, saved triggered-progress
counts, accepted non-trigger progress counts, and number of non-guard semantic
roles that varied in mutation candidates. It also reports whether lifted
`D_F` deltas occurred on triggered candidates, non-trigger candidates, or only
after the terminal trigger. Candidate scores strongly prioritize
`pretrigger_lift_guidance_ready`, and penalize
`lift_delta_only_on_triggered_candidates`, after the experiment-readiness and
binding-signal gates are accounted for. A trigger-only candidate therefore does
not outrank a candidate that moves lifted state before the terminal trigger.
This is the intended bridge for offline candidate generation, including manual
review or an optional LLM proposal step: candidate generation may be heuristic,
but candidate admission remains deterministic and runtime-grounded.

`scripts/run_formtrig_manifest_batch.sh` preserves the same distinction in
batch summaries. Its CSV/JSONL rows include `has_non_trigger_progress`,
`non_trigger_progress`, `saved_non_trigger_progress`, and
`saved_triggered_progress` so Magma/CVE long-run tables do not conflate
terminal triggers with lifted non-trigger guidance.

## LLVM Site Map

When `FORMTRIG_SITE_MAP` is set at compile time, the LLVM pass appends one TSV
row for each instrumented site:

```text
site_id kind function inst_no opcode file line column
```

`formtrig/tools/formtrig_site_map.c` filters this map by file, function, kind,
source line, and optional `inst_no` disambiguator. It can emit:

- `csv`: matching rows plus `mapping_status` (`exact`, `ambiguous`, `missing`).
- `ids`: comma-separated site ids.
- `env`: `FORMTRIG_TARGET_SITE_IDS=...` for source-line TC campaigns.
- `binding-context`: JSON context for offline BindingSpec candidate generation.
  It includes the TC/atom metadata, per-category minimum binding tier,
  candidate site rows, role requirements, and the deterministic gates that must
  accept any proposed candidate.
- `binding-spec`: a first-pass high-level BindingSpec manifest for the matched
  source event and requested atom/role.
- `lift-spec`: draft `role_component` rows for `FORMTRIG_LIFT_SPEC`.

Source-line generated BindingSpecs are intended to remove the site-id handoff
from experiment setup. Binding contexts are intended to make manual or optional
LLM-assisted candidate generation inspectable without putting heuristic choices
in FORMTRIG core. They are not evidence that lift is valid. Generated manifests
and draft lift-spec rows still represent only the roles requested or proposed:
a generated root-only BindingSpec can satisfy B1 numeric/equality binding, but
binary/null and lifecycle targets remain blocked until explicit producer/use or
lifecycle-event bindings are added. Draft lift-spec rows are only binding
inputs. They must still pass the native binding-tier audit and dynamic binding
signal diagnosis before a lifted plan is trusted.

## BindingSpec And Runtime Event Map

The first-class experiment input is a high-level BindingSpec manifest matching
`formtrig/binding_specs/schema.json`. It names the TC, atoms, root expressions,
semantic binding roles, role expressions, and `observe_at` source locations.
When one source location lowers to multiple IR events, `observe_at.inst_no`
selects the intended instruction without embedding a site id in the high-level
BindingSpec.
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

For binary/null predicates such as `a == NULL`, a BindingSpec is not a claim
that FORMTRIG recovered the complete influence set of `a`. It is a claim that
the campaign has supplied a TC-rooted guidance subset: root observation,
producer/reset/error-path evidence, guards, use context, same-object relation
when needed, and input-influence roles that typed mutation can act on. The
dynamic binding-signal gate must then prove that this subset is observed on
R-not-T executions, produces non-constant `D_F_spec_lifted` before `_T`, yields
accepted/saved non-trigger frontier progress, and is not supplied by
heuristic/manual lift. Otherwise the result is only observation lift or a
spec-repair blocker.

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

Lifecycle atoms also need explicit object-identity relation metadata. A
`same_object` binding is not enough by itself, even when its value mode observes
an operand. The BindingSpec must declare the relation endpoints and object
expression:

```yaml
role: same_object
relation_from: lifecycle_event
relation_to: use
object_expr: obj
```

The compiler emits:

```text
same_object_relation 1 lifecycle_event use obj
```

`formtrig_lift_spec_audit` and `formtrig_binding_map` require that relation for
compound/lifecycle B3. Without it, the atom is rejected with
`missing_same_object_relation` or `missing_same_object_endpoint`. This prevents a
single stateful probe from being misread as a same-object lifecycle binding.
The native runtime also consumes `same_object_relation`: when a relation is
declared, the `same_object` role is satisfied only after the declared
`relation_from` and `relation_to` roles report the same non-zero object value
through `a`, `b`, or `c` value modes. A lone `same_object` pointer observation
therefore cannot collapse lifecycle `D_F_spec_lifted` to a fully satisfied
role graph.

Binding rows also declare a `value_mode`. Basic modes forward the raw event
distance or operands (`distance`, `hit`, `outcome`, `a`, `b`, `c`). The
expression-driven modes `distance_to_a`, `distance_to_b`, and `distance_to_c`
compute `abs(observed_operand - binding.value)` in the runtime. This is a
generic TC-root transform: the BindingSpec chooses the semantic operand and
target constant, while the runtime only evaluates the declared transform and
does not inspect target ids or trigger-oracle state.

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
OUT/default/formtrig_binding_signal_diagnosis.json
```

This audit reads `formtrig_runtime_event_map.csv` and
`formtrig_progress.jsonl`. It verifies that nonzero-atom spec-lifted components
in AFL++ progress logs use `source_id` values present in the runtime event map.
For non-trigger accepted spec-lifted progress, at least one spec-lifted component
must map back to a BindingSpec/runtime event id. Accepted heuristic/manual lifted
progress fails FORMTRIG-main provenance because it is not BindingSpec-grounded
guidance; ignored heuristic/manual observations are reported separately.

The binding signal diagnosis reads the same progress log but answers a
different question: whether the mapped semantic roles produce useful dynamic
lift. It distinguishes initial/calibrated frontier states from mutation
candidate states. A binary/null target with exact B2 bindings can still be
marked `not_ready` if all mutation candidates preserve only a guard bit while
root, producer, opposite-producer, and use roles remain constant.

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
