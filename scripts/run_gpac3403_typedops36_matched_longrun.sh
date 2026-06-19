#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id="GPAC_3403"
category="compound-sequence-lifecycle"
duration="7200"
reps="3"
jobs="${FORMTRIG_JOBS:-1}"
mode="execute"
timeout_arg="5000+"
monitor_poll="${FORMTRIG_STATS_MONITOR_POLL:-10}"
typed_ops="36"
typed_mutation_max="64"
typed_retain_max="0"
typed_retain_mode="signal"
typed_retain_endpoint_replay="off"
typed_retain_endpoint_timeout="5"
typed_retain_endpoint_replays="1"
typed_retain_endpoint_max_records="0"
typed_retain_endpoint_selection="best-d-f"
typed_retain_endpoint_cmd=""
typed_retain_endpoint_positive_control=""
seed_preflight="require"
seed_preflight_max="1"
seed_preflight_timeout="2"
seed_dir="/tmp/formtrig_gpac3403_blackwhite_seed"
binding_spec="$repo_root/artifacts/binding_specs/GPAC_3403.native_b6_hevc_annexb_input_candidate.yml"
site_map="/tmp/formtrig_gpac3403_native_env/site_map.tsv"
white_mp4="$repo_root/benchmarks/cve_seeds/gpac/white.mp4"
formtrig_binary="/tmp/formtrig_gpac3403_src/bin/gcc/MP4Box"
plain_binary="/tmp/formtrig_gpac3403_aflpp_plain_asan_src/bin/gcc/MP4Box"
cmplog_binary="/tmp/formtrig_gpac3403_aflpp_cmplog_asan_src/bin/gcc/MP4Box"
afl_fuzz="$repo_root/experiments/aflplusplus/AFLplusplus/afl-fuzz"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
arms="formtrig,aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
out_dir=""
failed_jobs=0
continue_on_fail=0

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Runs matched GPAC_3403 FORMTRIG typedops36 and AFL++-family repetitions from
the same HEVC reached-not-trigger seed corpus and real MP4Box -cat endpoint.

options:
  --duration SEC          per-arm AFL++ budget, default 7200
  --reps N                repetitions per arm, default 3
  --jobs N                concurrent arm runs, default FORMTRIG_JOBS or 1
  --mode MODE             execute|dry-run, default execute
  --out DIR               output directory
  --arms LIST             comma/space-separated arms, default all
  --baselines LIST        comma/space-separated baseline arms for comparison
  --timeout AFL_T         AFL++ -t value, default 5000+
  --typed-ops N           FORMTRIG typed op count, default 36
  --typed-mutation-max N  FORMTRIG_TYPED_MUTATION_MAX, default 64
  --typed-retain-max N    retain up to N typed candidates per rep, default 0/off.
                          signal mode keeps old non-queued signal candidates;
                          hook/all modes also retain queued hook candidates.
  --typed-retain-mode MODE
                          signal|hook|all, default signal. hook also retains
                          hook-generated candidates without immediate D_F
  --typed-retain-endpoint-replay MODE
                          off|on, replay retained candidates through endpoint
                          before packaging, default off
  --typed-retain-endpoint-timeout SEC
                          per retained endpoint replay timeout, default 5
  --typed-retain-endpoint-replays N
                          endpoint replay repetitions per retained candidate,
                          default 1
  --typed-retain-endpoint-max-records N
                          max retained records to endpoint replay, 0 means all,
                          default 0
  --typed-retain-endpoint-selection MODE
                          input-order|best-d-f|op-diverse, default best-d-f
  --typed-retain-endpoint-cmd CMD
                          endpoint replay command; use @@ for retained input,
                          default FORMTRIG MP4Box -cat @@ white.mp4 -out /dev/null
  --typed-retain-endpoint-positive-control FILE
                          optional positive-control input replayed through the
                          same endpoint command
  --seed-dir DIR          HEVC RNT seed corpus
  --binding-spec FILE     FORMTRIG BindingSpec
  --site-map FILE         FORMTRIG native site map
  --white-mp4 FILE        second MP4Box -cat input, default GPAC white.mp4
  --formtrig-binary F     FORMTRIG-instrumented MP4Box
  --plain-binary F        plain AFL++/ASAN MP4Box
  --cmplog-binary F       AFL++ CmpLog/ASAN MP4Box
  --afl-fuzz FILE         AFL++ afl-fuzz
  --monitor-poll SEC      FORMTRIG stats monitor poll, default 10
  --seed-preflight MODE   off|warn|require, default require
  --seed-preflight-max N  max seed preflight replays, default 1
  --seed-preflight-timeout SEC per-seed replay timeout, default 2
  --continue-on-fail      keep summarizing if an arm fails

