#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
aflpp_dir="${AFLPP_DIR:-}"
afl_fuzz="$aflpp_dir/afl-fuzz"
seed_dir=""
out_dir=""
target_bug=""
category="generic"
lift_spec=""
binding_spec=""
target_site_ids=""
site_map=""
runtime_lift_spec=""
duration="60"
seed_preflight="warn"
seed_preflight_max="32"
seed_preflight_timeout="2"
mutation_hook_override=""
disable_mutation_hook=0
typed_ops=""
extra_afl_args=()

usage() {
  cat >&2 <<EOF
usage: $0 --in DIR --out DIR --target-bug LABEL [options] -- TARGET [ARGS...]

options:
  --category NAME      numeric|equality|binary-null|lifecycle|generic
  --binding-spec FILE  high-level FORMTRIG BindingSpec manifest to compile
  --lift-spec FILE     FORMTRIG_LIFT_SPEC file to export and audit
  --site-map FILE      LLVM FORMTRIG_SITE_MAP TSV for runtime event-map audit
  --target-site-ids S  comma-separated LLVM FORMTRIG site ids for known TC line
  --duration SEC       AFL++ -V time budget in seconds (default: 60)
  --seed-preflight M   off|warn|require native seed readiness check (default: warn)
  --seed-preflight-max N       max seeds to replay before fuzzing (default: 32)
  --seed-preflight-timeout SEC per-seed replay timeout (default: 2)
  --mutation-hook FILE override the BindingSpec external typed mutation hook
  --no-mutation-hook  disable the BindingSpec/env external mutation hook
  --typed-ops N       number of FORMTRIG typed-stage ops to enumerate
  --aflpp-dir DIR      AFL++ checkout/build directory
  --afl-arg ARG        extra afl-fuzz argument, repeatable

outputs:
  OUT/default/fuzzer_stats
  OUT/default/formtrig_progress.jsonl
  OUT/default/formtrig_summary.json
  OUT/default/formtrig_seed_readiness.json when seed preflight is enabled
  OUT/formtrig_lift_audit.csv when --lift-spec is set
EOF
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
}

formtrig_expected_abi_version() {
  awk '
    $1 == "#define" && $2 == "FORMTRIG_SHM_VERSION" {
      print $3
      exit
    }
  ' "$repo_root/formtrig/include/formtrig/formtrig_abi.h"
}

aflpp_dir_usable() {
  local dir="$1"
  [[ -x "$dir/afl-fuzz" ]]
}

aflpp_dir_abi_current() {
  local dir="$1"
  local expected_abi
  expected_abi="$(formtrig_expected_abi_version)"
  [[ -n "$expected_abi" ]] &&
    aflpp_dir_usable "$dir" &&
    grep -a -q "FORMTRIG_SHM_ABI_VERSION=$expected_abi" "$dir/afl-fuzz"
}

default_aflpp_dir() {
  local candidate
  for candidate in \
    "$repo_root/experiments/magma_workspace/magma/fuzzers/formtrig_native/repo" \
    "$repo_root/experiments/aflplusplus/AFLplusplus"
  do
    if aflpp_dir_abi_current "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  for candidate in \
    "$repo_root/experiments/magma_workspace/magma/fuzzers/formtrig_native/repo" \
    "$repo_root/experiments/aflplusplus/AFLplusplus"
  do
    if aflpp_dir_usable "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  printf '%s\n' "$repo_root/experiments/aflplusplus/AFLplusplus"
}

