#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

out_dir="/tmp/formtrig_libcoap_35862_selective_${timestamp}"
binding_spec="$repo_root/artifacts/binding_specs/LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml"
seed_dir="$repo_root/artifacts/rnt_corpus/LIBCOAP_CVE_2023_35862/seeds"
source_dir="$repo_root/benchmarks/cve_build/libcoap-cve-2023-35862-src"
harness_src="$repo_root/benchmarks/cve_harnesses/libcoap_oscore_conf_replay.c"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
target_site_ids=""
durations="30,120"
run_sweeps=1
use_asan=0

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Builds and optionally sweeps the admissible LIBCOAP_CVE_2023_35862 native
FORMTRIG target.

The flow is:

  harness admissibility audit
    -> full libcoap build and full site map
    -> BindingSpec compile, audit, and runtime event map
    -> target-site derivation from root_observe
    -> selective libcoap rebuild
    -> seed readiness + AFL++ sweeps

options:
  --out DIR              output directory (default: $out_dir)
  --binding-spec FILE    high-level BindingSpec
  --seed-dir DIR         RNT seed directory
  --source-dir DIR       libcoap source checkout/worktree
  --harness FILE         replay harness source
  --aflpp-dir DIR        patched AFL++ checkout/build
  --target-site-ids IDS  explicit target/reach site ids
  --durations LIST       comma/space-separated sweep durations
  --asan                 build with ASAN/UBSAN terminal oracle
  --no-sweeps            build selective target only
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

reset_build_dir() {
  local dir="$1"
  case "$dir" in
    "$out_dir"/libcoap-full-build|"$out_dir"/libcoap-selective-build)
      rm -rf -- "$dir"
      ;;
    *)
      echo "refusing to reset unexpected build directory: $dir" >&2
      exit 2
      ;;
  esac
}

configure_libcoap() {
  local build_dir="$1"
  cmake -S "$source_dir" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DENABLE_OSCORE=ON \
    -DOSCORE_BACKEND=none \
    -DENABLE_DTLS=OFF \
    -DENABLE_TCP=OFF \
    -DENABLE_WEBSOCKETS=OFF \
    -DENABLE_TESTS=OFF \
    -DENABLE_EXAMPLES=OFF \
    -DENABLE_DOCS=OFF
}

build_replay_binary() {
  local build_dir="$1"
  local binary="$2"
  cmake --build "$build_dir" -j "${FORMTRIG_JOBS:-4}"
  $CC $CFLAGS \
    -I"$build_dir/include" \
    -I"$source_dir/include" \
    -I"$build_dir" \
    "$harness_src" \
    "$build_dir/libcoap-3.a" \
    $LDFLAGS -lm \
    -o "$binary"
}

enable_sanitizers_if_requested() {
  if [[ "$use_asan" != "1" ]]; then
    return
  fi
  export AFL_USE_ASAN=1
  export AFL_CRASH_EXITCODE=86
  export ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0
  export UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0
  export CFLAGS="${CFLAGS:-} -fsanitize=address,undefined -fno-omit-frame-pointer"
  export LDFLAGS="${LDFLAGS:-} -fsanitize=address,undefined"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out_dir="${2:-}"
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
      durations="${2:-}"
      shift 2
      ;;
    --asan)
      use_asan=1
      shift
      ;;
    --no-sweeps)
      run_sweeps=0
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
binding_spec="$(abs_path "$binding_spec")"
seed_dir="$(abs_path "$seed_dir")"
source_dir="$(abs_path "$source_dir")"
harness_src="$(abs_path "$harness_src")"
aflpp_dir="$(abs_path "$aflpp_dir")"

require_path "$binding_spec"
require_path "$seed_dir"
require_path "$source_dir"
require_path "$harness_src"
require_path "$aflpp_dir/afl-fuzz"

mkdir -p "$out_dir/tools" "$out_dir/spec"
reset_build_dir "$out_dir/libcoap-full-build"
reset_build_dir "$out_dir/libcoap-selective-build"

"$repo_root/scripts/formtrig_harness_admissibility_audit.py" \
  --binding-spec "$binding_spec" \
  --harness "$harness_src" \
  --seed-dir "$seed_dir" \
  --out-json "$out_dir/formtrig_harness_admissibility.json" \
  --out-md "$out_dir/formtrig_harness_admissibility.md"

admissibility_status="$(jq -r '.status' "$out_dir/formtrig_harness_admissibility.json")"
if [[ "$admissibility_status" != "admissible" ]]; then
  echo "LIBCOAP_CVE_2023_35862 harness admissibility failed: $admissibility_status" >&2
  exit 1
fi

"$repo_root/scripts/prepare_formtrig_native_env.sh" \
  --out "$out_dir/full_native_env" \
  --aflpp-dir "$aflpp_dir" > "$out_dir/prepare_full_native_env.log"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_spec_compile.c" \
  -o "$out_dir/tools/formtrig_binding_spec_compile"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_lift_spec_audit.c" \
  -o "$out_dir/tools/formtrig_lift_spec_audit"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_map.c" \
  -o "$out_dir/tools/formtrig_binding_map"

(
  source "$out_dir/full_native_env/formtrig_native_env.sh"
  export FORMTRIG_INSTRUMENT_LEVEL=full
  enable_sanitizers_if_requested
  configure_libcoap "$out_dir/libcoap-full-build" \
    > "$out_dir/full_cmake_configure.log" 2>&1
  build_replay_binary "$out_dir/libcoap-full-build" \
    "$out_dir/libcoap_oscore_conf_replay_formtrig_full" \
    > "$out_dir/full_build.log" 2>&1
)

