# LIBARCHIVE_2935 Binding Draft Delta

- Target: `LIBARCHIVE_2935`
- Change: readiness moved from `ready_for_binding_spec` to `needs_binding_validation`
- Worklist action: `P1 validate_binding_spec_then_short_screen`
- BindingSpec: `artifacts/binding_specs/LIBARCHIVE_2935.native_b1_idr_extend_identifier_candidate.yml`
- Static TC-rooted audit: `pass`

This draft consumes the real-CVE TCIR and trigger graph, then emits only exact
source/range bindings: root observation, guard, use, and two input-influence
ranges. It does not emit the producer role because the trigger graph producer
node has no source location.

This is not endpoint evidence. The next gate is native site-map validation,
BindingSpec compilation, lift audit, and binding-signal/frontier diagnosis
before any matched FORMTRIG/baseline comparison.
