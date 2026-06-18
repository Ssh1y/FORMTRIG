#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id=""
duration="7200"
reps="3"
jobs="${FORMTRIG_JOBS:-1}"
baseline_jobs="${FORMTRIG_BASELINE_JOBS:-}"
mode="execute"
continue_on_fail=0
run_baseline_build=1
poll="30"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
manifest=""
manifest_list=""
inventory="$repo_root/artifacts/magma_canary_inventory.json"
magma_dir="$repo_root/experiments/magma_workspace/magma"
out_dir=""
guidance_out=""
comparison_out=""
failed_jobs=0
declare -a baseline_afl_args=()

usage() {
  cat >&2 <<EOF
usage: $0 --target-id ID [options]

Runs a matched Magma FORMTRIG-vs-AFL++ family experiment. The FORMTRIG
manifest batch and faithful Magma baselines are launched as parallel arms, then
the script emits gate, baseline guidance-gap, and comparison artifacts.

options:
  --target-id ID            Magma target id, for example PDF003
  --duration SEC            per-arm budget, default 7200
  --reps N                  repetitions, default 3
  --jobs N                  concurrent FORMTRIG manifest jobs
  --baseline-jobs N         concurrent baseline runs, default baselines*reps
  --mode MODE               execute|dry-run, default execute
  --out DIR                 output root
  --manifest FILE           single FORMTRIG manifest repeated --reps times
  --manifest-list FILE      explicit FORMTRIG manifest list
  --inventory JSON          Magma canary inventory
  --magma-dir DIR           Magma checkout/workspace
  --guidance-out DIR        baseline guidance-gap output directory
  --comparison-out DIR      comparison package output directory
  --baselines LIST          comma/space-separated baseline ids
  --poll SEC                Magma monitor poll interval, default 30
  --baseline-afl-arg ARG    extra AFL++ arg for baselines; repeatable
  --afl-arg ARG             alias for --baseline-afl-arg
  --no-build-baselines      skip Magma baseline builds
  --continue-on-fail        keep postprocessing after child runner failures

outputs:
  OUT/run_plan.sh
  OUT/run_plan.jsonl
  OUT/formtrig/
  OUT/baselines/
  OUT/schedule_audit.json
  OUT/schedule_audit.md
  OUT/live_status.json
  OUT/live_status.md
  OUT/formtrig_signal_path.json
  OUT/formtrig_signal_path.md
  OUT/formtrig_gate/gate_summary.csv
  OUT/baseline_guidance_gap/baseline_guidance_gap.json
  OUT/comparison/comparison.json
  OUT/comparison/evidence/
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

run_async_step() {
  local step="$1"
  local log="$2"
  shift 2
  local rendered
  rendered="$(quote_cmd "$@")"
  record_plan "$step" "$rendered" "$log"
  if [[ "$mode" == "dry-run" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$log")"
  (
    printf 'running %s at %s\n' "$step" "$(date -u +%FT%TZ)"
    printf '%s\n' "$rendered"
    "$@"
  ) > "$log" 2>&1 &
  pids+=("$!")
  pid_names+=("$step")
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

wait_for_parallel_arms() {
  local i status
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
      status=$?
      failed_jobs=1
      echo "parallel arm failed: ${pid_names[$i]} status=$status" >&2
    fi
  done
  if [[ "$failed_jobs" != "0" && "$continue_on_fail" == "0" ]]; then
    exit 1
  fi
}

manifest_value() {
  local manifest_file="$1"
  local key="$2"
  awk -v want="$key" '
    /^[[:space:]]*#/ { next }
    index($0, ":") == 0 { next }
    {
      k = $0
      sub(/:.*/, "", k)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
      if (k == want) {
        v = $0
        sub(/^[^:]*:/, "", v)
        sub(/[[:space:]]+#.*/, "", v)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
        print v
      }
    }
  ' "$manifest_file" | tail -n 1
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
  "parallel_arms": true,
  "reps": $reps,
  "target_id": "$target_id",
  "time_utc": "$(date -u +%FT%TZ)"
}
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --guidance-out)
      guidance_out="${2:-}"
      shift 2
      ;;
    --comparison-out)
      comparison_out="${2:-}"
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
    --baseline-afl-arg|--afl-arg)
      baseline_afl_args+=("${2:-}")
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
if [[ -z "$target_id" ]]; then
  usage
  exit 2
fi
for numeric in "$duration" "$reps" "$jobs" "$poll"; do
  if ! [[ "$numeric" =~ ^[0-9]+$ ]] || [[ "$numeric" -lt 1 ]]; then
    echo "duration, reps, jobs, baseline-jobs, and poll must be positive integers" >&2
    exit 2
  fi
done
if [[ -z "$baseline_jobs" ]]; then
  baseline_jobs=$(($(count_list "$baselines") * reps))
fi
for numeric in "$baseline_jobs"; do
  if ! [[ "$numeric" =~ ^[0-9]+$ ]] || [[ "$numeric" -lt 1 ]]; then
    echo "duration, reps, jobs, baseline-jobs, and poll must be positive integers" >&2
    exit 2
  fi
done
if [[ -z "$manifest" && -z "$manifest_list" ]]; then
  manifest_list="$repo_root/artifacts/formtrig_native_readiness/manifests/${target_id}.current_${reps}rep.list"
  if [[ ! -f "$manifest_list" ]]; then
    manifest_list="$repo_root/artifacts/formtrig_native_readiness/manifests/${target_id}.current_1rep.list"
  fi
fi

inventory="$(abs_path "$inventory")"
magma_dir="$(abs_path "$magma_dir")"
[[ -n "$manifest" ]] && manifest="$(abs_path "$manifest")"
[[ -n "$manifest_list" ]] && manifest_list="$(abs_path "$manifest_list")"

if [[ -z "$out_dir" ]]; then
  out_dir="$repo_root/artifacts/formtrig_native_readiness/raw/${target_id,,}_matched_${duration}s_${reps}rep_${timestamp}"
else
  out_dir="$(abs_path "$out_dir")"
fi
mkdir -p "$out_dir/logs"

formtrig_out="$out_dir/formtrig"
baseline_out="$out_dir/baselines"
gate_out="$out_dir/formtrig_gate"
if [[ -z "$guidance_out" ]]; then
  guidance_out="$out_dir/baseline_guidance_gap"
else
  guidance_out="$(abs_path "$guidance_out")"
fi
if [[ -z "$comparison_out" ]]; then
  comparison_out="$out_dir/comparison"
else
  comparison_out="$(abs_path "$comparison_out")"
fi
plan_jsonl="$out_dir/run_plan.jsonl"
plan_sh="$out_dir/run_plan.sh"
: > "$plan_jsonl"
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -euo pipefail\n\n'
} > "$plan_sh"
chmod +x "$plan_sh"

require_path "$inventory"
require_path "$repo_root/scripts/run_formtrig_manifest_batch.sh"
require_path "$repo_root/scripts/run_magma_baselines.sh"
require_path "$repo_root/scripts/formtrig_experiment_gate.sh"
require_path "$repo_root/tools/audit_magma_matched_schedule.py"
require_path "$repo_root/tools/live_magma_matched_status.py"
require_path "$repo_root/tools/analyze_formtrig_signal_path.py"
require_path "$repo_root/tools/analyze_baseline_guidance_gap.py"
require_path "$repo_root/tools/compare_formtrig_baselines.py"
require_path "$repo_root/tools/package_magma_matched_evidence.py"
if [[ "$mode" == "execute" ]]; then
  require_path "$magma_dir/tools/captain/build.sh"
  require_path "$magma_dir/tools/captain/start.sh"
fi

if [[ -n "$manifest_list" ]]; then
  manifest_list_path="$manifest_list"
  require_path "$manifest_list_path"
else
  require_path "$manifest"
  manifest_list_path="$out_dir/formtrig_manifest_list.txt"
  : > "$manifest_list_path"
  for _rep in $(seq 1 "$reps"); do
    printf '%s\n' "$manifest" >> "$manifest_list_path"
  done
fi

if [[ "${#baseline_afl_args[@]}" -eq 0 ]]; then
  first_manifest="$(awk 'NF && $1 !~ /^#/ { print $1; exit }' "$manifest_list_path")"
  if [[ -n "$first_manifest" && -f "$first_manifest" ]]; then
    read -r -a manifest_afl_args <<< "$(manifest_value "$first_manifest" afl_args)"
    baseline_afl_args+=("${manifest_afl_args[@]}")
  fi
fi

write_metadata
python3 "$repo_root/tools/audit_magma_matched_schedule.py" \
  --run-root "$out_dir" \
  --format md \
  --out-json "$out_dir/schedule_audit.json" \
  --out-md "$out_dir/schedule_audit.md" \
  > "$out_dir/logs/schedule_audit.log" 2>&1 || true

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
for arg in "${baseline_afl_args[@]}"; do
  [[ -n "$arg" ]] && BASELINE_CMD+=(--afl-arg "$arg")
done

declare -a pids=()
declare -a pid_names=()
run_async_step "formtrig_batch" "$out_dir/logs/formtrig_batch.log" "${FORMTRIG_CMD[@]}"
run_async_step "magma_baselines" "$out_dir/logs/magma_baselines.log" "${BASELINE_CMD[@]}"
wait_for_parallel_arms

LIVE_STATUS_CMD=(
  python3 "$repo_root/tools/live_magma_matched_status.py"
  --target-id "$target_id"
  --run-root "$out_dir"
  --format "md"
  --out-json "$out_dir/live_status.json"
  --out-md "$out_dir/live_status.md"
)
run_step "live_status" "$out_dir/logs/live_status.log" 1 "${LIVE_STATUS_CMD[@]}" || true

SIGNAL_PATH_CMD=(
  python3 "$repo_root/tools/analyze_formtrig_signal_path.py"
  --target-id "$target_id"
  --formtrig-dir "$formtrig_out"
  --run-root "$out_dir"
  --format "md"
  --out-json "$out_dir/formtrig_signal_path.json"
  --out-md "$out_dir/formtrig_signal_path.md"
)
run_step "formtrig_signal_path" "$out_dir/logs/formtrig_signal_path.log" 1 "${SIGNAL_PATH_CMD[@]}" || true

GATE_CMD=(
  "$repo_root/scripts/formtrig_experiment_gate.sh"
  --suite "${target_id}_matched_${duration}s_${reps}rep"
  --out "$gate_out"
  --min-runtime "$duration"
)
for rep in $(seq 1 "$reps"); do
  GATE_CMD+=(--run "rep${rep}=$(generated_gate_run_path "$rep")")
done
run_step "formtrig_gate" "$out_dir/logs/formtrig_gate.log" 1 "${GATE_CMD[@]}" || true

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
run_step "baseline_guidance_gap" "$out_dir/logs/baseline_guidance_gap.log" 1 "${GUIDANCE_CMD[@]}" || true

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
run_step "comparison" "$out_dir/logs/comparison.log" 0 "${COMPARE_CMD[@]}"

EVIDENCE_CMD=(
  python3 "$repo_root/tools/package_magma_matched_evidence.py"
  --target-id "$target_id"
  --duration "$duration"
  --reps "$reps"
  --run-root "$out_dir"
  --comparison-dir "$comparison_out"
  --baseline-dir "$baseline_out"
  --formtrig-dir "$formtrig_out"
  --gate-dir "$gate_out"
  --guidance-dir "$guidance_out"
)
run_step "evidence_bundle" "$out_dir/logs/evidence_bundle.log" 1 "${EVIDENCE_CMD[@]}" || true

echo "Magma matched long-run flow complete"
echo "  out=$out_dir"
echo "  plan=$plan_sh"
echo "  formtrig=$formtrig_out"
echo "  baselines=$baseline_out"
echo "  live_status=$out_dir/live_status.md"
echo "  formtrig_signal_path=$out_dir/formtrig_signal_path.md"
echo "  gate=$gate_out/gate_summary.csv"
echo "  guidance_gap=$guidance_out/baseline_guidance_gap.json"
echo "  comparison=$comparison_out/comparison.json"
echo "  evidence=$comparison_out/evidence"
