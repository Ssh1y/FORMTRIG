# LIBCOAP_CVE_2023_35862 30m Pre-Trigger Guidance Evidence

This run is the first admissible real-CVE 30-minute native FORMTRIG strict
pre-trigger campaign for `LIBCOAP_CVE_2023_35862`.

## Purpose

The target is an equality/magic real-CVE case in libcoap OSCORE configuration
parsing. The harness feeds the original input file to `coap_new_oscore_conf()`
and passed the harness admissibility audit; it does not expose a direct trigger
knob.

This non-ASAN run is not a terminal crash oracle run. Its purpose is to test
whether FORMTRIG provides useful `R -> T` guidance before the crash condition is
triggered:

- spec-driven lifted `D_F`;
- dominance/frontier retention;
- typed mutation from the BindingSpec hot range;
- no heuristic/manual lifted signal contamination.

## Command

```bash
FORMTRIG_JOBS=8 scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_selective_30m_20260615T182142Z \
  --durations 1800
```

Strict gate:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBCOAP_CVE_2023_35862_30m_pretrigger \
  --min-runtime 1800 \
  --out /tmp/formtrig_libcoap_35862_selective_30m_20260615T182142Z/gate_30m \
  --run libcoap30m=/tmp/formtrig_libcoap_35862_selective_30m_20260615T182142Z/selective_sweep_1800s/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml/default
```

## Result

Strict pre-trigger gate: `pass`.

Key fields from `gate_summary.csv`:

- `run_time=1800`
- `execs_done=4764811`
- `execs_per_sec=2647.11`
- `reached=2128534`
- `terminal_triggered=0`
- `queued_progress=1`
- `accepted_non_trigger=1`
- `saved_non_trigger=1`
- `saved_triggered=0`
- `spec_lifted=8524`
- `heuristic_lifted=0`
- `manual_lifted=0`
- `experiment_ready=true`
- `pretrigger_lift_guidance_ready=true`
- `non_trigger_candidate_lift_delta=true`
- `lift_delta_only_on_triggered=false`
- `binding_signal_status=pass`
- `binding_signal_diagnosis=role_signal_progress_observed`

Key fields from `formtrig_summary.json`:

- `formtrig_queued_progress=1`
- `formtrig_frontier_updates=2`
- `formtrig_typed_execs=283648`
- `formtrig_typed_finds=1`
- `formtrig_stability_checks=3`
- `formtrig_stability_failures=0`
- `formtrig_saved_non_trigger_log_seen=1`
- `d_f_spec_lifted_min=0`
- `d_f_spec_lifted_max=2`
- `d_f_spec_lifted_constant=false`
- `progress_status=progress_queued`
- `limiting_reason=none`

Key fields from `formtrig_binding_signal_diagnosis.json`:

- `accepted_non_trigger_progress_events=1`
- `triggered_events=0`
- `spec_d_f_non_trigger_candidate_values=[1,2,0]`
- `spec_d_f_calibration_values=[1]`
- `candidate_variable_roles=["root_observe"]`
- sampled roles: `root_observe`, `guard`, `use`, `input_influence`
- `root_observe` had `candidate_unique_values=32`

## Interpretation

This is positive pre-trigger evidence, not a terminal-crash result. FORMTRIG
reached the target region 2,128,534 times, never triggered the terminal oracle,
and still saved one replay-stable non-trigger progress seed. The saved progress
is TC-rooted: the variable role is `root_observe`, with guard/use/input-influence
roles sampled and stable. The lifted signal is not binary or constant:
candidate `D_F_spec_lifted` values include `1`, `2`, and `0`, while the
calibration value was `1`.

That means this run demonstrates the intended effect for this real-CVE target:
when terminal `D_T` is effectively absent before crash, FORMTRIG can still
produce a spec-driven, sortable, attributable, and mutation-connected `D_F`
signal that survives replay and enters the AFL++ queue.

## Caveats

- This run did not produce a terminal crash because it was the non-ASAN
  pre-trigger guidance campaign. Terminal oracle evidence is tracked separately
  through the ASAN exit-code mode.
- AFL++ reported `saved_hangs=12`. They did not invalidate the strict gate, but
  they should be tracked in longer runs and baseline comparisons.
- This is FORMTRIG readiness evidence. It must be paired with same-budget
  faithful baseline runs before it supports a comparative SOTA claim.

## Preserved Evidence

Raw summary evidence is preserved at:

`artifacts/formtrig_native_readiness/raw/libcoap_35862_30m_20260615T182142Z`

The preserved directory includes:

- `gate_summary.csv`
- `gate_summary.jsonl`
- `gate_report.md`
- `fuzzer_stats`
- `formtrig_summary.json`
- `formtrig_diagnosis.json`
- `formtrig_binding_signal_diagnosis.json`
- `formtrig_harness_admissibility.json`
- `formtrig_harness_admissibility.md`
- `summary.tsv`
- `summary.jsonl`
- `run_metadata.txt`
