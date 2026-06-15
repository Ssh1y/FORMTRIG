#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
seed_dir=""
out_json=""
target_bug=""
target_site_ids=""
lift_spec=""
max_seeds="32"
timeout_s="2"
shm_magic_expected="$((0x46545249))"
shm_version_expected="$(awk '
  $1 == "#define" && $2 == "FORMTRIG_SHM_VERSION" {
    gsub(/u$/, "", $3);
    print $3;
    exit;
  }
' "$repo_root/formtrig/include/formtrig/formtrig_abi.h")"

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

pre_reach_events=0
if [[ -n "$lift_spec" ]] &&
   grep -Eq '(^|[[:space:],])(pre_reach|pre-reach|before_reach|before-reach|any|both)([[:space:],]|$)' "$lift_spec"; then
  pre_reach_events=1
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
spec_df_values="$log_dir/spec_d_f_values.txt"
: > "$spec_df_values"

env_args=(
  FORMTRIG_LOG=
  FORMTRIG_PUBLISH_EAGER=1
  FORMTRIG_ALLOW_HEURISTIC_LIFT=0
  FORMTRIG_OBSERVE_HEURISTIC_LIFT=0
  FORMTRIG_ALLOW_MANUAL_LIFT=0
  FORMTRIG_PRE_REACH_EVENTS="$pre_reach_events"
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
observed_heuristic_lifted_count=0
observed_manual_lifted_count=0
component_count=0
atom_signal_count=0
role_signal_count=0
shm_seen_count=0
shm_abi_ok_count=0
shm_abi_mismatch_count=0

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
  shm_name="/formtrig_seed_readiness_${$}_${seed_index}"
  shm_path="/dev/shm${shm_name}"
  rm -f "$shm_path"
  dd if=/dev/zero of="$shm_path" bs=4096 count=1 status=none

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
  seed_env+=("__FORMTRIG_SHM_FILE=$shm_name")

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

  shm_magic=0
  shm_version=0
  shm_seen=0
  shm_abi_ok=0
  if [[ -e "$shm_path" ]]; then
    read -r shm_magic shm_version < <(od -An -N8 -tu4 "$shm_path")
    if [[ "${shm_magic:-0}" -eq "$shm_magic_expected" ]]; then
      shm_seen=1
      shm_seen_count=$((shm_seen_count + 1))
      if [[ "${shm_version:-0}" -eq "$shm_version_expected" ]]; then
        shm_abi_ok=1
        shm_abi_ok_count=$((shm_abi_ok_count + 1))
      else
        shm_abi_mismatch_count=$((shm_abi_mismatch_count + 1))
      fi
    fi
  fi
  rm -f "$shm_path"

  if [[ "$exit_code" -eq 124 || "$exit_code" -eq 137 ]]; then
    timed_out=1
    timeout_count=$((timeout_count + 1))
  fi

  reached=0
  triggered=0
  spec_lifted=0
  heuristic_lifted=0
  manual_lifted=0
  observed_heuristic_lifted=0
  observed_manual_lifted=0
  components=0
  atom_signals=0
  role_signals=0
  spec_df_value=""

  if [[ -s "$runtime_log" ]]; then
    runtime_logs=$((runtime_logs + 1))
    last_line="$(tail -n 1 "$runtime_log")"
    spec_df_value="$(
      sed -n 's/.*"D_F_spec_lifted":\([^,}]*\).*/\1/p' <<< "$last_line" |
        head -n 1
    )"
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
    if grep -q '"observed_runtime_heuristic":true' <<< "$last_line"; then
      observed_heuristic_lifted=1
      observed_heuristic_lifted_count=$((observed_heuristic_lifted_count + 1))
    fi
    if grep -q '"uses_manual_target":true' <<< "$last_line"; then
      manual_lifted=1
      manual_lifted_count=$((manual_lifted_count + 1))
    fi
    if grep -q '"observed_manual_target":true' <<< "$last_line"; then
      observed_manual_lifted=1
      observed_manual_lifted_count=$((observed_manual_lifted_count + 1))
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
  if [[ "$rnt" -eq 1 && "$spec_lifted" -eq 1 &&
        -n "$spec_df_value" && "$spec_df_value" != "null" ]]; then
    printf '%s\n' "$spec_df_value" >> "$spec_df_values"
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
  printf '"observed_heuristic_lifted":%s,' "$(json_bool "$observed_heuristic_lifted")" >&3
  printf '"observed_manual_lifted":%s,' "$(json_bool "$observed_manual_lifted")" >&3
  printf '"shm_seen":%s,' "$(json_bool "$shm_seen")" >&3
  printf '"shm_abi_ok":%s,' "$(json_bool "$shm_abi_ok")" >&3
  printf '"shm_magic":%s,' "${shm_magic:-0}" >&3
  printf '"shm_version":%s,' "${shm_version:-0}" >&3
  printf '"components":%s,' "$(json_bool "$components")" >&3
  printf '"atom_signals":%s,' "$(json_bool "$atom_signals")" >&3
  printf '"role_signals":%s' "$(json_bool "$role_signals")" >&3
  printf '}' >&3
