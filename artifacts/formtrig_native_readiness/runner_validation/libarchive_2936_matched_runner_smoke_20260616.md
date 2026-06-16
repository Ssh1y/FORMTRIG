# LIBARCHIVE_2936 Matched Runner Smoke

This smoke validates orchestration only. It is not performance evidence because
the budget is 2 seconds.

- Runner: `scripts/run_libarchive_2936_matched_longrun.sh`
- Command shape: `--mode execute --duration 2 --reps 1 --jobs 4 --continue-on-fail`
- Raw output: `/tmp/formtrig_libarchive_2936_runner_smoke_2s_20260616T164032Z`
- Generated outputs: `run_plan.sh`, `run_plan.jsonl`, `formtrig_gate/gate_summary.csv`, `baseline_summary.json`, `comparison/comparison.json`

FORMTRIG gate result:

| status | first _T | first exec | terminal count | binding signal | strict pre-trigger |
| --- | ---: | ---: | ---: | --- | --- |
| pass | 1.214s | 32 | 4 | pass / role_signal_progress_observed | true |

Baseline smoke rows:

| baseline | run time | saved crashes | success |
| --- | ---: | ---: | --- |
| AFL++ vanilla | 2s | 0 | false |
| AFL++ CmpLog | 2s | 0 | false |
| Redqueen/operand | 2s | 0 | false |

Interpretation: the matched runner can start all treatment/baseline arms and
produce the evidence files needed for long-run comparison. The 7200s x3 command
in the benefit-first worklist is still required for a real performance claim.
