#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

mode="execute"
args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      args+=("$1" "$2")
      shift 2
      ;;
    --help|-h)
      exec "$repo_root/scripts/run_gpac3403_b12_scal_ref_scaffold_matched.sh" --help
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

if [[ "$mode" == "dry-run" ]]; then
  seed_dir="$repo_root/artifacts/formtrig_native_readiness/preseeds/gpac3403_b12_scal_ref_scaffold_20260620/corpus"
  positive_control="$repo_root/artifacts/formtrig_native_readiness/raw/gpac3403_b11_scal_ref_preseed_probe_20260620T023303Z/two_track_scal_ref.mp4"
else
  work_dir="${FORMTRIG_GPAC3403_B12_ENDPOINT_WORKDIR:-/tmp/formtrig_gpac3403_b12_scal_ref_endpoint_${timestamp}}"
  scaffold_raw="$work_dir/scaffold_raw"
  positive_raw="$work_dir/positive_control_raw"
  seed_dir="$work_dir/corpus"
  mkdir -p "$scaffold_raw" "$positive_raw" "$seed_dir"

  common_probe_args=(
    --seed /tmp/formtrig_gpac3403_blackwhite_seed/blackwhite_yuv444p-frame.hevc
    --mp4box /tmp/formtrig_gpac3403_src/bin/gcc/MP4Box
    --companion-mp4 "$repo_root/benchmarks/cve_seeds/gpac/white.mp4"
  )
  lift_spec="$repo_root/artifacts/formtrig_native_readiness/raw/gpac3403_b10_extractor_return_spec_compile_20260620/.formtrig/formtrig_lift.normalized"
  if [[ -f "$lift_spec" ]]; then
    common_probe_args+=(--lift-spec "$lift_spec")
  fi

  python3 "$repo_root/tools/probe_gpac3403_scal_ref_preseed.py" \
    "${common_probe_args[@]}" \
    --enhanced-mode copy-base \
    --out "$scaffold_raw" \
    --out-json "$scaffold_raw/summary.json" \
    --out-md "$scaffold_raw/summary.md" \
    > "$scaffold_raw/probe.stdout.json"
  cp "$scaffold_raw/two_track_scal_ref.mp4" "$seed_dir/seed_two_track_scal_ref.mp4"

  python3 "$repo_root/tools/probe_gpac3403_scal_ref_preseed.py" \
    "${common_probe_args[@]}" \
    --hook "$repo_root/scripts/formtrig_hooks/hevc_annexb_structure_hook.py" \
    --enhanced-mode mutated \
    --out "$positive_raw" \
    --out-json "$positive_raw/summary.json" \
    --out-md "$positive_raw/summary.md" \
    > "$positive_raw/probe.stdout.json"
  positive_control="$positive_raw/two_track_scal_ref.mp4"
fi

exec "$repo_root/scripts/run_gpac3403_b12_scal_ref_scaffold_matched.sh" \
  --duration 60 \
  --reps 1 \
  --arms formtrig \
  --baselines "" \
  --seed-dir "$seed_dir" \
  --typed-retain-endpoint-replay on \
  --typed-retain-endpoint-selection best-d-f \
  --typed-retain-endpoint-timeout 5 \
  --typed-retain-endpoint-replays 1 \
  --typed-retain-endpoint-max-records 32 \
  --typed-retain-endpoint-positive-control "$positive_control" \
  "${args[@]}"
