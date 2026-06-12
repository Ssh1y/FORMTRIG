#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
clang_bin="${CLANG:-clang}"
cxx_bin="${CXX:-}"
llvm_config="${LLVM_CONFIG:-}"
out_dir=""

usage() {
  cat >&2 <<EOF
usage: $0 --out DIR [options]

Builds FORMTRIG's native runtime/pass support files and writes a source-able
environment file for compiling real targets with AFL++ plus FORMTRIG site-map
instrumentation.

options:
  --out DIR         output directory for pass/runtime/env artifacts
  --aflpp-dir DIR   AFL++ checkout/build directory
  --clang CMD       clang used to compile the runtime object
  --clang++ CMD     clang++ used by AFL++ for C++ target builds
  --llvm-config CMD llvm-config used by build_formtrig_llvm_pass.sh

outputs:
  DIR/formtrig_pass.so
  DIR/formtrig_runtime.o
  DIR/libformtrig_runtime.a
  DIR/site_map.tsv
  DIR/formtrig_native_env.sh
EOF
}

quote() {
  printf '%q' "$1"
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --aflpp-dir)
      aflpp_dir="${2:-}"
      shift 2
      ;;
    --clang)
      clang_bin="${2:-}"
      shift 2
      ;;
    --clang++)
      cxx_bin="${2:-}"
      shift 2
      ;;
    --llvm-config)
      llvm_config="${2:-}"
      shift 2
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

if [[ -z "$out_dir" ]]; then
  usage
  exit 2
fi

mkdir -p "$out_dir"
out_dir="$(cd "$out_dir" && pwd)"

if [[ -z "$cxx_bin" ]]; then
  if [[ "$clang_bin" == *clang-* ]]; then
    cxx_bin="${clang_bin/clang-/clang++-}"
  elif [[ "$clang_bin" == *clang ]]; then
    cxx_bin="${clang_bin%clang}clang++"
  else
    cxx_bin="clang++"
  fi
fi

if [[ -z "$llvm_config" ]]; then
  clang_major="$("$clang_bin" --version | sed -n \
    's/.* version \([0-9][0-9]*\).*/\1/p' | head -n 1)"
  if [[ -n "$clang_major" ]] && command -v "llvm-config-$clang_major" \
      >/dev/null 2>&1; then
    llvm_config="llvm-config-$clang_major"
  else
    llvm_config="llvm-config"
  fi
fi

afl_cc="$aflpp_dir/afl-cc"
afl_cxx="$aflpp_dir/afl-c++"
afl_fuzz="$aflpp_dir/afl-fuzz"
require_file "$afl_cc"
require_file "$afl_cxx"
require_file "$afl_fuzz"

if ! grep -a -q "FORMTRIG native signal channel enabled" "$afl_fuzz"; then
  echo "AFL++ checkout is not patched for FORMTRIG native guidance." >&2
  echo "Run: $repo_root/patches/aflplusplus/apply_formtrig_patch.sh" >&2
  exit 3
fi

pass_out="$out_dir/formtrig_pass.so"
pass_build="$(
  CLANG="$clang_bin" LLVM_CONFIG="$llvm_config" \
    "$repo_root/scripts/build_formtrig_llvm_pass.sh" "$pass_out"
)"
pass_args_line="$(printf '%s\n' "$pass_build" | sed -n \
  's/^FORMTRIG_CLANG_PASS_ARGS=//p')"
if [[ -z "$pass_args_line" ]]; then
  echo "FORMTRIG pass build did not report clang pass args" >&2
  printf '%s\n' "$pass_build" >&2
  exit 4
fi

runtime_o="$out_dir/formtrig_runtime.o"
runtime_a="$out_dir/libformtrig_runtime.a"
"$clang_bin" -O2 -fPIC -I"$repo_root/formtrig/include" \
  -c "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$runtime_o"
ar rcs "$runtime_a" "$runtime_o"

site_map="$out_dir/site_map.tsv"
: > "$site_map"

env_file="$out_dir/formtrig_native_env.sh"
{
  printf '# Source this file before configuring/building a FORMTRIG target.\n'
  printf 'export AFL_PATH=%s\n' "$(quote "$aflpp_dir")"
  printf 'export AFL_CC_COMPILER=LLVM\n'
  printf 'export AFL_CC=%s\n' "$(quote "$clang_bin")"
  printf 'export AFL_CXX=%s\n' "$(quote "$cxx_bin")"
  printf 'export CC=%s\n' "$(quote "$afl_cc")"
  printf 'export CXX=%s\n' "$(quote "$afl_cxx")"
  printf 'export FORMTRIG_SITE_MAP=%s\n' "$(quote "$site_map")"
  printf 'export FORMTRIG_PASS_ARGS=%s\n' "$(quote "$pass_args_line")"
  printf 'export FORMTRIG_RUNTIME_OBJECT=%s\n' "$(quote "$runtime_o")"
  printf 'export FORMTRIG_RUNTIME_ARCHIVE=%s\n' "$(quote "$runtime_a")"
  printf 'export FORMTRIG_CFLAGS=%s\n' \
    "$(quote "-gline-tables-only $pass_args_line -I$repo_root/formtrig/include")"
  printf 'export FORMTRIG_CXXFLAGS=%s\n' \
    "$(quote "-gline-tables-only $pass_args_line -I$repo_root/formtrig/include")"
  printf 'export FORMTRIG_LDFLAGS=%s\n' \
    "$(quote "-Wl,--whole-archive $runtime_a -Wl,--no-whole-archive -lrt -lm")"
  printf 'export CFLAGS="${CFLAGS:-} $FORMTRIG_CFLAGS"\n'
  printf 'export CXXFLAGS="${CXXFLAGS:-} $FORMTRIG_CXXFLAGS"\n'
  printf 'export LDFLAGS="${LDFLAGS:-} $FORMTRIG_LDFLAGS"\n'
} > "$env_file"

cat <<EOF
FORMTRIG native build environment prepared
  env=$env_file
  pass=$pass_out
  runtime_object=$runtime_o
  runtime_archive=$runtime_a
  site_map=$site_map
EOF
