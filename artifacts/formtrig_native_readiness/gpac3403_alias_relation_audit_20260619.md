# GPAC_3403 Alias Relation Audit

- Lift spec: `artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_runtime_smoke_20260619T194029Z/b7.normalized.lift`
- Runtime logs: 1
- Verdict: `release_reassign_alias_observed_terminal_cleanup_missing`
- Complete alias/free relation: `False`
- Release->reassign alias observed: `True`

## Runtime Summary

| runtime | status | records | release=reassign | cleanup values | best release | best same_object | best cleanup |
|---|---:|---:|---:|---:|---|---|---|
| artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_runtime_smoke_20260619T194029Z/variant_000005.b7.runtime.jsonl | `release_reassign_alias_observed_cleanup_differs` | 1 | 1 | 1 | `[98271827709808]` | `[98271827709808]` | `[98271827543568]` |

The sample release and reassign-buffer values match, but no runtime record proves the later GF_BitStream->original cleanup free uses the same pointer.
