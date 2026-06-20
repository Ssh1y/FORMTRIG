# GPAC_3403 B13 SCAL Payload Endpoint Gate Smoke

- status: `scaffold_to_terminal_smoke_success`
- raw_dir: `artifacts/formtrig_native_readiness/raw/gpac3403_b13_scal_ref_payload_endpoint_gate_smoke_20260620T030127Z`
- runner: `scripts/run_gpac3403_b13_scal_ref_payload_endpoint_gate.sh`
- mutation hook: `scripts/formtrig_hooks/gpac_scal_ref_mp4_hook.py`
- seed format: `mp4-scal-ref-scaffold`

## Gate

| metric | value |
|---|---:|
| first_terminal_time_s | 2.401 |
| first_terminal_execs | 8 |
| terminal_triggered | 1 |
| accepted_non_trigger | 3 |
| saved_non_trigger | 3 |
| spec_lifted | 11 |
| pretrigger_lift_guidance_ready | true |
| non_trigger_candidate_lift_delta | true |
| lift_delta_only_on_triggered | false |

## Endpoint Replay

| metric | value |
|---|---:|
| endpoint_replayed_variants | 4 |
| endpoint_native_crashes | 1 |
| endpoint_exit_code_-6 | 1 |
| endpoint_exit_code_1 | 3 |
| positive_control_native_crashes | 1 |

The terminal retained candidate is `op=52`, `sample=0` under the B13 hook's
HEVC sample bias. It exits with `-6` and stderr contains:

```text
free(): double free detected in tcache 2
```

## Interpretation

B13 closes the B12 scaffold-to-terminal gap in a short native smoke run. The
important distinction is that B12's generic MP4 hook produced strict pre-trigger
progress but no endpoint crash; B13 preserves the same SCAL scaffold and mutates
the enhanced HEVC payload, which reaches the GPAC double-free endpoint.

This is not yet a matched-baseline result. It is repair-hook evidence that the
SCAL scaffold is a viable R-not-T start state and that typed mutation can close
the R2T gap when it targets the right payload layer.
