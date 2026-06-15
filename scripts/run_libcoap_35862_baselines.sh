#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

out_dir="/tmp/formtrig_libcoap_35862_baselines_${timestamp}"
seed_dir="$repo_root/artifacts/rnt_corpus/LIBCOAP_CVE_2023_35862/seeds"
source_dir="$repo_root/benchmarks/cve_build/libcoap-cve-2023-35862-src"
harness_src="$repo_root/benchmarks/cve_harnesses/libcoap_oscore_conf_replay.c"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
durations="1800"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
use_asan=0
run_sweeps=1

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Builds faithful AFL++-family baselines for LIBCOAP_CVE_2023_35862 and runs them
through tools/run_post_reach_baseline.py.

options:
  --out DIR             output directory (default: $out_dir)
  --seed-dir DIR        RNT seed directory
  --source-dir DIR      libcoap source checkout/worktree
  --harness FILE        replay harness source
  --aflpp-dir DIR       AFL++ checkout/build directory
  --durations LIST      comma/space-separated budgets in seconds
  --baselines LIST      comma/space-separated baseline ids
  --asan                build/run ASAN terminal-oracle binaries
  --no-sweeps           build binaries only
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
    "$out_dir"/libcoap-aflpp-build|"$out_dir"/libcoap-cmplog-build)
      rm -rf -- "$dir"
      ;;
    *)
      echo "refusing to reset unexpected build directory: $dir" >&2
      exit 2
      ;;
  esac
}

enable_asan_if_requested() {
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

configure_libcoap() {
  local build_dir="$1"
  CC="$aflpp_dir/afl-clang-fast" cmake -S "$source_dir" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_C_COMPILER="$aflpp_dir/afl-clang-fast" \
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
  "$aflpp_dir/afl-clang-fast" ${CFLAGS:-} \
    -I"$build_dir/include" \
    -I"$source_dir/include" \
    -I"$build_dir" \
    "$harness_src" \
    "$build_dir/libcoap-3.a" \
    ${LDFLAGS:-} -lm \
    -o "$binary"
}

needs_cmplog() {
  split_list "$baselines" | grep -Eq '^(aflplusplus_cmplog|redqueen_operand)$'
}

preflight_cmplog_compiler() {
  local tmp_c
  local tmp_o
  local tmp_log
  tmp_c="$out_dir/cmplog_preflight.c"
  tmp_o="$out_dir/cmplog_preflight.o"
  tmp_log="$out_dir/cmplog_preflight.log"
  printf 'int main(void) { return 0; }\n' > "$tmp_c"
  if ! AFL_LLVM_CMPLOG=1 "$aflpp_dir/afl-clang-fast" \
      -c "$tmp_c" -o "$tmp_o" >"$tmp_log" 2>&1; then
    echo "AFL++ CmpLog compiler preflight failed; see $tmp_log" >&2
    echo "Build the AFL++ LLVM passes with a matching LLVM_CONFIG before running faithful CmpLog/RedQueen baselines." >&2
    exit 3
  fi
}

run_one_baseline() {
  local baseline="$1"
  local duration="$2"
  local run_out="$out_dir/runs/${baseline}_${duration}s"
  local runner_args=(
    --baseline "$baseline"
    --target-id LIBCOAP_CVE_2023_35862
    --tc-category equality-magic
    --seed-corpus "$seed_dir"
    --out-dir "$run_out"
    --budget-sec "$duration"
    --rep 1
    --target-cmd "$out_dir/libcoap_oscore_conf_replay_aflpp @@"
    --mode execute
    --afl-fuzz "$aflpp_dir/afl-fuzz"
  )
  if [[ "$baseline" == "aflplusplus_cmplog" || "$baseline" == "redqueen_operand" ]]; then
    runner_args+=(--cmplog-binary "$out_dir/libcoap_oscore_conf_replay_cmplog")
  fi
  if [[ "$use_asan" == "1" ]]; then
    runner_args+=(
      --env AFL_CRASH_EXITCODE=86
      --env ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:detect_leaks=0:symbolize=0
      --env UBSAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=86:print_stacktrace=0
    )
  fi
  "$repo_root/tools/run_post_reach_baseline.py" "${runner_args[@]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out_dir="${2:-}"
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
    --durations)
      durations="${2:-}"
      shift 2
      ;;
    --baselines)
      baselines="${2:-}"
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
seed_dir="$(abs_path "$seed_dir")"
source_dir="$(abs_path "$source_dir")"
harness_src="$(abs_path "$harness_src")"
aflpp_dir="$(abs_path "$aflpp_dir")"

require_path "$seed_dir"
require_path "$source_dir"
require_path "$harness_src"
require_path "$aflpp_dir/afl-fuzz"
require_path "$aflpp_dir/afl-clang-fast"

mkdir -p "$out_dir"
reset_build_dir "$out_dir/libcoap-aflpp-build"
reset_build_dir "$out_dir/libcoap-cmplog-build"

if needs_cmplog; then
  preflight_cmplog_compiler
fi

(
  enable_asan_if_requested
  configure_libcoap "$out_dir/libcoap-aflpp-build" \
    > "$out_dir/aflpp_cmake_configure.log" 2>&1
  build_replay_binary "$out_dir/libcoap-aflpp-build" \
    "$out_dir/libcoap_oscore_conf_replay_aflpp" \
    > "$out_dir/aflpp_build.log" 2>&1
)

if needs_cmplog; then
  (
    export AFL_LLVM_CMPLOG=1
    enable_asan_if_requested
    configure_libcoap "$out_dir/libcoap-cmplog-build" \
      > "$out_dir/cmplog_cmake_configure.log" 2>&1
    build_replay_binary "$out_dir/libcoap-cmplog-build" \
      "$out_dir/libcoap_oscore_conf_replay_cmplog" \
      > "$out_dir/cmplog_build.log" 2>&1
  )
fi

{
  printf 'out_dir=%s\n' "$out_dir"
  printf 'seed_dir=%s\n' "$seed_dir"
  printf 'source_dir=%s\n' "$source_dir"
  printf 'harness=%s\n' "$harness_src"
  printf 'aflpp_dir=%s\n' "$aflpp_dir"
  printf 'asan=%s\n' "$use_asan"
  printf 'baselines=%s\n' "$baselines"
  printf 'durations=%s\n' "$durations"
  printf 'binary=%s\n' "$out_dir/libcoap_oscore_conf_replay_aflpp"
  if [[ -e "$out_dir/libcoap_oscore_conf_replay_cmplog" ]]; then
    printf 'cmplog_binary=%s\n' "$out_dir/libcoap_oscore_conf_replay_cmplog"
  fi
} > "$out_dir/run_metadata.txt"

if [[ "$run_sweeps" == "1" ]]; then
  while IFS= read -r duration; do
    while IFS= read -r baseline; do
      case "$baseline" in
        aflplusplus_vanilla|aflplusplus_cmplog|redqueen_operand)
          run_one_baseline "$baseline" "$duration"
          ;;
        *)
          echo "unsupported faithful LIBCOAP baseline in this runner: $baseline" >&2
          exit 2
          ;;
      esac
    done < <(split_list "$baselines")
  done < <(split_list "$durations")
fi

echo "LIBCOAP_CVE_2023_35862 baseline flow complete"
echo "  out=$out_dir"
echo "  asan=$use_asan"
echo "  baselines=$baselines"
