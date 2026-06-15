#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
patch_file="$script_dir/formtrig_native_runtime.patch"
asan_exitcode_patch="$script_dir/formtrig_asan_exitcode.patch"
llvm18_cmplog_patch="$script_dir/formtrig_llvm18_cmplog_compat.patch"

if [[ ! -d "$aflpp_dir/.git" ]]; then
  echo "AFL++ checkout not found: $aflpp_dir" >&2
  exit 2
fi

apply_patch_once() {
  local patch="$1"
  shift
  local args=("$@")
  if git -C "$aflpp_dir" apply "${args[@]}" --reverse --check "$patch" \
      >/dev/null 2>&1; then
    echo "FORMTRIG AFL++ patch already applied: $patch"
  else
    git -C "$aflpp_dir" apply "${args[@]}" "$patch"
    echo "Applied FORMTRIG AFL++ patch: $patch"
  fi
}

apply_patch_once "$patch_file"
apply_patch_once "$asan_exitcode_patch" --unidiff-zero
apply_patch_once "$llvm18_cmplog_patch" --unidiff-zero

make -C "$aflpp_dir" afl-fuzz NO_PYTHON=1
if ldd "$aflpp_dir/afl-fuzz" 2>/dev/null | grep -qi python; then
  echo "afl-fuzz unexpectedly links against Python" >&2
  exit 3
fi

echo "FORMTRIG AFL++ native build is ready: $aflpp_dir/afl-fuzz"
