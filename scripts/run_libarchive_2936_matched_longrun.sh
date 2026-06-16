#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id="LIBARCHIVE_2936"
category="binary-state-null"
duration="7200"
reps="3"
jobs="${FORMTRIG_JOBS:-1}"
mode="execute"
timeout_arg="5000+"
monitor_poll="${FORMTRIG_STATS_MONITOR_POLL:-1}"
seed_dir="$repo_root/artifacts/rnt_corpus/LIBARCHIVE_2936/seeds"
binding_spec="$repo_root/artifacts/binding_specs/LIBARCHIVE_2936.native_b4_path_table_root_distance_candidate.yml"
site_map="/tmp/formtrig_libarchive_2936_native_env/site_map.tsv"
formtrig_binary="/tmp/formtrig_libarchive_2936_build/libarchive_write_replay_formtrig"
plain_binary="/tmp/formtrig_libarchive_2936_aflpp_plain_build/libarchive_write_replay_aflpp_plain"
cmplog_binary="/tmp/formtrig_libarchive_2936_aflpp_cmplog_build/libarchive_write_replay_aflpp_cmplog"
afl_fuzz="$repo_root/experiments/aflplusplus/AFLplusplus/afl-fuzz"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
arms="formtrig,aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
out_dir=""
failed_jobs=0
continue_on_fail=0

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Runs matched LIBARCHIVE_2936 FORMTRIG and AFL++-family long-run repetitions
from the same reached-not-trigger seed corpus and same terminal timeout oracle.

options:
  --duration SEC       per-arm AFL++ budget, default 7200
  --reps N             repetitions per arm, default 3
  --jobs N             concurrent arm runs, default FORMTRIG_JOBS or 1
  --mode MODE          execute|dry-run, default execute
  --out DIR            output directory
  --arms LIST          comma/space-separated arms, default all
  --baselines LIST     comma/space-separated baseline arms for comparison
  --timeout AFL_T      AFL++ -t value, default 5000+
  --seed-dir DIR       reached-not-trigger seed corpus
  --binding-spec FILE  FORMTRIG BindingSpec
  --site-map FILE      FORMTRIG native site map
  --formtrig-binary F  FORMTRIG-instrumented target
  --plain-binary F     plain AFL++ target
  --cmplog-binary F    AFL++ CmpLog target
  --afl-fuzz FILE      AFL++ afl-fuzz
  --monitor-poll SEC   FORMTRIG stats monitor poll, default 1
  --continue-on-fail   keep summarizing if an arm fails

outputs:
  OUT/run_plan.sh
  OUT/run_plan.jsonl
  OUT/runs/<arm>_rep<N>/{...}
  OUT/formtrig_gate/gate_summary.csv
  OUT/baseline_summary.json
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

