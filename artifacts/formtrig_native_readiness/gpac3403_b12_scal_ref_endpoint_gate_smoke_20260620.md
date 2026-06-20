# GPAC_3403 B12 SCAL Reference Endpoint Gate Smoke

- status: `endpoint_replay_gate_executed`
- raw_dir: `artifacts/formtrig_native_readiness/raw/gpac3403_b12_scal_ref_endpoint_gate_smoke_20260620T025307Z`
- runner: `scripts/run_gpac3403_b12_scal_ref_endpoint_gate.sh`
- seed_format: `mp4-scal-ref-scaffold`
- endpoint replay: `on`

## Gate

| metric | value |
|---|---:|
| duration_s | 5 |
| reached | 79 |
| terminal_triggered | 0 |
| accepted_non_trigger | 3 |
| saved_non_trigger | 3 |
| spec_lifted | 40 |
| pretrigger_lift_guidance_ready | true |
| non_trigger_candidate_lift_delta | true |
| lift_delta_only_on_triggered | false |

## Endpoint Replay

| metric | value |
|---|---:|
| selected_records | 15 |
| endpoint_replayed_variants | 15 |
| endpoint_native_crashes | 0 |
| endpoint_exit_code_0 | 2 |
| endpoint_exit_code_1 | 13 |
| positive_control_probe_runs | 1 |
| positive_control_native_crashes | 1 |
| positive_control_exit_code | -6 |

## Interpretation

The endpoint replay gate is now executable and calibrated. The B11 positive
control crashes through the same `MP4Box -cat @@ white.mp4 -out /dev/null`
endpoint, while the 15 retained B12 variants do not.

This is useful negative evidence: the B12 scaffold plus generic MP4 hook gives
strict pre-trigger FORMTRIG progress, but does not yet cross into the
double-free endpoint. The next repair should target the scaffold-to-terminal
mutation step: preserve the SCAL reference relation while mutating the enhanced
track payload toward the B11 op52/sample2 shape.
