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

"$repo_root/scripts/run_formtrig_source_site_smoke.sh" >/dev/null

"$repo_root/scripts/prepare_formtrig_native_env.sh" \
  --out "$work_dir/native_env" >/dev/null
cat > "$work_dir/native_env/env_target.c" <<'TARGET'
#include <stdio.h>

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  FILE *f = fopen(argv[1], "rb");
  if (!f) return 2;
  unsigned char b = 0;
  fread(&b, 1, 1, f);
  fclose(f);
  return b == 42 ? 0 : 1;
}
TARGET
bash -c 'source "$1" && $CC $CFLAGS "$2" $LDFLAGS -o "$3"' _ \
  "$work_dir/native_env/formtrig_native_env.sh" \
  "$work_dir/native_env/env_target.c" \
  "$work_dir/native_env/env_target"
if [[ ! -s "$work_dir/native_env/site_map.tsv" ]]; then
  echo "prepared native build environment did not emit a site map" >&2
  exit 40
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
  -Werror "$repo_root/formtrig/tools/formtrig_campaign_diagnose.c" \
  -o "$work_dir/formtrig_campaign_diagnose"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_site_map.c" \
  -o "$work_dir/formtrig_site_map"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_binding_spec_compile.c" \
  -o "$work_dir/formtrig_binding_spec_compile"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_binding_map.c" \
  -o "$work_dir/formtrig_binding_map"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_lift_feature_audit.c" \
  -o "$work_dir/formtrig_lift_feature_audit"