outputs:
  OUT/run_plan.sh
  OUT/run_plan.jsonl
  OUT/run_metadata.json
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
    echo "one or more GPAC_3403 matched runs failed" >&2
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
    printf ',"duration_s":%s,"typed_ops":%s,"typed_mutation_max":%s,' \
      "$duration" "$typed_ops" "$typed_mutation_max"
    printf '"typed_retain_max":%s,"typed_retain_mode":' "$typed_retain_max"
    json_escape "$typed_retain_mode"
    printf ',"command":'
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

target_cmd_string() {
  quote_cmd "$1" -cat "@@" "$white_mp4" -out /dev/null
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
    --target-cmd "$(target_cmd_string "$plain_binary")"
    --afl-fuzz "$afl_fuzz"
    --memory-limit none
    --mode execute
    --env "AFL_NO_AFFINITY=1"
    --env "ASAN_OPTIONS=abort_on_error=1:detect_leaks=0:symbolize=0"
    --env "UBSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_stacktrace=0"
    --afl-arg=-t
    --afl-arg="$timeout_arg"
  )
  if baseline_needs_cmplog "$baseline"; then
    BASELINE_CMD+=(--cmplog-binary "$cmplog_binary")
  fi
}

formtrig_command_array() {
  local arm="$1"
  local rep="$2"
  local run_out="$3"
  FORMTRIG_CMD=(
    "$repo_root/scripts/run_formtrig_aflpp_campaign.sh"
    --in "$seed_dir"
    --out "$run_out/fuzzer_out"
    --target-bug "$target_id"
    --category lifecycle
    --binding-spec "$binding_spec"
    --site-map "$site_map"
    --duration "$duration"
    --seed-preflight "$seed_preflight"
    --seed-preflight-max "$seed_preflight_max"
    --seed-preflight-timeout "$seed_preflight_timeout"
    --typed-ops "$typed_ops"
    --afl-arg "-t"
    --afl-arg "$timeout_arg"
    --afl-arg "-m"
    --afl-arg "none"
  )
  case "$arm" in
    formtrig)
      ;;
    formtrig_nohook)
      FORMTRIG_CMD+=(--no-mutation-hook)
      ;;
    *)
      echo "unsupported FORMTRIG arm: $arm" >&2
      exit 2
      ;;
  esac
  FORMTRIG_CMD+=(-- "$formtrig_binary" -cat "@@" "$white_mp4" -out /dev/null)
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
  local arm="$1"
  local rep="$2"
  local run_out="$out_dir/runs/${arm}_rep${rep}"
  mkdir -p "$run_out"
  formtrig_command_array "$arm" "$rep" "$run_out"
  local retain_dir="$run_out/typed_retained"
  local -a env_args=(
    "FORMTRIG_TYPED_MUTATION_MAX=$typed_mutation_max"
    "FORMTRIG_STATS_MONITOR_POLL=$monitor_poll"
  )
  if [[ "$typed_retain_max" != "0" ]]; then
    env_args+=(
      "FORMTRIG_TYPED_RETAIN_MAX=$typed_retain_max"
      "FORMTRIG_TYPED_RETAIN_DIR=$retain_dir"
      "FORMTRIG_TYPED_RETAIN_MODE=$typed_retain_mode"
    )
  fi
  local rendered
  rendered="$(quote_cmd "${env_args[@]}") $(quote_cmd "${FORMTRIG_CMD[@]}")"
  record_plan "$arm" "$rep" "formtrig" "$rendered"
  if [[ "$mode" == "dry-run" ]]; then
    return 0
  fi
  {
    printf 'running %s rep%s at %s\n' "$arm" "$rep" "$(date -u +%FT%TZ)"
    printf '%s\n' "$rendered"
    if [[ "$typed_retain_max" != "0" ]]; then
      mkdir -p "$retain_dir"
    fi
    env "${env_args[@]}" "${FORMTRIG_CMD[@]}"
  } > "$run_out/run.log" 2>&1
}