split_list() {
  printf '%s\n' "$1" | tr ', ' '\n' | awk 'NF { print }'
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

wait_for_job_slot() {
  local max_jobs="$1"
  while (( $(jobs -pr | wc -l) >= max_jobs )); do
    if ! wait -n; then
      failed_jobs=1
    fi
  done
}

wait_for_all_jobs() {
  while (( $(jobs -pr | wc -l) > 0 )); do
    if ! wait -n; then
      failed_jobs=1
    fi
  done
  if [[ "$failed_jobs" != "0" && "$continue_on_fail" == "0" ]]; then
    echo "one or more LIBARCHIVE_2936 matched runs failed" >&2
    exit 1
  fi
}

record_plan() {
  local arm="$1"
  local rep="$2"
  local kind="$3"
  local command="$4"
  {
    printf '{"arm":'
    json_escape "$arm"
    printf ',"rep":%s,"kind":' "$rep"
    json_escape "$kind"
    printf ',"duration_s":%s,"command":' "$duration"
    json_escape "$command"
    printf '}\n'
  } >> "$plan_jsonl"
  {
    printf '# %s rep%s (%s)\n' "$arm" "$rep" "$kind"
    printf '%s\n\n' "$command"
  } >> "$plan_sh"
}

baseline_needs_cmplog() {
  case "$1" in
    aflplusplus_cmplog|redqueen_operand)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

baseline_command_array() {
  local baseline="$1"
  local rep="$2"
  local run_out="$3"
  BASELINE_CMD=(
    python3 "$repo_root/tools/run_post_reach_baseline.py"
    --baseline "$baseline"
    --target-id "$target_id"
    --tc-category "$category"
    --seed-corpus "$seed_dir"
    --out-dir "$run_out"
    --budget-sec "$duration"
    --rep "$rep"
    --target-cmd "$plain_binary @@"
    --afl-fuzz "$afl_fuzz"
    --memory-limit none
    --mode execute
    --afl-arg=-t
    --afl-arg="$timeout_arg"
  )
  if baseline_needs_cmplog "$baseline"; then
    BASELINE_CMD+=(--cmplog-binary "$cmplog_binary")
  fi
}

formtrig_command_array() {
  local rep="$1"
  local run_out="$2"
  FORMTRIG_CMD=(
    "$repo_root/scripts/run_formtrig_aflpp_campaign.sh"
    --in "$seed_dir"
    --out "$run_out/fuzzer_out"
    --target-bug "$target_id"
    --category "$category"
    --binding-spec "$binding_spec"
    --site-map "$site_map"
    --duration "$duration"
    --seed-preflight require
    --seed-preflight-max 32
    --seed-preflight-timeout 5
    --afl-arg "-t"
    --afl-arg "$timeout_arg"
    -- "$formtrig_binary" "@@"
  )
}

run_baseline_one() {
  local baseline="$1"
  local rep="$2"
  local run_out="$out_dir/runs/${baseline}_rep${rep}"
  mkdir -p "$run_out"
  baseline_command_array "$baseline" "$rep" "$run_out"
  record_plan "$baseline" "$rep" "baseline" "$(quote_cmd "${BASELINE_CMD[@]}")"
  if [[ "$mode" == "dry-run" ]]; then
    return 0
  fi
  {
    printf 'running %s rep%s at %s\n' "$baseline" "$rep" "$(date -u +%FT%TZ)"
    quote_cmd "${BASELINE_CMD[@]}"
    printf '\n'
    "${BASELINE_CMD[@]}"
  } > "$run_out/run.log" 2>&1
}

run_formtrig_one() {
  local rep="$1"
  local run_out="$out_dir/runs/formtrig_rep${rep}"
  mkdir -p "$run_out"
  formtrig_command_array "$rep" "$run_out"
  local rendered
  rendered="FORMTRIG_STATS_MONITOR_POLL=$monitor_poll $(quote_cmd "${FORMTRIG_CMD[@]}")"
  record_plan "formtrig" "$rep" "formtrig" "$rendered"
  if [[ "$mode" == "dry-run" ]]; then
    return 0
  fi
  {
    printf 'running formtrig rep%s at %s\n' "$rep" "$(date -u +%FT%TZ)"
    printf '%s\n' "$rendered"
    FORMTRIG_STATS_MONITOR_POLL="$monitor_poll" "${FORMTRIG_CMD[@]}"
  } > "$run_out/run.log" 2>&1
}

write_metadata() {
  cat > "$out_dir/run_metadata.json" <<EOF
{
  "arms": "$arms",
  "baselines": "$baselines",
  "binding_spec": "$binding_spec",
  "category": "$category",
  "duration_s": $duration,
  "mode": "$mode",
  "reps": $reps,
  "seed_dir": "$seed_dir",
  "site_map": "$site_map",
  "target_id": "$target_id",
  "time_utc": "$(date -u +%FT%TZ)",
  "timeout_oracle": "-t $timeout_arg"
}
EOF
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
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --arms)
      arms="${2:-}"
      shift 2
      ;;
    --baselines)
      baselines="${2:-}"
      shift 2
      ;;
    --timeout)
      timeout_arg="${2:-}"
      shift 2
      ;;
    --seed-dir)
      seed_dir="${2:-}"
      shift 2
      ;;
    --binding-spec)
      binding_spec="${2:-}"
      shift 2
      ;;
    --site-map)
      site_map="${2:-}"
      shift 2
      ;;
    --formtrig-binary)
      formtrig_binary="${2:-}"
      shift 2
      ;;
    --plain-binary)
      plain_binary="${2:-}"
      shift 2
      ;;
    --cmplog-binary)
      cmplog_binary="${2:-}"
      shift 2
      ;;
    --afl-fuzz)
      afl_fuzz="${2:-}"
      shift 2
      ;;
    --monitor-poll)
      monitor_poll="${2:-}"
      shift 2
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
for numeric in "$duration" "$reps" "$jobs" "$monitor_poll"; do
  if ! [[ "$numeric" =~ ^[0-9]+$ ]] || [[ "$numeric" -lt 1 ]]; then
    echo "duration, reps, jobs, and monitor poll must be positive integers" >&2
    exit 2
  fi
done

