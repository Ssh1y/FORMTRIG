#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id="TIF012"
duration="7200"
reps="3"
jobs="${FORMTRIG_JOBS:-1}"
baseline_jobs="${FORMTRIG_BASELINE_JOBS:-}"
mode="execute"
continue_on_fail=0
run_baseline_build=1
poll="30"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
manifest="$repo_root/artifacts/formtrig_native_readiness/manifests/TIF012.native_draft_magma_canary.hook_b5.final_30s.manifest"
manifest_list=""
inventory="$repo_root/artifacts/magma_canary_inventory.json"
magma_dir="$repo_root/experiments/magma_workspace/magma"
out_dir=""

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Runs a matched TIF012 B5 FORMTRIG-vs-AFL++ family experiment from the same
reached-not-trigger seed corpus and Magma oracle, then emits gate, baseline,
and comparison artifacts.

options:
  --duration SEC          per-arm budget, default 7200
  --reps N                repetitions, default 3
  --jobs N                concurrent FORMTRIG manifest jobs
  --baseline-jobs N       concurrent baseline runs, default --jobs
  --mode MODE             execute|dry-run, default execute
  --out DIR               output directory
  --manifest FILE         FORMTRIG manifest repeated for --reps
  --manifest-list FILE    explicit FORMTRIG manifest list
  --inventory JSON        Magma canary inventory
  --magma-dir DIR         Magma checkout/workspace
  --baselines LIST        comma/space-separated baseline ids
  --poll SEC              Magma monitor poll interval, default 30
  --no-build-baselines    skip Magma baseline builds
  --continue-on-fail      keep building summaries after child runner failures

outputs:
  OUT/run_plan.sh
  OUT/run_plan.jsonl
  OUT/formtrig/
  OUT/baselines/
  OUT/formtrig_gate/gate_summary.csv
  OUT/comparison/comparison.json
EOF
}

require_path() {
  if [[ ! -e "$1" ]]; then
    echo "missing required path: $1" >&2
    exit 2
  fi
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

count_list() {
  printf '%s\n' "$1" | tr ', ' '\n' | awk 'NF { count++ } END { print count + 0 }'
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

write_metadata() {
  local baseline_count baseline_run_count baseline_batches
  baseline_count="$(count_list "$baselines")"
  baseline_run_count=$((baseline_count * reps))
  baseline_batches=$(((baseline_run_count + baseline_jobs - 1) / baseline_jobs))
  cat > "$out_dir/run_metadata.json" <<EOF
{
  "baselines": "$baselines",
  "baseline_count": $baseline_count,
  "baseline_run_count": $baseline_run_count,
  "baseline_batches": $baseline_batches,
  "duration_s": $duration,
  "formtrig_jobs": $jobs,
  "baseline_jobs": $baseline_jobs,
  "inventory": "$inventory",
  "manifest": "$manifest",
  "manifest_list": "$manifest_list_path",
  "magma_dir": "$magma_dir",
  "mode": "$mode",
  "reps": $reps,
  "target_id": "$target_id",
  "time_utc": "$(date -u +%FT%TZ)"
}
EOF
}

generated_gate_run_path() {
  local rep="$1"
  local indexed="$formtrig_out/$(printf '%03d_%s' "$rep" "$target_id")/out"
  local single="$formtrig_out/$target_id/out"
  if [[ "$mode" == "dry-run" ]]; then
    if [[ "$reps" -gt 1 || "$jobs" -gt 1 ]]; then
      printf '%s\n' "$indexed"
    else
      printf '%s\n' "$single"
    fi
    return
  fi
  if [[ -d "$indexed" ]]; then
    printf '%s\n' "$indexed"
  elif [[ -d "$single" ]]; then
    printf '%s\n' "$single"
  else
    printf '%s\n' "$indexed"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --duration)
      duration="${2:-}"
      shift 2
      ;;
    --reps)
      reps="${2:-}"
      shift 2
      ;;
    --jobs)
      jobs="${2:-}"
      shift 2
      ;;
    --baseline-jobs)
      baseline_jobs="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --manifest)
      manifest="${2:-}"
      shift 2
      ;;
    --manifest-list)
      manifest_list="${2:-}"
      shift 2
      ;;
    --inventory)
      inventory="${2:-}"
      shift 2
      ;;
    --magma-dir)
      magma_dir="${2:-}"
      shift 2
      ;;
    --baselines)
      baselines="${2:-}"
      shift 2
      ;;
    --poll)
      poll="${2:-}"
      shift 2
      ;;
    --no-build-baselines)
      run_baseline_build=0
      shift
      ;;
    --continue-on-fail)
      continue_on_fail=1
      shift
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
if [[ -z "$baseline_jobs" ]]; then
  baseline_jobs="$jobs"