cat > "$work_dir/initial_only_stats" <<'STATS'
execs_done : 1
corpus_count : 1
formtrig_seen_execs : 1
formtrig_reached_execs : 1
formtrig_triggered_execs : 0
formtrig_queued_progress : 0
formtrig_frontier_updates : 1
formtrig_typed_execs : 0
formtrig_typed_finds : 0
formtrig_stability_checks : 0
formtrig_stability_failures : 0
STATS
cat > "$work_dir/initial_only_progress.jsonl" <<'PROGRESS'
{"event":"frontier_accept","reason":"initial_frontier_seed","reached":true,"triggered":false,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":1,"source_flags":2}
PROGRESS
"$work_dir/formtrig_progress_summary" "$work_dir/initial_only_stats" \
  "$work_dir/initial_only_progress.jsonl" \
  > "$work_dir/initial_only_summary.json"
if ! grep -q '"progress_status": "not_progressing"' \
  "$work_dir/initial_only_summary.json"; then
  echo "progress summary counted initial frontier seed as progress" >&2
  cat "$work_dir/initial_only_summary.json" >&2
  exit 41
fi
if ! grep -q '"frontier_progress_accept_events": 0' \
  "$work_dir/initial_only_summary.json"; then
  echo "progress summary did not separate initial and progress accepts" >&2
  cat "$work_dir/initial_only_summary.json" >&2
  exit 42
fi
"$work_dir/formtrig_campaign_diagnose" \
  "$work_dir/initial_only_summary.json" - \
  > "$work_dir/initial_only_diagnosis.json"
if ! grep -q '"has_tc_rooted_progress": false' \
  "$work_dir/initial_only_diagnosis.json"; then
  echo "campaign diagnosis counted initial frontier seed as progress" >&2
  cat "$work_dir/initial_only_diagnosis.json" >&2
  exit 43
fi

cat > "$work_dir/site_map.tsv" <<'SITEMAP'
101	cmp	known_tc	7	icmp	bench/known_tc.c	42	11
102	branch	known_tc	8	br	bench/known_tc.c	42	19
103	branch	known_tc	9	br	bench/known_tc.c	42	27
104	branch	known_tc	10	br	bench/known_tc.c	42	35
201	binary	helper	3	add	bench/helper.c	9	5
SITEMAP

site_ids="$("$work_dir/formtrig_site_map" --file known_tc.c --line 42 \
  --kind cmp --emit ids "$work_dir/site_map.tsv")"
if [[ "$site_ids" != "101" ]]; then
  echo "site-map tool did not resolve source line to site ids" >&2
  echo "site_ids=$site_ids" >&2
  exit 16
fi

"$work_dir/formtrig_site_map" --file known_tc.c --line 42 --kind cmp \
  --emit lift-spec --atom 7 --role root_observe --component 3 \
  --priority 10 --direction lower --value-mode distance \
  "$work_dir/site_map.tsv" > "$work_dir/generated_numeric_lift_spec.txt"

cat > "$work_dir/binary_lift_spec.txt" <<'SPEC'
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 guard 5 1 20 higher hit 1.0 1.0
role_component 8 103 desired_producer 6 1 30 higher hit 1.0 1.0
role_component 8 104 use 6 1 40 higher hit 1.0 1.0
SPEC

cat > "$work_dir/binary_binding_spec.yml" <<'SPEC'
tc_id: native_afl_smoke
tc:
  category: binary-state-null
  expression: root == NULL
atoms:
  - id: 1
    expr: root == NULL
    kind: binary-state-null
    root: root
bindings:
  - id: root_state
    atom: 1
    role: root_observe
    expr: guard <= 8
    observe_at:
      kind: cmp
      function: known_tc
      file: known_tc.c
      line: 42
      column: 11
    component: boundary_margin
    priority: 10
    direction: lower
    value_mode: distance
    value: 1.0
    confidence: 1.0
  - id: guard_path
    atom: 1
    role: guard
    expr: guard <= 32
    observe_at:
      kind: branch
      function: known_tc
      file: known_tc.c
      line: 42
      column: 19
    component: guard_progress
    priority: 20
    direction: higher
    value_mode: hit
    value: 1.0
    confidence: 1.0
  - id: desired_producer
    atom: 1
    role: desired_producer
    expr: desired_state
    observe_at:
      kind: branch
      function: known_tc
      file: known_tc.c
      line: 42
      column: 27
    component: producer_use
    priority: 30
    direction: higher
    value_mode: hit
    value: 1.0
    confidence: 1.0
  - id: use_context
    atom: 1
    role: use
    expr: use_reached
    observe_at:
      kind: branch
      function: known_tc
      file: known_tc.c
      line: 42
      column: 35
    component: producer_use
    priority: 40
    direction: higher
    value_mode: hit
    value: 1.0
    confidence: 1.0
SPEC

"$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/binary_binding_compiled.lift" \
  "$work_dir/binary_binding_spec.yml"
if ! grep -q 'atom_category 1 binary-state-null' \
  "$work_dir/binary_binding_compiled.lift"; then
  echo "BindingSpec compiler did not emit atom category metadata" >&2
  cat "$work_dir/binary_binding_compiled.lift" >&2
  exit 31
fi
if ! grep -q 'role_component 7 101 root_observe 3 1 10 lower distance' \
  "$work_dir/binary_binding_compiled.lift"; then
  echo "BindingSpec compiler did not emit root_observe lift row" >&2
  cat "$work_dir/binary_binding_compiled.lift" >&2
  exit 27
fi
if ! grep -q 'role_component 8 104 use 6 1 40 higher hit' \
  "$work_dir/binary_binding_compiled.lift"; then
  echo "BindingSpec compiler did not emit use lift row" >&2
  cat "$work_dir/binary_binding_compiled.lift" >&2
  exit 28
fi

cat > "$work_dir/bad_binding_spec.yml" <<'SPEC'
tc_id: bad_native_afl_smoke
tc:
  category: binary-state-null
  expression: root == NULL
atoms:
  - id: 1
    expr: root == NULL
    kind: binary-state-null
    root: root
bindings:
  - id: missing_expr
    atom: 1
    role: root_observe
    observe_at:
      kind: cmp
      function: known_tc
      file: known_tc.c
      line: 42
      column: 11
    component: boundary_margin
    priority: 10
    direction: lower
    value_mode: distance
SPEC
if "$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/bad_binding_compiled.lift" \
  "$work_dir/bad_binding_spec.yml" 2>"$work_dir/bad_binding.err"; then
  echo "BindingSpec compiler allowed a binding without semantic expr" >&2
  cat "$work_dir/bad_binding_compiled.lift" >&2
  exit 29
fi
if ! grep -q 'missing semantic expression' "$work_dir/bad_binding.err"; then
  echo "BindingSpec compiler did not explain missing semantic expr" >&2
  cat "$work_dir/bad_binding.err" >&2
  exit 30
fi

cat > "$work_dir/mixed_lift_spec.txt" <<'SPEC'
atom_category 1 equality-magic
atom_category 2 binary-state-null
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 root_observe 3 2 10 lower distance 1.0 1.0
role_component 8 103 desired_producer 6 2 30 higher hit 1.0 1.0
role_component 8 104 use 6 2 40 higher hit 1.0 1.0
SPEC
"$work_dir/formtrig_lift_spec_audit" --category binary-null \
  "$work_dir/mixed_lift_spec.txt" > "$work_dir/mixed_lift_audit.csv"
if ! grep -q '1,equality-magic,B1,true' \
  "$work_dir/mixed_lift_audit.csv"; then
  echo "lift spec audit did not apply per-atom equality category" >&2
  cat "$work_dir/mixed_lift_audit.csv" >&2
  exit 32
fi
if ! grep -q '2,binary-state-null,B2,true' \
  "$work_dir/mixed_lift_audit.csv"; then
  echo "lift spec audit did not apply per-atom binary category" >&2
  cat "$work_dir/mixed_lift_audit.csv" >&2
  exit 33
fi
"$work_dir/formtrig_binding_map" --category binary-null \
  --site-map "$work_dir/site_map.tsv" \
  --normalized-spec "$work_dir/mixed_lift.normalized" \
  "$work_dir/mixed_lift_spec.txt" \
  > "$work_dir/mixed_runtime_event_map.csv"
if ! grep -q '1,equality-magic,root_observe' \
  "$work_dir/mixed_runtime_event_map.csv"; then
  echo "runtime event-map gate did not preserve equality atom category" >&2
  cat "$work_dir/mixed_runtime_event_map.csv" >&2
  exit 34
fi
if ! grep -q '2,binary-state-null,use' \
  "$work_dir/mixed_runtime_event_map.csv"; then
  echo "runtime event-map gate did not preserve binary atom category" >&2
  cat "$work_dir/mixed_runtime_event_map.csv" >&2
  exit 35
fi

"$work_dir/formtrig_lift_spec_audit" --category binary-null \
  "$work_dir/binary_lift_spec.txt" > "$work_dir/binary_lift_audit.csv"

if ! grep -q '1,binary-state-null,B2,true' "$work_dir/binary_lift_audit.csv"; then
  echo "lift spec audit did not allow a B2 binary binding" >&2
  cat "$work_dir/binary_lift_audit.csv" >&2
  exit 9
fi

"$work_dir/formtrig_binding_map" --category binary-null \
  --site-map "$work_dir/site_map.tsv" \
  --normalized-spec "$work_dir/binary_lift.normalized" \
  "$work_dir/binary_lift_spec.txt" \
  > "$work_dir/runtime_event_map.csv"
if ! grep -q 'binary-state-null,root_observe,7,101,' \
  "$work_dir/runtime_event_map.csv"; then
  echo "runtime event map did not include root binding" >&2
  cat "$work_dir/runtime_event_map.csv" >&2
  exit 18
fi
if ! grep -q ',exact,0x00000000,B2,true,ok,' \
  "$work_dir/runtime_event_map.csv"; then
  echo "runtime event map did not mark B2 binary binding as exact/allowed" >&2
  cat "$work_dir/runtime_event_map.csv" >&2
  exit 19
fi
if ! awk 'NF != 13 { exit 1 }' "$work_dir/binary_lift.normalized"; then
  echo "normalized lift spec did not include source/context event ids" >&2
  cat "$work_dir/binary_lift.normalized" >&2
  exit 22
fi
root_event_id="$(
  awk -F ',' '$4 == "root_observe" { print $7; exit }' \
    "$work_dir/runtime_event_map.csv"
)"
root_source_id="$(
  awk 'NR == 1 { print $(NF - 1) }' "$work_dir/binary_lift.normalized"
)"
cat > "$work_dir/progress_mapped.jsonl" <<PROGRESS
{"event":"frontier_accept","reason":"non_dominated_frontier_seed","triggered":false,"lifted":1,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":21,"source_id":$root_source_id,"context_hash":"0000000000000000","value":4,"confidence":1}]}
PROGRESS
"$work_dir/formtrig_lift_feature_audit" "$work_dir/runtime_event_map.csv" \
  "$work_dir/progress_mapped.jsonl" > "$work_dir/lift_feature_audit_ok.json"
if ! grep -q '"status": "pass"' "$work_dir/lift_feature_audit_ok.json"; then
  echo "lift feature audit rejected mapped lifted component" >&2
  cat "$work_dir/lift_feature_audit_ok.json" >&2
  exit 24
fi
cat > "$work_dir/progress_unmapped.jsonl" <<'PROGRESS'
{"event":"frontier_accept","reason":"non_dominated_frontier_seed","triggered":false,"lifted":1,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":21,"source_id":999999,"context_hash":"0000000000000000","value":4,"confidence":1}]}
PROGRESS
if "$work_dir/formtrig_lift_feature_audit" "$work_dir/runtime_event_map.csv" \
  "$work_dir/progress_unmapped.jsonl" > "$work_dir/lift_feature_audit_bad.json"; then
  echo "lift feature audit allowed unmapped lifted component" >&2
  cat "$work_dir/lift_feature_audit_bad.json" >&2
  exit 25
fi

cat > "$work_dir/collapsed_lift_spec.txt" <<'SPEC'
role_component 8 101 guard 5 1 20 higher hit 1.0 1.0
role_component 8 101 use 6 1 40 higher hit 1.0 1.0
SPEC
if "$work_dir/formtrig_binding_map" --category binary-null \
  --site-map "$work_dir/site_map.tsv" "$work_dir/collapsed_lift_spec.txt" \
  > "$work_dir/collapsed_runtime_event_map.csv"; then
  echo "runtime event-map gate allowed collapsed guard/use binding" >&2
  cat "$work_dir/collapsed_runtime_event_map.csv" >&2
  exit 20
fi
if ! grep -q 'semantic_role_collapse' \
  "$work_dir/collapsed_runtime_event_map.csv"; then
  echo "runtime event-map gate did not explain collapsed guard/use binding" >&2
  cat "$work_dir/collapsed_runtime_event_map.csv" >&2
  exit 21
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
  --binding-spec "$work_dir/binary_binding_spec.yml" \
  --site-map "$work_dir/site_map.tsv" \
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
require_file "$work_dir/out/formtrig_runtime_event_map.csv"
require_file "$work_dir/out/.formtrig/formtrig_lift.normalized"
require_file "$work_dir/out/default/formtrig_lift_feature_audit.json"
require_file "$work_dir/out/default/formtrig_diagnosis.json"
require_file "$work_dir/out/default/formtrig_seed_readiness.json"
if ! awk 'NF != 13 { exit 1 }' \
  "$work_dir/out/.formtrig/formtrig_lift.normalized"; then
  echo "campaign normalized lift spec did not include event ids" >&2
  cat "$work_dir/out/.formtrig/formtrig_lift.normalized" >&2
  exit 23
fi
if ! grep -q '"status": "pass"' \
  "$work_dir/out/default/formtrig_lift_feature_audit.json"; then
  echo "campaign lifted feature audit did not pass" >&2
  cat "$work_dir/out/default/formtrig_lift_feature_audit.json" >&2
  exit 26
fi
if ! grep -q '"status": "pass"' \
  "$work_dir/out/default/formtrig_seed_readiness.json"; then
  echo "campaign seed readiness did not pass for native smoke seed" >&2
  cat "$work_dir/out/default/formtrig_seed_readiness.json" >&2
  exit 46
fi
if ! grep -q '"rnt": 1' "$work_dir/out/default/formtrig_seed_readiness.json"; then
  echo "campaign seed readiness did not find a reached non-trigger seed" >&2
  cat "$work_dir/out/default/formtrig_seed_readiness.json" >&2
  exit 47
fi
if ! grep -q '"spec_lifted": 1' \
  "$work_dir/out/default/formtrig_seed_readiness.json"; then
  echo "campaign seed readiness did not observe spec-driven lifted signal" >&2
  cat "$work_dir/out/default/formtrig_seed_readiness.json" >&2
  exit 48
fi

summary_queued_progress="$(json_number formtrig_queued_progress "$summary")"
summary_typed_execs="$(json_number formtrig_typed_execs "$summary")"
summary_atom_signals="$(json_number atom_signal_events "$summary")"
summary_role_signals="$(json_number role_signal_events "$summary")"
summary_spec_lifted="$(json_number spec_lifted_events "$summary")"
summary_heuristic_lifted="$(json_number heuristic_lifted_events "$summary")"
summary_manual_lifted="$(json_number manual_lifted_events "$summary")"

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

if [[ "${summary_spec_lifted:-0}" -le 0 ]]; then
  echo "progress summary did not report spec-driven lifted source" >&2
  cat "$summary" >&2
  exit 36
fi

if [[ "${summary_heuristic_lifted:-0}" -ne 0 ]]; then
  echo "FORMTRIG-main smoke unexpectedly used heuristic lifted source" >&2
  cat "$summary" >&2
  exit 37
fi

if [[ "${summary_manual_lifted:-0}" -ne 0 ]]; then
  echo "FORMTRIG-main smoke unexpectedly used manual target lifted source" >&2
  cat "$summary" >&2
  exit 38
fi

if ! grep -q '"source_flags":2' "$progress"; then
  echo "progress log did not mark BindingSpec source flags" >&2
  tail -n 20 "$progress" >&2
  exit 39
fi

if ! grep -q '"status": "ready"' \
  "$work_dir/out/default/formtrig_diagnosis.json"; then
  echo "campaign diagnosis did not mark native smoke ready" >&2
  cat "$work_dir/out/default/formtrig_diagnosis.json" >&2
  exit 44
fi

if ! grep -q '"has_tc_rooted_progress": true' \
  "$work_dir/out/default/formtrig_diagnosis.json"; then
  echo "campaign diagnosis missed queued TC-rooted progress" >&2
  cat "$work_dir/out/default/formtrig_diagnosis.json" >&2
  exit 45
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
