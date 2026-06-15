#!/usr/bin/env bash
set -euo pipefail

suite="formtrig_native"
out_dir=""
min_runtime=0
require_terminal=0
terminal_oracle_only=0
declare -a runs=()

usage() {
  cat >&2 <<EOF
usage: $0 --out DIR [options] --run LABEL=DIR [--run LABEL=DIR ...]

Audits completed native FORMTRIG campaign directories and emits a strict
experiment-readiness gate. DIR may be the AFL++ output directory containing
default/ or the default/ directory itself.

options:
  --suite NAME          label written to outputs
  --min-runtime SEC     require fuzzer_stats run_time >= SEC
  --require-terminal    require terminal_triggered_execs > 0
  --terminal-oracle-only
                        validate terminal oracle accounting only; this does not
                        satisfy the strict pre-trigger guidance gate
  --run LABEL=DIR       campaign output to audit, repeatable

outputs:
  OUT/gate_summary.csv
  OUT/gate_summary.jsonl
  OUT/gate_report.md

The strict pre-trigger gate requires:
  - experiment_ready=true
  - pretrigger_lift_guidance_ready=true
  - accepted_non_trigger_progress_events > 0
  - saved_non_trigger_progress_events > 0
  - non_trigger_candidate_lift_delta=true
  - lift_delta_only_on_triggered_candidates=false
  - heuristic/manual lifted event counts are zero
  - binding signal status is pass
EOF
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

jq_value() {
  local file="$1"
  local expr="$2"
  local default_value="${3:-}"
  if [[ -s "$file" ]]; then
    jq -r "$expr // \"$default_value\"" "$file" 2>/dev/null ||
      printf '%s\n' "$default_value"
  else
    printf '%s\n' "$default_value"
  fi
}

jq_number() {
  local file="$1"
  local expr="$2"
  local default_value="${3:-0}"
  if [[ -s "$file" ]]; then
    jq -r "$expr // $default_value" "$file" 2>/dev/null ||
      printf '%s\n' "$default_value"
  else
    printf '%s\n' "$default_value"
  fi
}

stat_value() {
  local file="$1"
  local key="$2"
  local default_value="${3:-0}"
  if [[ -s "$file" ]]; then
    awk -F: -v want="$key" -v default_value="$default_value" '
      {
        key = $1
        gsub(/^[ \t]+|[ \t]+$/, "", key)
      }
      key == want {
        value = $2
        gsub(/^[ \t]+|[ \t]+$/, "", value)
        print value
        found = 1
        exit
      }
      END {
        if (!found) print default_value
      }
    ' "$file"
  else
    printf '%s\n' "$default_value"
  fi
}

add_reason() {
  local reason="$1"
  if [[ -z "$reasons" ]]; then
    reasons="$reason"
  else
    reasons="$reasons;$reason"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --suite)
      suite="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --min-runtime)
      min_runtime="${2:-}"
      shift 2
      ;;
    --require-terminal)
      require_terminal=1
      shift
      ;;
    --terminal-oracle-only)
      terminal_oracle_only=1
      require_terminal=1
      shift
      ;;
    --run)
      runs+=("${2:-}")
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

if [[ -z "$out_dir" || "${#runs[@]}" -eq 0 ]]; then
  usage
  exit 2
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "missing required command: jq" >&2
  exit 2
fi

mkdir -p "$out_dir"
out_dir="$(abs_path "$out_dir")"
summary_csv="$out_dir/gate_summary.csv"
summary_jsonl="$out_dir/gate_summary.jsonl"
report_md="$out_dir/gate_report.md"

printf 'suite,run,status,reasons,run_time,execs_done,execs_per_sec,reached,terminal_triggered,queued_progress,accepted_non_trigger,saved_non_trigger,saved_triggered,spec_lifted,heuristic_lifted,manual_lifted,experiment_ready,pretrigger_lift_guidance_ready,non_trigger_candidate_lift_delta,lift_delta_only_on_triggered,binding_signal_status,binding_signal_diagnosis,out_dir\n' \
  > "$summary_csv"
: > "$summary_jsonl"

pass_count=0
fail_count=0