summarize_typed_retained_one() {
  local arm="$1"
  local rep="$2"
  local run_out="$out_dir/runs/${arm}_rep${rep}"
  if [[ "$typed_retain_max" == "0" || ! -d "$run_out" ]]; then
    return 0
  fi
  python3 "$repo_root/tools/summarize_typed_retained_candidates.py" \
    --retain-dir "$run_out/typed_retained" \
    --allow-empty \
    --out-json "$run_out/typed_retained_summary.json" \
    --out-records-jsonl "$run_out/typed_retained_records.jsonl" \
    > "$run_out/typed_retained_summary.stdout"
  local package_records="$run_out/typed_retained_records.jsonl"
  local -a package_args=()
  if [[ "$typed_retain_endpoint_replay" == "on" ]]; then
    local endpoint_cmd="$typed_retain_endpoint_cmd"
    if [[ -z "$endpoint_cmd" ]]; then
      endpoint_cmd="$(target_cmd_string "$formtrig_binary")"
    fi
    local -a replay_args=(
      python3 "$repo_root/tools/replay_gpac3403_typed_retained_endpoint.py"
      --run-dir "$run_out"
      --records-jsonl "$run_out/typed_retained_records.jsonl"
      --endpoint-cmd "$endpoint_cmd"
      --endpoint-timeout "$typed_retain_endpoint_timeout"
      --endpoint-replays "$typed_retain_endpoint_replays"
      --selection "$typed_retain_endpoint_selection"
      --out-summary "$run_out/typed_retained_endpoint_replay_summary.json"
      --out-records-jsonl "$run_out/typed_retained_endpoint_records.jsonl"
    )
    if [[ "$typed_retain_endpoint_max_records" != "0" ]]; then
      replay_args+=(--max-records "$typed_retain_endpoint_max_records")
    fi
    if [[ -n "$typed_retain_endpoint_positive_control" ]]; then
      replay_args+=(--endpoint-positive-control "$typed_retain_endpoint_positive_control")
    fi
    "${replay_args[@]}" > "$run_out/typed_retained_endpoint_replay.stdout"
    package_records="$run_out/typed_retained_endpoint_records.jsonl"
    package_args+=(--endpoint-summary "$run_out/typed_retained_endpoint_replay_summary.json")
  fi
  python3 "$repo_root/tools/package_gpac3403_typed_retained_audit.py" \
    --run-dir "$run_out" \
    --records-jsonl "$package_records" \
    "${package_args[@]}" \
    --out "$run_out/typed_retained_audit_package.json" \
    > "$run_out/typed_retained_audit_package.stdout"
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
  "seed_preflight": "$seed_preflight",
  "site_map": "$site_map",
  "target_id": "$target_id",
  "target_cmd": "$(target_cmd_string "$formtrig_binary")",
  "time_utc": "$(date -u +%FT%TZ)",
  "timeout_oracle": "-t $timeout_arg",
  "typed_mutation_max": $typed_mutation_max,
  "typed_retain_max": $typed_retain_max,
  "typed_retain_mode": "$typed_retain_mode",
  "typed_retain_endpoint_replay": "$typed_retain_endpoint_replay",
  "typed_retain_endpoint_timeout": $typed_retain_endpoint_timeout,
  "typed_retain_endpoint_replays": $typed_retain_endpoint_replays,
  "typed_retain_endpoint_max_records": $typed_retain_endpoint_max_records,
  "typed_retain_endpoint_selection": "$typed_retain_endpoint_selection",
  "typed_retain_endpoint_cmd": $(json_escape "$typed_retain_endpoint_cmd"),
  "typed_retain_endpoint_positive_control": $(json_escape "$typed_retain_endpoint_positive_control"),
  "typed_ops": $typed_ops,
  "white_mp4": "$white_mp4"
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
    --typed-ops)
      typed_ops="${2:-}"
      shift 2
      ;;
    --typed-mutation-max)
      typed_mutation_max="${2:-}"
      shift 2
      ;;
    --typed-retain-max)
      typed_retain_max="${2:-}"
      shift 2
      ;;
    --typed-retain-mode)
      typed_retain_mode="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-replay)
      typed_retain_endpoint_replay="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-timeout)
      typed_retain_endpoint_timeout="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-replays)
      typed_retain_endpoint_replays="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-max-records)
      typed_retain_endpoint_max_records="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-selection)
      typed_retain_endpoint_selection="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-cmd)
      typed_retain_endpoint_cmd="${2:-}"
      shift 2
      ;;
    --typed-retain-endpoint-positive-control)
      typed_retain_endpoint_positive_control="${2:-}"
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
    --white-mp4)
      white_mp4="${2:-}"
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
    --seed-preflight)
      seed_preflight="${2:-}"
      shift 2
      ;;
    --seed-preflight-max)
      seed_preflight_max="${2:-}"
      shift 2
      ;;
    --seed-preflight-timeout)
      seed_preflight_timeout="${2:-}"
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
case "$seed_preflight" in
  off|warn|require)
    ;;
  *)
    echo "--seed-preflight must be off, warn, or require" >&2
    exit 2
    ;;
