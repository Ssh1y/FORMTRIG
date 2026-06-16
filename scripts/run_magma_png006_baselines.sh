#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

out_dir="/tmp/formtrig_png006_baselines_${timestamp}"
magma_dir="$repo_root/experiments/magma_workspace/magma"
seed_dir="$repo_root/artifacts/rnt_corpus/PNG006/seeds"
durations="1800"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
poll="30"
run_build=1
run_sweeps=1

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Builds and runs faithful AFL++-family Magma baselines for PNG006, then harvests
Magma monitor _T evidence through tools/run_post_reach_baseline.py.

options:
  --out DIR             output directory
  --magma-dir DIR       Magma checkout/workspace
  --seed-dir DIR        RNT/post-reach seed directory
  --durations LIST      comma/space-separated budgets in seconds
  --baselines LIST      comma/space-separated baseline ids
  --poll SEC            Magma monitor poll interval, default 30
  --no-build            skip captain build
  --no-sweeps           build only
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

magma_fuzzer_for_baseline() {
  case "$1" in
    aflplusplus_vanilla)
      printf '%s\n' "aflplusplus_plain"
      ;;
    aflplusplus_cmplog|redqueen_operand)
      printf '%s\n' "aflplusplus"
      ;;
    *)
      echo "unsupported faithful PNG006 baseline: $1" >&2
      exit 2
      ;;
  esac
}

build_magma_fuzzer() {
  local fuzzer="$1"
  (
    cd "$magma_dir"
    FUZZER="$fuzzer" TARGET=libpng PROGRAM=libpng_read_fuzzer \
      CANARY_MODE=1 FORMTRIG_TARGET_BUG=PNG006 \
      ./tools/captain/build.sh
  ) > "$out_dir/build_${fuzzer}.log" 2>&1
}

run_one_baseline() {
  local baseline="$1"
  local duration="$2"
  local fuzzer
  fuzzer="$(magma_fuzzer_for_baseline "$baseline")"

  local shared="$out_dir/magma/${baseline}_${duration}s"
  local run_out="$out_dir/runs/${baseline}_${duration}s"
  mkdir -p "$shared" "$run_out"

  (
    cd "$magma_dir"
    FUZZER="$fuzzer" TARGET=libpng PROGRAM=libpng_read_fuzzer \
      ARGS=@@ CANARY_MODE=1 SHARED="$shared" POLL="$poll" \
      TIMEOUT="${duration}s" MAGMA_INPUT_CORPUS="$seed_dir" \
      MAGMA_SKIP_SEED_PRUNE=1 \
      ./tools/captain/start.sh
  ) > "$run_out/captain_stdout.log" 2> "$run_out/captain_stderr.log"

  "$repo_root/tools/run_post_reach_baseline.py" \
    --baseline "$baseline" \
    --target-id PNG006 \
    --tc-category binary-state-null \
    --seed-corpus "$seed_dir" \
    --out-dir "$run_out" \
    --budget-sec "$duration" \
    --rep 1 \
    --mode harvest \
    --existing-fuzzer-out "$shared/findings" \
    --magma-monitor-dir "$shared/monitor" \
    --magma-bug-id PNG006 \
    --target-cmd "magma/captain $fuzzer libpng libpng_read_fuzzer @@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --magma-dir)
      magma_dir="${2:-}"
      shift 2
      ;;
    --seed-dir)
      seed_dir="${2:-}"
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
    --poll)
      poll="${2:-}"
      shift 2
      ;;
    --no-build)
      run_build=0
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
magma_dir="$(abs_path "$magma_dir")"
seed_dir="$(abs_path "$seed_dir")"

require_path "$magma_dir/tools/captain/build.sh"
require_path "$magma_dir/tools/captain/start.sh"
require_path "$seed_dir"

{
  printf 'out_dir=%s\n' "$out_dir"
  printf 'magma_dir=%s\n' "$magma_dir"
  printf 'seed_dir=%s\n' "$seed_dir"
  printf 'baselines=%s\n' "$baselines"
  printf 'durations=%s\n' "$durations"
  printf 'poll=%s\n' "$poll"
} > "$out_dir/run_metadata.txt"

if [[ "$run_build" == "1" ]]; then
  declare -A built_fuzzers=()
  while IFS= read -r baseline; do
    fuzzer="$(magma_fuzzer_for_baseline "$baseline")"
    if [[ -n "${built_fuzzers[$fuzzer]:-}" ]]; then
      continue
    fi
    built_fuzzers[$fuzzer]=1
    build_magma_fuzzer "$fuzzer"
  done < <(split_list "$baselines")
fi

if [[ "$run_sweeps" == "1" ]]; then
  while IFS= read -r duration; do
    while IFS= read -r baseline; do
      run_one_baseline "$baseline" "$duration"
    done < <(split_list "$baselines")
  done < <(split_list "$durations")
fi

echo "PNG006 Magma baseline flow complete"
echo "  out=$out_dir"
echo "  baselines=$baselines"
echo "  durations=$durations"
