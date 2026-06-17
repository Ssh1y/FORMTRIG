#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id=""
duration=""
reps=""
baselines=""
run_root=""
guidance_out=""
comparison_out=""
mode="execute"

usage() {
  cat >&2 <<EOF
usage: $0 --run-root DIR [options]

Rebuilds postprocessing artifacts for a completed or in-flight generic Magma
matched FORMTRIG-vs-baseline run. This is intended for old runs, interrupted
runs, and manual evidence repair without rerunning fuzzers.

options:
  --run-root DIR        matched run root containing formtrig/ and baselines/
  --target-id ID        override metadata target id
  --duration SEC        override metadata per-arm duration
  --reps N              override metadata repetition count
  --baselines LIST      override metadata baseline ids
  --guidance-out DIR    guidance-gap output, default RUN_ROOT/baseline_guidance_gap
  --comparison-out DIR  comparison output, default RUN_ROOT/comparison
  --mode MODE           execute|dry-run, default execute

outputs:
  RUN_ROOT/finalize_plan.sh
  RUN_ROOT/finalize_plan.jsonl
  RUN_ROOT/schedule_audit.json
  RUN_ROOT/schedule_audit.md
  RUN_ROOT/live_status.json
  RUN_ROOT/live_status.md
  RUN_ROOT/formtrig_signal_path.json
  RUN_ROOT/formtrig_signal_path.md
  RUN_ROOT/formtrig_gate/gate_summary.csv
  GUIDANCE_OUT/baseline_guidance_gap.json
  COMPARISON_OUT/comparison.json
  COMPARISON_OUT/evidence/
EOF
}

abs_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s\n' "$path"
  elif [[ -d "$path" ]]; then
    (cd "$path" && pwd)
  else
    local dir base
    dir="$(dirname "$path")"
    base="$(basename "$path")"
    (cd "$dir" && printf '%s/%s\n' "$(pwd)" "$base")
  fi
}

json_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "$value"
}

quote_cmd() {
  local first=1
  for arg in "$@"; do
    if [[ "$first" == "0" ]]; then
      printf ' '
    fi
    printf '%q' "$arg"
    first=0
  done
}

metadata_value() {
  local key="$1"
  local default_value="${2:-}"
  python3 - "$run_root/run_metadata.json" "$key" "$default_value" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path


path = Path(sys.argv[1])
key = sys.argv[2]
default = sys.argv[3]
if not path.exists():
    print(default)
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    print(default)
    raise SystemExit(0)
value = payload.get(key, default) if isinstance(payload, dict) else default
print(default if value is None else value)
PY
}

require_path() {
  if [[ ! -e "$1" ]]; then
    echo "missing required path: $1" >&2
    exit 2
  fi
}

record_plan() {
  local step="$1"
  local command="$2"
  local log="$3"
  {
    printf '{"step":'
    json_escape "$step"
    printf ',"duration_s":%s,"reps":%s,"command":' "$duration" "$reps"
    json_escape "$command"
    printf ',"log":'
    json_escape "$log"
    printf '}\n'
  } >> "$plan_jsonl"
  {
    printf '# %s\n' "$step"
    printf '%s\n' "$command"
    printf '# log: %s\n\n' "$log"
  } >> "$plan_sh"
}

run_step() {
  local step="$1"
  local log="$2"
  local allow_failure="$3"
  shift 3
  local rendered
  rendered="$(quote_cmd "$@")"
  record_plan "$step" "$rendered" "$log"
  if [[ "$mode" == "dry-run" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$log")"
  if ! "$@" > "$log" 2>&1; then
    echo "step failed: $step (log: $log)" >&2
    if [[ "$allow_failure" != "1" ]]; then
      exit 1
    fi
    return 1
  fi
}

generated_gate_run_path() {
  local rep="$1"
  local indexed="$formtrig_out/$(printf '%03d_%s' "$rep" "$target_id")/out"
  local single="$formtrig_out/$target_id/out"
  if [[ -d "$indexed" || "$reps" -gt 1 ]]; then
    printf '%s\n' "$indexed"
  elif [[ -d "$single" ]]; then
    printf '%s\n' "$single"
  else
    printf '%s\n' "$indexed"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-root)
      run_root="${2:-}"
      shift 2
      ;;
    --target-id)
      target_id="${2:-}"
      shift 2
      ;;
    --duration)
      duration="${2:-}"
      shift 2
      ;;
    --reps)
      reps="${2:-}"
      shift 2
      ;;
    --baselines)
      baselines="${2:-}"
      shift 2
      ;;
    --guidance-out)
      guidance_out="${2:-}"
      shift 2
      ;;
    --comparison-out)
      comparison_out="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

case "$mode" in
  execute|dry-run)
    ;;
  *)
    echo "--mode must be execute or dry-run: $mode" >&2
    exit 2
    ;;
esac

if [[ -z "$run_root" ]]; then
  usage
  exit 2
fi
run_root="$(abs_path "$run_root")"
require_path "$run_root"

[[ -z "$target_id" ]] && target_id="$(metadata_value target_id)"
[[ -z "$duration" ]] && duration="$(metadata_value duration_s)"
[[ -z "$reps" ]] && reps="$(metadata_value reps)"
[[ -z "$baselines" ]] && baselines="$(metadata_value baselines)"
if [[ -z "$target_id" || -z "$duration" || -z "$reps" || -z "$baselines" ]]; then
  echo "missing target-id, duration, reps, or baselines; pass overrides or provide run_metadata.json" >&2
  exit 2
fi
for numeric in "$duration" "$reps"; do
  if ! [[ "$numeric" =~ ^[0-9]+$ ]] || [[ "$numeric" -lt 1 ]]; then
    echo "duration and reps must be positive integers" >&2
    exit 2
  fi
done

