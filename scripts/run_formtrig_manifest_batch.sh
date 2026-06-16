#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat >&2 <<EOF
usage: $0 [options] <manifest> [manifest...]

Runs native FORMTRIG manifests and writes a batch summary.

Options:
  --manifest-list FILE    newline-delimited manifest paths
  --duration SEC          override each manifest duration
  --out-root DIR          override each manifest out_dir as DIR/<target_id>
  --jobs N                run up to N manifests concurrently (default: 1)
  --stop-on-trigger       stop the batch after the first triggered target
                           (requires --jobs 1)
  --continue-on-fail      keep running after manifest failures

Outputs:
  <out-root>/batch_summary.csv
  <out-root>/batch_summary.jsonl
  <out-root>/<target_id>/batch_run.log                 # --jobs 1
  <out-root>/<index>_<target_id>/batch_run.log         # --jobs N
EOF
}

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

abs_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s' "$path"
  else
    printf '%s/%s' "$PWD" "$path"
  fi
}

manifest_value() {
  local manifest="$1"
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
  ' "$manifest" | tail -n 1
}

json_string() {
  local path="$1"
  local key="$2"
  awk -v key="\"$key\"" '
    index($0, key) {
      line = $0
      sub(".*" key "[[:space:]]*:[[:space:]]*\"", "", line)
      sub("\".*", "", line)
      print line
      exit
    }
  ' "$path"
}

json_number() {
  local path="$1"
  local key="$2"
  awk -v key="\"$key\"" '
    index($0, key) {
      line = $0
      sub(".*" key "[[:space:]]*:[[:space:]]*", "", line)
      sub("[,}].*", "", line)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
      print line
      exit
    }
  ' "$path"
}

csv_escape() {
  local value="${1:-}"
  value="${value//\"/\"\"}"
  printf '"%s"' "$value"
}

json_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "$value"
}

manifest_list=""
duration_override=""
out_root=""
stop_on_trigger=0
continue_on_fail=0
jobs=1
declare -a manifests

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest-list)
      manifest_list="${2:-}"
      shift 2
      ;;
    --duration)
      duration_override="${2:-}"
      shift 2
      ;;
    --out-root)
      out_root="${2:-}"
      shift 2
      ;;
    --jobs)
      jobs="${2:-}"
      shift 2
      ;;
    --stop-on-trigger)
      stop_on_trigger=1
      shift
      ;;
    --continue-on-fail)
      continue_on_fail=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      usage
      exit 2
      ;;
    *)
      manifests+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$manifest_list" ]]; then
  if [[ ! -f "$manifest_list" ]]; then
    echo "missing manifest list: $manifest_list" >&2
    exit 2
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="$(trim "$line")"
    [[ -z "$line" ]] && continue
    manifests+=("$line")
  done < "$manifest_list"
fi

if [[ "${#manifests[@]}" -eq 0 ]]; then
  usage
  exit 2
fi

if ! [[ "$jobs" =~ ^[0-9]+$ ]] || [[ "$jobs" -lt 1 ]]; then
  echo "--jobs must be a positive integer: $jobs" >&2
  exit 2
fi
if [[ "$jobs" -gt 1 && "$stop_on_trigger" -eq 1 ]]; then
  echo "--stop-on-trigger requires --jobs 1" >&2
  exit 2
fi

if [[ -z "$out_root" ]]; then
  out_root="$repo_root/results/formtrig_native_batch/$(date -u +%Y%m%dT%H%M%SZ)"
else
  out_root="$(abs_path "$out_root")"
fi
mkdir -p "$out_root"
result_root="$out_root/.batch_results"
mkdir -p "$result_root"

summary_csv="$out_root/batch_summary.csv"
summary_jsonl="$out_root/batch_summary.jsonl"
printf 'manifest,target_id,status,experiment_ready,pretrigger_lift_guidance_ready,diagnosis,progress_status,has_non_trigger_progress,non_trigger_progress,saved_non_trigger_progress,saved_triggered_progress,execs_done,reached,triggered,queued_progress,spec_lifted,heuristic_lifted,manual_lifted,d_f_constant,out_dir,log\n' > "$summary_csv"
: > "$summary_jsonl"

failures=0
trigger_seen=0

