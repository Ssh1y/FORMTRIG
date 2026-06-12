#!/usr/bin/env bash
set -euo pipefail

seed_dir=""
out_json=""
target_bug=""
target_site_ids=""
lift_spec=""
max_seeds="32"
timeout_s="2"

usage() {
  cat >&2 <<EOF
usage: $0 --in DIR --out FILE [options] -- TARGET [ARGS...]

Replays seed corpus entries through a native FORMTRIG target before a campaign
starts. The output explains whether the corpus already contains a reached,
non-trigger seed with spec-driven lifted signal.

options:
  --target-bug LABEL       FORMTRIG_TARGET_BUG value
  --target-site-ids IDS    comma-separated source-site ids
  --lift-spec FILE         normalized FORMTRIG_LIFT_SPEC file
  --max-seeds N            maximum seeds to replay, default 32
  --timeout SEC            per-seed timeout, default 2

The target command may contain @@. If it does not, each seed is sent on stdin.
EOF
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

json_bool() {
  if [[ "$1" -ne 0 ]]; then
    printf 'true'
  else
    printf 'false'
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --in)
      seed_dir="${2:-}"
      shift 2
      ;;
    --out)
      out_json="${2:-}"
      shift 2
      ;;
    --target-bug)
      target_bug="${2:-}"
      shift 2
      ;;
    --target-site-ids)
      target_site_ids="${2:-}"
      shift 2
      ;;
    --lift-spec)
      lift_spec="${2:-}"
      shift 2
      ;;
    --max-seeds)
      max_seeds="${2:-}"
      shift 2
      ;;
    --timeout)
      timeout_s="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$seed_dir" || -z "$out_json" || $# -eq 0 ]]; then
  usage
  exit 2
fi

require_file "$seed_dir"
if [[ -n "$lift_spec" ]]; then
  require_file "$lift_spec"
fi

case "$max_seeds" in
  ''|*[!0-9]*)
    echo "--max-seeds must be a positive integer" >&2
    exit 2
    ;;
esac
if [[ "$max_seeds" -le 0 ]]; then
  echo "--max-seeds must be positive" >&2
  exit 2
fi

mkdir -p "$(dirname "$out_json")"
log_dir="${out_json%.json}.logs"
rm -rf "$log_dir"
mkdir -p "$log_dir"

env_args=(
  FORMTRIG_LOG=
  FORMTRIG_PUBLISH_EAGER=1
)
if [[ -n "$target_bug" ]]; then
  env_args+=(FORMTRIG_TARGET_BUG="$target_bug")
fi
if [[ -n "$target_site_ids" ]]; then
  env_args+=(FORMTRIG_TARGET_SITE_IDS="$target_site_ids")
fi
if [[ -n "$lift_spec" ]]; then
  env_args+=(FORMTRIG_LIFT_SPEC="$lift_spec")
fi

total=0
replayed=0
runtime_logs=0
missing_logs=0
timeout_count=0
reached_count=0
triggered_count=0
rnt_count=0
spec_lifted_count=0
heuristic_lifted_count=0
manual_lifted_count=0
component_count=0
atom_signal_count=0
role_signal_count=0

tmp_out="$out_json.tmp.$$"
exec 3>"$tmp_out"
printf '{\n' >&3
printf '  "seeds": [\n' >&3

