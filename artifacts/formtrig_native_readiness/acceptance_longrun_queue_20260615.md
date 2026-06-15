# FORMTRIG Native Acceptance Long-Run Queue - 2026-06-15

This queue defines the current path from native smoke evidence to acceptance
evidence for a real experimental FORMTRIG.

## Acceptance Rule

A run is accepted as evidence that FORMTRIG helps a binary/uninformative TC only
if `scripts/formtrig_experiment_gate.sh` passes. The strict gate requires:

- `experiment_ready=true`
- `pretrigger_lift_guidance_ready=true`
- accepted and saved non-trigger progress
- non-trigger candidate `D_F` delta
- `lift_delta_only_on_triggered_candidates=false`
- heuristic/manual lifted event counts are zero
- binding-signal status is `pass`

Terminal crashes are useful as final oracle evidence, but they do not replace
pre-trigger lifted guidance. A run also must pass harness admissibility review:
inputs must naturally drive parser state, length, magic, structure, or lifecycle
constraints. A replay harness that exposes the trigger as a direct input knob is
only a sanity target, even if `formtrig_experiment_gate.sh` passes.

The broader experimental claim also requires faithful baseline comparison.
FORMTRIG-only long runs prove native readiness, but they do not prove superiority
over SOTA. A target can enter the main comparison package only after the
FORMTRIG run is paired with same-seed, same-budget faithful baseline runs under
`artifacts/formtrig_native_readiness/baseline_faithfulness_policy_20260615.md`.
Representative signal-family stand-ins are not accepted as SOTA baselines.
`tools/run_post_reach_baseline.py` is the common post-reach baseline entrypoint
and refuses representative-only baselines by default.

## Positive Long-Run Queue

### Magma: PNG006

Current status: 2-hour native acceptance passed with external eXIf insertion
hook from the BindingSpec. It still needs same-budget faithful baseline runs
before it can support the final comparative claim.

Runner:

```bash
scripts/run_formtrig_png006_native_longrun.sh \
  --out /tmp/formtrig_png006_exif_longrun_20260615 \
  --durations 1800,7200
```

Gate examples:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite PNG006_30m_acceptance \
  --min-runtime 1800 \
  --out /tmp/formtrig_png006_exif_longrun_20260615/gate_30m \
  --run PNG006_exif_30m=/tmp/formtrig_png006_exif_longrun_20260615/png006_exif_1800s/candidates/001_PNG006.native_b2_exif_insert_candidate.yml/default
```

Completed 30-minute evidence:

- Run root: `/tmp/formtrig_png006_exif_longrun_20260615T1045Z`
- Strict gate: `/tmp/formtrig_png006_exif_longrun_20260615T1045Z/gate_30m/gate_summary.csv`
- Evidence note: `artifacts/formtrig_native_readiness/png006_exif_longrun_20260615.md`
- Result: pass with `run_time=1800`, `execs_done=9527259`,
  `accepted_non_trigger=1`, `saved_non_trigger=1`, `spec_lifted=1273466`,
  `heuristic_lifted=0`, and `manual_lifted=0`.

Completed 2-hour evidence:

- Run root: `/tmp/formtrig_png006_exif_longrun_20260615T1250Z`
- Strict gate: `/tmp/formtrig_png006_exif_longrun_20260615T1250Z/gate_2h/gate_summary.csv`
- Preserved raw evidence:
  `artifacts/formtrig_native_readiness/raw/png006_2h_20260615T1250Z`
- Evidence note: `artifacts/formtrig_native_readiness/png006_exif_2h_20260615.md`
- Result: pass with `run_time=7200`, `execs_done=29754905`,
  `reached=26319188`, `terminal_triggered=17276659`,
  `queued_progress=1919630`, `accepted_non_trigger=1`,
  `saved_non_trigger=1`, `spec_lifted=3844204`,
  `heuristic_lifted=0`, and `manual_lifted=0`.
- Stability caveat: the run had `formtrig_stability_failures=2` from rejected
  `queue_calibration_regressed` candidates and one typed
  `not_replay_stable` skip. The accepted progress still passed the strict gate.

## Real-CVE Smoke / Long-Run Candidate

### CVE: LIBCOAP_CVE_2023_35862

Current status: admissible native smoke path passed, 30-minute strict
pre-trigger guidance passed, and 2-hour strict pre-trigger guidance passed.
This is the replacement real-CVE candidate for LIBXML2_1107. It still needs a
long ASAN campaign before it can count as full FORMTRIG real-CVE acceptance
evidence. It also needs faithful baseline runs before it can enter the final
SOTA comparison package.

Runner:

```bash
scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_selective_20260615 \
  --durations 1800,7200
```

ASAN terminal-oracle build:

```bash
FORMTRIG_JOBS=8 scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_asan_20260615 \
  --asan \
  --durations 1800,7200
