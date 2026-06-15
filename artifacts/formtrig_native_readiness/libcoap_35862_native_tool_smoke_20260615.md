# LIBCOAP_CVE_2023_35862 Native FORMTRIG Tool Smoke

Date: 2026-06-15

## Status

`LIBCOAP_CVE_2023_35862` is the current admissible real-CVE smoke target for
native FORMTRIG. Unlike `LIBXML2_1107`, the harness does not expose a direct
trigger knob: it reads an OSCORE config file and passes it to
`coap_new_oscore_conf()`.

Harness admissibility:

- `status=admissible`
- `core_evidence_allowed=true`
- no audit flags

## Repro Commands

Build selective non-ASAN target:

```bash
scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_runner_smoke_20260615Tnow \
  --no-sweeps
```

Run a short FORMTRIG-guidance campaign:

```bash
scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_sweep_smoke_20260615Tnow \
  --durations 10
```

Build selective ASAN/UBSAN target:

```bash
FORMTRIG_JOBS=8 scripts/run_formtrig_libcoap_35862_selective.sh \
  --out /tmp/formtrig_libcoap_35862_asan_smoke_20260615Tnow \
  --asan \
  --no-sweeps
```

## Tooling Fixes Validated Here

- `scripts/formtrig_harness_admissibility_audit.py` rejects harnesses that
  encode a direct input-to-trigger switch, and marks admissible harnesses as
  usable for core evidence.
- `scripts/run_formtrig_libcoap_35862_selective.sh` now resets its in-output
  CMake build directories before compiling, preventing stale object files from
  producing an incomplete `site_map.tsv`.
- The LIBCOAP BindingSpec includes source columns, so ASAN builds can remap
  changed `inst_no` values with `relaxed_inst_no` while still selecting the same
  semantic sites.

## Concrete Evidence

Non-ASAN selective replay:

- Seed `master_secret,hex,00\n`: `rc=0`, `reached=true`,
  `D_F_spec_lifted=1`, `df_source.distance=1`,
  hot range `{start=13,len=1,hint=insert_byte,value=88}`.
- PoC `master_secretX,hex,00\n`: `rc=0`, `reached=true`,
  `D_F_spec_lifted=0`, `df_source.outcome=14`, `df_source.distance=0`.

ASAN selective replay:

- Seed: `rc=0`, `reached=true`, `D_F_spec_lifted=1`.
- PoC `master_secretX,hex,00\n`: `rc=134`, AddressSanitizer reports
  `global-buffer-overflow`, `READ of size 14`, at the libcoap OSCORE parser.
  FORMTRIG JSON is empty for this PoC because ASAN aborts before the runtime
  flushes the log; terminal validation is the sanitizer exit/report.

Short campaign gate:

- suite: `LIBCOAP_CVE_2023_35862_smoke`
- runtime: 10 seconds
- execs: 27115
- reached: 10008
- terminal_triggered: 0
- queued_progress: 1
- accepted_non_trigger: 1
- saved_non_trigger: 1
- spec_lifted: 4098
- `pretrigger_lift_guidance_ready=true`
- `non_trigger_candidate_lift_delta=true`
- binding diagnosis: `pass / role_signal_progress_observed`

## Interpretation

This target now demonstrates the intended tool behavior before long runs:

- FORMTRIG observes an admissible real-CVE pre-trigger state.
- The lifted spec gives a monotonic feature distance: seed distance is 1, PoC
  distance is 0.
- The typed mutation hint points at the relevant byte position and operation.
- A sanitizer build independently confirms that the distance-0 PoC is a real
  terminal bug.

This is not final generalization evidence. It is a usable, reproducible smoke
path for one real CVE that should be extended into ASAN fuzz campaigns and then
into the multi-target Magma/CVE acceptance queue.
