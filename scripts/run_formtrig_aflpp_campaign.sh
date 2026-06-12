#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
afl_fuzz="$aflpp_dir/afl-fuzz"
seed_dir=""
out_dir=""
target_bug=""
category="generic"
lift_spec=""
target_site_ids=""
duration="60"
extra_afl_args=()

usage() {
  cat >&2 <<EOF
usage: $0 --in DIR --out DIR --target-bug LABEL [options] -- TARGET [ARGS...]

options:
  --category NAME      numeric|equality|binary-null|lifecycle|generic
  --lift-spec FILE     FORMTRIG_LIFT_SPEC file to export and audit
  --target-site-ids S  comma-separated LLVM FORMTRIG site ids for known TC line
  --duration SEC       AFL++ -V time budget in seconds (default: 60)
  --aflpp-dir DIR      AFL++ checkout/build directory
  --afl-arg ARG        extra afl-fuzz argument, repeatable

outputs:
  OUT/default/fuzzer_stats
  OUT/default/formtrig_progress.jsonl
  OUT/default/formtrig_summary.json
  OUT/formtrig_lift_audit.csv when --lift-spec is set
EOF
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
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
    --target-site-ids)
      target_site_ids="${2:-}"
      shift 2
      ;;
    --duration)
      duration="${2:-}"
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

require_file "$seed_dir"
require_file "$afl_fuzz"

if ! grep -a -q "FORMTRIG native signal channel enabled" "$afl_fuzz"; then
  echo "AFL++ checkout is not patched for FORMTRIG native guidance." >&2
  echo "Run: $repo_root/patches/aflplusplus/apply_formtrig_patch.sh" >&2
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

if [[ -n "$lift_spec" ]]; then
  require_file "$lift_spec"
  cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
    "$repo_root/formtrig/tools/formtrig_lift_spec_audit.c" \
    -o "$out_dir/.formtrig/formtrig_lift_spec_audit"
  if ! "$out_dir/.formtrig/formtrig_lift_spec_audit" --category "$category" \
    "$lift_spec" > "$out_dir/formtrig_lift_audit.csv"; then
    echo "FORMTRIG lift binding audit failed: $out_dir/formtrig_lift_audit.csv" >&2
    exit 4
  fi
fi

env_args=(
  AFL_FORMTRIG=1
  AFL_NO_UI="${AFL_NO_UI:-1}"
  AFL_SKIP_CPUFREQ="${AFL_SKIP_CPUFREQ:-1}"
  AFL_NO_AFFINITY="${AFL_NO_AFFINITY:-1}"
  AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES="${AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES:-1}"
  FORMTRIG_TARGET_BUG="$target_bug"
  FORMTRIG_PROGRESS_LOG="${FORMTRIG_PROGRESS_LOG:-1}"
)

if [[ -n "$lift_spec" ]]; then
  env_args+=(FORMTRIG_LIFT_SPEC="$lift_spec")
fi

if [[ -n "$target_site_ids" ]]; then
  env_args+=(FORMTRIG_TARGET_SITE_IDS="$target_site_ids")
fi

env "${env_args[@]}" "$afl_fuzz" \
  -i "$seed_dir" -o "$out_dir" -V "$duration" "${extra_afl_args[@]}" -- "$@"

stats="$out_dir/default/fuzzer_stats"
progress="$out_dir/default/formtrig_progress.jsonl"
require_file "$stats"
require_file "$progress"

"$out_dir/.formtrig/formtrig_progress_summary" "$stats" "$progress" \
  > "$out_dir/default/formtrig_summary.json"

echo "FORMTRIG campaign complete"
echo "  stats=$stats"
echo "  progress=$progress"
echo "  summary=$out_dir/default/formtrig_summary.json"
if [[ -n "$lift_spec" ]]; then
  echo "  binding_audit=$out_dir/formtrig_lift_audit.csv"
fi
