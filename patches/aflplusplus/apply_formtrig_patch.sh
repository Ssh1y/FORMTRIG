#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
aflpp_dir="${AFLPP_DIR:-}"
patch_file="$script_dir/formtrig_native_runtime.patch"
abi_guard_patch="$script_dir/formtrig_abi_rebuild_guard.patch"
runtime_upgrade_patch="$script_dir/formtrig_native_runtime_upgrade.patch"
asan_exitcode_patch="$script_dir/formtrig_asan_exitcode.patch"
llvm18_cmplog_patch="$script_dir/formtrig_llvm18_cmplog_compat.patch"

default_aflpp_dir() {
  local candidate
  for candidate in \
    "$repo_root/experiments/magma_workspace/magma/fuzzers/formtrig_native/repo" \
    "$repo_root/experiments/aflplusplus/AFLplusplus"
  do
    if aflpp_checkout_usable "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  printf '%s\n' "$repo_root/experiments/aflplusplus/AFLplusplus"
}

aflpp_checkout_usable() {
  local dir="$1"
  [[ -f "$dir/GNUmakefile" && -d "$dir/src" && -d "$dir/include" ]]
}

if [[ -z "$aflpp_dir" ]]; then
  aflpp_dir="$(default_aflpp_dir)"
fi

if ! aflpp_checkout_usable "$aflpp_dir"; then
  echo "AFL++ checkout not found: $aflpp_dir" >&2
  exit 2
fi

apply_patch_once() {
  local patch="$1"
  shift
  local args=("$@")
  local git_top prefix
  git_top="$(git -C "$aflpp_dir" rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$git_top" ]]; then
    prefix="$(git -C "$aflpp_dir" rev-parse --show-prefix)"
    if git -C "$git_top" apply --directory="$prefix" "${args[@]}" \
        --reverse --check "$patch" >/dev/null 2>&1 ||
       patch -d "$aflpp_dir" -p1 -R --dry-run --batch < "$patch" \
        >/dev/null 2>&1; then
      echo "FORMTRIG AFL++ patch already applied: $patch"
    else
      if ! git -C "$git_top" apply --directory="$prefix" "${args[@]}" \
          "$patch" >/dev/null 2>&1; then
        patch -d "$aflpp_dir" -p1 --batch --forward < "$patch"
      fi
      echo "Applied FORMTRIG AFL++ patch: $patch"
    fi
  else
    if patch -d "$aflpp_dir" -p1 -R --dry-run < "$patch" >/dev/null 2>&1; then
      echo "FORMTRIG AFL++ patch already applied: $patch"
    else
      patch -d "$aflpp_dir" -p1 < "$patch"
      echo "Applied FORMTRIG AFL++ patch: $patch"
    fi
  fi
}

if grep -q 'formtrig_capture_last' "$aflpp_dir/src/afl-fuzz-queue.c" &&
   grep -q 'formtrig/formtrig_abi.h' "$aflpp_dir/include/afl-fuzz.h"; then
  echo "FORMTRIG AFL++ native runtime patch already present: $patch_file"
else
  apply_patch_once "$patch_file"
fi
if grep -q 'FORMTRIG_AFLPP_ABI_MARKER' "$aflpp_dir/src/afl-fuzz-queue.c" &&
   grep -q 'FORMTRIG_ABI_HEADER' "$aflpp_dir/GNUmakefile"; then
  echo "FORMTRIG AFL++ ABI rebuild guard already present: $abi_guard_patch"
else
  apply_patch_once "$abi_guard_patch"
fi
if grep -q 'formtrig_meta_atom_signal_count' "$aflpp_dir/src/afl-fuzz-queue.c" &&
   grep -q 'atom_signal_count' "$aflpp_dir/include/afl-fuzz.h"; then
  echo "FORMTRIG AFL++ native runtime patch is current: $runtime_upgrade_patch"
else
  patch -d "$aflpp_dir" -p1 --batch --forward < "$runtime_upgrade_patch"
  echo "Applied FORMTRIG AFL++ native runtime upgrade: $runtime_upgrade_patch"
fi
apply_patch_once "$asan_exitcode_patch" --unidiff-zero
apply_patch_once "$llvm18_cmplog_patch" --unidiff-zero

make -C "$aflpp_dir" afl-fuzz NO_PYTHON=1 \
  FORMTRIG_RUNTIME_ROOT="$repo_root/formtrig" -B
if ldd "$aflpp_dir/afl-fuzz" 2>/dev/null | grep -qi python; then
  echo "afl-fuzz unexpectedly links against Python" >&2
  exit 3
fi

echo "FORMTRIG AFL++ native build is ready: $aflpp_dir/afl-fuzz"
