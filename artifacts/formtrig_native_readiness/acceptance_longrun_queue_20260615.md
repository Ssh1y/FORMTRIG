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
pre-trigger lifted guidance.

## Positive Long-Run Queue

### CVE: LIBXML2_1107

Current status: 30-minute selective native acceptance passed. The 2-hour normal
and terminal-accounting runs remain pending.

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

### Magma: PNG006

Current status: 2-hour native acceptance passed with external eXIf insertion
hook from the BindingSpec.

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
- Evidence note: `artifacts/formtrig_native_readiness/png006_exif_2h_20260615.md`
- Result: pass with `run_time=7200`, `execs_done=29754905`,
  `reached=26319188`, `terminal_triggered=17276659`,
  `queued_progress=1919630`, `accepted_non_trigger=1`,
  `saved_non_trigger=1`, `spec_lifted=3844204`,
  `heuristic_lifted=0`, and `manual_lifted=0`.
- Stability caveat: the run had `formtrig_stability_failures=2` from rejected
  `queue_calibration_regressed` candidates and one typed
  `not_replay_stable` skip. The accepted progress still passed the strict gate.

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
