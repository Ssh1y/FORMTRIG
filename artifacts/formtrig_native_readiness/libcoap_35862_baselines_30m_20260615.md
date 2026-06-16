# LIBCOAP_CVE_2023_35862 30m Faithful Baseline Evidence

This package records the first 30-minute faithful AFL++-family baseline runs
for `LIBCOAP_CVE_2023_35862`, using the same RNT seed corpus and target harness
as the FORMTRIG native runs.

## Purpose

The goal is to move the baseline comparison from representative placeholders to
real executable artifacts. These runs are not the final SOTA comparison because
they are non-ASAN runs; terminal success is observable only as a native crash.
The ASAN terminal-oracle baseline variant is still required.

Accepted baseline scope:

- `aflplusplus_vanilla`: local AFL++ coverage/reach-only control.
- `aflplusplus_cmplog`: local AFL++ CmpLog comparison-feedback artifact.
- `redqueen_operand`: AFL++ Redqueen/CmpLog operand mode. This is not claimed
  to be the original Redqueen artifact unless a separate paper-equivalence
  mapping is added.

The runner contract now requires each accepted baseline id to carry
`paper_anchors`, `artifact_anchors`, and an explicit `information_budget`.
Representative ids, unsupported ids, or accepted-looking contracts missing
those anchors are rejected before dry-run or execution. The historical raw
evidence for this 30-minute package predates that stricter contract schema, but
the baseline identities and caveats above match the same policy.

Related-paper anchors for this package:

- `related_papers/AFL++ CMPLOG.pdf`
- `related_papers/Redqueen.pdf`
- `paper/notes/RELATED_PAPER_ARTIFACTS.md`
- `paper/notes/TC_GAP_CAPABILITY_MATRIX.md`

## Command

```bash
FORMTRIG_JOBS=8 scripts/run_libcoap_35862_baselines.sh \
  --out /tmp/formtrig_libcoap_35862_baselines_30m_20260615T211555Z \
  --durations 1800 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand
```

The runner wrote `baseline_contract` metadata into each `run_config.json`,
`status.json`, and `run_record.json`.

## Results

| baseline | budget | run_time | execs_done | exec/s | corpus_count | saved_crashes | saved_hangs | success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aflplusplus_vanilla` | 1800 | 1800 | 7233966 | 4018.87 | 139 | 0 | 20 | false |
| `aflplusplus_cmplog` | 1800 | 1800 | 7414238 | 4119.01 | 138 | 0 | 16 | false |
| `redqueen_operand` | 1800 | 1800 | 7902220 | 4390.10 | 143 | 0 | 15 | false |

All three runs completed the full 1800-second budget and found no native crash.
This is useful baseline execution evidence, but it is not by itself proof that
the baselines cannot trigger the bug under a sanitizer oracle.

## Interpretation

The comparison is currently asymmetric:

- FORMTRIG 30m and 2h non-ASAN runs expose internal `R -> T` guidance:
  replay-stable non-trigger progress, spec-driven lifted `D_F`, typed mutation,
  and binding-role attribution.
- These AFL++-family baselines expose native crash outcomes, coverage corpus
  growth, hangs, and throughput, but no target-state `D_F` signal and no
  FORMTRIG BindingSpec semantics.

The immediate result is therefore a faithful execution milestone, not a final
performance claim. It establishes that the selected AFL++-family baselines are
buildable and runnable under the same seed corpus and 30-minute budget, and that
none produced a native crash during this run.

## Caveats

- Non-ASAN native crash accounting is not equivalent to the ASAN
  terminal-oracle mode used for confirmed vulnerability triggering.
- This is one repetition. Main comparisons need repetitions and the 2-hour
  budget, plus the ASAN baseline variant.
- `redqueen_operand` currently uses the AFL++ CmpLog/Redqueen path. Treat it as
  an AFL++ operand baseline, not a claim about the original Redqueen artifact.
- Hangs are nonzero across all three runs and should be tracked in the ASAN and
  2-hour baseline packages.
- The ASAN follow-up is recorded in
  `artifacts/formtrig_native_readiness/libcoap_35862_baselines_asan_30m_20260615.md`.
  In that same-oracle package, all three AFL++-family baselines triggered
  quickly. Treat LIBCOAP as pipeline/oracle validation and negative-control
  evidence, not as a final SOTA-positive FORMTRIG terminal-advantage target.

## Preserved Evidence

Raw summary evidence is preserved at:

`artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_30m_20260615T211555Z`

The preserved directory includes:

- baseline build logs and CmpLog compiler preflight log;
- `run_metadata.txt`;
- per-baseline `run_config.json`;
- per-baseline `events.jsonl`;
- per-baseline `status.json`;
- per-baseline `run_record.json`;
- per-baseline `fuzzer_stats`.
