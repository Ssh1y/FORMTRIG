#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id=""
inventory="$repo_root/artifacts/magma_canary_inventory.json"
out_dir=""
magma_dir="$repo_root/experiments/magma_workspace/magma"
seed_dir=""
durations="600,1800"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
poll="30"
reps="1"
jobs="${FORMTRIG_JOBS:-1}"
run_build=1
run_sweeps=1
failed_jobs=0

usage() {
  cat >&2 <<EOF
usage: $0 --target-id ID [options]

Builds and runs faithful AFL++-family Magma baselines for any target in the
Magma canary inventory, then harvests Magma monitor _T evidence through
tools/run_post_reach_baseline.py.

options:
  --target-id ID        Magma bug/target id, for example PNG007
  --inventory JSON      Magma canary inventory, default artifacts/magma_canary_inventory.json
  --out DIR             output directory, default /tmp/formtrig_<target>_baselines_<timestamp>
  --magma-dir DIR       Magma checkout/workspace
  --seed-dir DIR        seed directory; defaults to artifacts/rnt_corpus/<ID>/seeds if present,
                        otherwise the inventory initial_seed_corpus
  --durations LIST      comma/space-separated budgets in seconds, default 600,1800
  --baselines LIST      comma/space-separated baseline ids
  --reps N              repetitions per baseline/budget, default 1
  --jobs N              concurrent baseline runs, default FORMTRIG_JOBS or 1
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

abs_repo_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s/%s\n' "$repo_root" "$path"
  fi
}

split_list() {
  printf '%s\n' "$1" | tr ', ' '\n' | awk 'NF { print }'
}

inventory_field() {
  local field="$1"
  python3 - "$inventory" "$target_id" "$field" <<'PY'
import json
import sys

path, target_id, field = sys.argv[1:4]
with open(path, encoding="utf-8") as handle:
    payload = json.load(handle)
for record in payload.get("records", []):
    if record.get("target_id") == target_id:
        value = record.get(field, "")
        print("" if value is None else value)
        raise SystemExit(0)
raise SystemExit(f"target_id not found in inventory: {target_id}")
PY
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
      echo "unsupported faithful Magma baseline: $1" >&2
      exit 2
      ;;
  esac
}

build_magma_fuzzer() {
  local fuzzer="$1"
  (
    cd "$magma_dir"
    FUZZER="$fuzzer" TARGET="$magma_target" PROGRAM="$program" \
      CANARY_MODE=1 FORMTRIG_TARGET_BUG="$target_id" \
      ./tools/captain/build.sh
  ) > "$out_dir/build_${fuzzer}.log" 2>&1
}

copy_seed_corpus() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  find "$seed_dir" -maxdepth 1 -type f -exec cp {} "$dest/" \;
  if ! find "$dest" -maxdepth 1 -type f | grep -q .; then
    echo "seed corpus is empty after copy: $seed_dir" >&2
    exit 2
  fi
}

run_one_baseline() {
  local baseline="$1"
  local duration="$2"
  local rep="$3"
  local fuzzer
  fuzzer="$(magma_fuzzer_for_baseline "$baseline")"

  local suffix="${baseline}_${duration}s"
  if [[ "$reps" -gt 1 ]]; then
    suffix="${suffix}_rep${rep}"
  fi
  local shared="$out_dir/magma/$suffix"
  local run_out="$out_dir/runs/$suffix"
  mkdir -p "$shared" "$run_out"
  copy_seed_corpus "$shared/input_corpus"

  (
    cd "$magma_dir"
    FUZZER="$fuzzer" TARGET="$magma_target" PROGRAM="$program" \
      ARGS="$args_template" CANARY_MODE=1 SHARED="$shared" POLL="$poll" \
      TIMEOUT="${duration}s" MAGMA_INPUT_CORPUS=/magma_shared/input_corpus \
      MAGMA_SKIP_SEED_PRUNE=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 \
      FORMTRIG_TARGET_BUG="$target_id" ./tools/captain/start.sh
  ) > "$run_out/captain_stdout.log" 2> "$run_out/captain_stderr.log"

  "$repo_root/tools/run_post_reach_baseline.py" \
    --baseline "$baseline" \
    --target-id "$target_id" \
    --tc-category "$tc_category" \
    --seed-corpus "$seed_dir" \
    --out-dir "$run_out" \
    --budget-sec "$duration" \
    --rep "$rep" \
    --mode harvest \
    --existing-fuzzer-out "$shared/findings" \
    --magma-monitor-dir "$shared/monitor" \
    --magma-bug-id "$target_id" \
    --target-cmd "magma/captain $fuzzer $magma_target $program $args_template"
}