fi
for numeric in "$duration" "$reps" "$jobs" "$baseline_jobs" "$poll"; do
  if ! [[ "$numeric" =~ ^[0-9]+$ ]] || [[ "$numeric" -lt 1 ]]; then
    echo "duration, reps, jobs, baseline-jobs, and poll must be positive integers" >&2
    exit 2
  fi
done

manifest="$(abs_path "$manifest")"
inventory="$(abs_path "$inventory")"
magma_dir="$(abs_path "$magma_dir")"

if [[ -z "$out_dir" ]]; then
  out_dir="$repo_root/artifacts/formtrig_native_readiness/raw/tif012_b5_matched_${duration}s_${reps}rep_${timestamp}"
else
  out_dir="$(abs_path "$out_dir")"
fi
mkdir -p "$out_dir"

formtrig_out="$out_dir/formtrig"
baseline_out="$out_dir/baselines"
gate_out="$out_dir/formtrig_gate"
comparison_out="$out_dir/comparison"
plan_jsonl="$out_dir/run_plan.jsonl"
plan_sh="$out_dir/run_plan.sh"
: > "$plan_jsonl"
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -euo pipefail\n\n'
} > "$plan_sh"
chmod +x "$plan_sh"

require_path "$manifest"
require_path "$inventory"
require_path "$repo_root/scripts/run_formtrig_manifest_batch.sh"
require_path "$repo_root/scripts/run_magma_baselines.sh"
require_path "$repo_root/scripts/formtrig_experiment_gate.sh"
require_path "$repo_root/tools/compare_formtrig_baselines.py"
if [[ "$mode" == "execute" ]]; then
  require_path "$magma_dir/tools/captain/build.sh"
  require_path "$magma_dir/tools/captain/start.sh"
fi

if [[ -n "$manifest_list" ]]; then
  manifest_list_path="$(abs_path "$manifest_list")"
  require_path "$manifest_list_path"
else
  manifest_list_path="$out_dir/formtrig_manifest_list.txt"
  : > "$manifest_list_path"
  for _rep in $(seq 1 "$reps"); do
    printf '%s\n' "$manifest" >> "$manifest_list_path"
  done
fi

write_metadata

FORMTRIG_CMD=(
  "$repo_root/scripts/run_formtrig_manifest_batch.sh"
  --manifest-list "$manifest_list_path"
  --duration "$duration"
  --out-root "$formtrig_out"
  --jobs "$jobs"
  --continue-on-fail
)

BASELINE_CMD=(
  "$repo_root/scripts/run_magma_baselines.sh"
  --target-id "$target_id"
  --inventory "$inventory"
  --out "$baseline_out"
  --magma-dir "$magma_dir"
  --durations "$duration"
  --baselines "$baselines"
  --reps "$reps"
  --jobs "$baseline_jobs"
  --poll "$poll"
)
if [[ "$run_baseline_build" == "0" ]]; then
  BASELINE_CMD+=(--no-build)
fi

run_step "formtrig_batch" "$out_dir/logs/formtrig_batch.log" "$continue_on_fail" "${FORMTRIG_CMD[@]}" || true
run_step "magma_baselines" "$out_dir/logs/magma_baselines.log" "$continue_on_fail" "${BASELINE_CMD[@]}" || true

GATE_CMD=(
  "$repo_root/scripts/formtrig_experiment_gate.sh"
  --suite "TIF012_b5_matched_${duration}s_${reps}rep"
  --out "$gate_out"
  --min-runtime "$duration"
)
for rep in $(seq 1 "$reps"); do
  GATE_CMD+=(--run "rep${rep}=$(generated_gate_run_path "$rep")")
done
run_step "formtrig_gate" "$out_dir/logs/formtrig_gate.log" 1 "${GATE_CMD[@]}" || true

COMPARE_CMD=(
  python3 "$repo_root/tools/compare_formtrig_baselines.py"
  --comparison-id "tif012_b5_matched_${duration}s_${reps}rep_${timestamp}"
  --target-id "$target_id"
  --formtrig-gate "b5_${duration}s_${reps}rep=$gate_out/gate_summary.csv"
  --baseline-summary "aflpp_family_${duration}s_${reps}rep=$baseline_out/summary.json"
  --out-dir "$comparison_out"
  --min-reps "$reps"
  --required-baselines "$baselines"
)
run_step "comparison" "$out_dir/logs/comparison.log" 0 "${COMPARE_CMD[@]}"

echo "TIF012 B5 matched long-run flow complete"
echo "  out=$out_dir"
echo "  plan=$plan_sh"
echo "  formtrig=$formtrig_out"
echo "  baselines=$baseline_out"
echo "  gate=$gate_out/gate_summary.csv"
echo "  comparison=$comparison_out/comparison.json"