stats_field() {
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

json_or_null() {
  local value="${1:-}"
  if [[ -z "$value" ]]; then
    printf 'null'
  else
    printf '%s' "$value"
  fi
}

monitor_formtrig_stats() {
  local stats_path="$1"
  local monitor_dir="$2"
  local poll="$3"
  local start_ts
  start_ts="$(date +%s)"
  mkdir -p "$monitor_dir"
  while :; do
    if [[ -f "$stats_path" ]]; then
      local now elapsed
      now="$(date +%s)"
      elapsed=$((now - start_ts))
      cp "$stats_path" "$monitor_dir/${elapsed}.stats" 2>/dev/null || true
    fi
    sleep "$poll" || break
  done
}

write_terminal_monitor_json() {
  local monitor_dir="$1"
  local out_json="$2"
  local snapshot_count=0
  local first_time=""
  local first_triggered=""
  local first_file=""
  local latest_time=""
  local latest_triggered=0
  local latest_file=""

  if [[ -d "$monitor_dir" ]]; then
    while IFS= read -r snapshot; do
      snapshot_count=$((snapshot_count + 1))
      local triggered run_time
      triggered="$(stats_field "$snapshot" formtrig_triggered_execs 0)"
      run_time="$(stats_field "$snapshot" run_time "")"
      latest_time="$run_time"
      latest_triggered="$triggered"
      latest_file="$snapshot"
      if [[ -z "$first_time" && "$triggered" =~ ^[0-9]+$ &&
            "$triggered" -gt 0 ]]; then
        first_time="$run_time"
        first_triggered="$triggered"
        first_file="$snapshot"
      fi
    done < <(find "$monitor_dir" -maxdepth 1 -type f -name '*.stats' | sort -V)
  fi

  {
    printf '{\n'
    printf '  "snapshot_count": %s,\n' "$snapshot_count"
    printf '  "first_trigger_time_s": '
    json_or_null "$first_time"
    printf ',\n'
    printf '  "first_triggered_execs": '
    json_or_null "$first_triggered"
    printf ',\n'
    if [[ -n "$first_file" ]]; then
      printf '  "first_trigger_snapshot": "%s",\n' "$first_file"
    else
      printf '  "first_trigger_snapshot": null,\n'
    fi
    printf '  "latest_time_s": '
    json_or_null "$latest_time"
    printf ',\n'
    printf '  "latest_triggered_execs": %s,\n' "$latest_triggered"
    if [[ -n "$latest_file" ]]; then
      printf '  "latest_snapshot": "%s"\n' "$latest_file"
    else
      printf '  "latest_snapshot": null\n'
    fi
    printf '}\n'
  } > "$out_json"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --in)
      seed_dir="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --target-bug)
      target_bug="${2:-}"
      shift 2
      ;;
    --category)
      category="${2:-}"
      shift 2
      ;;
    --lift-spec)
      lift_spec="${2:-}"
      shift 2
      ;;
    --binding-spec)
      binding_spec="${2:-}"
      shift 2
      ;;
    --target-site-ids)
      target_site_ids="${2:-}"
      shift 2
      ;;
    --site-map)
      site_map="${2:-}"
      shift 2
      ;;
    --duration)
      duration="${2:-}"
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
    --mutation-hook)
      mutation_hook_override="${2:-}"
      shift 2
      ;;
    --no-mutation-hook)
      disable_mutation_hook=1
      shift
      ;;
    --typed-ops)
      typed_ops="${2:-}"
      shift 2
      ;;
    --aflpp-dir)
      aflpp_dir="${2:-}"
      afl_fuzz="$aflpp_dir/afl-fuzz"
      shift 2
      ;;
    --afl-arg)
      extra_afl_args+=("${2:-}")
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

if [[ -z "$seed_dir" || -z "$out_dir" || -z "$target_bug" || $# -eq 0 ]]; then
  usage
  exit 2
fi

if [[ -z "$aflpp_dir" ]]; then
  aflpp_dir="$(default_aflpp_dir)"
  afl_fuzz="$aflpp_dir/afl-fuzz"
fi

require_file "$seed_dir"
require_file "$afl_fuzz"

if [[ -n "$binding_spec" && -n "$lift_spec" ]]; then
  echo "--binding-spec and --lift-spec are mutually exclusive" >&2
  exit 2
fi

if [[ -n "$binding_spec" && -z "$site_map" ]]; then
  echo "--binding-spec requires --site-map so source bindings are runtime-grounded" >&2
  exit 2
fi
if [[ "$disable_mutation_hook" == "1" && -n "$mutation_hook_override" ]]; then
  echo "--no-mutation-hook and --mutation-hook are mutually exclusive" >&2
  exit 2
fi
if [[ -n "$typed_ops" && ! "$typed_ops" =~ ^[0-9]+$ ]]; then
  echo "--typed-ops must be a positive integer" >&2
  exit 2
fi
if [[ -n "$typed_ops" && "$typed_ops" -lt 1 ]]; then
  echo "--typed-ops must be a positive integer" >&2
  exit 2
fi

case "$seed_preflight" in
  off|warn|require)
    ;;
  *)
    echo "--seed-preflight must be off, warn, or require" >&2
    exit 2
    ;;
