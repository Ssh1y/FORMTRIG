# PDF016 B3 to B4 Signal Repair

Generated: `2026-06-18T05:21:30+00:00`

## Problem

`PDF016.native_b3_parser_ref_candidate.yml` reached the Magma canary and produced terminal `_T`, but it did not create accepted pre-trigger frontier progress:

- validation status: `terminal_only_variable_semantic_roles_no_pretrigger_guidance`
- accepted non-trigger progress: `0`
- saved triggered progress: `1`
- root role values varied, but scalar `D_F_spec_lifted` stayed constant at `1`

The cause was not missing dependencies or native site-map failure. B3 bound every `Parser.cc:190` canary-line comparison as `root_observe higher outcome`. Several of those comparisons are macro/control-flow bookkeeping and are already true on non-trigger inputs. The role graph therefore treated the root role as satisfied as soon as any such comparison was true, collapsing the useful `R2T` signal into a constant.

## Repair

B4 keeps the lifecycle/use/same-object roles, but changes the root binding to the replay-confirmed variable comparison:

- BindingSpec: `artifacts/binding_specs/PDF016.native_b4_parser_gen_distance_candidate.yml`
- root site: `3624284787`
- root mode: `direction=lower`, `value_mode=distance`
- runtime change: unsatisfied lower-is-better BindingSpec roles retain their numeric distance in the role graph instead of contributing a flat `+1`

Replay evidence on the rebuilt native PDF016 target showed the root distance moving through the expected states:

- normal seed: `D_F_spec_lifted=2 -> 1`
- triggering queue input: `D_F_spec_lifted=2 -> 1 -> 0`

## Validation Result

Run: `artifacts/formtrig_native_readiness/raw/pdf016_b4_binding_validation_600s_t5000_r2/summary.jsonl`

- validation status: `native_binding_validated`
- ready for short gate: `true`
- execs: `5684`
- reached execs: `5475`
- candidate events: `2188`
- accepted non-trigger progress: `4`
- saved non-trigger progress: `4`
- saved triggered progress: `1`
- terminal `_T`: `8`
- first `_T`: `544s`

Observed root-distance distribution in progress events:

- `D_F_spec_lifted=2`: `802`
- `D_F_spec_lifted=1`: `1390`
- `D_F_spec_lifted=0`: `1`

## Interpretation

B4 turns PDF016 from a terminal-only negative validation into a valid pre-trigger guidance case. This is not yet an endpoint-performance claim against SOTA baselines. The next required step is a matched short screen against faithful AFL++ family baselines with the same seed corpus and `-t 5000` timeout.
