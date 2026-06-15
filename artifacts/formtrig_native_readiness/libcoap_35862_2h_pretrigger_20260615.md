# LIBCOAP_CVE_2023_35862 2h Pre-Trigger Guidance Evidence

This run extends the 30-minute `LIBCOAP_CVE_2023_35862` native FORMTRIG
pre-trigger result to a 2-hour strict campaign.

## Purpose

The target is the admissible libcoap OSCORE configuration parsing real-CVE
case. The harness feeds input into `coap_new_oscore_conf()` and passed harness
admissibility review; it does not expose the trigger as a direct input knob.

This non-ASAN run is a pre-trigger guidance run. It tests whether FORMTRIG keeps
providing useful `R -> T` signal over a longer budget when terminal `D_T`
remains absent:

- spec-driven lifted `D_F`;
- dominance/frontier retention;
- typed mutation from the BindingSpec hot range;
- no heuristic/manual lifted signal contamination.

## Command

```bash
FORMTRIG_JOBS=8 scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_selective_2h_20260615T191111Z \
  --durations 7200
```

Strict gate:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBCOAP_CVE_2023_35862_2h_pretrigger \
  --min-runtime 7200 \
  --out /tmp/formtrig_libcoap_35862_selective_2h_20260615T191111Z/gate_2h \
  --run libcoap2h=/tmp/formtrig_libcoap_35862_selective_2h_20260615T191111Z/selective_sweep_7200s/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml/default
```

## Result

Strict pre-trigger gate: `pass`.

Key fields from `gate_summary.csv`:

- `run_time=7200`
- `execs_done=18627489`
- `execs_per_sec=2587.15`
- `reached=8843324`
- `terminal_triggered=0`
- `queued_progress=1`
- `accepted_non_trigger=1`
- `saved_non_trigger=1`
- `saved_triggered=0`
- `spec_lifted=19756`
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
- `formtrig_typed_execs=936960`
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
- `spec_d_f_non_trigger_candidate_values=[1,0,2]`
- `spec_d_f_calibration_values=[1]`
- `candidate_variable_roles=["root_observe"]`
- sampled roles: `root_observe`, `guard`, `use`, `input_influence`
- `root_observe` had `candidate_unique_values=32`

## Interpretation

This is stronger real-CVE pre-trigger evidence than the 30-minute run. FORMTRIG
reached the target region 8,843,324 times over 2 hours, never triggered the
terminal oracle, and still preserved one replay-stable non-trigger progress
seed. The accepted progress is TC-rooted through `root_observe`; guard, use, and
input-influence roles are bound and sampled.

The lifted signal is not binary or constant. Candidate `D_F_spec_lifted` values
include `1`, `0`, and `2`, while calibration stayed at `1`. That is the desired
case for FORMTRIG: terminal `D_T` gives no useful pre-crash ranking, but the
spec-driven lifted `D_F` gives a sortable and mutation-connected signal that can
enter the AFL++ queue.

This run does not prove SOTA superiority by itself. It proves that the
FORMTRIG treatment arm has stable 2-hour real-CVE pre-trigger guidance and is
ready to be paired with faithful same-budget baselines.

## Caveats

- This run did not produce a terminal crash because it was the non-ASAN
  pre-trigger guidance campaign. Terminal oracle evidence must come from the
  ASAN exit-code mode.
- AFL++ reported `saved_hangs=17`. The strict gate passed, but hangs should be
  tracked in ASAN and baseline comparisons.
- `formtrig_progress_log_dropped=8838309`, so the full high-frequency progress
  JSONL is not a complete event stream. The preserved evidence relies on
  replay-stable saved progress, summary counters, and binding diagnosis.
- This is not a comparative baseline result. Same-seed, same-budget faithful
  AFL++/CmpLog/Redqueen/AFLGo or other paper-artifact baselines are still
  required.

## Preserved Evidence

Raw summary evidence is preserved at:

`artifacts/formtrig_native_readiness/raw/libcoap_35862_2h_20260615T191111Z`

The preserved directory includes:

- `gate_summary.csv`
- `gate_summary.jsonl`
- `gate_report.md`
- `fuzzer_stats`
- `formtrig_summary.json`
- `formtrig_diagnosis.json`
- `formtrig_binding_signal_diagnosis.json`
- `formtrig_lift_feature_audit.json`
- `formtrig_seed_readiness.json`
- `formtrig_seed_signal_entropy.json`
- `formtrig_harness_admissibility.json`
- `formtrig_harness_admissibility.md`
- `summary.tsv`
- `summary.jsonl`
- `run_metadata.txt`
