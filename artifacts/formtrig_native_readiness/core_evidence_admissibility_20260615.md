# FORMTRIG Core Evidence Admissibility - 2026-06-15

This note separates experimental evidence that can support the core FORMTRIG
claim from engineering sanity evidence.

## Core-Evidence Rule

A target can support the main claim only if all of these hold:

- The original input naturally drives the relevant parser state, size, length,
  magic, structure, object relation, or lifecycle transition.
- The harness does not expose the trigger through a direct control knob such as
  "input byte N selects malloc failure K".
- BindingSpec roles may use harness-visible source sites only when those sites
  encode natural input parsing behavior, not an injected trigger oracle.
- Typed mutation hints may focus an input range, but they must not simply name a
  one-byte terminal switch introduced by the harness.
- `scripts/formtrig_experiment_gate.sh` passes with spec-driven lifted `D_F`,
  accepted non-trigger progress, `lift_delta_only_on_triggered_candidates=false`,
  and zero heuristic/manual lifted events.

## Current Target Status

| target | status | use |
|---|---|---|
| PNG006 eXIf | admissible Magma evidence | Keep as current positive 2-hour Magma structure/state case. |
| LIBCOAP_CVE_2023_35862 | admissible real-CVE smoke | Promote to real-CVE long-run candidate after ASAN campaign wiring. |
| LIBXML2_1107 | inadmissible as core evidence | Keep only as native pipeline, BindingSpec, typed mutation, and crash-accounting sanity case. |
| PNG007 PLTE | TrigFuzz-motivated control / negative | TrigFuzz explicitly uses PNG007 as a binary triggering-distance limitation, but current FORMTRIG BindingSpecs are terminal-only: `pretrigger_lift_guidance_ready=false`, `saved_non_trigger_progress_events=0`, and `lift_delta_only_on_triggered_candidates=true`. |
| SQL013 | not positive | Binding is insufficient without planner-internal root/same-object/lifecycle evidence. |

## LIBXML2_1107 Finding

`LIBXML2_1107` is real vulnerable library code, but the current replay harness
turns the trigger into an artificial knob:

- `buf[0]` is assigned to `g_fail_malloc_at`.
- `hook_malloc` returns `NULL` when `g_malloc_count == g_fail_malloc_at`.
- The RNT seed is two bytes: `00 61`.
- The terminal crashing input is essentially one byte away: `02 61`.
- The BindingSpec includes `range_start: 0`, `range_len: 1`,
  `mutation_hint: set_byte`, and `mutation_value: 2`.

That is useful for testing whether FORMTRIG plumbing can observe, mutate, and
account for a binary-null crash path. It does not show that FORMTRIG solves a
natural R2T problem where the fuzzer must construct a parser state or structural
relationship from the input.

## Required Replacement

The real-CVE queue needs at least one replacement target whose triggering path is
not a harness-level oracle. Prefer targets already present in the local CVE
inventory:

- `LIBARCHIVE_2925`: binary-state-null plus numeric margin, archive structure
  input.
- `LIBARCHIVE_2936`: binary-state-null plus compound lifecycle, archive virtual
  directory state.
- `LIBCOAP_CVE_2023_35862`: equality/magic path in configuration parsing.
  The native smoke path now passes harness admissibility, non-ASAN `D_F`
  replay, short pre-trigger guidance gate, and ASAN terminal replay. It still
  needs longer ASAN campaign evidence before it can stand as long-run evidence.
- `PCRE2_CVE_2025_58050`: equality/magic plus compound lifecycle in regex
  compilation.

Each replacement must pass the harness admissibility audit before it can be used
as core FORMTRIG evidence.

## PNG007 Current-Site Update

On 2026-06-16, the PNG007 BindingSpecs were repaired against the current native
site map:

- `MAGMA_png_read_transform_info`, `pngrtran.c:1947`, cmp inst `19`
- `MAGMA_png_read_transform_info`, `pngrtran.c:1967`, root/use pairs
  `46/47`, `49/50`, `58/59`, and `70/71`
- `MAGMA_png_set_PLTE`, `pngset.c:634`, branch inst `81`

The sweep result is benefit-negative, not implementation-negative. All four
current-site candidates compiled and triggered Magma `_T` in 20s, with terminal
triggered exec counts between `594` and `1217`. But every candidate reported
`pretrigger_lift_guidance_ready=false`, `saved_non_trigger_progress_events=0`,
`non_trigger_candidate_lift_delta=false`, and
`lift_delta_only_on_triggered_candidates=true`.

Therefore PNG007 does not currently show that FORMTRIG guides R-to-T before the
terminal state is reached. It can remain as a control or negative example, but
main long-run budget should move to targets that first show spec-driven
non-trigger progress and then convert that progress into same-budget terminal
TTE benefit.

On 2026-06-18, the local TrigFuzz paper copy was rechecked at
`third_party/TrigFuzz/docs/trigfuzz.pdf` with the repository README at
`third_party/TrigFuzz/README.md`. The paper explicitly names PNG007 and
`png_ptr->palette == NULL` as a correctly generated triggering condition whose
distance collapses to `1` for non-triggered executions and `0` only when the
vulnerability is already triggered. The paper states that this binary distance
does not effectively guide scheduling or mutation and can reduce TrigFuzz to
its AFLGo baseline behavior.

This makes PNG007 a strong motivation/control target for the binary-`D_T`
problem. It does not make PNG007 positive FORMTRIG evidence in the current
artifact state, because FORMTRIG must show pre-trigger accepted progress before
claiming it solved the R-to-T guidance gap on this target.
