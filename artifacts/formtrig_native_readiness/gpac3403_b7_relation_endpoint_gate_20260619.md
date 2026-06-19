# GPAC_3403 B7 Relation Endpoint Gate - 2026-06-19

Raw run:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_20260619T231431Z`

Runner:
`scripts/run_gpac3403_b7_relation_endpoint_gate.sh`

BindingSpec:
`artifacts/binding_specs/GPAC_3403.native_b7_relation_value_candidate.yml`

## Result

The 601s FORMTRIG-only B7 relation gate passed the strict pre-trigger guidance
gate but did not reach endpoint terminal behavior.

```text
execs_done = 2894
reached_execs = 2895
terminal_triggered_execs = 0
queued_progress = 35
accepted_non_trigger = 35
saved_non_trigger = 35
typed_execs = 224
typed_finds = 38
spec_lifted_events = 1819
D_F_spec_lifted = 2..5
```

The run therefore supports FORMTRIG mechanism evidence on GPAC_3403:
TC-rooted lifted signal is stable, non-constant, saved as non-trigger progress,
and used by the typed-retained endpoint replay path. It is not endpoint benefit
evidence.

## Endpoint Replay

Typed retention captured 224 records and replayed 128 endpoint variants.
None produced ASAN, double-free, native crash, sanitizer crash, or timeout.
The positive control still crashes natively and contains the ASAN double-free
signature, so the endpoint oracle is live.

```text
variant HEVC import files = 38 / 128
variant max HEVC import scale = 8 samples / 26 NALUs
variant L-HEVC import files = 6 / 128
variant ASAN double-free files = 0

positive control max HEVC import scale = 172 samples / 413 NALUs
positive control ASAN double-free files = 1
missing positive-control signatures = nal_type_49_not_handled, asan_double_free
```

Compared with the earlier standalone op44-op47 endpoint-scale sweep, this
standard retained gate has better packaging and relation auditing, but its
retained variants are much smaller at the parser/import layer. That points to a
selection/retention problem, not only a HEVC mutator problem.

## Alias Relation

The repaired audit now reads campaign `formtrig_progress.jsonl`
`component_values`, not only direct runtime `components` arrays. The B7 gate
therefore proves release->reassign alias observation:

```text
alias verdict = release_reassign_alias_observed_terminal_cleanup_missing
release value = 111371568390752
same_object value = 111371568390752
cleanup value = 111371568313776
release=same_object = yes
release=cleanup = no
same_object=cleanup = no
```

Claim boundary: GPAC_3403 is still a lifecycle-alias repair target. Do not run
matched 7200s baselines or claim endpoint R2T closure until the cleanup
GF_BitStream->original relation matches the release/reassign pointer, or until
ASAN/double-free appears under the same gate.