```

ASAN terminal-oracle gate:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBCOAP_CVE_2023_35862_asan_terminal_oracle \
  --min-runtime 1800 \
  --terminal-oracle-only \
  --out /tmp/formtrig_libcoap_35862_asan_20260615/gate_30m_terminal_oracle \
  --run asan30m=/tmp/formtrig_libcoap_35862_asan_20260615/selective_sweep_1800s/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml/default
```

Smoke evidence:

- Evidence note:
  `artifacts/formtrig_native_readiness/libcoap_35862_native_tool_smoke_20260615.md`
- ASAN terminal-oracle note:
  `artifacts/formtrig_native_readiness/libcoap_35862_asan_terminal_oracle_20260615.md`
- Harness audit: `admissible`, `core_evidence_allowed=true`.
- Non-ASAN replay: seed has `D_F_spec_lifted=1`; PoC
  `master_secretX,hex,00\n` has `D_F_spec_lifted=0`.
- ASAN replay: the same PoC exits `86` with AddressSanitizer
  `global-buffer-overflow` in FORMTRIG's ASAN exit-code oracle mode.
- ASAN 30-second terminal-oracle sweep: `saved_crashes=7`, `saved_hangs=0`,
  `terminal_triggered_execs=7`, terminal-only gate pass.
- 10-second pre-trigger gate: pass with `run_time=10`, `execs_done=27115`,
  `reached=10008`, `accepted_non_trigger=1`, `saved_non_trigger=1`,
  `spec_lifted=4098`, and `binding_signal_diagnosis=role_signal_progress_observed`.

Completed 30-minute pre-trigger evidence:

- Run root: `/tmp/formtrig_libcoap_35862_selective_30m_20260615T182142Z`
- Strict gate:
  `/tmp/formtrig_libcoap_35862_selective_30m_20260615T182142Z/gate_30m/gate_summary.csv`
- Preserved raw evidence:
  `artifacts/formtrig_native_readiness/raw/libcoap_35862_30m_20260615T182142Z`
- Evidence note:
  `artifacts/formtrig_native_readiness/libcoap_35862_30m_pretrigger_20260615.md`
- Result: pass with `run_time=1800`, `execs_done=4764811`,
  `execs_per_sec=2647.11`, `reached=2128534`,
  `terminal_triggered=0`, `accepted_non_trigger=1`,
  `saved_non_trigger=1`, `spec_lifted=8524`,
  `heuristic_lifted=0`, `manual_lifted=0`,
  `non_trigger_candidate_lift_delta=true`, and
  `binding_signal_diagnosis=role_signal_progress_observed`.
- Performance caveat: AFL++ saved `12` hangs. They did not invalidate the
  strict pre-trigger gate, but they should be tracked in the 2-hour and
  baseline runs.

Completed 2-hour pre-trigger evidence:

- Run root: `/tmp/formtrig_libcoap_35862_selective_2h_20260615T191111Z`
- Strict gate:
  `/tmp/formtrig_libcoap_35862_selective_2h_20260615T191111Z/gate_2h/gate_summary.csv`
- Preserved raw evidence:
  `artifacts/formtrig_native_readiness/raw/libcoap_35862_2h_20260615T191111Z`
- Evidence note:
  `artifacts/formtrig_native_readiness/libcoap_35862_2h_pretrigger_20260615.md`
- Result: pass with `run_time=7200`, `execs_done=18627489`,
  `execs_per_sec=2587.15`, `reached=8843324`,
  `terminal_triggered=0`, `accepted_non_trigger=1`,
  `saved_non_trigger=1`, `spec_lifted=19756`,
  `heuristic_lifted=0`, `manual_lifted=0`,
  `non_trigger_candidate_lift_delta=true`, and
  `binding_signal_diagnosis=role_signal_progress_observed`.
- Stability caveat: `formtrig_stability_failures=0`, but AFL++ saved `17`
  hangs. `formtrig_progress_log_dropped=8838309`, so the full progress JSONL is
  not complete; the accepted evidence is the replay-stable saved progress plus
  summary and binding diagnosis counters.

Baseline comparison queue:

- AFL++ vanilla: required faithful coverage/reach-only control.
- AFL++ CmpLog/Redqueen: required faithful comparison-feedback baseline for this
  equality/magic target.
- AFLGo or another faithfully wired directed-fuzzing artifact: required reach
  baseline if the target can be built with the artifact.
- TrigFuzz-style native `D_T`: required only after the distance, scheduling, and
  mutation behavior are implemented from the paper/artifact; a replay-only or
  representative stand-in is not sufficient.
- Faithful AFL++-family baseline build/execute smoke is recorded in
  `artifacts/formtrig_native_readiness/libcoap_35862_baseline_smoke_20260615.md`.
  This confirms the runner can build and launch the baseline artifacts; it is
  not a long-run comparison result.

Faithful AFL++-family baseline runner:

```bash
scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baselines_20260615 \
  --durations 1800,7200 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
```

ASAN terminal-oracle variant:

