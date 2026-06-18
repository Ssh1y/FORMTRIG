# GPAC_3403 ASAN Baseline Pre-Screen

- Target: `GPAC_3403`
- Scope: 60s ASAN endpoint baseline pre-screen from `artifacts/rnt_corpus/GPAC_3403/seeds`
- Status: short-gate evidence only; not a long-run SOTA-pain proof

## Build Sanity

Two independent AFL++ baseline binaries were built from GPAC commit
`3ab9394473dfcdc830a4fb44a138db5276ae4bdb`:

| binary | path | sha256 |
| --- | --- | --- |
| plain ASAN | `/tmp/formtrig_gpac3403_aflpp_plain_asan_src/bin/gcc/MP4Box` | `fb3437d513755c24b6bee983a34cbbacb95b3848bfba46e8b352a3801c48775f` |
| CmpLog ASAN | `/tmp/formtrig_gpac3403_aflpp_cmplog_asan_src/bin/gcc/MP4Box` | `e4e02af748a4ccef1985de6a878c664b2d65c068db856e9b74c9805c63b19d6e` |

The plain ASAN binary reproduces the known POC:

- command: `MP4Box -cat benchmarks/cve_pocs/gpac/GPAC_3403.poc benchmarks/cve_seeds/gpac/white.mp4 -out /dev/null`
- exit code: `134`
- signal: `AddressSanitizer attempting double-free`

## Baseline Result

Valid run rule: return code is `0` or `124`, `run_time >= 50`, and `execs_done > 0`.

| baseline | valid reps | invalid reps | endpoint successes | median execs | median corpus | max corpus |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `aflplusplus_vanilla` | 3 | 0 | 0 | 1467 | 58 | 67 |
| `aflplusplus_cmplog` | 3 | 0 | 0 | 1406 | 56 | 63 |
| `redqueen_operand` | 2 | 1 | 0 | 1000.5 | 32.0 | 63 |

`redqueen_operand` rep2 is excluded from endpoint conclusions because the CmpLog
forkserver crashed before fuzzing began (`execs_done=0`, `run_time=2`).

## FORMTRIG Reference

Existing FORMTRIG 60s binding validation:
`artifacts/formtrig_native_readiness/binding_validation/GPAC_3403.binding_validation_60s_20260618.json`

- terminal `_T`: not observed
- accepted non-trigger progress events: `2`
- saved non-trigger progress events: `2`
- spec `D_F` candidate values: `[4, 2, 3]`
- typed mutation: `109` typed execs, `14` typed finds
- same-object role: bound statically, but not observed dynamically

## Interpretation

This is useful because GPAC_3403 now has both sides of the first short gate:
FORMTRIG produces strict pre-trigger lifted guidance, while ASAN-enabled AFL++
family baselines did not find the endpoint crash in valid 60s runs from the same
RNT seed corpus.

This is not yet enough to claim that GPAC_3403 proves the SOTA pain point. The
next step is a matched 10m/2h campaign with ASAN endpoint baselines, a FORMTRIG
terminal oracle that is comparable to that endpoint, and repaired same-object
runtime observability.
