#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec "$repo_root/scripts/run_gpac3403_b13_scal_ref_payload_endpoint_gate.sh" \
  --duration 60 \
  --reps 1 \
  --jobs "${FORMTRIG_JOBS:-2}" \
  --arms formtrig,formtrig_nohook,aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  --baselines aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand \
  "$@"