esac

if ! grep -a -q "FORMTRIG native signal channel enabled" "$afl_fuzz"; then
  echo "AFL++ checkout is not patched for FORMTRIG native guidance." >&2
  echo "Run: $repo_root/patches/aflplusplus/apply_formtrig_patch.sh" >&2
  exit 2
fi
expected_abi="$(formtrig_expected_abi_version)"
if [[ -z "$expected_abi" ]] ||
   ! grep -a -q "FORMTRIG_SHM_ABI_VERSION=$expected_abi" "$afl_fuzz"; then
  echo "AFL++ FORMTRIG ABI is missing or stale for FORMTRIG_SHM_VERSION=$expected_abi." >&2
  echo "Run: AFLPP_DIR=$aflpp_dir $repo_root/patches/aflplusplus/apply_formtrig_patch.sh" >&2
  exit 2
fi

if ldd "$afl_fuzz" 2>/dev/null | grep -qi python; then
  echo "afl-fuzz links against Python; rebuild with NO_PYTHON=1" >&2
  exit 3
fi

mkdir -p "$out_dir/.formtrig"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_progress_summary.c" \
  -o "$out_dir/.formtrig/formtrig_progress_summary"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_campaign_diagnose.c" \
  -o "$out_dir/.formtrig/formtrig_campaign_diagnose"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_signal_diagnose.c" \
  -o "$out_dir/.formtrig/formtrig_binding_signal_diagnose"

if [[ -n "$binding_spec" ]]; then
  require_file "$binding_spec"
  require_file "$site_map"
  lift_spec="$out_dir/.formtrig/formtrig_binding.lift"
  cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
    "$repo_root/formtrig/tools/formtrig_binding_spec_compile.c" \
    -o "$out_dir/.formtrig/formtrig_binding_spec_compile"
  if ! "$out_dir/.formtrig/formtrig_binding_spec_compile" \
    --site-map "$site_map" --out "$lift_spec" "$binding_spec"; then
    echo "FORMTRIG BindingSpec compilation failed: $binding_spec" >&2
    exit 4
  fi
fi

if [[ -n "$lift_spec" ]]; then
  require_file "$lift_spec"
  runtime_lift_spec="$lift_spec"
  cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
    "$repo_root/formtrig/tools/formtrig_lift_spec_audit.c" \
    -o "$out_dir/.formtrig/formtrig_lift_spec_audit"
  if ! "$out_dir/.formtrig/formtrig_lift_spec_audit" --category "$category" \
    "$lift_spec" > "$out_dir/formtrig_lift_audit.csv"; then
    echo "FORMTRIG lift binding audit failed: $out_dir/formtrig_lift_audit.csv" >&2
    exit 4
  fi
  if [[ -n "$site_map" ]]; then
    require_file "$site_map"
    runtime_lift_spec="$out_dir/.formtrig/formtrig_lift.normalized"
    cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
      "$repo_root/formtrig/tools/formtrig_binding_map.c" \
      -o "$out_dir/.formtrig/formtrig_binding_map"
    cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
      "$repo_root/formtrig/tools/formtrig_lift_feature_audit.c" \
      -o "$out_dir/.formtrig/formtrig_lift_feature_audit"
    if ! "$out_dir/.formtrig/formtrig_binding_map" --category "$category" \
      --site-map "$site_map" --normalized-spec "$runtime_lift_spec" "$lift_spec" \
      > "$out_dir/formtrig_runtime_event_map.csv"; then
      echo "FORMTRIG runtime event-map binding gate failed: $out_dir/formtrig_runtime_event_map.csv" >&2
      exit 4
    fi
    require_file "$runtime_lift_spec"
    if [[ -z "$target_site_ids" ]]; then
      target_site_ids="$(awk -F, '
        NR > 1 && $4 == "root_observe" && $6 != "*" && $6 != "" {
          if (seen[$6]++) next;
          out = out ? out "," $6 : $6;
        }
        END { print out }
      ' "$out_dir/formtrig_runtime_event_map.csv")"
      if [[ -z "$target_site_ids" ]]; then
        target_site_ids="$(awk -F, '
          NR > 1 && $6 != "*" && $6 != "" {
            if (seen[$6]++) next;
            out = out ? out "," $6 : $6;
          }
          END { print out }
        ' "$out_dir/formtrig_runtime_event_map.csv")"
      fi
    fi
  fi
