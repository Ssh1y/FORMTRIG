#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
patch_file="$script_dir/formtrig_native_runtime.patch"

if [[ ! -d "$aflpp_dir/.git" ]]; then
  echo "AFL++ checkout not found: $aflpp_dir" >&2
  exit 2
fi

if git -C "$aflpp_dir" apply --reverse --check "$patch_file" >/dev/null 2>&1; then
  echo "FORMTRIG AFL++ patch already applied: $aflpp_dir"
else
  git -C "$aflpp_dir" apply "$patch_file"
  echo "Applied FORMTRIG AFL++ patch: $aflpp_dir"
fi

make -C "$aflpp_dir" afl-fuzz NO_PYTHON=1
if ldd "$aflpp_dir/afl-fuzz" 2>/dev/null | grep -qi python; then
  echo "afl-fuzz unexpectedly links against Python" >&2
  exit 3
fi

echo "FORMTRIG AFL++ native build is ready: $aflpp_dir/afl-fuzz"
