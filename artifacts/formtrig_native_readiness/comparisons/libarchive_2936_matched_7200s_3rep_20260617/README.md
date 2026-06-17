# LIBARCHIVE_2936 Matched 7200s x3

This package records a completed matched native real-CVE run for
`LIBARCHIVE_2936`.

Result:

- FORMTRIG: 3/3 terminal success; first `_T` times `1.358s`, `2.320s`,
  `1.494s`; terminal counts `10`, `23`, `46`.
- AFL++ vanilla: 3/3 terminal success; median first `_T` `56.056s`,
  fastest run `42.154s`.
- AFL++ CmpLog: 3/3 terminal success; median first `_T` `52.977s`,
  fastest run `51.275s`.
- Local AFL++ Redqueen/operand path: 3/3 terminal success; median first `_T`
  `32.517s`, fastest run `9.456s`.
- FORMTRIG speedup over the fastest successful baseline run: `6.96x`.
- FORMTRIG speedup over the fastest successful baseline-family median:
  `23.94x`.

Interpretation:

This is real speedup and attribution evidence, not main SOTA-gap evidence. The
same reached-not-trigger corpus, timeout oracle, and replay harness let every
required baseline family trigger in all three repetitions, and the fastest
faithful baseline run reaches `_T` at 9.456 seconds. The comparison package therefore
marks `experiment_strength.main_claim_strength` as
`not_hard_pain_baseline_fast_enough`.

The harness passed the static admissibility audit: it is a generic
`libarchive_write_replay` byte grammar and does not hard-code `_compare_path_table`
or a NULL-parent crash. However, the replay grammar and current RNT seed are too
easy for faithful baselines to expose the SOTA pain point cleanly. Main-budget
evidence must come from a higher-fidelity/raw-format harness, farther RNT seeds,
no-hook and generic-hook ablations, or harder Magma/real-CVE targets where
strong baselines do not trigger within an acceptable time budget.

Files:

- `comparison.json`, `comparison.md`, `comparison.tsv`: regenerated comparison
  package with experiment-strength gating.
- `baseline_summary.json`, `baseline_summary.tsv`: matched AFL++ family results.
- `formtrig_gate_summary.csv`, `formtrig_gate_report.md`: FORMTRIG gate output.
- `harness_admissibility.json`, `harness_admissibility.md`: static harness audit.
- `run_metadata.json`: runner metadata.