```bash
scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baselines_asan_20260615 \
  --asan \
  --durations 1800,7200 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
```

## Sanity / Demoted Queue

### CVE: LIBXML2_1107

Current status: demoted from positive evidence. The selective native runs are
useful for build, BindingSpec, seed-readiness, typed mutation, and terminal
crash-accounting checks, but the case is not admissible as core real-CVE R2T
guidance evidence.

Reason: the replay harness maps input byte 0 to `g_fail_malloc_at`, and the
BindingSpec includes a one-byte `set_byte` mutation hint for the terminal malloc
failure index. This makes the R2T process mostly an artificial harness knob.

Audit artifact:
`artifacts/formtrig_native_readiness/raw/libxml2_1107_harness_admissibility_20260615.json`.

Runner:

```bash
scripts/run_formtrig_libxml2_1107_selective.sh \
  --out /tmp/formtrig_libxml2_1107_selective_longrun_20260615 \
  --durations 1800,7200 \
  --terminal-durations 1800,7200
```

Normal timeout runs should be used for throughput and pre-trigger `D_F`
stability. Timeout-adjusted runs validate crash classification for this slow
terminal path.

Gate examples:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBXML2_1107_30m_acceptance \
  --min-runtime 1800 \
  --out /tmp/formtrig_libxml2_1107_selective_longrun_20260615/gate_30m \
  --run selective30m=/tmp/formtrig_libxml2_1107_selective_longrun_20260615/selective_sweep_1800s/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default
```

Use `--require-terminal` only on timeout-adjusted terminal-accounting runs.

Completed 30-minute evidence:

- Run root: `/tmp/formtrig_libxml2_1107_selective_longrun_20260615T1117Z`
- Normal strict gate: `/tmp/formtrig_libxml2_1107_selective_longrun_20260615T1117Z/gate_30m/gate_summary.csv`
- Terminal strict gate: `/tmp/formtrig_libxml2_1107_selective_longrun_20260615T1117Z/gate_30m_terminal/gate_summary.csv`
- Evidence note: `artifacts/formtrig_native_readiness/libxml2_1107_longrun_20260615.md`
- Normal result: pass with `run_time=1800`, `execs_done=3548966`,
  `terminal_triggered=0`, `accepted_non_trigger=1`,
  `saved_non_trigger=1`, `spec_lifted=6046`,
  `heuristic_lifted=0`, and `manual_lifted=0`.
- Terminal result: pass with `run_time=1800`, `execs_done=391483`,
  `terminal_triggered=2`, `saved_crashes=2`, `saved_hangs=0`,
  `accepted_non_trigger=1`, `spec_lifted=4217`,
  `heuristic_lifted=0`, and `manual_lifted=0`.

## Negative / Blocked Queue

### Magma: PNG007

Current status: terminal-trigger smoke only. It fails the strict pre-trigger
gate because `accepted_non_trigger_progress=0`,
`non_trigger_candidate_lift_delta=false`, and
`lift_delta_only_on_triggered_candidates=true`.

Do not use PNG007 as main positive evidence until producer/root/use binding or
mutation strategy yields accepted non-trigger progress.

### Magma: SQL013

Current status: insufficient binding. Do not claim numeric or lifecycle lift
unless planner-internal root/same-object/lifecycle events can be bound and pass
static plus dynamic gates.

## Smoke Gate Commands Already Run

CVE selective smoke gate:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite LIBXML2_1107_selective_acceptance \
  --out /tmp/formtrig_libxml2_1107_gate_20260615 \
  --run full30=/tmp/formtrig_libxml2_1107_full_strict_sweep_30s/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default \
  --run selective30=/tmp/formtrig_libxml2_1107_selective_20260615T100923Z/selective_sweep_30s/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default \
  --run selective120=/tmp/formtrig_libxml2_1107_selective_20260615T100923Z/selective_sweep_120s/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default \
  --run selective30_t3000=/tmp/formtrig_libxml2_1107_selective_20260615T100923Z/selective_sweep_30s_t3000/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default \
  --run selective120_t3000=/tmp/formtrig_libxml2_1107_selective_20260615T100923Z/selective_sweep_120s_t3000/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default
```

Magma smoke gate:

```bash
scripts/formtrig_experiment_gate.sh \
  --suite magma_native_smoke_gate \
  --out /tmp/formtrig_magma_smoke_gate_20260615 \
  --run PNG006_exif_30s=/tmp/formtrig_png006_exif_insert_sweep_30s/candidates/001_PNG006.native_b2_exif_insert_candidate.yml/default \
  --run PNG006_exif_120s=/tmp/formtrig_png006_exif_insert_sweep_120s/candidates/001_PNG006.native_b2_exif_insert_candidate.yml/default \
  --run PNG007_plte_120s=/tmp/formtrig_png007_plte_multi_sweep_120s/candidates/001_PNG007.native_b2_plte_multi_delete_candidate.yml/default
```

The expected result is PNG006 pass and PNG007 fail.
