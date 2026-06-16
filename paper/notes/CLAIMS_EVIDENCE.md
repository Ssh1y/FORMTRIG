# Claim-Evidence Ledger

Use this file to prevent unsupported claims. Every non-obvious claim in the
paper should map to a local artifact, a verified citation, or a clearly marked
TODO.

## Core Claims

| ID | Claim | Evidence | Paper Location | Status |
| --- | --- | --- | --- | --- |
| C1 | FORMTRIG is a target-state-guided post-reach layer, not a reachability replacement. | `docs/formtrig_positioning.md`, `docs/known_rt_experiment_protocol.md` | Introduction, Discussion | Supported locally |
| C2 | PRET separates time to reach from time to target-state, and reached-seedbank campaigns set TTR to 0 by construction. | `docs/formtrig_positioning.md`, `tools/summarize_magma_campaign.py` | Introduction, Evaluation | Supported locally |
| C3 | FORMTRIG evaluates operationalization of known or validated target-state information, not triggering-condition discovery accuracy. | `docs/formtrig_positioning.md`, `docs/known_rt_experiment_protocol.md` | Introduction, Approach, Threats | Supported locally |
| C4 | Binary sink distances can be uninformative and need lifting. | `docs/trigfuzz_formtrig_complementarity.md`, toy results | Motivation, Results | Needs citation plus toy table |
| C5 | Parser replay treats parse success as an oracle, not the source of `D_F`. | `experiments/results/EXPERIMENT_STATUS.md`, `experiments/results/real_replay_metrics.json` | Results | Needs table extraction |
| C6 | PNG001 clean gate: AFL++ has null TTE in 5/5; FORMTRIG-Full has TTE 30s in 5/5. | `experiments/results/magma_campaigns_png001_clean_gate_5rep_2m_summary.json` | Results | Historical local result; re-verify against current implementation before using |
| C7 | PNG001 ablation: NoLift and NoField do not expose in 3/3 short runs. | `experiments/results/magma_campaigns_png001_ablation_3rep_1m_summary.json` | Results | Historical local result; re-verify against current implementation before using |
| C8 | PNG007 was previously negative or insufficient evidence in older runs. | `experiments/results/magma_campaigns_png007_full_3rep_5m_summary.json` | Results, Limitations | Historical local result; superseded for current discussion by trend-centered smoke evidence |
| C9 | FORMTRIG instrumentation has lower exec/sec than AFL++ in libpng campaigns. | `experiments/results/EXPERIMENT_STATUS.md`, campaign summaries | Discussion | Needs final table |
| C10 | For PNG001/PNG007/SQL013, current short runs should be interpreted by trend signals, not final `_T` alone. PNG007 and SQL013 show positive post-reach trends; PNG001 shows active state/probe movement but no current 5-minute `_T`. | `CHANGELOG.md`, `experiments/results/state_score_3bugs_5m_tuned/*`, `/tmp/trend_PNG001.json`, `/tmp/trend_PNG007.json`, `/tmp/trend_SQL013.json` | Results, Discussion | Smoke/trend evidence only; needs repeated runs and baselines |
| C11 | The formal Magma controlled experiment uses `_R` only to build reached seedbanks and `_T` only as the target-state oracle; `MAGMA_LOG` predicate expressions do not define formal `D_F`. | `docs/known_rt_experiment_protocol.md`, `tools/run_known_rt_campaign.py` | Evaluation, Threats | Supported locally |
| C12 | Known R/T experiments are summarized with `TTR=0` because every input seed has already been replay-filtered as reached and not `_T`. | `tools/extract_reached_corpus.py`, `tools/summarize_magma_campaign.py`, seedbank manifests | Evaluation | Supported locally |
| C13 | In current PNG001/PNG007 smoke or historical replay data, native `D_T` is flat among reached-but-not-target-state seeds: one unique value, entropy `0.0`, and same-D_T ratio `1.0`. | `experiments/results/dt_study_full.json`, `experiments/results/dt_study_full.csv`, `paper/notes/DT_STUDY_RESULTS.md` | Motivation, Empirical Study | Smoke/historical evidence only; needs formal collection for all 9 Magma targets |
| C14 | The related-paper set mostly separates into reach-focused DGF, target-state/condition-guided work, and runtime value/field feedback; this motivates measuring post-reach native `D_T` information directly. | `paper/notes/RELATED_PAPER_MATRIX.md`, `paper/notes/DT_STUDY_LITERATURE.md`, `experiments/dt_study/related_papers_matrix.json` | Related Work, Motivation | Supported as local reading notes; citations still need final BibTeX verification |
| C15 | Among the 14 local related papers, 9 explicitly mention an official artifact/repository in the paper text, 4 explicitly mention reproduction artifacts/logs/data, and all 14 contain evaluation evidence. | `paper/notes/RELATED_PAPER_ARTIFACTS.md`, `experiments/dt_study/related_papers_artifacts.json` | Related Work, Evaluation Setup | Supported by local PDF text extraction; live artifact availability still needs separate verification |
| C16 | The empirical study is a feedback-signal information measurement study: it tests whether known/validated target-state information still yields low-information post-reach guidance for existing tools. | `paper/notes/MEASUREMENT_STUDY_SCOPE.md`, `docs/dt_informativeness_study.md`, `experiments/results/dt_study_full.json` | Introduction, Motivation, Evaluation | Supported as study framing; formal claims require additional aligned baseline runs |
| C17 | In the 14 local related papers, 4 explicitly use or discuss Magma as a benchmark/dataset in their evaluation: CSFuzz, Locus, SDFuzz, and TrigFuzz. | `paper/notes/MAGMA_RELATED_PAPERS.md`, `experiments/dt_study/magma_related_papers.json` | Related Work, Evaluation Setup | Supported by local PDF text extraction |
| C18 | Under a shared known/validated-TC assumption, each of the 14 local related-work tool ideas can be mapped to a native post-reach `D_T` feedback model; this supports measuring feedback-signal information before fully reimplementing every tool. | `paper/notes/NATIVE_DT_MODELS_BY_TOOL_IDEA.md`, `experiments/dt_study/native_dt_models_by_paper.json`, `paper/notes/MEASUREMENT_STUDY_SCOPE.md` | Motivation, Methodology, Evaluation Setup | Supported as measurement design; per-tool empirical rows still require replay/log collection |
| C19 | The current D_T contribution framework implements a unified TC-known native `D_T` module, mutation contribution metrics, offline scheduling contribution metrics, and campaign-timeline outputs without modifying a fuzzer. | `experiments/dt_contribution/distance_modules/native_dt.py`, `tools/analyze_dt_contribution.py`, `tests/test_dt_contribution.py`, `paper/notes/DT_DISTANCE_DESIGNS.md` | Methodology, Evaluation Setup | Supported locally |
| C20 | In the current 9-target Magma pilot, binary-oracle native `D_T` is flat for every target that has reached-but-not-`_T` seeds, and reach-preserving mutation improvement is zero except for PDF016's target-state rows. | `experiments/dt_contribution/reports/dt_informativeness_by_target.csv`, `experiments/dt_contribution/reports/dt_mutation_sensitivity.csv`, `experiments/dt_contribution/reports/dt_summary.md` | Motivation, Pilot Results | Preliminary pilot evidence only; not a final main-study claim |
| C21 | FORMTRIG evaluation must be benefit-first: performance claims come from same-budget terminal success, first `_T`/TTE/PRET, repetition rate, and cost; `D_F`, BindingSpec, dominance frontier, and typed mutation are attribution/mechanism evidence, not cross-tool performance metrics. | `docs/goal.md`, `artifacts/formtrig_native_readiness/acceptance_longrun_queue_20260615.md`, `tools/compare_formtrig_baselines.py`, `artifacts/formtrig_native_readiness/comparison_packages_20260616.md` | Evaluation, Results, Discussion | Supported locally |
| C22 | LIBARCHIVE_2936 currently supports a matched-budget speedup/attribution claim, not a baseline-impossibility claim: in 60s x3 with the same `-t 5000+` oracle, FORMTRIG triggers in 3/3 with first `_T` values 1.196s, 2.000s, and 1.326s; AFL++ vanilla triggers in 3/3 at 22.883s, 24.450s, and 37.648s; AFL++ CmpLog triggers in 3/3 at 34.169s, 28.505s, and 60.976s; the local AFL++ Redqueen/operand path triggers in 2/3 at 34.587s and 30.505s. One 10m confirmation preserves the direction: FORMTRIG first `_T` is 1.220s / exec 32 versus the fastest successful baseline at 20.671s / exec 28677. | `artifacts/formtrig_native_readiness/comparisons/libarchive_2936_b4_path_hierarchy_hook_60s_20260616/comparison.json`, `docs/goal.md` | Results, Discussion | Local speedup evidence; still needs 2h matched repetitions and harder Magma/real-CVE targets before broad efficacy claims |
| C23 | The experimental queue must be benefit-first: a target is promoted by endpoint benefit or a validated short-screen gate, while `D_F`, BindingSpec, dominance frontier, and typed mutation are mechanism evidence used to attribute the benefit and decide whether to spend long-run budget. | `tools/plan_formtrig_experiment_worklist.py`, `artifacts/formtrig_native_readiness/experiment_worklists/benefit_first_worklist_20260616.json`, `artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.json` | Evaluation, Results, Discussion | Supported locally as planning/guardrail artifact; not itself a performance result |
| C24 | LIBARCHIVE_2936 now has a reusable matched long-run runner that launches FORMTRIG, AFL++ vanilla, AFL++ CmpLog, and the local Redqueen/operand path under the same seed corpus and `-t 5000+` oracle, then emits FORMTRIG gate, baseline summary, and comparison artifacts. | `scripts/run_libarchive_2936_matched_longrun.sh`, `tests/test_libarchive_matched_runner.py`, `artifacts/formtrig_native_readiness/runner_validation/libarchive_2936_matched_runner_smoke_20260616.json` | Evaluation Artifact, Reproduction | Smoke-supported orchestration claim only; the 2s smoke is not performance evidence and the 7200s x3 run remains required |

## Hard Rules

- Do not cite a paper unless the sentence is supported by that paper.
- Do not cite a title from memory. Import it into `references.bib` from Zotero
  or a verified metadata source.
- Do not turn a smoke test into a formal efficacy claim.
- Report null TTE/PRET as null.
- Do not claim FORMTRIG discovers correct triggering conditions in the main
  evaluation.
- Do not use Magma `MAGMA_LOG` predicate expressions as formal FORMTRIG
  distance sources.
- Label diagnostic reach counts as diagnostic, not efficacy evidence.
- Keep negative results when they clarify the boundary of the method.
- For binary or plateau-like cases, report intermediate guidance trends
  (`_R` series, bucket/state movement, probe/change, repair/change, exec/sec,
  and queue growth) separately from final `_T`.
- State the user-visible or experiment-visible benefit before the design
  mechanism. Intermediate FORMTRIG signals can explain and attribute a benefit,
  but they cannot replace matched-budget terminal/TTE evidence.
