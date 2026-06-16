# FORMTRIG Comparison Packages - 2026-06-16

This note records the first machine-generated comparison packages that combine
saved FORMTRIG gate evidence with same-target baseline summaries. These
packages are not final acceptance evidence by themselves; they are audit
artifacts that prevent manual reinterpretation of mismatched budgets,
terminal-only runs, and low-repetition baselines.

## Tool

```bash
tools/compare_formtrig_baselines.py
```

The tool is benefit-first. Each generated Markdown/JSON package starts with a
`Benefit Readout` that states:

- primary benefit statements allowed by matched-budget evidence;
- endpoint observations such as FORMTRIG terminal success or first `_T` upper
  bounds;
- mechanism benefits such as converting binary/sparse trigger feedback into
  accepted non-trigger search progress;
- benefit statements that are blocked or not yet supported;
- design evidence that can be used only for attribution after the benefit is
  stated.

Only after that does it list the FORMTRIG internal signals and baseline groups.
This prevents `D_F`, BindingSpec roles, typed mutation, or terminal-state volume
from being presented as performance claims by themselves.

The tool also keeps three facts separate:

- strict FORMTRIG pre-trigger guidance:
  accepted and saved non-trigger `D_F` progress, spec-lifted signal, no
  heuristic/manual lift, and binding-signal `pass`;
- FORMTRIG terminal oracle success;
- baseline terminal oracle success.

Strict pre-trigger guidance is a FORMTRIG admissibility and mechanism check,
not a ranking metric against CmpLog, Redqueen, or other baselines. Baseline
comparison should use same-budget terminal success, TTE/first-trigger upper
bounds, throughput/cost, and repetitions. Terminal-state volume is auxiliary
unless the compared arms use the same oracle and counter semantics.

It refuses to silently compare different budgets. A comparison with no matched
baseline budget receives:

```text
not_comparable_missing_matched_budget
```

It also marks single-repetition evidence as `low_replication`.
When `--required-baselines` is provided, a package that is missing one of the
required matched-budget baseline families receives:

```text
incomplete_required_baseline_set
```

## Generated Packages

### PNG006: FORMTRIG 2h vs baseline 30m gap

Command:

```bash
python3 tools/compare_formtrig_baselines.py \
  --comparison-id PNG006_formtrig_2h_vs_baseline_30m_gap_20260616 \
  --target-id PNG006 \
  --formtrig-gate formtrig_2h=artifacts/formtrig_native_readiness/raw/png006_2h_20260615T1250Z/gate_summary.csv \
  --baseline-summary magma_30m=artifacts/formtrig_native_readiness/raw/png006_baselines_30m_20260616T013914Z/summary.json \
  --out-dir artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_baseline_30m_gap_20260616
```

Output:

```text
artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_baseline_30m_gap_20260616
```

Verdict:

```text
not_comparable_missing_matched_budget
```

Reason: the saved FORMTRIG evidence is 7200 seconds, while the current faithful
baseline package is 1800 seconds. The package records that FORMTRIG has strict
pre-trigger guidance and terminal oracle evidence, but the comparative claim is
blocked until 7200-second faithful baselines are run.

### PNG006: FORMTRIG 2h vs vanilla 2h incomplete baseline set

Command:

```bash
python3 tools/compare_formtrig_baselines.py \
  --comparison-id PNG006_formtrig_2h_vs_vanilla_2h_incomplete_20260616 \
  --target-id PNG006 \
  --formtrig-gate formtrig_2h=artifacts/formtrig_native_readiness/raw/png006_2h_20260615T1250Z/gate_summary.csv \
  --baseline-summary vanilla_2h=artifacts/formtrig_native_readiness/raw/png006_baselines_2h_vanilla_20260616T033317Z/summary.json \
  --required-baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --out-dir artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_vanilla_2h_incomplete_20260616
```

Output:

```text
artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_vanilla_2h_incomplete_20260616
```

Verdict:

```text
incomplete_required_baseline_set
```

Reason: the saved FORMTRIG 2-hour evidence is now paired with a matched
7200-second `aflplusplus_vanilla` baseline. The vanilla run has
`PNG006_R=23144616` and `PNG006_T=0`, while FORMTRIG has strict pre-trigger
guidance and terminal oracle evidence. The package is still incomplete because
the required matched-budget `aflplusplus_cmplog` and `redqueen_operand` runs
are missing and there is only one repetition.

Benefit readout: this package allows a limited primary benefit statement against the
vanilla reach-only control: FORMTRIG reaches terminal success where vanilla does
not trigger in the matched 7200-second budget. It blocks final performance
claims because first FORMTRIG `_T`/TTE was not recorded, CmpLog/Redqueen are
missing in this package, and replication is low.

