#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

out_dir="/tmp/formtrig_libxml2_1107_selective_${timestamp}"
full_site_map="/tmp/formtrig_libxml2_1107_full_20260615T090425Z/native_env/site_map.tsv"
binding_spec="$repo_root/artifacts/binding_specs/LIBXML2_1107.native_b2_alloc_fail_candidate.yml"
seed_dir="$repo_root/artifacts/rnt_corpus/LIBXML2_1107/seeds"
source_dir="$repo_root/benchmarks/cve_build/libxml2-a7511af0-src"
harness_src="$repo_root/benchmarks/cve_harnesses/libxml2_regexp_strdup_fail_replay.c"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
target_site_ids="820871835,787463692"
normal_durations="30,120"
terminal_durations="30,120"
terminal_timeout="3000+"
run_sweeps=1
run_terminal_sweeps=1

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Builds and optionally sweeps the LIBXML2_1107 selective FORMTRIG native target.
The flow is:

  harness admissibility audit
    -> full site map + BindingSpec
    -> compiled lift-spec
    -> runtime-grounded normalized lift-spec
    -> compile-time site-id allowlist
    -> selective libxml2/harness rebuild
    -> seed readiness + AFL++ sweeps

options:
  --out DIR              output directory (default: $out_dir)
  --full-site-map FILE   full/slice site map used to ground the BindingSpec
  --binding-spec FILE    high-level BindingSpec
  --seed-dir DIR         RNT seed directory
  --source-dir DIR       libxml2 source checkout/worktree
  --harness FILE         replay harness source
  --aflpp-dir DIR        patched AFL++ checkout/build
  --target-site-ids IDS  explicit target/reach site ids
  --durations LIST       comma/space-separated normal sweep durations
  --terminal-durations LIST
                         comma/space-separated timeout-adjusted sweep durations
  --terminal-timeout T   AFL++ -t value for terminal accounting (default: 3000+)
  --no-sweeps            build selective target only
  --no-terminal-sweeps   skip timeout-adjusted terminal-accounting sweeps
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
    local dir
    dir="$(dirname "$path")"
    local base
    base="$(basename "$path")"
    (cd "$dir" && printf '%s/%s\n' "$(pwd)" "$base")
  fi
}

split_list() {
  printf '%s\n' "$1" | tr ', ' '\n' | awk 'NF { print }'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --full-site-map)
      full_site_map="${2:-}"
      shift 2
      ;;
    --binding-spec)
      binding_spec="${2:-}"
      shift 2
      ;;
    --seed-dir)
      seed_dir="${2:-}"
      shift 2
      ;;
    --source-dir)
      source_dir="${2:-}"
      shift 2
      ;;
    --harness)
      harness_src="${2:-}"
      shift 2
      ;;
    --aflpp-dir)
      aflpp_dir="${2:-}"
      shift 2
      ;;
    --target-site-ids)
      target_site_ids="${2:-}"
      shift 2
      ;;
    --durations)
      normal_durations="${2:-}"
      shift 2
      ;;
    --terminal-durations)
      terminal_durations="${2:-}"
      shift 2
      ;;
    --terminal-timeout)
      terminal_timeout="${2:-}"
      shift 2
      ;;
    --no-sweeps)
      run_sweeps=0
      shift
      ;;
    --no-terminal-sweeps)
      run_terminal_sweeps=0
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

mkdir -p "$out_dir"
out_dir="$(abs_path "$out_dir")"
full_site_map="$(abs_path "$full_site_map")"
binding_spec="$(abs_path "$binding_spec")"
seed_dir="$(abs_path "$seed_dir")"
source_dir="$(abs_path "$source_dir")"
harness_src="$(abs_path "$harness_src")"
aflpp_dir="$(abs_path "$aflpp_dir")"

require_path "$full_site_map"
require_path "$binding_spec"
require_path "$seed_dir"
require_path "$source_dir"
require_path "$harness_src"
require_path "$aflpp_dir/afl-fuzz"

mkdir -p "$out_dir/tools" "$out_dir/spec"

"$repo_root/scripts/formtrig_harness_admissibility_audit.py" \
  --binding-spec "$binding_spec" \
  --harness "$harness_src" \
  --seed-dir "$seed_dir" \
  --out-json "$out_dir/formtrig_harness_admissibility.json" \
  --out-md "$out_dir/formtrig_harness_admissibility.md"

"$repo_root/scripts/prepare_formtrig_native_env.sh" \
  --out "$out_dir/native_env" \
  --aflpp-dir "$aflpp_dir" > "$out_dir/prepare_native_env.log"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_spec_compile.c" \
  -o "$out_dir/tools/formtrig_binding_spec_compile"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_lift_spec_audit.c" \
  -o "$out_dir/tools/formtrig_lift_spec_audit"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_map.c" \
  -o "$out_dir/tools/formtrig_binding_map"

"$out_dir/tools/formtrig_binding_spec_compile" \
  --site-map "$full_site_map" \
  --out "$out_dir/spec/formtrig_binding.lift" \
  "$binding_spec" > "$out_dir/spec/compile.log"

"$out_dir/tools/formtrig_lift_spec_audit" --category binary-null \
  "$out_dir/spec/formtrig_binding.lift" \
  > "$out_dir/spec/formtrig_lift_audit.csv"