for run_spec in "${runs[@]}"; do
  if [[ "$run_spec" != *=* ]]; then
    echo "--run must be LABEL=DIR: $run_spec" >&2
    exit 2
  fi
  label="${run_spec%%=*}"
  run_dir="${run_spec#*=}"
  run_dir="$(abs_path "$run_dir")"
  default_dir="$run_dir"
  if [[ ! -f "$default_dir/formtrig_diagnosis.json" &&
        -d "$default_dir/default" ]]; then
    default_dir="$default_dir/default"
  fi

  diagnosis_json="$default_dir/formtrig_diagnosis.json"
  summary_json="$default_dir/formtrig_summary.json"
  binding_signal_json="$default_dir/formtrig_binding_signal_diagnosis.json"
  stats_file="$default_dir/fuzzer_stats"

  status="pass"
  reasons=""

  if [[ ! -s "$diagnosis_json" ]]; then
    status="fail"
    add_reason "missing_diagnosis"
  fi
  if [[ ! -s "$summary_json" ]]; then
    status="fail"
    add_reason "missing_summary"
  fi
  if [[ ! -s "$binding_signal_json" ]]; then
    status="fail"
    add_reason "missing_binding_signal_diagnosis"
  fi
  if [[ ! -s "$stats_file" ]]; then
    status="fail"
    add_reason "missing_fuzzer_stats"
  fi

  experiment_ready="$(jq_value "$diagnosis_json" '.experiment_ready' "false")"
  pretrigger_ready="$(jq_value "$diagnosis_json" \
    '.pretrigger_lift_guidance_ready' "false")"
  non_trigger_delta="$(jq_value "$diagnosis_json" \
    '.non_trigger_candidate_lift_delta' "false")"
  lift_delta_only_on_triggered="$(jq_value "$diagnosis_json" \
    '.lift_delta_only_on_triggered_candidates' "false")"
  binding_signal_status="$(jq_value "$binding_signal_json" '.status' "missing")"
  binding_signal_diagnosis="$(jq_value "$binding_signal_json" \
    '.diagnosis' "")"
  if [[ -z "$binding_signal_diagnosis" ]]; then
    binding_signal_diagnosis="$(jq_value "$diagnosis_json" \
      '.binding_signal_diagnosis' "missing")"
  fi

  accepted_non_trigger="$(jq_number "$binding_signal_json" \
    '.accepted_non_trigger_progress_events' "0")"
  saved_non_trigger="$(jq_number "$diagnosis_json" \
    '.saved_non_trigger_progress_events' "0")"
  saved_triggered="$(jq_number "$diagnosis_json" \
    '.saved_triggered_progress_events' "0")"
  terminal_triggered="$(jq_number "$diagnosis_json" \
    '.terminal_triggered_execs' "0")"
  queued_progress="$(jq_number "$diagnosis_json" \
    '.formtrig_queued_progress' "0")"
  reached="$(jq_number "$diagnosis_json" '.formtrig_reached_execs' "0")"
  spec_lifted="$(jq_number "$diagnosis_json" '.spec_lifted_events' "0")"
  heuristic_lifted="$(jq_number "$diagnosis_json" \
    '.heuristic_lifted_events' "0")"
  manual_lifted="$(jq_number "$diagnosis_json" '.manual_lifted_events' "0")"

  if [[ "$spec_lifted" == "0" ]]; then
    spec_lifted="$(jq_number "$summary_json" '.spec_lifted_events' "0")"
  fi
  if [[ "$heuristic_lifted" == "0" ]]; then
    heuristic_lifted="$(jq_number "$summary_json" \
      '.heuristic_lifted_events' "0")"
  fi
  if [[ "$manual_lifted" == "0" ]]; then
    manual_lifted="$(jq_number "$summary_json" '.manual_lifted_events' "0")"
  fi

  run_time="$(stat_value "$stats_file" run_time 0)"
  execs_done="$(stat_value "$stats_file" execs_done 0)"
  execs_per_sec="$(stat_value "$stats_file" execs_per_sec 0)"

  if [[ "$terminal_oracle_only" != "1" ]]; then
    if [[ "$experiment_ready" != "true" ]]; then
      status="fail"
      add_reason "experiment_not_ready"
    fi
    if [[ "$pretrigger_ready" != "true" ]]; then
      status="fail"
      add_reason "pretrigger_lift_not_ready"
    fi
    if [[ "$accepted_non_trigger" == "0" ]]; then
      status="fail"
      add_reason "no_accepted_non_trigger_progress"
    fi
    if [[ "$saved_non_trigger" == "0" ]]; then
      status="fail"
      add_reason "no_saved_non_trigger_progress"
    fi
    if [[ "$non_trigger_delta" != "true" ]]; then
      status="fail"
      add_reason "no_non_trigger_lift_delta"
    fi
    if [[ "$lift_delta_only_on_triggered" == "true" ]]; then
      status="fail"
      add_reason "lift_delta_only_on_triggered"
    fi
  fi
  if [[ "$heuristic_lifted" != "0" ]]; then
    status="fail"
    add_reason "heuristic_lift_contamination"
  fi
  if [[ "$manual_lifted" != "0" ]]; then
    status="fail"
    add_reason "manual_lift_contamination"
  fi
  if [[ "$binding_signal_status" != "pass" ]]; then
    status="fail"
    add_reason "binding_signal_status_not_pass"
  fi
  if [[ "$run_time" =~ ^[0-9]+$ && "$min_runtime" =~ ^[0-9]+$ ]]; then
    if (( run_time < min_runtime )); then
      status="fail"
      add_reason "runtime_below_minimum"
    fi
  fi
  if [[ "$require_terminal" == "1" && "$terminal_triggered" == "0" ]]; then
    status="fail"
    add_reason "terminal_not_triggered"
  fi
  [[ -z "$reasons" ]] && reasons="ok"

  if [[ "$status" == "pass" ]]; then
    pass_count=$((pass_count + 1))
  else
    fail_count=$((fail_count + 1))
  fi

  {
    csv_escape "$suite"; printf ','
    csv_escape "$label"; printf ','
    csv_escape "$status"; printf ','
    csv_escape "$reasons"; printf ','
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,' \
      "$run_time" "$execs_done" "$execs_per_sec" "$reached" \
      "$terminal_triggered" "$queued_progress" "$accepted_non_trigger" \
      "$saved_non_trigger" "$saved_triggered" "$spec_lifted" \
      "$heuristic_lifted" "$manual_lifted"
    csv_escape "$experiment_ready"; printf ','
    csv_escape "$pretrigger_ready"; printf ','
    csv_escape "$non_trigger_delta"; printf ','
    csv_escape "$lift_delta_only_on_triggered"; printf ','
    csv_escape "$binding_signal_status"; printf ','
    csv_escape "$binding_signal_diagnosis"; printf ','
    csv_escape "$default_dir"; printf '\n'
  } >> "$summary_csv"

  {
    printf '{"suite":'
    json_escape "$suite"
    printf ',"run":'
    json_escape "$label"
    printf ',"status":'
    json_escape "$status"
    printf ',"reasons":'
    json_escape "$reasons"
    printf ',"run_time":%s,"execs_done":%s,"execs_per_sec":' \
      "$run_time" "$execs_done"
    json_escape "$execs_per_sec"
    printf ',"reached":%s,"terminal_triggered":%s,"queued_progress":%s,' \
      "$reached" "$terminal_triggered" "$queued_progress"
    printf '"accepted_non_trigger":%s,"saved_non_trigger":%s,' \
      "$accepted_non_trigger" "$saved_non_trigger"
    printf '"saved_triggered":%s,"spec_lifted":%s,' \
      "$saved_triggered" "$spec_lifted"
    printf '"heuristic_lifted":%s,"manual_lifted":%s,' \
      "$heuristic_lifted" "$manual_lifted"
    printf '"experiment_ready":%s,"pretrigger_lift_guidance_ready":%s,' \
      "$experiment_ready" "$pretrigger_ready"
    printf '"non_trigger_candidate_lift_delta":%s,' "$non_trigger_delta"
    printf '"lift_delta_only_on_triggered":%s,' "$lift_delta_only_on_triggered"
    printf '"binding_signal_status":'
    json_escape "$binding_signal_status"
    printf ',"binding_signal_diagnosis":'
    json_escape "$binding_signal_diagnosis"
    printf ',"out_dir":'
    json_escape "$default_dir"
    printf '}\n'
  } >> "$summary_jsonl"