### PNG006: FORMTRIG 2h vs vanilla+CmpLog 2h incomplete baseline set

Command:

```bash
python3 tools/compare_formtrig_baselines.py \
  --comparison-id PNG006_formtrig_2h_vs_vanilla_cmplog_2h_incomplete_20260616 \
  --target-id PNG006 \
  --formtrig-gate formtrig_2h=artifacts/formtrig_native_readiness/raw/png006_2h_20260615T1250Z/gate_summary.csv \
  --baseline-summary vanilla_2h=artifacts/formtrig_native_readiness/raw/png006_baselines_2h_vanilla_20260616T033317Z/summary.json \
  --baseline-summary cmplog_2h=artifacts/formtrig_native_readiness/raw/png006_baselines_2h_cmplog_20260616T053928Z/summary.json \
  --required-baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --out-dir artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_vanilla_cmplog_2h_incomplete_20260616
```

Output:

```text
artifacts/formtrig_native_readiness/comparisons/png006_formtrig_2h_vs_vanilla_cmplog_2h_incomplete_20260616
```

Verdict:

```text
incomplete_required_baseline_set
```

Reason: the saved FORMTRIG 2-hour evidence is paired with matched 7200-second
`aflplusplus_vanilla` and `aflplusplus_cmplog` baselines. Vanilla remains at
`PNG006_T=0`, but CmpLog reaches target-specific `PNG006_T=2362` and first
observes `_T` at the 120-second Magma monitor upper bound. The package is still
incomplete because `redqueen_operand` is missing and there is only one
repetition, but it also records `matched_baseline_also_triggers`. PNG006 should
therefore be treated as a control/native-readiness target rather than a main
SOTA-gap target.

Benefit readout: this package allows no primary performance benefit statement
because a matched CmpLog baseline also triggers. It still allows the mechanism
benefit statement that binary or sparse trigger feedback was lifted into
accepted non-trigger search progress. It blocks the performance-advantage statement
because a matched CmpLog baseline also triggers and FORMTRIG first `_T`/TTE was
not recorded for the saved run.

### LIBCOAP: pre-trigger FORMTRIG 30m vs non-ASAN baselines

Before comparison, the generic baseline summarizer was run on the preserved
LIBCOAP non-ASAN baseline raw directory:

```bash
python3 tools/summarize_post_reach_baselines.py \
  --root artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_30m_20260615T211555Z \
  --out-json artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_30m_20260615T211555Z/summary.json \
  --out-tsv artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_30m_20260615T211555Z/summary.tsv
```

Comparison command:

```bash
python3 tools/compare_formtrig_baselines.py \
  --comparison-id LIBCOAP_35862_pretrigger_30m_vs_non_asan_baselines_20260616 \
  --target-id LIBCOAP_CVE_2023_35862 \
  --formtrig-gate formtrig_pretrigger_30m=artifacts/formtrig_native_readiness/raw/libcoap_35862_30m_20260615T182142Z/gate_summary.csv \
  --baseline-summary non_asan_30m=artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_30m_20260615T211555Z/summary.json \
  --out-dir artifacts/formtrig_native_readiness/comparisons/libcoap_35862_pretrigger_30m_vs_non_asan_baselines_20260616
```

Output:

```text
artifacts/formtrig_native_readiness/comparisons/libcoap_35862_pretrigger_30m_vs_non_asan_baselines_20260616
```

Verdict:

```text
pretrigger_guidance_only
```

Reason: FORMTRIG has strict pre-trigger guidance in the non-ASAN 30-minute run,
and the three non-ASAN AFL++-family baselines have target success rate 0/1 in
this package. However, FORMTRIG terminal oracle success is absent in this
pre-trigger-only run, and all baselines have only one repetition.

### LIBCOAP: ASAN terminal FORMTRIG 30m vs ASAN baselines

Before comparison, the generic baseline summarizer was run on the preserved
LIBCOAP ASAN baseline raw directory:

```bash
python3 tools/summarize_post_reach_baselines.py \
  --root artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_asan_30m_20260615T233518Z \
  --out-json artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_asan_30m_20260615T233518Z/summary.json \
  --out-tsv artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_asan_30m_20260615T233518Z/summary.tsv
```

Comparison command:

```bash
python3 tools/compare_formtrig_baselines.py \
  --comparison-id LIBCOAP_35862_asan_terminal_30m_vs_asan_baselines_20260616 \
  --target-id LIBCOAP_CVE_2023_35862 \
  --formtrig-gate formtrig_asan_terminal_30m=artifacts/formtrig_native_readiness/raw/libcoap_35862_asan_30m_20260615T225016Z/gate_summary.csv \
  --baseline-summary asan_30m=artifacts/formtrig_native_readiness/raw/libcoap_35862_baselines_asan_30m_20260615T233518Z/summary.json \
  --out-dir artifacts/formtrig_native_readiness/comparisons/libcoap_35862_asan_terminal_30m_vs_asan_baselines_20260616
```