"$out_dir/tools/formtrig_binding_map" --category binary-null \
  --site-map "$full_site_map" \
  --normalized-spec "$out_dir/spec/formtrig_lift.normalized" \
  "$out_dir/spec/formtrig_binding.lift" \
  > "$out_dir/spec/formtrig_runtime_event_map.full.csv"

"$repo_root/scripts/formtrig_site_allowlist_from_lift_spec.sh" \
  --lift-spec "$out_dir/spec/formtrig_lift.normalized" \
  --target-site-ids "$target_site_ids" \
  --out "$out_dir/spec/formtrig_site_allowlist.txt"

(
  source "$out_dir/native_env/formtrig_native_env.sh"
  export FORMTRIG_INSTRUMENT_LEVEL=full
  export FORMTRIG_INSTRUMENT_SITE_ID_FILE="$out_dir/spec/formtrig_site_allowlist.txt"

  cmake -S "$source_dir" -B "$out_dir/libxml2-build" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DBUILD_SHARED_LIBS=OFF \
    -DLIBXML2_WITH_PROGRAMS=OFF \
    -DLIBXML2_WITH_TESTS=OFF \
    -DLIBXML2_WITH_PYTHON=OFF \
    -DLIBXML2_WITH_ICONV=OFF \
    -DLIBXML2_WITH_THREADS=OFF \
    -DLIBXML2_WITH_MODULES=OFF \
    -DLIBXML2_WITH_ZLIB=OFF \
    > "$out_dir/cmake_configure.log" 2>&1

  cmake --build "$out_dir/libxml2-build" -j "${FORMTRIG_JOBS:-4}" \
    > "$out_dir/cmake_build.log" 2>&1

  $CC $CFLAGS \
    -I"$source_dir/include" \
    -I"$out_dir/libxml2-build" \
    "$harness_src" \
    "$out_dir/libxml2-build/libxml2.a" \
    $LDFLAGS \
    -o "$out_dir/libxml2_regexp_strdup_fail_replay_formtrig_selective" \
    > "$out_dir/harness_build.log" 2>&1
)

"$out_dir/tools/formtrig_binding_map" --category binary-null \
  --site-map "$out_dir/native_env/site_map.tsv" \
  --normalized-spec "$out_dir/spec/formtrig_lift.selective.normalized" \
  "$out_dir/spec/formtrig_binding.lift" \
  > "$out_dir/spec/formtrig_runtime_event_map.selective.csv"

binary="$out_dir/libxml2_regexp_strdup_fail_replay_formtrig_selective"

{
  printf 'out_dir=%s\n' "$out_dir"
  printf 'binary=%s\n' "$binary"
  printf 'full_site_map=%s\n' "$full_site_map"
  printf 'selective_site_map=%s\n' "$out_dir/native_env/site_map.tsv"
  printf 'allowlist=%s\n' "$out_dir/spec/formtrig_site_allowlist.txt"
  printf 'harness_admissibility=%s\n' "$out_dir/formtrig_harness_admissibility.json"
  printf 'selective_site_rows=%s\n' \
    "$(wc -l < "$out_dir/native_env/site_map.tsv")"
  printf 'allowlist_rows=%s\n' \
    "$(wc -l < "$out_dir/spec/formtrig_site_allowlist.txt")"
} > "$out_dir/run_metadata.txt"

run_sweep() {
  local duration="$1"
  local suffix="$2"
  local timeout_arg="${3:-}"
  local sweep_out="$out_dir/selective_sweep_${duration}s${suffix}"
  local args=(
    --in "$seed_dir"
    --out "$sweep_out"
    --target-bug LIBXML2_1107
    --category binary-null
    --site-map "$out_dir/native_env/site_map.tsv"
    --candidate "$binding_spec"
    --duration "$duration"
    --seed-preflight require
    --seed-preflight-max 32
    --seed-preflight-timeout 2
    --target-site-ids "$target_site_ids"
    --aflpp-dir "$aflpp_dir"
  )
  if [[ -n "$timeout_arg" ]]; then
    args+=(--afl-arg -t --afl-arg "$timeout_arg")
  fi
  "$repo_root/scripts/run_formtrig_binding_candidate_sweep.sh" \
    "${args[@]}" -- "$binary" @@
}

if [[ "$run_sweeps" == "1" ]]; then
  while IFS= read -r duration; do
    run_sweep "$duration" "" ""
  done < <(split_list "$normal_durations")

  if [[ "$run_terminal_sweeps" == "1" ]]; then
    while IFS= read -r duration; do
      run_sweep "$duration" "_t${terminal_timeout//[^A-Za-z0-9_.-]/_}" \
        "$terminal_timeout"
    done < <(split_list "$terminal_durations")
  fi
fi

echo "FORMTRIG LIBXML2_1107 selective flow complete"
echo "  out=$out_dir"
echo "  binary=$binary"
echo "  site_map=$out_dir/native_env/site_map.tsv"
echo "  allowlist=$out_dir/spec/formtrig_site_allowlist.txt"
echo "  harness_admissibility=$out_dir/formtrig_harness_admissibility.json"
