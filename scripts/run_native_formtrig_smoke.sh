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

json_number() {
  awk -F ':' -v key="\"$1\"" '{
    lhs = $1
    rhs = $2
    gsub(/^[ \t]+|[ \t]+$/, "", lhs)
    gsub(/^[ \t]+|[ \t,]+$/, "", rhs)
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

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_lift_spec_audit.c" \
  -o "$work_dir/formtrig_lift_spec_audit"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_progress_summary.c" \
  -o "$work_dir/formtrig_progress_summary"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_site_map.c" \
  -o "$work_dir/formtrig_site_map"

cat > "$work_dir/site_map.tsv" <<'SITEMAP'
101	cmp	known_tc	7	icmp	bench/known_tc.c	42	11
102	cmp	known_tc	8	icmp	bench/known_tc.c	42	19
201	binary	helper	3	add	bench/helper.c	9	5
SITEMAP

site_ids="$("$work_dir/formtrig_site_map" --file known_tc.c --line 42 \
  --kind cmp --emit ids "$work_dir/site_map.tsv")"
if [[ "$site_ids" != "101,102" ]]; then
  echo "site-map tool did not resolve source line to site ids" >&2
  echo "site_ids=$site_ids" >&2
  exit 16
fi

"$work_dir/formtrig_site_map" --file known_tc.c --line 42 --kind cmp \
  --emit lift-spec --atom 7 --role root_observe --component 3 \
  --priority 10 --direction lower --value-mode distance \
  "$work_dir/site_map.tsv" > "$work_dir/generated_numeric_lift_spec.txt"

cat > "$work_dir/binary_lift_spec.txt" <<'SPEC'
role_component 8 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 guard 5 1 20 higher hit 1.0 1.0
role_component 8 103 desired_producer 6 1 30 higher hit 1.0 1.0
role_component 8 104 use 6 1 40 higher hit 1.0 1.0
SPEC

"$work_dir/formtrig_lift_spec_audit" --category binary-null \
  "$work_dir/binary_lift_spec.txt" > "$work_dir/binary_lift_audit.csv"

if ! grep -q '1,binary-state-null,B2,true' "$work_dir/binary_lift_audit.csv"; then
  echo "lift spec audit did not allow a B2 binary binding" >&2
  cat "$work_dir/binary_lift_audit.csv" >&2
  exit 9
fi

"$work_dir/formtrig_lift_spec_audit" --category numeric \
  "$work_dir/generated_numeric_lift_spec.txt" \
  > "$work_dir/generated_numeric_lift_audit.csv"
if ! grep -q '7,numeric-margin,B1,true' \
  "$work_dir/generated_numeric_lift_audit.csv"; then
  echo "site-map generated lift spec did not produce a valid B1 numeric binding" >&2
  cat "$work_dir/generated_numeric_lift_audit.csv" >&2
  exit 17
fi

if "$work_dir/formtrig_lift_spec_audit" --category binary-null \
  "$work_dir/role_spec.txt" > "$work_dir/insufficient_lift_audit.csv"; then
  echo "lift spec audit allowed an insufficient binary binding" >&2
  cat "$work_dir/insufficient_lift_audit.csv" >&2
  exit 10
fi

if ! grep -q 'insufficient_binding_tier' \
  "$work_dir/insufficient_lift_audit.csv"; then
  echo "lift spec audit did not explain insufficient binding" >&2
  cat "$work_dir/insufficient_lift_audit.csv" >&2
  exit 11
fi

AFL_PATH="$aflpp_dir" "$afl_cc" -I"$repo_root/formtrig/include" \
  "$repo_root/formtrig/tests/native_afl_role_target.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/native_afl_role_target" -lrt -lm

FORMTRIG_NO_CRASH=1 "$repo_root/scripts/run_formtrig_aflpp_campaign.sh" \
  --in "$work_dir/in" \
  --out "$work_dir/out" \
  --target-bug native_afl_smoke \
  --category binary-null \
  --lift-spec "$work_dir/binary_lift_spec.txt" \
  --target-site-ids "$site_ids" \
  --duration 2 \
  --aflpp-dir "$aflpp_dir" \
  -- "$work_dir/native_afl_role_target" @@ >/dev/null

stats="$work_dir/out/default/fuzzer_stats"
progress="$work_dir/out/default/formtrig_progress.jsonl"
require_file "$stats"
require_file "$progress"

queued_progress="$(stat_value formtrig_queued_progress "$stats")"
typed_execs="$(stat_value formtrig_typed_execs "$stats")"
typed_finds="$(stat_value formtrig_typed_finds "$stats")"
stability_checks="$(stat_value formtrig_stability_checks "$stats")"

summary="$work_dir/out/default/formtrig_summary.json"
require_file "$summary"

summary_queued_progress="$(json_number formtrig_queued_progress "$summary")"
summary_typed_execs="$(json_number formtrig_typed_execs "$summary")"
summary_atom_signals="$(json_number atom_signal_events "$summary")"
summary_role_signals="$(json_number role_signal_events "$summary")"

if [[ "${queued_progress:-0}" -le 0 ]]; then
  echo "FORMTRIG did not queue progress" >&2
  exit 5
fi

if [[ "${typed_execs:-0}" -le 0 ]]; then
  echo "FORMTRIG typed mutation stage did not run" >&2
  exit 6
fi

if [[ "${summary_queued_progress:-0}" -le 0 ||
      "${summary_typed_execs:-0}" -le 0 ]]; then
  echo "FORMTRIG progress summary missed queue or typed execution" >&2
  cat "$summary" >&2
  exit 7
fi

if [[ "${summary_atom_signals:-0}" -le 0 ]]; then
  echo "AFL++ progress summary did not capture atom signals" >&2
  cat "$summary" >&2
  exit 7
fi

if [[ "${summary_role_signals:-0}" -le 0 ]]; then
  echo "AFL++ progress summary did not capture role bits" >&2
  cat "$summary" >&2
  exit 8
fi

if ! grep -Eq '"progress_status": "(progress_queued|triggered)"' "$summary"; then
  echo "FORMTRIG progress summary did not classify progress or trigger" >&2
  cat "$summary" >&2
  exit 12
fi

if ! grep -Eq '"limiting_reason": "(none|terminal_triggered)"' "$summary"; then
  echo "FORMTRIG progress summary reported an unexpected limiting reason" >&2
  cat "$summary" >&2
  exit 13
fi

if ! grep -q '"accept_reason_counts"' "$summary"; then
  echo "FORMTRIG progress summary did not separate accept reasons" >&2
  cat "$summary" >&2
  exit 14
fi

if ! grep -q '"reject_reason_counts"' "$summary"; then
  echo "FORMTRIG progress summary did not separate reject reasons" >&2
  cat "$summary" >&2
  exit 15
fi

cat <<EOF
FORMTRIG native smoke passed
  queued_progress=$queued_progress
  typed_execs=$typed_execs
  typed_finds=${typed_finds:-0}
  stability_checks=${stability_checks:-0}
EOF