seed_index=0
first_record=1
while IFS= read -r seed; do
  if [[ "$seed_index" -ge "$max_seeds" ]]; then
    break
  fi
  seed_index=$((seed_index + 1))
  total=$((total + 1))

  runtime_log="$log_dir/seed_${seed_index}.runtime.jsonl"
  stdout_log="$log_dir/seed_${seed_index}.stdout"
  stderr_log="$log_dir/seed_${seed_index}.stderr"

  run_cmd=()
  used_at=0
  for arg in "$@"; do
    if [[ "$arg" == *@@* ]]; then
      run_cmd+=("${arg//@@/$seed}")
      used_at=1
    else
      run_cmd+=("$arg")
    fi
  done

  replayed=$((replayed + 1))
  exit_code=0
  timed_out=0
  seed_env=("${env_args[@]}")
  seed_env[0]="FORMTRIG_LOG=$runtime_log"

  set +e
  if [[ "$used_at" -eq 1 ]]; then
    env "${seed_env[@]}" timeout -k 1 "$timeout_s" \
      "${run_cmd[@]}" >"$stdout_log" 2>"$stderr_log"
    exit_code=$?
  else
    env "${seed_env[@]}" timeout -k 1 "$timeout_s" \
      "${run_cmd[@]}" <"$seed" >"$stdout_log" 2>"$stderr_log"
    exit_code=$?
  fi
  set -e

  if [[ "$exit_code" -eq 124 || "$exit_code" -eq 137 ]]; then
    timed_out=1
    timeout_count=$((timeout_count + 1))
  fi

  reached=0
  triggered=0
  spec_lifted=0
  heuristic_lifted=0
  manual_lifted=0
  components=0
  atom_signals=0
  role_signals=0

  if [[ -s "$runtime_log" ]]; then
    runtime_logs=$((runtime_logs + 1))
    last_line="$(tail -n 1 "$runtime_log")"
    if grep -q '"reached":true' <<< "$last_line"; then
      reached=1
      reached_count=$((reached_count + 1))
    fi
    if grep -q '"crash_predicate":true' <<< "$last_line" ||
       grep -q '"triggered":true' <<< "$last_line"; then
      triggered=1
      triggered_count=$((triggered_count + 1))
    fi
    if grep -q '"uses_spec_lifted":true' <<< "$last_line"; then
      spec_lifted=1
      spec_lifted_count=$((spec_lifted_count + 1))
    fi
    if grep -q '"uses_runtime_heuristic":true' <<< "$last_line"; then
      heuristic_lifted=1
      heuristic_lifted_count=$((heuristic_lifted_count + 1))
    fi
    if grep -q '"uses_manual_target":true' <<< "$last_line"; then
      manual_lifted=1
      manual_lifted_count=$((manual_lifted_count + 1))
    fi
    if grep -q '"components":\[{' <<< "$last_line"; then
      components=1
      component_count=$((component_count + 1))
    fi
    if grep -q '"atom_signals":\[{' <<< "$last_line"; then
      atom_signals=1
      atom_signal_count=$((atom_signal_count + 1))
    fi
    if grep -q '"role_bits":[1-9]' <<< "$last_line"; then
      role_signals=1
      role_signal_count=$((role_signal_count + 1))
    fi
  else
    missing_logs=$((missing_logs + 1))
  fi

  if [[ "$reached" -eq 1 && "$triggered" -eq 0 ]]; then
    rnt=1
    rnt_count=$((rnt_count + 1))
  else
    rnt=0
  fi

  if [[ "$first_record" -eq 0 ]]; then
    printf ',\n' >&3
  fi
  first_record=0
  printf '    {' >&3
  printf '"seed":"%s",' "$(json_escape "$seed")" >&3
  printf '"exit_code":%d,' "$exit_code" >&3
  printf '"timed_out":%s,' "$(json_bool "$timed_out")" >&3
  printf '"runtime_log":"%s",' "$(json_escape "$runtime_log")" >&3
  printf '"reached":%s,' "$(json_bool "$reached")" >&3
  printf '"triggered":%s,' "$(json_bool "$triggered")" >&3
  printf '"rnt":%s,' "$(json_bool "$rnt")" >&3
  printf '"spec_lifted":%s,' "$(json_bool "$spec_lifted")" >&3
  printf '"heuristic_lifted":%s,' "$(json_bool "$heuristic_lifted")" >&3
  printf '"manual_lifted":%s,' "$(json_bool "$manual_lifted")" >&3
  printf '"components":%s,' "$(json_bool "$components")" >&3
  printf '"atom_signals":%s,' "$(json_bool "$atom_signals")" >&3
  printf '"role_signals":%s' "$(json_bool "$role_signals")" >&3
  printf '}' >&3
done < <(find "$seed_dir" -maxdepth 1 -type f | sort)

if [[ "$first_record" -eq 0 ]]; then
  printf '\n' >&3
fi
printf '  ],\n' >&3

status="pass"
diagnosis="ready"
if [[ "$total" -eq 0 ]]; then
  status="fail"
  diagnosis="no_seed_files"
elif [[ "$runtime_logs" -eq 0 ]]; then
  status="fail"
  diagnosis="no_formtrig_runtime_signal"
elif [[ "$reached_count" -eq 0 ]]; then
  status="fail"
  diagnosis="seed_does_not_reach_target"
elif [[ "$rnt_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_reached_non_trigger_seed"
elif [[ -n "$lift_spec" && "$spec_lifted_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_spec_lifted_signal"
elif [[ "$heuristic_lifted_count" -ne 0 ]]; then
  status="fail"
  diagnosis="heuristic_lift_used"
elif [[ "$manual_lifted_count" -ne 0 ]]; then
  status="fail"
  diagnosis="manual_target_lift_used"
elif [[ -n "$lift_spec" && "$component_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_lifted_components"
elif [[ -n "$lift_spec" && "$atom_signal_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_atom_signal"
elif [[ -n "$lift_spec" && "$role_signal_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_role_signal"
fi

printf '  "status": "%s",\n' "$status" >&3
printf '  "diagnosis": "%s",\n' "$diagnosis" >&3
printf '  "total_seeds": %d,\n' "$total" >&3
printf '  "replayed_seeds": %d,\n' "$replayed" >&3
printf '  "runtime_logs": %d,\n' "$runtime_logs" >&3
printf '  "missing_runtime_logs": %d,\n' "$missing_logs" >&3
printf '  "timeouts": %d,\n' "$timeout_count" >&3
printf '  "reached": %d,\n' "$reached_count" >&3
printf '  "triggered": %d,\n' "$triggered_count" >&3
printf '  "rnt": %d,\n' "$rnt_count" >&3
printf '  "spec_lifted": %d,\n' "$spec_lifted_count" >&3
printf '  "heuristic_lifted": %d,\n' "$heuristic_lifted_count" >&3
printf '  "manual_lifted": %d,\n' "$manual_lifted_count" >&3
printf '  "components": %d,\n' "$component_count" >&3
printf '  "atom_signals": %d,\n' "$atom_signal_count" >&3
printf '  "role_signals": %d\n' "$role_signal_count" >&3
printf '}\n' >&3
exec 3>&-
mv "$tmp_out" "$out_json"

if [[ "$status" == "pass" ]]; then
  exit 0
fi
exit 1
