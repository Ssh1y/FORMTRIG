#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec "$repo_root/scripts/run_gpac3403_typedops36_matched_longrun.sh" \
  --duration 600 \
  --reps 1 \
  --arms formtrig \
  --baselines "" \
  --seed-preflight-timeout 10 \
  --binding-spec "$repo_root/artifacts/binding_specs/GPAC_3403.native_b7_relation_value_candidate.yml" \
  --typed-ops 48 \
  --typed-op-start 44 \
  --typed-schedule op-first \
  --typed-mutation-max 256 \
  --typed-retain-max 256 \
  --typed-retain-mode all \
  --typed-retain-endpoint-replay on \
  --typed-retain-endpoint-selection op-diverse \
  --typed-retain-endpoint-max-records 128 \
  --typed-retain-endpoint-positive-control "$repo_root/benchmarks/cve_pocs/gpac/GPAC_3403.poc" \
  "$@"
