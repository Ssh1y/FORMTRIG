#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

out_dir="/tmp/formtrig_png006_exif_longrun_${timestamp}"
binary="/tmp/formtrig_png007_native_build_20260615T045038Z/libpng_read_fuzzer_env18"
site_map="/tmp/formtrig_png007_native_build_20260615T045038Z/native_env18/site_map.tsv"
binding_spec="$repo_root/artifacts/binding_specs/PNG006.native_b2_exif_insert_candidate.yml"
seed_dir="$repo_root/artifacts/rnt_corpus/PNG006/seeds"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
target_site_ids="3373319550,1343477914"
durations="1800,7200"
run_gate=1

usage() {
  cat >&2 <<EOF
usage: $0 [options]

Runs the validated Magma/libpng PNG006 native FORMTRIG BindingSpec candidate
for long-run acceptance. This is an experiment runner; PNG-specific semantics
remain in the external BindingSpec and mutation hook.

options:
  --out DIR              output directory
  --binary FILE          native libpng_read_fuzzer binary
  --site-map FILE        native FORMTRIG site map for the binary
  --binding-spec FILE    PNG006 BindingSpec
  --seed-dir DIR         RNT seed directory
  --aflpp-dir DIR        patched AFL++ checkout/build
  --target-site-ids IDS  explicit target/root site ids
  --durations LIST       comma/space-separated durations, default 1800,7200
  --no-gate              skip final formtrig_experiment_gate audit
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --binary)
      binary="${2:-}"
      shift 2
      ;;
    --site-map)
      site_map="${2:-}"
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
    --no-gate)
      run_gate=0
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
binary="$(abs_path "$binary")"
site_map="$(abs_path "$site_map")"
binding_spec="$(abs_path "$binding_spec")"
seed_dir="$(abs_path "$seed_dir")"
aflpp_dir="$(abs_path "$aflpp_dir")"

require_path "$binary"
require_path "$site_map"
require_path "$binding_spec"
require_path "$seed_dir"
require_path "$aflpp_dir/afl-fuzz"

{
  printf 'out_dir=%s\n' "$out_dir"
  printf 'binary=%s\n' "$binary"
  printf 'site_map=%s\n' "$site_map"
  printf 'binding_spec=%s\n' "$binding_spec"
  printf 'seed_dir=%s\n' "$seed_dir"
  printf 'target_site_ids=%s\n' "$target_site_ids"
  printf 'durations=%s\n' "$durations"
} > "$out_dir/run_metadata.txt"

declare -a gate_runs=()

while IFS= read -r duration; do
  run_out="$out_dir/png006_exif_${duration}s"
  "$repo_root/scripts/run_formtrig_binding_candidate_sweep.sh" \
    --in "$seed_dir" \
    --out "$run_out" \
    --target-bug PNG006 \
    --category binary-null \
    --site-map "$site_map" \
    --candidate "$binding_spec" \
    --duration "$duration" \
    --seed-preflight require \
    --seed-preflight-max 32 \
    --seed-preflight-timeout 2 \
    --target-site-ids "$target_site_ids" \
    --aflpp-dir "$aflpp_dir" \
    -- "$binary" @@
  gate_runs+=("--run" "PNG006_exif_${duration}s=$run_out/candidates/001_$(basename "$binding_spec")/default")
done < <(split_list "$durations")

if [[ "$run_gate" == "1" ]]; then
  "$repo_root/scripts/formtrig_experiment_gate.sh" \
    --suite PNG006_native_longrun \
    --out "$out_dir/gate" \
    "${gate_runs[@]}"
fi

echo "FORMTRIG PNG006 native longrun complete"
echo "  out=$out_dir"
echo "  metadata=$out_dir/run_metadata.txt"
if [[ "$run_gate" == "1" ]]; then
  echo "  gate=$out_dir/gate/gate_summary.csv"
fi