done

{
  printf '# FORMTRIG Experiment Gate\n\n'
  printf -- '- Suite: `%s`\n' "$suite"
  printf -- '- Runs: `%s`\n' "${#runs[@]}"
  printf -- '- Pass: `%s`\n' "$pass_count"
  printf -- '- Fail: `%s`\n' "$fail_count"
  if [[ "$terminal_oracle_only" == "1" ]]; then
    printf -- '- Mode: `terminal_oracle_only`\n'
  else
    printf -- '- Mode: `strict_pretrigger`\n'
  fi
  printf -- '- Require terminal: `%s`\n' "$require_terminal"
  printf -- '- Minimum runtime: `%s`\n\n' "$min_runtime"
  printf '## Summary\n\n'
  printf '| run | status | reasons | run_time | exec/s | reached | terminal | accepted_non_trigger | saved_non_trigger |\n'
  printf '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n'
  tail -n +2 "$summary_csv" | while IFS=, read -r _suite run status reasons \
      run_time _execs_done execs_per_sec reached terminal _queued accepted \
      saved _saved_triggered _spec _heur _manual _ready _pre _delta _only \
      _binding_status _binding_diag _out; do
    run="${run%\"}"; run="${run#\"}"
    status="${status%\"}"; status="${status#\"}"
    reasons="${reasons%\"}"; reasons="${reasons#\"}"
    printf '| `%s` | `%s` | `%s` | %s | %s | %s | %s | %s | %s |\n' \
      "$run" "$status" "$reasons" "$run_time" "$execs_per_sec" \
      "$reached" "$terminal" "$accepted" "$saved"
  done
} > "$report_md"

echo "FORMTRIG experiment gate complete"
echo "  out=$out_dir"
echo "  summary_csv=$summary_csv"
echo "  summary_jsonl=$summary_jsonl"
echo "  report=$report_md"

if [[ "$fail_count" -ne 0 ]]; then
  exit 1
fi
