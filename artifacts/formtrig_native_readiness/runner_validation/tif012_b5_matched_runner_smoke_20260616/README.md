# TIF012 B5 Matched Runner Smoke

This package records a 1s, 2-repetition smoke run of
`scripts/run_tif012_b5_matched_longrun.sh`.

Purpose:

- validate the one-command TIF012 matched flow:
  FORMTRIG manifest batch, Magma AFL++-family baselines, FORMTRIG gate, and
  comparison package rebuild;
- validate that repeated TIF012 manifests use distinct output directories even
  with `--jobs 1`;
- keep this separate from long-run efficacy evidence.

This is not a performance result. The budget is intentionally too small for a
paper claim, and the comparison verdict is recorded only as a smoke-test output
from the same comparison tool used by longer runs.

Observed smoke output:

- FORMTRIG directories: `001_TIF012/out` and `002_TIF012/out`;
- FORMTRIG terminal `_T`: 2/2 runs, first upper bounds `0.034s` and `0.035s`;
- matched baselines loaded: 3 families x 2 repetitions, 1s budget;
- comparison verdict: `positive_endpoint_matched_comparison`;
- raw smoke directory at run time:
  `/tmp/formtrig_tif012_b5_runner_dup_smoke_20260616T222404Z`.
