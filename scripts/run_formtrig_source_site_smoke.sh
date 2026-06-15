#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
clang_bin="${CLANG:-clang}"
llvm_config="${LLVM_CONFIG:-llvm-config}"
work_dir="${TMPDIR:-/tmp}/formtrig_source_site_smoke.$$"

cleanup() {
  rm -rf "$work_dir"
}
trap cleanup EXIT

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing command: $1" >&2
    exit 2
  fi
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
}

require_cmd "$clang_bin"
require_cmd "$llvm_config"
mkdir -p "$work_dir"

pass_out="$work_dir/formtrig_pass.so"
pass_build="$("$repo_root/scripts/build_formtrig_llvm_pass.sh" "$pass_out")"
pass_args_line="$(printf '%s\n' "$pass_build" | sed -n 's/^FORMTRIG_CLANG_PASS_ARGS=//p')"
if [[ -z "$pass_args_line" ]]; then
  echo "FORMTRIG pass build did not report clang pass args" >&2
  printf '%s\n' "$pass_build" >&2
  exit 3
fi
read -r -a pass_args <<< "$pass_args_line"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_site_map.c" \
  -o "$work_dir/formtrig_site_map"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_spec_compile.c" \
  -o "$work_dir/formtrig_binding_spec_compile"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_lift_spec_audit.c" \
  -o "$work_dir/formtrig_lift_spec_audit"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
  "$repo_root/formtrig/tools/formtrig_binding_map.c" \
  -o "$work_dir/formtrig_binding_map"

cat > "$work_dir/source_site_target.c" <<'TARGET'
#include "formtrig/formtrig_runtime.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  FILE *f = fopen(argv[1], "rb");
  if (!f) return 2;
  unsigned char b = 0;
  size_t n = fread(&b, 1, 1, f);
  fclose(f);
  formtrig_register_input(&b, n);
  if (b < 100) return 1;
  formtrig_finalize();
  return 0;
}
TARGET

site_map="$work_dir/site_map.tsv"
FORMTRIG_SITE_MAP="$site_map" "$clang_bin" -g -O0 "${pass_args[@]}" \
  -I"$repo_root/formtrig/include" \
  -c "$work_dir/source_site_target.c" \
  -o "$work_dir/source_site_target.o"
require_file "$site_map"

"$clang_bin" -O0 -I"$repo_root/formtrig/include" \
  -c "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/formtrig_runtime.o"
"$clang_bin" "$work_dir/source_site_target.o" "$work_dir/formtrig_runtime.o" \
  -o "$work_dir/source_site_target" -lrt -lm

tc_line="$(awk '/b < 100/ { print NR; exit }' "$work_dir/source_site_target.c")"
site_ids="$("$work_dir/formtrig_site_map" --file source_site_target.c \
  --line "$tc_line" --kind cmp --emit ids "$site_map")"
if [[ -z "$site_ids" ]]; then
  echo "FORMTRIG site map did not resolve the TC source line" >&2
  cat "$site_map" >&2
  exit 4
fi

"$work_dir/formtrig_site_map" --file source_site_target.c \
  --line "$tc_line" --kind cmp --emit lift-spec --atom 1 \
  --role root_observe --component 3 --priority 10 --direction lower \
  --value-mode distance "$site_map" > "$work_dir/source_site.lift"
"$work_dir/formtrig_site_map" --file source_site_target.c \
  --line "$tc_line" --kind cmp --emit binding-spec \
  --tc-id source_site_numeric --tc-category numeric-margin \
  --tc-expr 'b < 100' --atom 1 --atom-kind numeric-margin \
  --atom-expr 'b < 100' --atom-root b \
  --role root_observe --component 3 --priority 10 --direction lower \
  --value-mode distance "$site_map" > "$work_dir/source_site_binding.yml"
"$work_dir/formtrig_site_map" --file source_site_target.c \
  --line "$tc_line" --kind cmp --emit binding-context \
  --tc-id source_site_numeric --tc-category numeric-margin \
  --tc-expr 'b < 100' --atom 1 --atom-kind numeric-margin \
  --atom-expr 'b < 100' --atom-root b \
  "$site_map" > "$work_dir/source_site_binding_context.json"
if ! grep -q '"schema": "formtrig_binding_context_v1"' \
  "$work_dir/source_site_binding_context.json"; then
  echo "source-site binding context did not declare the expected schema" >&2
  cat "$work_dir/source_site_binding_context.json" >&2
  exit 16
fi
if ! grep -q '"minimum_binding_tier": "B1"' \
  "$work_dir/source_site_binding_context.json"; then
  echo "source-site binding context did not carry numeric minimum tier" >&2
  cat "$work_dir/source_site_binding_context.json" >&2
  exit 17
fi
if ! grep -q '"role": "root_observe"' \
  "$work_dir/source_site_binding_context.json"; then
  echo "source-site binding context did not include root_observe requirement" >&2
  cat "$work_dir/source_site_binding_context.json" >&2
  exit 18