done < <(find "$seed_dir" -maxdepth 1 -type f | sort)

if [[ "$first_record" -eq 0 ]]; then
  printf '\n' >&3
fi
printf '  ],\n' >&3

spec_df_samples=0
spec_df_unique=0
spec_df_constant=0
if [[ -s "$spec_df_values" ]]; then
  spec_df_samples="$(wc -l < "$spec_df_values" | tr -d '[:space:]')"
  spec_df_unique="$(sort -u "$spec_df_values" | wc -l | tr -d '[:space:]')"
  if [[ "$spec_df_samples" -gt 1 && "$spec_df_unique" -le 1 ]]; then
    spec_df_constant=1
  fi
fi

signal_entropy_json="${out_json%.json}.signal_entropy.json"
signal_entropy_status="not_run"
signal_entropy_constant_components=0
signal_entropy_variable_components=0
signal_entropy_component_keys=0
signal_entropy_actionable_component_keys=0
signal_entropy_constant_actionable_components=0
signal_entropy_variable_actionable_components=0
if [[ "$runtime_logs" -gt 0 ]]; then
  signal_entropy_tool="$log_dir/formtrig_lift_signal_entropy"
  if cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
    "$repo_root/formtrig/tools/formtrig_lift_signal_entropy.c" \
    -o "$signal_entropy_tool" -lm; then
    mapfile -t runtime_jsonls < <(
      find "$log_dir" -maxdepth 1 -type f -name 'seed_*.runtime.jsonl' \
        -size +0c | sort
    )
    if [[ "${#runtime_jsonls[@]}" -gt 0 ]]; then
      if "$signal_entropy_tool" "${runtime_jsonls[@]}" \
        > "$signal_entropy_json"; then
        signal_entropy_status="pass"
      else
        signal_entropy_status="fail"
      fi
      signal_entropy_constant_components="$(
        sed -n 's/.*"constant_components": \([0-9][0-9]*\),.*/\1/p' \
          "$signal_entropy_json" | head -n 1
      )"
      signal_entropy_variable_components="$(
        sed -n 's/.*"variable_components": \([0-9][0-9]*\),.*/\1/p' \
          "$signal_entropy_json" | head -n 1
      )"
      signal_entropy_component_keys="$(
        sed -n 's/.*"component_keys": \([0-9][0-9]*\),.*/\1/p' \
          "$signal_entropy_json" | head -n 1
      )"
      signal_entropy_actionable_component_keys="$(
        sed -n 's/.*"actionable_component_keys": \([0-9][0-9]*\),.*/\1/p' \
          "$signal_entropy_json" | head -n 1
      )"
      signal_entropy_constant_actionable_components="$(
        sed -n 's/.*"constant_actionable_components": \([0-9][0-9]*\),.*/\1/p' \
          "$signal_entropy_json" | head -n 1
      )"
      signal_entropy_variable_actionable_components="$(
        sed -n 's/.*"variable_actionable_components": \([0-9][0-9]*\),.*/\1/p' \
          "$signal_entropy_json" | head -n 1
      )"
      signal_entropy_constant_components="${signal_entropy_constant_components:-0}"
      signal_entropy_variable_components="${signal_entropy_variable_components:-0}"
      signal_entropy_component_keys="${signal_entropy_component_keys:-0}"
      signal_entropy_actionable_component_keys="${signal_entropy_actionable_component_keys:-0}"
      signal_entropy_constant_actionable_components="${signal_entropy_constant_actionable_components:-0}"
      signal_entropy_variable_actionable_components="${signal_entropy_variable_actionable_components:-0}"
    fi
  else
    signal_entropy_status="compile_failed"
  fi