if [[ -z "$guidance_out" ]]; then
  guidance_out="$run_root/baseline_guidance_gap"
else
  guidance_out="$(abs_path "$guidance_out")"
fi
if [[ -z "$comparison_out" ]]; then
  comparison_out="$run_root/comparison"
else
  comparison_out="$(abs_path "$comparison_out")"
fi

formtrig_out="$run_root/formtrig"
baseline_out="$run_root/baselines"
gate_out="$run_root/formtrig_gate"
logs_dir="$run_root/logs"
plan_jsonl="$run_root/finalize_plan.jsonl"
plan_sh="$run_root/finalize_plan.sh"
mkdir -p "$logs_dir"
: > "$plan_jsonl"
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -euo pipefail\n\n'
} > "$plan_sh"
chmod +x "$plan_sh"

require_path "$repo_root/tools/audit_magma_matched_schedule.py"
require_path "$repo_root/tools/live_magma_matched_status.py"
require_path "$repo_root/tools/analyze_formtrig_signal_path.py"
require_path "$repo_root/scripts/formtrig_experiment_gate.sh"
require_path "$repo_root/tools/analyze_baseline_guidance_gap.py"
require_path "$repo_root/tools/compare_formtrig_baselines.py"
require_path "$repo_root/tools/package_magma_matched_evidence.py"

SCHEDULE_CMD=(
  python3 "$repo_root/tools/audit_magma_matched_schedule.py"
  --run-root "$run_root"
  --format "md"
  --out-json "$run_root/schedule_audit.json"
  --out-md "$run_root/schedule_audit.md"
)
run_step "schedule_audit" "$logs_dir/finalize_schedule_audit.log" 1 "${SCHEDULE_CMD[@]}" || true

LIVE_STATUS_CMD=(
  python3 "$repo_root/tools/live_magma_matched_status.py"
  --target-id "$target_id"
  --run-root "$run_root"
  --format "md"
  --out-json "$run_root/live_status.json"
  --out-md "$run_root/live_status.md"
)
run_step "live_status" "$logs_dir/finalize_live_status.log" 1 "${LIVE_STATUS_CMD[@]}" || true

SIGNAL_PATH_CMD=(
  python3 "$repo_root/tools/analyze_formtrig_signal_path.py"
  --target-id "$target_id"
  --formtrig-dir "$formtrig_out"
  --run-root "$run_root"
  --format "md"
  --out-json "$run_root/formtrig_signal_path.json"
  --out-md "$run_root/formtrig_signal_path.md"
)
run_step "formtrig_signal_path" "$logs_dir/finalize_formtrig_signal_path.log" 1 "${SIGNAL_PATH_CMD[@]}" || true

GATE_CMD=(
  "$repo_root/scripts/formtrig_experiment_gate.sh"
  --suite "${target_id}_matched_${duration}s_${reps}rep"
  --out "$gate_out"
  --min-runtime "$duration"
)
for rep in $(seq 1 "$reps"); do
  GATE_CMD+=(--run "rep${rep}=$(generated_gate_run_path "$rep")")
done
run_step "formtrig_gate" "$logs_dir/finalize_formtrig_gate.log" 1 "${GATE_CMD[@]}" || true

GUIDANCE_CMD=(
  python3 "$repo_root/tools/analyze_baseline_guidance_gap.py"
  --analysis-id "${target_id,,}_matched_${duration}s_${reps}rep_${timestamp}_baseline_guidance_gap"
  --target-id "$target_id"
  --baseline-summary "aflpp_family_${duration}s_${reps}rep=$baseline_out/summary.json"
  --out-dir "$guidance_out"
  --required-baselines "$baselines"
  --min-reps "$reps"
  --acceptable-trigger-s "600"
  --hard-trigger-s "1800"
)
run_step "baseline_guidance_gap" "$logs_dir/finalize_baseline_guidance_gap.log" 1 "${GUIDANCE_CMD[@]}" || true

COMPARE_CMD=(
  python3 "$repo_root/tools/compare_formtrig_baselines.py"
  --comparison-id "${target_id,,}_matched_${duration}s_${reps}rep_${timestamp}"
  --target-id "$target_id"
  --formtrig-gate "typed_hook_${duration}s_${reps}rep=$gate_out/gate_summary.csv"
  --baseline-summary "aflpp_family_${duration}s_${reps}rep=$baseline_out/summary.json"
  --baseline-guidance-gap "$guidance_out"
  --out-dir "$comparison_out"
  --min-reps "$reps"
  --required-baselines "$baselines"
)
run_step "comparison" "$logs_dir/finalize_comparison.log" 0 "${COMPARE_CMD[@]}"

EVIDENCE_CMD=(
  python3 "$repo_root/tools/package_magma_matched_evidence.py"
  --target-id "$target_id"
  --duration "$duration"
  --reps "$reps"
  --run-root "$run_root"
  --comparison-dir "$comparison_out"
  --baseline-dir "$baseline_out"
  --formtrig-dir "$formtrig_out"
  --gate-dir "$gate_out"
  --guidance-dir "$guidance_out"
)
run_step "evidence_bundle" "$logs_dir/finalize_evidence_bundle.log" 1 "${EVIDENCE_CMD[@]}" || true

echo "Magma matched finalize flow complete"
echo "  run_root=$run_root"
echo "  plan=$plan_sh"
echo "  schedule_audit=$run_root/schedule_audit.md"
echo "  live_status=$run_root/live_status.md"
echo "  formtrig_signal_path=$run_root/formtrig_signal_path.md"
echo "  gate=$gate_out/gate_summary.csv"
echo "  guidance_gap=$guidance_out/baseline_guidance_gap.json"
echo "  comparison=$comparison_out/comparison.json"
echo "  evidence=$comparison_out/evidence"