seed_dir="$(abs_path "$seed_dir")"
binding_spec="$(abs_path "$binding_spec")"
afl_fuzz="$(abs_path "$afl_fuzz")"
if [[ "$site_map" != /* ]]; then site_map="$(abs_path "$site_map")"; fi
if [[ "$formtrig_binary" != /* ]]; then formtrig_binary="$(abs_path "$formtrig_binary")"; fi
if [[ "$plain_binary" != /* ]]; then plain_binary="$(abs_path "$plain_binary")"; fi
if [[ "$cmplog_binary" != /* ]]; then cmplog_binary="$(abs_path "$cmplog_binary")"; fi

if [[ -z "$out_dir" ]]; then
  timeout_safe="${timeout_arg//[^A-Za-z0-9]/}"
  out_dir="$repo_root/artifacts/formtrig_native_readiness/raw/libarchive_2936_matched_${duration}s_t${timeout_safe}_${timestamp}"
else
  out_dir="$(abs_path "$out_dir")"
fi
mkdir -p "$out_dir/runs"
plan_jsonl="$out_dir/run_plan.jsonl"
plan_sh="$out_dir/run_plan.sh"
: > "$plan_jsonl"
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -euo pipefail\n\n'
} > "$plan_sh"
chmod +x "$plan_sh"
write_metadata

if [[ "$mode" == "execute" ]]; then
  require_path "$seed_dir"
  require_path "$binding_spec"
  require_path "$site_map"
  require_path "$formtrig_binary"
  require_path "$plain_binary"
  require_path "$afl_fuzz"
  for baseline in $(split_list "$baselines"); do
    if baseline_needs_cmplog "$baseline"; then
      require_path "$cmplog_binary"
    fi
  done
fi

for rep in $(seq 1 "$reps"); do
  for arm in $(split_list "$arms"); do
    case "$arm" in
      formtrig)
        if [[ "$mode" == "dry-run" ]]; then
          run_formtrig_one "$rep"
        else
          wait_for_job_slot "$jobs"
          run_formtrig_one "$rep" &
        fi
        ;;
      aflplusplus_vanilla|aflplusplus_cmplog|redqueen_operand)
        if [[ "$mode" == "dry-run" ]]; then
          run_baseline_one "$arm" "$rep"
        else
          wait_for_job_slot "$jobs"
          run_baseline_one "$arm" "$rep" &
        fi
        ;;
      *)
        echo "unsupported arm: $arm" >&2
        exit 2
        ;;
    esac
  done
done
wait_for_all_jobs

if [[ "$mode" == "dry-run" ]]; then
  echo "LIBARCHIVE_2936 matched long-run dry-run complete"
  echo "  out=$out_dir"
  echo "  plan=$plan_sh"
  exit 0
fi

gate_args=(
  "$repo_root/scripts/formtrig_experiment_gate.sh"
  --suite "LIBARCHIVE_2936_matched_${duration}s"
  --out "$out_dir/formtrig_gate"
  --min-runtime "$duration"
)
for rep in $(seq 1 "$reps"); do
  if [[ -d "$out_dir/runs/formtrig_rep${rep}/fuzzer_out" ]]; then
    gate_args+=(--run "formtrig_rep${rep}=$out_dir/runs/formtrig_rep${rep}/fuzzer_out")
  fi
done
if [[ "${#gate_args[@]}" -gt 7 ]]; then
  if ! "${gate_args[@]}"; then
    if [[ "$continue_on_fail" == "0" ]]; then
      exit 1
    fi
  fi
fi

python3 "$repo_root/tools/summarize_post_reach_baselines.py" \
  --root "$out_dir/runs" \
  --out-json "$out_dir/baseline_summary.json" \
  --out-tsv "$out_dir/baseline_summary.tsv"

if [[ -s "$out_dir/formtrig_gate/gate_summary.csv" &&
      -s "$out_dir/baseline_summary.json" ]]; then
  python3 "$repo_root/tools/compare_formtrig_baselines.py" \
    --comparison-id "libarchive_2936_matched_${duration}s_${reps}rep_${timestamp}" \
    --target-id "$target_id" \
    --formtrig-gate "formtrig=$out_dir/formtrig_gate/gate_summary.csv" \
    --baseline-summary "matched=$out_dir/baseline_summary.json" \
    --out-dir "$out_dir/comparison" \
    --min-reps "$reps" \
    --required-baselines "$baselines"
fi

echo "LIBARCHIVE_2936 matched long-run complete"
echo "  out=$out_dir"
echo "  plan=$plan_sh"
echo "  gate=$out_dir/formtrig_gate/gate_summary.csv"
echo "  baseline_summary=$out_dir/baseline_summary.json"
echo "  comparison=$out_dir/comparison/comparison.json"