fi

status="pass"
diagnosis="ready"
if [[ "$total" -eq 0 ]]; then
  status="fail"
  diagnosis="no_seed_files"
elif [[ "$runtime_logs" -eq 0 ]]; then
  status="fail"
  diagnosis="no_formtrig_runtime_signal"
elif [[ "$shm_seen_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_formtrig_shm_signal"
elif [[ "$shm_abi_ok_count" -eq 0 ]]; then
  status="fail"
  diagnosis="formtrig_shm_abi_mismatch"
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
elif [[ "$observed_heuristic_lifted_count" -ne 0 ]]; then
  status="fail"
  diagnosis="heuristic_lift_observed"
elif [[ "$observed_manual_lifted_count" -ne 0 ]]; then
  status="fail"
  diagnosis="manual_target_lift_observed"
elif [[ -n "$lift_spec" && "$component_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_lifted_components"
elif [[ -n "$lift_spec" && "$atom_signal_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_atom_signal"
elif [[ -n "$lift_spec" && "$role_signal_count" -eq 0 ]]; then
  status="fail"
  diagnosis="no_role_signal"
elif [[ -n "$lift_spec" && "$signal_entropy_status" == "compile_failed" ]]; then
  status="fail"
  diagnosis="signal_entropy_compile_failed"
elif [[ -n "$lift_spec" &&
        "$signal_entropy_actionable_component_keys" -le 0 ]]; then
  status="fail"
  diagnosis="no_actionable_lifted_component"
elif [[ -n "$lift_spec" && "$rnt_count" -gt 1 &&
        "$signal_entropy_variable_actionable_components" -le 0 ]]; then
  if [[ "$spec_df_constant" -ne 0 ]]; then
    diagnosis="ready_constant_seed_spec_d_f_needs_mutation_calibration"
  else
    diagnosis="ready_constant_seed_lift_components_needs_mutation_calibration"
  fi
elif [[ -n "$lift_spec" && "$spec_df_constant" -ne 0 ]]; then
  diagnosis="constant_scalar_d_f_variable_lifted_components"
elif [[ -n "$lift_spec" && "$rnt_count" -le 1 ]]; then
  diagnosis="ready_single_rnt_seed"
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
printf '  "observed_heuristic_lifted": %d,\n' "$observed_heuristic_lifted_count" >&3
printf '  "observed_manual_lifted": %d,\n' "$observed_manual_lifted_count" >&3
printf '  "spec_d_f_samples": %d,\n' "$spec_df_samples" >&3
printf '  "spec_d_f_unique": %d,\n' "$spec_df_unique" >&3
printf '  "spec_d_f_constant": %s,\n' "$(json_bool "$spec_df_constant")" >&3
printf '  "signal_entropy_status": "%s",\n' "$signal_entropy_status" >&3
printf '  "signal_entropy_path": "%s",\n' \
  "$(json_escape "$signal_entropy_json")" >&3
printf '  "signal_entropy_component_keys": %d,\n' \
  "$signal_entropy_component_keys" >&3
printf '  "signal_entropy_actionable_component_keys": %d,\n' \
  "$signal_entropy_actionable_component_keys" >&3
printf '  "signal_entropy_constant_components": %d,\n' \
  "$signal_entropy_constant_components" >&3
printf '  "signal_entropy_variable_components": %d,\n' \
  "$signal_entropy_variable_components" >&3
printf '  "signal_entropy_constant_actionable_components": %d,\n' \
  "$signal_entropy_constant_actionable_components" >&3
printf '  "signal_entropy_variable_actionable_components": %d,\n' \
  "$signal_entropy_variable_actionable_components" >&3
printf '  "shm_seen": %d,\n' "$shm_seen_count" >&3
printf '  "shm_abi_ok": %d,\n' "$shm_abi_ok_count" >&3
printf '  "shm_abi_mismatch": %d,\n' "$shm_abi_mismatch_count" >&3
printf '  "expected_shm_version": %d,\n' "$shm_version_expected" >&3
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