fi

pre_reach_events=0
if [[ -n "$runtime_lift_spec" ]] &&
   grep -Eq '(^|[[:space:],])(pre_reach|pre-reach|before_reach|before-reach|any|both)([[:space:],]|$)' "$runtime_lift_spec"; then
  pre_reach_events=1
fi

mutation_hook=""
mutation_hook_source="none"
if [[ "$disable_mutation_hook" == "1" ]]; then
  mutation_hook_source="disabled_ablation"
elif [[ -n "$mutation_hook_override" ]]; then
  mutation_hook="$mutation_hook_override"
  if [[ "$mutation_hook" != /* ]]; then
    mutation_hook="$repo_root/$mutation_hook"
  fi
  mutation_hook_source="cli_override"
else
  mutation_hook="${FORMTRIG_TYPED_MUTATION_HOOK:-}"
  if [[ -n "$mutation_hook" ]]; then
    mutation_hook_source="environment"
    if [[ "$mutation_hook" != /* ]]; then
      mutation_hook="$(pwd)/$mutation_hook"
    fi
  elif [[ -n "$lift_spec" ]]; then
    mutation_hook="$(awk '$1 == "mutation_hook" { print $2; exit }' "$lift_spec")"
    if [[ -n "$mutation_hook" && "$mutation_hook" != /* ]]; then
      mutation_hook="$repo_root/$mutation_hook"
    fi
    if [[ -n "$mutation_hook" ]]; then
      mutation_hook_source="binding_spec"
    fi
  fi
fi
if [[ -n "$mutation_hook" ]]; then
  require_file "$mutation_hook"
  if [[ ! -x "$mutation_hook" ]]; then
    echo "FORMTRIG mutation hook is not executable: $mutation_hook" >&2
    exit 4
  fi
fi

hook_sha256=""
if [[ -n "$mutation_hook" ]]; then
  hook_sha256="$(sha256sum "$mutation_hook" | awk '{ print $1 }')"
fi
{
  printf '{\n'
  if [[ -n "$mutation_hook" ]]; then
    printf '  "enabled": true,\n'
    printf '  "source": "%s",\n' "$mutation_hook_source"
    printf '  "path": "%s",\n' "$mutation_hook"
    printf '  "sha256": "%s"\n' "$hook_sha256"
  else
    printf '  "enabled": false,\n'
    printf '  "source": "%s",\n' "$mutation_hook_source"
    printf '  "path": null,\n'
    printf '  "sha256": null\n'
  fi
  printf '}\n'
} > "$out_dir/formtrig_mutation_hook.json"

env_args=(
  AFL_FORMTRIG=1
  AFL_NO_UI="${AFL_NO_UI:-1}"
  AFL_SKIP_CPUFREQ="${AFL_SKIP_CPUFREQ:-1}"
  AFL_NO_AFFINITY="${AFL_NO_AFFINITY:-1}"
  AFL_DISABLE_TRIM="${AFL_DISABLE_TRIM:-1}"
  AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES="${AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES:-1}"
  FORMTRIG_TARGET_BUG="$target_bug"
  FORMTRIG_PROGRESS_LOG="${FORMTRIG_PROGRESS_LOG:-1}"
  FORMTRIG_SAVED_PROGRESS_LOG_LIMIT="${FORMTRIG_SAVED_PROGRESS_LOG_LIMIT:-8192}"
  FORMTRIG_SAVED_PROGRESS_LOG_SAMPLE_RATE="${FORMTRIG_SAVED_PROGRESS_LOG_SAMPLE_RATE:-1024}"
  FORMTRIG_ALLOW_HEURISTIC_LIFT=0
  FORMTRIG_OBSERVE_HEURISTIC_LIFT=0
  FORMTRIG_ALLOW_MANUAL_LIFT=0
  FORMTRIG_PRE_REACH_EVENTS="$pre_reach_events"
)

if [[ -n "$mutation_hook" ]]; then
  env_args+=(FORMTRIG_TYPED_MUTATION_HOOK="$mutation_hook")
fi

if [[ -n "$typed_ops" ]]; then
  env_args+=(FORMTRIG_TYPED_OPS="$typed_ops")
fi

{
  printf '{\n'
  if [[ -n "$typed_ops" ]]; then
    printf '  "typed_ops": %s,\n' "$typed_ops"
    printf '  "source": "cli"\n'
  else
    printf '  "typed_ops": null,\n'
    printf '  "source": "runtime_default"\n'
  fi
  printf '}\n'
} > "$out_dir/formtrig_typed_ops.json"

if [[ -n "$runtime_lift_spec" ]]; then
  env_args+=(FORMTRIG_LIFT_SPEC="$runtime_lift_spec")
fi

if [[ -n "$target_site_ids" ]]; then
  env_args+=(FORMTRIG_TARGET_SITE_IDS="$target_site_ids")
fi

seed_readiness=""
if [[ "$seed_preflight" != "off" ]]; then
  seed_readiness="$out_dir/.formtrig/formtrig_seed_readiness.json"
  seed_args=(
    --in "$seed_dir"
    --out "$seed_readiness"
    --target-bug "$target_bug"
    --max-seeds "$seed_preflight_max"
    --timeout "$seed_preflight_timeout"
  )
  if [[ -n "$runtime_lift_spec" ]]; then
    seed_args+=(--lift-spec "$runtime_lift_spec")
  fi
  if [[ -n "$target_site_ids" ]]; then
    seed_args+=(--target-site-ids "$target_site_ids")
  fi
  if ! "$repo_root/scripts/run_formtrig_seed_readiness.sh" \
      "${seed_args[@]}" -- "$@"; then
    if [[ "$seed_preflight" == "require" ]]; then
      echo "FORMTRIG seed readiness failed: $seed_readiness" >&2
      exit 6
    fi
    echo "FORMTRIG seed readiness warning: $seed_readiness" >&2
  fi
fi

stats_monitor_poll="${FORMTRIG_STATS_MONITOR_POLL:-30}"
stats_monitor_pid=""
stats_monitor_dir="$out_dir/formtrig_stats_monitor"
cleanup_stats_monitor() {
  if [[ -n "${stats_monitor_pid:-}" ]]; then
    kill "$stats_monitor_pid" 2>/dev/null || true
    wait "$stats_monitor_pid" 2>/dev/null || true
    stats_monitor_pid=""
  fi
}

if [[ "$stats_monitor_poll" =~ ^[0-9]+$ && "$stats_monitor_poll" -gt 0 ]]; then
  monitor_formtrig_stats "$out_dir/default/fuzzer_stats" \
    "$stats_monitor_dir" "$stats_monitor_poll" &
  stats_monitor_pid=$!
fi
trap cleanup_stats_monitor EXIT
set +e
env "${env_args[@]}" "$afl_fuzz" \
  -i "$seed_dir" -o "$out_dir" -V "$duration" "${extra_afl_args[@]}" -- "$@"
afl_status=$?
set -e
cleanup_stats_monitor
trap - EXIT
if [[ "$afl_status" != "0" ]]; then
  exit "$afl_status"
fi

stats="$out_dir/default/fuzzer_stats"
progress="$out_dir/default/formtrig_progress.jsonl"
require_file "$stats"
require_file "$progress"
if [[ -d "$stats_monitor_dir" ]]; then
  cp "$stats" "$stats_monitor_dir/final.stats"
  write_terminal_monitor_json "$stats_monitor_dir" \
    "$out_dir/default/formtrig_terminal_monitor.json"
fi
if [[ -n "$seed_readiness" ]]; then
  cp "$seed_readiness" "$out_dir/default/formtrig_seed_readiness.json"
  seed_signal_entropy="${seed_readiness%.json}.signal_entropy.json"
  if [[ -s "$seed_signal_entropy" ]]; then
    cp "$seed_signal_entropy" \
      "$out_dir/default/formtrig_seed_signal_entropy.json"
  fi
fi

"$out_dir/.formtrig/formtrig_progress_summary" "$stats" "$progress" \
  > "$out_dir/default/formtrig_summary.json"

if [[ -n "$site_map" ]]; then
  if ! "$out_dir/.formtrig/formtrig_lift_feature_audit" \
    "$out_dir/formtrig_runtime_event_map.csv" "$progress" \
    > "$out_dir/default/formtrig_lift_feature_audit.json"; then
    echo "FORMTRIG lifted feature provenance audit failed: $out_dir/default/formtrig_lift_feature_audit.json" >&2
    exit 5
  fi
  if ! "$out_dir/.formtrig/formtrig_binding_signal_diagnose" \
    "$out_dir/formtrig_runtime_event_map.csv" "$progress" \
    > "$out_dir/default/formtrig_binding_signal_diagnosis.json"; then
    echo "FORMTRIG binding signal diagnosis found non-actionable lift dynamics: $out_dir/default/formtrig_binding_signal_diagnosis.json" >&2
  fi
fi

diagnosis_args=("$out_dir/default/formtrig_summary.json")
if [[ -n "$site_map" ]]; then
  diagnosis_args+=("$out_dir/formtrig_runtime_event_map.csv")
else
  diagnosis_args+=("-")
fi
if [[ -n "$site_map" ]]; then
  diagnosis_args+=("$out_dir/default/formtrig_lift_feature_audit.json")
fi
if [[ -n "$site_map" ]]; then
  diagnosis_args+=("$out_dir/default/formtrig_binding_signal_diagnosis.json")
fi
"$out_dir/.formtrig/formtrig_campaign_diagnose" "${diagnosis_args[@]}" \
  > "$out_dir/default/formtrig_diagnosis.json"

echo "FORMTRIG campaign complete"
echo "  stats=$stats"
echo "  progress=$progress"
echo "  summary=$out_dir/default/formtrig_summary.json"
echo "  diagnosis=$out_dir/default/formtrig_diagnosis.json"
if [[ -n "$seed_readiness" ]]; then
  echo "  seed_readiness=$out_dir/default/formtrig_seed_readiness.json"
  if [[ -s "$out_dir/default/formtrig_seed_signal_entropy.json" ]]; then
    echo "  seed_signal_entropy=$out_dir/default/formtrig_seed_signal_entropy.json"
  fi
fi
if [[ -n "$lift_spec" ]]; then
  echo "  binding_audit=$out_dir/formtrig_lift_audit.csv"
fi
if [[ -n "$binding_spec" ]]; then
  echo "  binding_spec=$binding_spec"
  echo "  compiled_lift_spec=$out_dir/.formtrig/formtrig_binding.lift"
fi
if [[ -n "$site_map" ]]; then
  echo "  runtime_event_map=$out_dir/formtrig_runtime_event_map.csv"
  echo "  runtime_lift_spec=$runtime_lift_spec"
  echo "  lift_feature_audit=$out_dir/default/formtrig_lift_feature_audit.json"
  echo "  binding_signal_diagnosis=$out_dir/default/formtrig_binding_signal_diagnosis.json"
fi
