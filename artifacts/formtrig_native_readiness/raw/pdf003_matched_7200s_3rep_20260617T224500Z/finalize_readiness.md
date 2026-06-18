# Magma Matched Finalize Readiness: PDF003

- ready to finalize: `true`
- expected runs: `9`
- selected runs: `9`
- complete selected runs: `9`
- duplicate policy: `prefer-later`
- boundary: ready_to_finalize only checks baseline run-record completeness and duplicate resolution; final claims still require finalize output review

## Duplicate Runs

- `aflplusplus_cmplog_7200s_rep3` policy=`prefer-later` kept=`artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard_7200s_20260618T014149Z`
- `aflplusplus_vanilla_7200s_rep3` policy=`prefer-later` kept=`artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard_7200s_20260618T014149Z`
- `redqueen_operand_7200s_rep3` policy=`prefer-later` kept=`artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard_7200s_20260618T014149Z`

## Commands

```bash
python3 tools/merge_magma_baseline_roots.py --out artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/merged_baselines --source artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/baselines --source artifacts/formtrig_native_readiness/raw/pdf003_baselines_rep3_shard_7200s_20260618T014149Z --duplicate-policy prefer-later
scripts/finalize_magma_matched_run.sh --run-root artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z --baseline-dir artifacts/formtrig_native_readiness/raw/pdf003_matched_7200s_3rep_20260617T224500Z/merged_baselines --guidance-out artifacts/formtrig_native_readiness/baseline_guidance_gap/pdf003_matched_7200s_3rep_20260617T224500Z --comparison-out artifacts/formtrig_native_readiness/comparisons/pdf003_matched_7200s_3rep_20260617T224500Z
```
