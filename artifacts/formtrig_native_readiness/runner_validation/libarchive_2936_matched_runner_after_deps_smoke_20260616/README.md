# LIBARCHIVE_2936 Matched Runner Smoke After Dependency Install

This package records a 2s, 1-repetition smoke run of
`scripts/run_libarchive_2936_matched_longrun.sh` after `libjpeg-dev` and
`liblzma-dev` were installed.

Purpose:

- validate that the matched runner can launch FORMTRIG, AFL++ vanilla,
  AFL++ CmpLog, and the local Redqueen/operand path;
- validate that the runner emits a FORMTRIG gate summary, baseline summary,
  and comparison package;
- keep this separate from long-run efficacy evidence.

This is not a performance result. The budget is intentionally too small for a
paper claim, and the comparison verdict is recorded only as a smoke-test
output from the same comparison tool used by longer runs.

Observed smoke output:

- FORMTRIG gate: pass, `terminal_triggered=4`, first terminal time `1.208s`;
- matched baselines loaded: 3 families, 1 repetition each, 2s budget;
- comparison verdict: `positive_endpoint_matched_comparison`;
- raw smoke directory at run time:
  `/tmp/formtrig_libarchive_runner_smoke_after_deps_20260616T221249Z`.
