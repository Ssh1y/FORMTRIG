#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export FORMTRIG_GPAC3403_MP4BOX="${FORMTRIG_GPAC3403_MP4BOX:-/tmp/formtrig_gpac3403_src/bin/gcc/MP4Box}"
export FORMTRIG_GPAC3403_BASE_HEVC="${FORMTRIG_GPAC3403_BASE_HEVC:-/tmp/formtrig_gpac3403_blackwhite_seed/blackwhite_yuv444p-frame.hevc}"
export FORMTRIG_GPAC3403_HEVC_HOOK="${FORMTRIG_GPAC3403_HEVC_HOOK:-$repo_root/scripts/formtrig_hooks/hevc_annexb_structure_hook.py}"
export FORMTRIG_GPAC3403_HEVC_SAMPLE_BIAS="${FORMTRIG_GPAC3403_HEVC_SAMPLE_BIAS:-2}"
export FORMTRIG_GPAC3403_HEVC_OFF="${FORMTRIG_GPAC3403_HEVC_OFF:-6}"

exec "$repo_root/scripts/run_gpac3403_b12_scal_ref_endpoint_gate.sh" \
  --duration 60 \
  --typed-op-start 52 \
  --typed-schedule op-first \
  --mutation-hook "$repo_root/scripts/formtrig_hooks/gpac_scal_ref_mp4_hook.py" \
  "$@"