write_manifest_result() {
  local result_base="$1"
  local manifest="$2"
  local target_id="$3"
  local status="$4"
  local experiment_ready="$5"
  local pretrigger_lift_guidance_ready="$6"
  local diagnosis="$7"
  local progress_status="$8"
  local has_non_trigger_progress="$9"
  local non_trigger_progress="${10}"
  local saved_non_trigger="${11}"
  local saved_triggered="${12}"
  local execs_done="${13}"
  local reached="${14}"
  local triggered="${15}"
  local queued="${16}"
  local spec="${17}"
  local heuristic="${18}"
  local manual="${19}"
  local d_f_constant="${20}"
  local out_dir="${21}"
  local log="${22}"

  {
    csv_escape "$manifest"; printf ','
    csv_escape "$target_id"; printf ','
    csv_escape "$status"; printf ','
    csv_escape "$experiment_ready"; printf ','
    csv_escape "$pretrigger_lift_guidance_ready"; printf ','
    csv_escape "$diagnosis"; printf ','
    csv_escape "$progress_status"; printf ','
    csv_escape "$has_non_trigger_progress"; printf ','
    printf '%s,%s,%s,' "$non_trigger_progress" "$saved_non_trigger" \
      "$saved_triggered"
    printf '%s,%s,%s,%s,%s,%s,%s,' "$execs_done" "$reached" "$triggered" \
      "$queued" "$spec" "$heuristic" "$manual"
    csv_escape "$d_f_constant"; printf ','
    csv_escape "$out_dir"; printf ','
    csv_escape "$log"; printf '\n'
  } > "$result_base.csv"

  {
    printf '{"manifest":'
    json_escape "$manifest"
    printf ',"target_id":'
    json_escape "$target_id"
    printf ',"status":'
    json_escape "$status"
    printf ',"experiment_ready":'
    json_escape "$experiment_ready"
    printf ',"pretrigger_lift_guidance_ready":%s' \
      "$pretrigger_lift_guidance_ready"
    printf ',"diagnosis":'
    json_escape "$diagnosis"
    printf ',"progress_status":'
    json_escape "$progress_status"
    printf ',"has_non_trigger_progress":%s,"non_trigger_progress":%s,"saved_non_trigger_progress":%s,"saved_triggered_progress":%s,"execs_done":%s,"reached":%s,"triggered":%s,"queued_progress":%s,"spec_lifted":%s,"heuristic_lifted":%s,"manual_lifted":%s,"out_dir":' \
      "$has_non_trigger_progress" "$non_trigger_progress" \
      "$saved_non_trigger" "$saved_triggered" "$execs_done" "$reached" \
      "$triggered" "$queued" "$spec" "$heuristic" "$manual"
    json_escape "$out_dir"
    printf ',"log":'
    json_escape "$log"
    printf '}\n'
  } > "$result_base.jsonl"

  printf '%s\n' "$status" > "$result_base.status"
  printf '%s\n' "$triggered" > "$result_base.triggered"
}

run_one_manifest() {
  local index="$1"
  local manifest="$2"
  local result_base="$result_root/$(printf '%03d' "$index")"

  manifest="$(abs_path "$manifest")"
  if [[ ! -f "$manifest" ]]; then
    echo "missing manifest: $manifest" >&2
    write_manifest_result "$result_base" "$manifest" "$(basename "$manifest")" \
      "missing_manifest" "false" "false" "missing_manifest" "unknown" \
      "false" 0 0 0 0 0 0 0 0 0 0 "unknown" "" ""
    return 2
  fi

  target_id="$(manifest_value "$manifest" target_id)"
  if [[ -z "$target_id" ]]; then
    target_id="$(basename "$manifest")"
    target_id="${target_id%.*}"
  fi

  run_dir="$out_root/$target_id"
  if [[ "$jobs" -gt 1 ]]; then
    run_dir="$out_root/$(printf '%03d_%s' "$index" "$target_id")"
  fi
  mkdir -p "$run_dir"
  run_manifest="$run_dir/batch.manifest"
  cp "$manifest" "$run_manifest"
  if [[ -n "$duration_override" ]]; then
    printf '\nduration: %s\n' "$duration_override" >> "$run_manifest"
  fi
  printf '\nout_dir: %s\n' "$run_dir/out" >> "$run_manifest"

  log="$run_dir/batch_run.log"
  status="ok"
  if ! "$repo_root/scripts/run_formtrig_native_manifest.sh" "$run_manifest" \
      > "$log" 2>&1; then
    status="runner_failed"
  fi

  diagnosis_path="$run_dir/out/default/formtrig_diagnosis.json"
  summary_path="$run_dir/out/default/formtrig_summary.json"
  experiment_ready="false"
  diagnosis="missing_diagnosis"
  progress_status="unknown"
  pretrigger_lift_guidance_ready="false"
  has_non_trigger_progress="false"
  non_trigger_progress=0
  saved_non_trigger=0
  saved_triggered=0
  execs_done=0
  reached=0
  triggered=0
  queued=0
  spec=0
  heuristic=0
  manual=0
  d_f_constant="unknown"

  if [[ -f "$diagnosis_path" ]]; then
    diagnosis="$(json_string "$diagnosis_path" diagnosis)"
    experiment_ready="$(json_string "$diagnosis_path" experiment_ready)"
    [[ -z "$(trim "$experiment_ready")" ]] &&
      experiment_ready="$(json_number "$diagnosis_path" experiment_ready)"
    progress_status="$(json_string "$diagnosis_path" progress_status)"
    pretrigger_lift_guidance_ready="$(json_string "$diagnosis_path" pretrigger_lift_guidance_ready)"
    [[ -z "$(trim "$pretrigger_lift_guidance_ready")" ]] &&
      pretrigger_lift_guidance_ready="$(json_number "$diagnosis_path" pretrigger_lift_guidance_ready)"
    has_non_trigger_progress="$(json_string "$diagnosis_path" has_non_trigger_progress)"
    [[ -z "$(trim "$has_non_trigger_progress")" ]] &&
      has_non_trigger_progress="$(json_number "$diagnosis_path" has_non_trigger_progress)"
  fi
  if [[ -f "$summary_path" ]]; then
    non_trigger_progress="$(json_number "$summary_path" non_trigger_progress_events)"
    saved_non_trigger="$(json_number "$summary_path" saved_non_trigger_progress_events)"
    saved_triggered="$(json_number "$summary_path" saved_triggered_progress_events)"
    execs_done="$(json_number "$summary_path" execs_done)"
    reached="$(json_number "$summary_path" formtrig_reached_execs)"
    triggered="$(json_number "$summary_path" formtrig_triggered_execs)"
    queued="$(json_number "$summary_path" formtrig_queued_progress)"
    spec="$(json_number "$summary_path" spec_lifted_events)"
    heuristic="$(json_number "$summary_path" heuristic_lifted_events)"
    manual="$(json_number "$summary_path" manual_lifted_events)"
    d_f_constant="$(json_number "$summary_path" d_f_constant)"
  fi

  [[ -z "$diagnosis" ]] && diagnosis="unknown"
  [[ -z "$progress_status" ]] && progress_status="unknown"
  [[ -z "$pretrigger_lift_guidance_ready" ]] && pretrigger_lift_guidance_ready="false"
  [[ -z "$has_non_trigger_progress" ]] && has_non_trigger_progress="false"
  [[ -z "$non_trigger_progress" ]] && non_trigger_progress=0
  [[ -z "$saved_non_trigger" ]] && saved_non_trigger=0
  [[ -z "$saved_triggered" ]] && saved_triggered=0
  [[ -z "$execs_done" ]] && execs_done=0
  [[ -z "$reached" ]] && reached=0
  [[ -z "$triggered" ]] && triggered=0
  [[ -z "$queued" ]] && queued=0
  [[ -z "$spec" ]] && spec=0
  [[ -z "$heuristic" ]] && heuristic=0
  [[ -z "$manual" ]] && manual=0
  [[ -z "$d_f_constant" ]] && d_f_constant="unknown"

  write_manifest_result "$result_base" "$manifest" "$target_id" "$status" \
    "$experiment_ready" "$pretrigger_lift_guidance_ready" "$diagnosis" \
    "$progress_status" "$has_non_trigger_progress" "$non_trigger_progress" \
    "$saved_non_trigger" "$saved_triggered" "$execs_done" "$reached" \
    "$triggered" "$queued" "$spec" "$heuristic" "$manual" "$d_f_constant" \
    "$run_dir/out" "$log"

  [[ "$status" == "ok" ]]
}

