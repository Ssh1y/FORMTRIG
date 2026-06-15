# FORMTRIG Baseline Faithfulness Policy - 2026-06-15

This policy is part of the native FORMTRIG acceptance criteria. Baseline
comparisons must be faithful implementations, not family-name placeholders.
The baseline universe starts from the local related-paper audit, especially
`paper/notes/TC_GAP_CAPABILITY_MATRIX.md`,
`paper/notes/DT_RELATED_PAPER_MATRIX.md`, and the PDFs/text extracts under
`related_papers/` and `/tmp/formtrig_related_texts`. New baseline rows must
cite those paper/artifact anchors before they can enter an experiment table.

## Main Rule

A baseline result may enter the main quantitative comparison only if it is one
of:

- an official or artifact-author-provided implementation, built and run on the
  evaluated target with the same seed corpus, time budget, repetitions, and
  oracle policy as FORMTRIG;
- a paper-equivalent reimplementation whose implemented signal, scheduler, and
  mutator behavior are explicitly mapped to the paper mechanism and whose code,
  configuration, limitations, and validation smoke tests are preserved;
- a locally integrated implementation of a public artifact where the adapter is
  thin and auditable, with the upstream commit and local patch set recorded.

The following are not acceptable as main comparison evidence:

- "representative" signal-family stand-ins;
- offline proxy scoring that does not drive fuzzing unless the paper baseline is
  explicitly a replay/offline scoring method;
- a different fuzzer from the same broad family used as a substitute without
  paper-level equivalence;
- reusing FORMTRIG's lifted `D_F`, typed mutation registry, or BindingSpec
  semantics inside a baseline that did not have that information.

## Baseline Classes

The local related-work notes identify these comparison classes:

- reach/directed greybox fuzzing: AFLGo, FishFuzz, ParmeSan, WindRanger,
  SelectFuzz, DAFL;
- branch/compare feedback: AFL++ CmpLog, Redqueen, Angora, GreyOne;
- constraint/state feedback: CAFL, CSFuzz, SDFuzz, Locus, Lyso, UAFUZZ,
  StorFuzz;
- field/mutation feedback: IDFuzz and related field-contribution systems;
- TC-distance feedback: TrigFuzz-style triggering-condition distance.

For the main experiment, each selected baseline must have an executable adapter
that implements the paper/artifact mechanism for the evaluated target. If an
adapter is missing, the baseline stays in the related-work or gap-analysis table
and must not be counted in performance comparisons.

## Required Evidence Per Baseline Run

Each accepted baseline run must preserve:

- `run_config.json`, `events.jsonl`, `status.json`, and `run_record.json`;
- the exact command line, environment overrides, seed corpus, time budget,
  repetition id, target id, TC category, and oracle policy;
- raw fuzzer output, including `fuzzer_stats` or the baseline's equivalent
  progress log;
- artifact source path, upstream commit, local patches, and build logs;
- paper/artifact anchors and a paper-mechanism mapping that explains what signal
  is being used and what information budget the baseline receives.

FORMTRIG and all baselines must use the same RNT seed corpus, same terminal
oracle definition, same time budget, and comparable instrumentation class for a
given target. If a baseline cannot consume target-state information, that is a
reported limitation, not a reason to inject FORMTRIG-only information into it.

## Runner Contract

`tools/run_post_reach_baseline.py` is the common post-reach execution entrypoint.
It currently provides real AFL-family execution for:

- `aflplusplus_vanilla`;
- `aflplusplus_cmplog`;
- `redqueen_operand`, via AFL++ CmpLog/Redqueen machinery;
- `aflgo`, via the local AFLGo artifact path or `AFLGO_FUZZ`.

The runner refuses representative-only baselines with
`not_faithful_baseline_adapter`. This is intentional: those rows can guide
implementation work, but they are not evidence that FORMTRIG outperforms SOTA.
The runner also writes a `baseline_contract` object into `run_config.json`,
`status.json`, and `run_record.json`. For example, `redqueen_operand` is
declared as the AFL++ Redqueen/CmpLog implementation, not as the original
Redqueen artifact unless a separate paper-equivalence mapping is added.

## Immediate Queue Impact

The next accepted real-CVE and Magma comparison packages must pair each
FORMTRIG long run with faithful baseline runs for at least:

- AFL++ vanilla as the coverage/reach-only control;
- AFL++ CmpLog/Redqueen for visible comparison feedback;
- AFLGo or another faithfully wired directed-fuzzing artifact for reach
  guidance;
- a TC-distance baseline such as TrigFuzz-style native `D_T`, only if its
  distance, scheduler, and mutation behavior are implemented faithfully from the
  paper or artifact.

Additional SOTA baselines may be added only after their artifact adapter passes
the evidence requirements above.
