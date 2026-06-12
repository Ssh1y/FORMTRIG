#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llvm_config="${LLVM_CONFIG:-llvm-config}"
cxx="${CXX:-clang++}"
out="${1:-$repo_root/build/formtrig_pass.so}"

if ! command -v "$llvm_config" >/dev/null 2>&1; then
  echo "missing llvm-config; set LLVM_CONFIG=/path/to/llvm-config" >&2
  exit 2
fi

if ! command -v "$cxx" >/dev/null 2>&1; then
  echo "missing C++ compiler: $cxx" >&2
  exit 2
fi

mkdir -p "$(dirname "$out")"

"$cxx" -fPIC -shared -I"$repo_root/formtrig/include" \
  $("$llvm_config" --cxxflags --ldflags --system-libs --libs \
    core passes support transformutils) \
  "$repo_root/formtrig/llvm/formtrig_pass.cpp" \
  -o "$out"

version="$("$llvm_config" --version)"
major="${version%%.*}"

echo "$out"
if [[ "$major" =~ ^[0-9]+$ && "$major" -lt 12 ]]; then
  echo "FORMTRIG_CLANG_PASS_ARGS=-Xclang -load -Xclang $out"
else
  echo "FORMTRIG_CLANG_PASS_ARGS=-fpass-plugin=$out"
fi