esac
for numeric in "$duration" "$reps" "$jobs" "$monitor_poll" "$typed_ops" \
  "$typed_mutation_max" "$seed_preflight_max" "$seed_preflight_timeout" \
  "$typed_retain_endpoint_timeout" "$typed_retain_endpoint_replays"; do
  if ! [[ "$numeric" =~ ^[0-9]+$ ]] || [[ "$numeric" -lt 1 ]]; then
    echo "duration, reps, jobs, monitor poll, typed ops, mutation max, seed preflight limits, and endpoint replay limits must be positive integers" >&2
    exit 2
  fi
done
if ! [[ "$typed_retain_max" =~ ^[0-9]+$ ]]; then
  echo "typed retain max must be a non-negative integer" >&2
  exit 2
fi
case "$typed_retain_mode" in
  signal|hook|all)
    ;;
  *)
    echo "--typed-retain-mode must be signal, hook, or all: $typed_retain_mode" >&2
    exit 2
    ;;
esac
if ! [[ "$typed_retain_endpoint_max_records" =~ ^[0-9]+$ ]]; then
  echo "typed retain endpoint max records must be a non-negative integer" >&2
  exit 2
fi
case "$typed_retain_endpoint_replay" in
  off|on)
    ;;
  *)
    echo "--typed-retain-endpoint-replay must be off or on: $typed_retain_endpoint_replay" >&2
    exit 2
    ;;
esac
case "$typed_retain_endpoint_selection" in
  input-order|best-d-f|op-diverse)
    ;;
  *)
    echo "--typed-retain-endpoint-selection must be input-order, best-d-f, or op-diverse: $typed_retain_endpoint_selection" >&2
    exit 2
    ;;
esac

