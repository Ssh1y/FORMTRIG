#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
afl_fuzz="$aflpp_dir/afl-fuzz"
afl_cc="$aflpp_dir/afl-cc"
work_dir="${TMPDIR:-/tmp}/formtrig_native_smoke.$$"

cleanup() {
  rm -rf "$work_dir"
}
trap cleanup EXIT

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
}

stat_value() {
  awk -F ':' -v key="$1" '{
    lhs = $1
    rhs = $2
    gsub(/^[ \t]+|[ \t]+$/, "", lhs)
    gsub(/^[ \t]+|[ \t]+$/, "", rhs)
    if (lhs == key) print rhs
  }' "$2"
}

require_file "$afl_fuzz"
require_file "$afl_cc"

if ! grep -a -q "FORMTRIG native signal channel enabled" "$afl_fuzz"; then
  echo "AFL++ checkout is not patched for FORMTRIG native guidance." >&2
  echo "Run: $repo_root/patches/aflplusplus/apply_formtrig_patch.sh" >&2
  exit 2
fi

if ldd "$afl_fuzz" 2>/dev/null | grep -qi python; then
  echo "afl-fuzz links against Python; rebuild with NO_PYTHON=1" >&2
  exit 3
fi

mkdir -p "$work_dir/in" "$work_dir/out"
printf '\377' > "$work_dir/in/seed"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror \
  "$repo_root/formtrig/tests/role_signal_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/role_signal_smoke" -lrt -lm
FORMTRIG_LOG="$work_dir/role_signal.jsonl" FORMTRIG_PUBLISH_EAGER=1 \
  "$work_dir/role_signal_smoke"

if ! grep -q '"atom_signals":\[' "$work_dir/role_signal.jsonl"; then
  echo "runtime role smoke did not emit atom_signals" >&2
  exit 4
fi

printf 'role_component 8 123 guard 5 1 20 higher hit 1.0 0.9 201 2001\n' \
  > "$work_dir/role_spec.txt"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror \
  "$repo_root/formtrig/tests/role_spec_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/role_spec_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/role_spec.txt" "$work_dir/role_spec_smoke"

AFL_PATH="$aflpp_dir" "$afl_cc" -I"$repo_root/formtrig/include" \
  "$repo_root/formtrig/tests/native_afl_role_target.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/native_afl_role_target" -lrt -lm

AFL_NO_UI=1 AFL_SKIP_CPUFREQ=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 \
  AFL_NO_AFFINITY=1 AFL_FORMTRIG=1 FORMTRIG_TARGET_BUG=native_afl_smoke \
  FORMTRIG_NO_CRASH=1 FORMTRIG_PROGRESS_LOG=1 \
  "$afl_fuzz" -i "$work_dir/in" -o "$work_dir/out" -V 2 -- \
  "$work_dir/native_afl_role_target" @@ >/dev/null

stats="$work_dir/out/default/fuzzer_stats"
progress="$work_dir/out/default/formtrig_progress.jsonl"
require_file "$stats"
require_file "$progress"

queued_progress="$(stat_value formtrig_queued_progress "$stats")"
typed_execs="$(stat_value formtrig_typed_execs "$stats")"
typed_finds="$(stat_value formtrig_typed_finds "$stats")"
stability_checks="$(stat_value formtrig_stability_checks "$stats")"

if [[ "${queued_progress:-0}" -le 0 ]]; then
  echo "FORMTRIG did not queue progress" >&2
  exit 5
fi

if [[ "${typed_execs:-0}" -le 0 ]]; then
  echo "FORMTRIG typed mutation stage did not run" >&2
  exit 6
fi

if ! grep -q '"atom_signals":[1-9]' "$progress"; then
  echo "AFL++ progress log did not capture atom signals" >&2
  exit 7
fi

if ! grep -q '"role_bits":[1-9]' "$progress"; then
  echo "AFL++ progress log did not capture role bits" >&2
  exit 8
fi

cat <<EOF
FORMTRIG native smoke passed
  queued_progress=$queued_progress
  typed_execs=$typed_execs
  typed_finds=${typed_finds:-0}
  stability_checks=${stability_checks:-0}
EOF