Output:

```text
artifacts/formtrig_native_readiness/comparisons/libcoap_35862_asan_terminal_30m_vs_asan_baselines_20260616
```

Verdict:

```text
baseline_also_triggers_not_sota_advantage
```

Reason: the FORMTRIG ASAN terminal-oracle run has terminal success, but all
three ASAN AFL++-family baselines also trigger in the same 1800-second budget.
This confirms the earlier decision to keep LIBCOAP as a pipeline/oracle
validation target rather than a strong SOTA-positive FORMTRIG target.

## Current Acceptance Implication

The comparison packages make the current evidence state explicit:

- PNG006 now has 7200-second faithful vanilla and CmpLog controls. CmpLog
  triggers within the 120-second monitor upper bound, so PNG006 is not a hard
  SOTA-positive case for FORMTRIG. Redqueen/CmpLog-path and repetitions remain
  useful for completeness, but harder targets should receive the long-run
  budget first.
- LIBCOAP demonstrates real-CVE pre-trigger guidance and terminal-oracle
  plumbing, but it does not prove a SOTA advantage because the ASAN baselines
  also trigger.
- No final "FORMTRIG beats SOTA" claim should be made from these packages
  alone.

## Hard-Target Triage

The target-level queue is generated from comparison packages by:

```bash
python3 tools/triage_formtrig_targets.py \
  --comparison artifacts/formtrig_native_readiness/comparisons \
  --manual-target 'LIBXML2_1107|demote_harness_artifact|harness exposes terminal trigger as a direct input knob; not admissible as core R2T evidence|do not use as core evidence; keep only build, BindingSpec, and crash-accounting sanity checks|artifacts/formtrig_native_readiness/raw/libxml2_1107_harness_admissibility_20260615.json' \
  --out-json artifacts/formtrig_native_readiness/hard_target_triage_20260616.json \
  --out-csv artifacts/formtrig_native_readiness/hard_target_triage_20260616.csv \
  --out-packages-csv artifacts/formtrig_native_readiness/hard_target_package_triage_20260616.csv \
  --out-md artifacts/formtrig_native_readiness/hard_target_triage_20260616.md
```

Outputs:

```text
artifacts/formtrig_native_readiness/hard_target_triage_20260616.json
artifacts/formtrig_native_readiness/hard_target_triage_20260616.csv
artifacts/formtrig_native_readiness/hard_target_package_triage_20260616.csv
artifacts/formtrig_native_readiness/hard_target_triage_20260616.md
```

Current result: `PNG006` and `LIBCOAP_CVE_2023_35862` are
`demote_to_control_or_negative`; `LIBXML2_1107` is
`demote_harness_artifact`. The current package set therefore contains no main
hard-target candidate. The next experiment step is hard-target discovery and
short triage, not more primary-claim long runs on these demoted targets.

## Hard-Target Discovery

The next queue is generated from the Magma inventory, real-CVE candidate audit,
current comparison triage, and available BindingSpec candidates:

```bash
python3 tools/plan_formtrig_hard_targets.py \
  --out-json artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.json \
  --out-csv artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.csv \
  --out-md artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.md \
  --limit 30
```

Outputs:

```text
artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.json
artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.csv
artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.md
```

Current top queue: `GPAC_3403`, `LIBARCHIVE_2936`, `PNG007`, `PDF003`,
`SSL011`, `SSL015`, and `TIF012`. This is not a performance claim; it is the
next experiment allocation plan. Magma baseline short screens should use the
generic inventory-driven runner:

```bash
scripts/run_magma_baselines.sh \
  --target-id PNG007 \
  --durations 600,1800 \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --jobs 3
```

The real-CVE readiness subset is generated by:

```bash
python3 tools/audit_real_cve_readiness.py \
  --out-json artifacts/formtrig_native_readiness/real_cve_readiness_20260616.json \
  --out-csv artifacts/formtrig_native_readiness/real_cve_readiness_20260616.csv \
  --out-md artifacts/formtrig_native_readiness/real_cve_readiness_20260616.md
```

Current readiness result: `GPAC_3403` and `LIBARCHIVE_2936` already have the
core opportunity evidence for a binary/uninformative trigger-guidance case
(`R=1,T=0`, native `D_T=1`, and terminal validation). Their blocker is now
specific: no executable BindingSpec candidate exists yet.