"$out_dir/tools/formtrig_binding_spec_compile" \
  --site-map "$out_dir/full_native_env/site_map.tsv" \
  --out "$out_dir/spec/formtrig_binding.lift" \
  "$binding_spec" > "$out_dir/spec/compile.log"

"$out_dir/tools/formtrig_lift_spec_audit" --category equality \
  "$out_dir/spec/formtrig_binding.lift" \
  > "$out_dir/spec/formtrig_lift_audit.csv"

"$out_dir/tools/formtrig_binding_map" --category equality \
  --site-map "$out_dir/full_native_env/site_map.tsv" \
  --normalized-spec "$out_dir/spec/formtrig_lift.normalized" \
  "$out_dir/spec/formtrig_binding.lift" \
  > "$out_dir/spec/formtrig_runtime_event_map.full.csv"

if [[ -z "$target_site_ids" ]]; then
  target_site_ids="$(
    awk '$1 == "role_component" && $4 == "root_observe" { print $3; exit }' \
      "$out_dir/spec/formtrig_lift.normalized"
  )"
fi
if [[ -z "$target_site_ids" ]]; then
  echo "could not derive target site id from normalized BindingSpec" >&2
  exit 1
fi

"$repo_root/scripts/formtrig_site_allowlist_from_lift_spec.sh" \
  --lift-spec "$out_dir/spec/formtrig_lift.normalized" \
  --target-site-ids "$target_site_ids" \
  --out "$out_dir/spec/formtrig_site_allowlist.txt"

"$repo_root/scripts/prepare_formtrig_native_env.sh" \
  --out "$out_dir/selective_native_env" \
  --aflpp-dir "$aflpp_dir" > "$out_dir/prepare_selective_native_env.log"

(
  source "$out_dir/selective_native_env/formtrig_native_env.sh"
  export FORMTRIG_INSTRUMENT_LEVEL=full
  export FORMTRIG_INSTRUMENT_SITE_ID_FILE="$out_dir/spec/formtrig_site_allowlist.txt"
  enable_sanitizers_if_requested
  configure_libcoap "$out_dir/libcoap-selective-build" \
    > "$out_dir/selective_cmake_configure.log" 2>&1
  build_replay_binary "$out_dir/libcoap-selective-build" \
    "$out_dir/libcoap_oscore_conf_replay_formtrig_selective" \
    > "$out_dir/selective_build.log" 2>&1
)

"$out_dir/tools/formtrig_binding_map" --category equality \
  --site-map "$out_dir/selective_native_env/site_map.tsv" \
  --normalized-spec "$out_dir/spec/formtrig_lift.selective.normalized" \
  "$out_dir/spec/formtrig_binding.lift" \
  > "$out_dir/spec/formtrig_runtime_event_map.selective.csv"

binary="$out_dir/libcoap_oscore_conf_replay_formtrig_selective"

{
  printf 'out_dir=%s\n' "$out_dir"
  printf 'binary=%s\n' "$binary"
  printf 'asan=%s\n' "$use_asan"
  printf 'full_site_map=%s\n' "$out_dir/full_native_env/site_map.tsv"
  printf 'selective_site_map=%s\n' "$out_dir/selective_native_env/site_map.tsv"
  printf 'allowlist=%s\n' "$out_dir/spec/formtrig_site_allowlist.txt"
  printf 'harness_admissibility=%s\n' "$out_dir/formtrig_harness_admissibility.json"
  printf 'target_site_ids=%s\n' "$target_site_ids"
  printf 'full_site_rows=%s\n' \
    "$(wc -l < "$out_dir/full_native_env/site_map.tsv")"
  printf 'selective_site_rows=%s\n' \
    "$(wc -l < "$out_dir/selective_native_env/site_map.tsv")"
  printf 'allowlist_rows=%s\n' \
    "$(wc -l < "$out_dir/spec/formtrig_site_allowlist.txt")"
} > "$out_dir/run_metadata.txt"

run_sweep() {
  local duration="$1"
  local sweep_out="$out_dir/selective_sweep_${duration}s"
  local args=(
    --in "$seed_dir"
    --out "$sweep_out"
    --target-bug LIBCOAP_CVE_2023_35862
    --category equality
    --site-map "$out_dir/selective_native_env/site_map.tsv"
    --candidate "$binding_spec"
    --duration "$duration"
    --seed-preflight require
    --seed-preflight-max 32
    --seed-preflight-timeout 2
    --target-site-ids "$target_site_ids"
    --aflpp-dir "$aflpp_dir"
  )
  if [[ "$use_asan" == "1" ]]; then
    args+=(--afl-arg -m --afl-arg none)
  fi
  "$repo_root/scripts/run_formtrig_binding_candidate_sweep.sh" \
    "${args[@]}" -- "$binary" @@
}

if [[ "$run_sweeps" == "1" ]]; then
  enable_sanitizers_if_requested
  while IFS= read -r duration; do
    run_sweep "$duration"
  done < <(split_list "$durations")
fi

echo "FORMTRIG LIBCOAP_CVE_2023_35862 selective flow complete"
echo "  out=$out_dir"
echo "  binary=$binary"
echo "  asan=$use_asan"
echo "  target_site_ids=$target_site_ids"
echo "  site_map=$out_dir/selective_native_env/site_map.tsv"
echo "  allowlist=$out_dir/spec/formtrig_site_allowlist.txt"
echo "  harness_admissibility=$out_dir/formtrig_harness_admissibility.json"