seed_dir="$(abs_path "$seed_dir")"
binding_spec="$(abs_path "$binding_spec")"
white_mp4="$(abs_path "$white_mp4")"
afl_fuzz="$(abs_path "$afl_fuzz")"
if [[ "$site_map" != /* ]]; then site_map="$(abs_path "$site_map")"; fi
if [[ "$formtrig_binary" != /* ]]; then formtrig_binary="$(abs_path "$formtrig_binary")"; fi
if [[ "$plain_binary" != /* ]]; then plain_binary="$(abs_path "$plain_binary")"; fi
if [[ "$cmplog_binary" != /* ]]; then cmplog_binary="$(abs_path "$cmplog_binary")"; fi
if [[ -n "$typed_retain_endpoint_positive_control" && "$typed_retain_endpoint_positive_control" != /* ]]; then
  typed_retain_endpoint_positive_control="$(abs_path "$typed_retain_endpoint_positive_control")"
fi

if [[ -z "$out_dir" ]]; then
  timeout_safe="${timeout_arg//[^A-Za-z0-9]/}"
  out_dir="$repo_root/artifacts/formtrig_native_readiness/raw/gpac3403_b8_typedops${typed_ops}_matched_${duration}s_t${timeout_safe}_${reps}rep_${timestamp}"
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
  require_path "$white_mp4"
  require_path "$formtrig_binary"
  require_path "$plain_binary"
  require_path "$afl_fuzz"
  if [[ -n "$typed_retain_endpoint_positive_control" ]]; then
    require_path "$typed_retain_endpoint_positive_control"
  fi
  for baseline in $(split_list "$baselines"); do
    if baseline_needs_cmplog "$baseline"; then
      require_path "$cmplog_binary"
    fi
  done
fi

for rep in $(seq 1 "$reps"); do
  for arm in $(split_list "$arms"); do
    case "$arm" in
      formtrig|formtrig_nohook)
        if [[ "$mode" == "dry-run" ]]; then
          run_formtrig_one "$arm" "$rep"
        else
          wait_for_job_slot "$jobs"
          run_formtrig_one "$arm" "$rep" &
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
  echo "GPAC_3403 typedops${typed_ops} matched long-run dry-run complete"
  echo "  out=$out_dir"
  echo "  plan=$plan_sh"
  exit 0
fi

for rep in $(seq 1 "$reps"); do
  for arm in $(split_list "$arms"); do
    case "$arm" in
      formtrig|formtrig_nohook)
        summarize_typed_retained_one "$arm" "$rep"
        ;;
      *)
        ;;
    esac
  done
done

for arm in $(split_list "$arms"); do
  case "$arm" in
    formtrig|formtrig_nohook)
      gate_out="$out_dir/${arm}_gate"
      if [[ "$arm" == "formtrig" ]]; then
        gate_out="$out_dir/formtrig_gate"
      fi
      gate_args=(
        "$repo_root/scripts/formtrig_experiment_gate.sh"
        --suite "GPAC_3403_${arm}_typedops${typed_ops}_${duration}s"
        --out "$gate_out"
        --min-runtime "$duration"
      )
      for rep in $(seq 1 "$reps"); do
        if [[ -d "$out_dir/runs/${arm}_rep${rep}/fuzzer_out" ]]; then
          gate_args+=(--run "${arm}_rep${rep}=$out_dir/runs/${arm}_rep${rep}/fuzzer_out")
        fi
      done
      if [[ "${#gate_args[@]}" -gt 7 ]]; then
        if ! "${gate_args[@]}"; then
          if [[ "$continue_on_fail" == "0" ]]; then
            exit 1
          fi
        fi
      fi
      ;;
    *)
      ;;
  esac
done

python3 "$repo_root/tools/summarize_post_reach_baselines.py" \
  --root "$out_dir/runs" \
  --out-json "$out_dir/baseline_summary.json" \
  --out-tsv "$out_dir/baseline_summary.tsv"

if [[ -s "$out_dir/formtrig_gate/gate_summary.csv" &&
      -s "$out_dir/baseline_summary.json" ]]; then
  python3 "$repo_root/tools/compare_formtrig_baselines.py" \
    --comparison-id "gpac3403_typedops${typed_ops}_matched_${duration}s_${reps}rep_${timestamp}" \
    --target-id "$target_id" \
    --formtrig-gate "typedops${typed_ops}=$out_dir/formtrig_gate/gate_summary.csv" \
    --baseline-summary "matched=$out_dir/baseline_summary.json" \
    --out-dir "$out_dir/comparison" \
    --min-reps "$reps" \
    --required-baselines "$baselines"
fi

echo "GPAC_3403 typedops${typed_ops} matched long-run complete"
echo "  out=$out_dir"
echo "  plan=$plan_sh"
echo "  gate=$out_dir/formtrig_gate/gate_summary.csv"
echo "  nohook_gate=$out_dir/formtrig_nohook_gate/gate_summary.csv"
echo "  baseline_summary=$out_dir/baseline_summary.json"
echo "  comparison=$out_dir/comparison/comparison.json"