fi
if ! grep -q '"formtrig_binding_signal_diagnose D_F entropy' \
  "$work_dir/source_site_binding_context.json"; then
  echo "source-site binding context did not list dynamic signal gate" >&2
  cat "$work_dir/source_site_binding_context.json" >&2
  exit 19
fi
"$work_dir/formtrig_binding_spec_compile" --site-map "$site_map" \
  --out "$work_dir/source_site_binding.lift" \
  "$work_dir/source_site_binding.yml"
if ! grep -q 'atom_category 1 numeric-margin' \
  "$work_dir/source_site_binding.lift"; then
  echo "source-site BindingSpec did not preserve per-atom category" >&2
  cat "$work_dir/source_site_binding.yml" >&2
  cat "$work_dir/source_site_binding.lift" >&2
  exit 12
fi
if ! grep -q 'role_component 7 .* root_observe 3 1 10 lower distance' \
  "$work_dir/source_site_binding.lift"; then
  echo "source-site BindingSpec did not compile to root_observe lift row" >&2
  cat "$work_dir/source_site_binding.yml" >&2
  cat "$work_dir/source_site_binding.lift" >&2
  exit 13
fi
"$work_dir/formtrig_lift_spec_audit" --category numeric \
  "$work_dir/source_site.lift" > "$work_dir/source_site_audit.csv"
if ! grep -q '1,numeric-margin,B1,true' "$work_dir/source_site_audit.csv"; then
  echo "generated source-site lift spec did not pass B1 numeric audit" >&2
  cat "$work_dir/source_site_audit.csv" >&2
  exit 5
fi
"$work_dir/formtrig_lift_spec_audit" --category generic \
  "$work_dir/source_site_binding.lift" \
  > "$work_dir/source_site_binding_audit.csv"
if ! grep -q '1,numeric-margin,B1,true' \
  "$work_dir/source_site_binding_audit.csv"; then
  echo "source-site BindingSpec output did not pass B1 numeric audit" >&2
  cat "$work_dir/source_site_binding_audit.csv" >&2
  exit 14
fi
"$work_dir/formtrig_binding_map" --category numeric --site-map "$site_map" \
  --normalized-spec "$work_dir/source_site.normalized.lift" \
  "$work_dir/source_site.lift" > "$work_dir/source_site_event_map.csv"
if ! grep -q ',exact,0x00000000,B1,true,ok,' \
  "$work_dir/source_site_event_map.csv"; then
  echo "source-site runtime event-map gate did not allow numeric binding" >&2
  cat "$work_dir/source_site_event_map.csv" >&2
  exit 8
fi
"$work_dir/formtrig_binding_map" --category generic --site-map "$site_map" \
  --normalized-spec "$work_dir/source_site_binding.normalized.lift" \
  "$work_dir/source_site_binding.lift" \
  > "$work_dir/source_site_binding_event_map.csv"
if ! grep -q ',exact,0x00000000,B1,true,ok,' \
  "$work_dir/source_site_binding_event_map.csv"; then
  echo "source-site BindingSpec runtime event-map gate did not allow numeric binding" >&2
  cat "$work_dir/source_site_binding_event_map.csv" >&2
  exit 15
fi

printf '\x78' > "$work_dir/seed"
FORMTRIG_TARGET_SITE_IDS="$site_ids" \
  FORMTRIG_LIFT_SPEC="$work_dir/source_site.normalized.lift" \
  FORMTRIG_LOG="$work_dir/runtime.jsonl" \
  "$work_dir/source_site_target" "$work_dir/seed"

if ! grep -q '"reached":true' "$work_dir/runtime.jsonl"; then
  echo "source-site target did not mark FORMTRIG reached" >&2
  cat "$work_dir/runtime.jsonl" >&2
  exit 6
fi

if ! grep -q '"D_F":21' "$work_dir/runtime.jsonl"; then
  echo "source-site target did not preserve the expected lifted margin" >&2
  cat "$work_dir/runtime.jsonl" >&2
  exit 7
fi
if ! grep -q '"components":\[{' "$work_dir/runtime.jsonl"; then
  echo "source-site target did not emit lifted components" >&2
  cat "$work_dir/runtime.jsonl" >&2
  exit 9
fi
event_id="$(
  awk -F ',' 'NR == 2 { print $7 }' "$work_dir/source_site_event_map.csv"
)"
source_id="$(
  awk 'NR == 1 { print $(NF - 1) }' "$work_dir/source_site.normalized.lift"
)"
if [[ -z "$event_id" || -z "$source_id" ]]; then
  echo "source-site normalized spec did not carry an event id" >&2
  cat "$work_dir/source_site_event_map.csv" >&2
  cat "$work_dir/source_site.normalized.lift" >&2
  exit 10
fi
if ! grep -q "\"source_id\":$source_id" "$work_dir/runtime.jsonl"; then
  echo "source-site lifted component did not reference runtime event-map id" >&2
  echo "event_id=$event_id source_id=$source_id" >&2
  cat "$work_dir/runtime.jsonl" >&2
  exit 11
fi

cat <<EOF
FORMTRIG source-site smoke passed
  pass=$pass_out
  site_ids=$site_ids
  tc_line=$tc_line
EOF