append_result() {
  local index="$1"
  local result_base="$result_root/$(printf '%03d' "$index")"
  [[ -f "$result_base.csv" ]] && cat "$result_base.csv" >> "$summary_csv"
  [[ -f "$result_base.jsonl" ]] && cat "$result_base.jsonl" >> "$summary_jsonl"

  local status="missing_result"
  local triggered=0
  [[ -f "$result_base.status" ]] && status="$(<"$result_base.status")"
  [[ -f "$result_base.triggered" ]] && triggered="$(<"$result_base.triggered")"

  if [[ "$status" != "ok" ]]; then
    failures=$((failures + 1))
  fi

  if [[ "$triggered" != "0" && "$triggered" != "null" ]]; then
    trigger_seen=1
  fi

  [[ "$status" == "ok" ]]
}

wait_for_job_slot() {
  local max_jobs="$1"
  while (( $(jobs -pr | wc -l) >= max_jobs )); do
    wait -n || true
  done
}

wait_for_all_jobs() {
  while (( $(jobs -pr | wc -l) > 0 )); do
    wait -n || true
  done
}

if [[ "$jobs" -gt 1 ]]; then
  idx=0
  for manifest in "${manifests[@]}"; do
    idx=$((idx + 1))
    wait_for_job_slot "$jobs"
    run_one_manifest "$idx" "$manifest" &
  done
  wait_for_all_jobs

  idx=0
  for _manifest in "${manifests[@]}"; do
    idx=$((idx + 1))
    append_result "$idx" || true
  done
else
  idx=0
  for manifest in "${manifests[@]}"; do
    idx=$((idx + 1))
    run_one_manifest "$idx" "$manifest" || true
    append_result "$idx" || true

    if [[ "$trigger_seen" -eq 1 && "$stop_on_trigger" -eq 1 ]]; then
      break
    fi
    if [[ "$failures" -ne 0 && "$continue_on_fail" -ne 1 ]]; then
      break
    fi
  done
fi

echo "FORMTRIG manifest batch complete"
echo "  out_root=$out_root"
echo "  summary_csv=$summary_csv"
echo "  summary_jsonl=$summary_jsonl"

if [[ "$failures" -ne 0 ]]; then
  exit 1
fi
if [[ "$trigger_seen" -eq 1 ]]; then
  exit 0
fi
