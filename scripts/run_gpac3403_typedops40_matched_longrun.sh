#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$repo_root/scripts/run_gpac3403_typedops36_matched_longrun.sh" --typed-ops 40 "$@"
