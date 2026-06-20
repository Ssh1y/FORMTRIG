#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

mode="execute"
seed_dir=""
seed_dir_set=0
args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      args+=("$1" "$2")
      shift 2
      ;;
    --seed-dir)
      seed_dir="${2:-}"
      seed_dir_set=1
      args+=("$1" "$2")
      shift 2
      ;;
    --help|-h)
      exec "$repo_root/scripts/run_gpac3403_typedops36_matched_longrun.sh" --help
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

if [[ "$seed_dir_set" == "0" ]]; then
  if [[ "$mode" == "dry-run" ]]; then
    seed_dir="$repo_root/artifacts/formtrig_native_readiness/preseeds/gpac3403_b12_scal_ref_scaffold_20260620/corpus"
  else
    work_dir="${FORMTRIG_GPAC3403_B12_SCAFFOLD_WORKDIR:-/tmp/formtrig_gpac3403_b12_scal_ref_scaffold_${timestamp}}"
    raw_dir="$work_dir/raw"
    seed_dir="$work_dir/corpus"
    mkdir -p "$raw_dir" "$seed_dir"

    probe_args=(
      python3 "$repo_root/tools/probe_gpac3403_scal_ref_preseed.py"
      --seed /tmp/formtrig_gpac3403_blackwhite_seed/blackwhite_yuv444p-frame.hevc
      --enhanced-mode copy-base
      --mp4box /tmp/formtrig_gpac3403_src/bin/gcc/MP4Box
      --companion-mp4 "$repo_root/benchmarks/cve_seeds/gpac/white.mp4"
      --out "$raw_dir"
      --out-json "$raw_dir/summary.json"
      --out-md "$raw_dir/summary.md"
    )
    lift_spec="$repo_root/artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_spec_compile_20260620/.formtrig/formtrig_lift.normalized"
    if [[ -f "$lift_spec" ]]; then
      probe_args+=(--lift-spec "$lift_spec")
    fi
    "${probe_args[@]}" > "$raw_dir/probe.stdout.json"
    cp "$raw_dir/two_track_scal_ref.mp4" "$seed_dir/seed_two_track_scal_ref.mp4"
  fi
  args+=(--seed-dir "$seed_dir")
fi

exec "$repo_root/scripts/run_gpac3403_typedops36_matched_longrun.sh" \
  --duration 600 \
  --reps 1 \
  --seed-format mp4-scal-ref-scaffold \
  --binding-spec "$repo_root/artifacts/binding_specs/GPAC_3403.native_b10_extractor_return_candidate.yml" \
  --mutation-hook "$repo_root/scripts/formtrig_hooks/mp4_box_structure_hook.py" \
  --typed-ops 64 \
  --typed-mutation-max 256 \
  --typed-retain-max 128 \
  --typed-retain-mode all \
  "${args[@]}"
