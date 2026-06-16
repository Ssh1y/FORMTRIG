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

The tool keeps three facts separate:

- strict FORMTRIG pre-trigger guidance:
  accepted and saved non-trigger `D_F` progress, spec-lifted signal, no
  heuristic/manual lift, and binding-signal `pass`;
- FORMTRIG terminal oracle success;
- baseline terminal oracle success.

It refuses to silently compare different budgets. A comparison with no matched
baseline budget receives:

```text
not_comparable_missing_matched_budget
```

It also marks single-repetition evidence as `low_replication`.

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

- PNG006 still needs the 7200-second faithful baseline package and repetitions.
- LIBCOAP demonstrates real-CVE pre-trigger guidance and terminal-oracle
  plumbing, but it does not prove a SOTA advantage because the ASAN baselines
  also trigger.
- No final "FORMTRIG beats SOTA" claim should be made from these packages
  alone.