wait_for_job_slot() {
  local max_jobs="$1"
  while (( $(jobs -pr | wc -l) >= max_jobs )); do
    if ! wait -n; then
      failed_jobs=1
    fi
  done
}

wait_for_all_jobs() {
  while (( $(jobs -pr | wc -l) > 0 )); do
    if ! wait -n; then
      failed_jobs=1
    fi
  done
  if [[ "$failed_jobs" != "0" ]]; then
    echo "one or more baseline jobs failed" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-id)
      target_id="${2:-}"
      shift 2
      ;;
    --inventory)
      inventory="${2:-}"
      shift 2
      ;;
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
    --reps)
      reps="${2:-}"
      shift 2
      ;;
    --jobs)
      jobs="${2:-}"
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

if [[ -z "$target_id" ]]; then
  echo "--target-id is required" >&2
  usage
  exit 2
fi

inventory="$(abs_path "$inventory")"
magma_dir="$(abs_path "$magma_dir")"
require_path "$inventory"
require_path "$magma_dir/tools/captain/build.sh"
require_path "$magma_dir/tools/captain/start.sh"

magma_target="$(inventory_field project)"
program="$(inventory_field program)"
args_template="$(inventory_field args_template)"
tc_category="$(inventory_field primary_tc_category)"
inventory_seed_corpus="$(inventory_field initial_seed_corpus)"
if [[ "$args_template" != *"@@"* ]]; then
  echo "inventory args_template must contain @@ for AFL substitution: $args_template" >&2
  exit 2
fi

if [[ -z "$out_dir" ]]; then
  out_dir="/tmp/formtrig_${target_id,,}_baselines_${timestamp}"
fi

if [[ -z "$seed_dir" ]]; then
  rnt_seed_dir="$repo_root/artifacts/rnt_corpus/$target_id/seeds"
  if [[ -d "$rnt_seed_dir" ]]; then
    seed_dir="$rnt_seed_dir"
  else
    seed_dir="$(abs_repo_path "$inventory_seed_corpus")"
  fi
fi

mkdir -p "$out_dir"
out_dir="$(abs_path "$out_dir")"
seed_dir="$(abs_path "$seed_dir")"
require_path "$seed_dir"

if ! [[ "$reps" =~ ^[0-9]+$ ]] || [[ "$reps" -lt 1 ]]; then
  echo "--reps must be a positive integer: $reps" >&2
  exit 2
fi
if ! [[ "$jobs" =~ ^[0-9]+$ ]] || [[ "$jobs" -lt 1 ]]; then
  echo "--jobs must be a positive integer: $jobs" >&2
  exit 2
fi

{
  printf 'target_id=%s\n' "$target_id"
  printf 'magma_target=%s\n' "$magma_target"
  printf 'program=%s\n' "$program"
  printf 'args_template=%s\n' "$args_template"
  printf 'tc_category=%s\n' "$tc_category"
  printf 'out_dir=%s\n' "$out_dir"
  printf 'magma_dir=%s\n' "$magma_dir"
  printf 'seed_dir=%s\n' "$seed_dir"
  printf 'inventory=%s\n' "$inventory"
  printf 'baselines=%s\n' "$baselines"
  printf 'durations=%s\n' "$durations"
  printf 'reps=%s\n' "$reps"
  printf 'jobs=%s\n' "$jobs"
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
    for ((rep = 1; rep <= reps; rep++)); do
      while IFS= read -r baseline; do
        if [[ "$jobs" -gt 1 ]]; then
          wait_for_job_slot "$jobs"
          run_one_baseline "$baseline" "$duration" "$rep" &
        else
          run_one_baseline "$baseline" "$duration" "$rep"
        fi
      done < <(split_list "$baselines")
    done
  done < <(split_list "$durations")
  if [[ "$jobs" -gt 1 ]]; then
    wait_for_all_jobs
  fi

  python3 "$repo_root/tools/summarize_post_reach_baselines.py" \
    --root "$out_dir/runs" \
    --out-json "$out_dir/summary.json" \
    --out-tsv "$out_dir/summary.tsv"
fi

echo "$target_id Magma baseline flow complete"
echo "  out=$out_dir"
echo "  magma_target=$magma_target"
echo "  program=$program"
echo "  baselines=$baselines"
echo "  durations=$durations"
echo "  reps=$reps"
echo "  jobs=$jobs"
