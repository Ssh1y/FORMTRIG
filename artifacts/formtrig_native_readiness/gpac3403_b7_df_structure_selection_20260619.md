# GPAC_3403 B7 Endpoint Selection Repair - 2026-06-19

Basis run:
`artifacts/formtrig_native_readiness/raw/gpac3403_b7_relation_endpoint_gate_20260619T231431Z`

This repair changes typed-retained endpoint replay selection from pure
operator diversity to `df-structure`: first rank by FORMTRIG's lifted
`D_F_spec_lifted`, then use HEVC structure as a tie-breaker.

## Replay Comparison

| selection | HEVC import files | L-HEVC import files | max import scale | missing positive-control signatures | crashes |
| --- | ---: | ---: | --- | --- | --- |
| `op-diverse` | 38 / 128 | 6 / 128 | 8 samples / 26 NALUs | `nal_type_49_not_handled`, `asan_double_free` | 0 |
| `structure-best` | 5 / 128 | 0 / 128 | 8 samples / 26 NALUs | 9 signatures, including L-HEVC and ASAN | 0 |
| `df-structure` | 60 / 128 | 11 / 128 | 8 samples / 26 NALUs | `nal_type_49_not_handled`, `asan_double_free` | 0 |

The negative result is important: pure structure maximization selects large
malformed candidates that GPAC rejects early. The useful policy keeps
FORMTRIG's lifted objective first and only uses structure to choose among
candidate inputs at the same lifted-distance tier.

## Status

`df-structure` is now implemented in:

- `tools/replay_gpac3403_typed_retained_endpoint.py`
- `scripts/run_gpac3403_typedops36_matched_longrun.sh`
- `scripts/run_gpac3403_b7_relation_endpoint_gate.sh`

Claim boundary: this is endpoint-selection repair, not endpoint success.
GPAC_3403 still has `_T=0` and ASAN/double-free=0 in these replays. Matched
baselines remain blocked until the B7 relation gate either closes the
alias/free relation or reaches ASAN/double-free.

## Full Gate Confirmation

The standard B7 gate now uses `df-structure` and confirms the same direction:
`artifacts/formtrig_native_readiness/gpac3403_b7_relation_endpoint_gate_dfstructure_20260619.json`.
It passes strict pre-trigger guidance, saves 41 non-trigger progress entries,
and replays 128 df-structure-selected endpoint variants with 60 HEVC import files
and 11 L-HEVC import files. It still has `_T=0`, ASAN/double-free=0, and the
same cleanup alias/free blocker.
