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
first_native_site_id="$(awk 'NF { print $1; exit }' \
  "$work_dir/native_env/site_map.tsv")"
selective_site_map="$work_dir/native_env/selective_site_map.tsv"
: > "$selective_site_map"
bash -c 'source "$1" && FORMTRIG_SITE_MAP="$4" FORMTRIG_INSTRUMENT_SITE_IDS="$5" $CC $CFLAGS "$2" $LDFLAGS -o "$3"' _ \
  "$work_dir/native_env/formtrig_native_env.sh" \
  "$work_dir/native_env/env_target.c" \
  "$work_dir/native_env/env_target_selective" \
  "$selective_site_map" \
  "$first_native_site_id"
selective_rows="$(wc -l < "$selective_site_map")"
if [[ "$selective_rows" != "1" ]] ||
   ! awk -v id="$first_native_site_id" '$1 == id { found=1 } END { exit !found }' \
     "$selective_site_map"; then
  echo "compile-time FORMTRIG site allowlist did not restrict instrumentation" >&2
  echo "expected one row for site id $first_native_site_id, got $selective_rows" >&2
  cat "$selective_site_map" >&2
  exit 41
fi
cat > "$work_dir/native_env/allowlist_spec.lift" <<SPEC
role_component 7 $first_native_site_id root_observe 3 1 10 higher hit 1.0 1.0
SPEC
"$repo_root/scripts/formtrig_site_allowlist_from_lift_spec.sh" \
  --lift-spec "$work_dir/native_env/allowlist_spec.lift" \
  --target-site-ids "$first_native_site_id,999999" \
  --out "$work_dir/native_env/generated_site_allowlist.txt"
if ! grep -qx "$first_native_site_id" \
    "$work_dir/native_env/generated_site_allowlist.txt" ||
   ! grep -qx "999999" "$work_dir/native_env/generated_site_allowlist.txt"; then
  echo "site allowlist generator did not include lift-spec and target site ids" >&2
  cat "$work_dir/native_env/generated_site_allowlist.txt" >&2
  exit 42
fi

mkdir -p "$work_dir/in" "$work_dir/out"
printf '\377' > "$work_dir/in/seed"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
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
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/role_spec_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/role_spec_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/role_spec.txt" "$work_dir/role_spec_smoke"

{
  printf 'role_component 11 777 root_observe 3 1 10 lower distance_to_c 42 1.0\n'
  printf 'range * * 2 3 0.8 set_byte 65\n'
} \
  > "$work_dir/value_mode_spec.txt"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/value_mode_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/value_mode_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/value_mode_spec.txt" "$work_dir/value_mode_smoke"

printf 'role_component 11 888 root_observe 3 1 10 lower distance_to_c 20 1.0 pre_reach\n' \
  > "$work_dir/pre_reach_value_mode_spec.txt"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/pre_reach_value_mode_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/pre_reach_value_mode_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/pre_reach_value_mode_spec.txt" \
  FORMTRIG_PRE_REACH_EVENTS=1 \
  "$work_dir/pre_reach_value_mode_smoke"

cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/pre_reach_boundary_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/pre_reach_boundary_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/pre_reach_value_mode_spec.txt" \
  FORMTRIG_PRE_REACH_EVENTS=1 \
  FORMTRIG_TARGET_SITE_IDS=888 \
  "$work_dir/pre_reach_boundary_smoke"

printf 'role_component 8 123 use 6 1 10 higher hit 1.0 1.0 111 2001\nrole_component 8 999 opposite_producer 6 1 20 higher absent 1.0 1.0 222 2001\n' \
  > "$work_dir/absent_value_mode_spec.txt"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/absent_value_mode_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/absent_value_mode_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/absent_value_mode_spec.txt" \
  "$work_dir/absent_value_mode_smoke"

printf 'role_component 8 111 guard 5 1 10 higher outcome 1.0 1.0 1111 3001 pre_reach\nrole_component 8 222 opposite_producer 6 1 20 higher absent 1.0 1.0 2222 3001 any\n' \
  > "$work_dir/pre_reach_absent_value_mode_spec.txt"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/pre_reach_absent_value_mode_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/pre_reach_absent_value_mode_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/pre_reach_absent_value_mode_spec.txt" \
  FORMTRIG_PRE_REACH_EVENTS=1 \
  "$work_dir/pre_reach_absent_value_mode_smoke"

cat > "$work_dir/role_graph_distance_spec.txt" <<'SPEC'
role_component 7 201 root_observe 3 1 10 higher outcome 1.0 1.0
role_component 8 202 use 6 1 20 higher hit 1.0 1.0
role_component 8 203 opposite_producer 6 1 30 higher absent 1.0 1.0
role_component 8 204 desired_producer 6 1 40 higher hit 1.0 1.0
role_component 7 301 root_observe 3 2 10 lower distance 0.0 1.0
role_component 8 302 use 6 2 20 higher hit 1.0 1.0
SPEC
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/role_graph_distance_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/role_graph_distance_smoke" -lrt -lm
FORMTRIG_LIFT_SPEC="$work_dir/role_graph_distance_spec.txt" \
  "$work_dir/role_graph_distance_smoke"

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
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_binding_signal_diagnose.c" \
  -o "$work_dir/formtrig_binding_signal_diagnose"
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Werror "$repo_root/formtrig/tools/formtrig_lift_signal_entropy.c" \
  -o "$work_dir/formtrig_lift_signal_entropy" -lm

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
{"event":"frontier_accept","reason":"initial_frontier_seed","reached":true,"triggered":false,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":1,"source_flags":2,"observed_source_flags":2}
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
if ! grep -q '"observed_spec_lifted_events": 1' \
  "$work_dir/initial_only_summary.json"; then
  echo "progress summary did not report observed spec-driven source" >&2
  cat "$work_dir/initial_only_summary.json" >&2
  exit 52
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

cat > "$work_dir/calibrated_only_stats" <<'STATS'
execs_done : 2
corpus_count : 2
formtrig_seen_execs : 2
formtrig_reached_execs : 2
formtrig_triggered_execs : 0
formtrig_queued_progress : 0
formtrig_frontier_updates : 2
formtrig_typed_execs : 0
formtrig_typed_finds : 0
formtrig_stability_checks : 0
formtrig_stability_failures : 0
STATS
cat > "$work_dir/calibrated_only_progress.jsonl" <<'PROGRESS'
{"event":"calibrated_frontier","reason":"initial_frontier_seed","reached":true,"triggered":false,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":4,"source_flags":2,"observed_source_flags":2}
{"event":"calibrated_frontier","reason":"root_aligned_state_transition","reached":true,"triggered":false,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":3,"source_flags":2,"observed_source_flags":2}
PROGRESS
"$work_dir/formtrig_progress_summary" "$work_dir/calibrated_only_stats" \
  "$work_dir/calibrated_only_progress.jsonl" \
  > "$work_dir/calibrated_only_summary.json"
if ! grep -q '"progress_status": "not_progressing"' \
  "$work_dir/calibrated_only_summary.json"; then
  echo "progress summary counted calibrated frontier as search progress" >&2
  cat "$work_dir/calibrated_only_summary.json" >&2
  exit 53
fi
if ! grep -q '"calibrated_frontier_events": 2' \
  "$work_dir/calibrated_only_summary.json"; then
  echo "progress summary did not report calibrated frontier events" >&2
  cat "$work_dir/calibrated_only_summary.json" >&2
  exit 54
fi
if ! grep -q '"frontier_progress_accept_events": 0' \
  "$work_dir/calibrated_only_summary.json"; then
  echo "progress summary counted calibrated frontier as frontier progress" >&2
  cat "$work_dir/calibrated_only_summary.json" >&2
  exit 55
fi
"$work_dir/formtrig_campaign_diagnose" \
  "$work_dir/calibrated_only_summary.json" - \
  > "$work_dir/calibrated_only_diagnosis.json"
if ! grep -q '"has_tc_rooted_progress": false' \
  "$work_dir/calibrated_only_diagnosis.json"; then
  echo "campaign diagnosis counted calibrated frontier as TC-rooted progress" >&2
  cat "$work_dir/calibrated_only_diagnosis.json" >&2
  exit 56
fi

cat > "$work_dir/trigger_vs_nontrigger_stats" <<'STATS'
execs_done : 4
corpus_count : 3
formtrig_seen_execs : 4
formtrig_reached_execs : 4
formtrig_triggered_execs : 1
formtrig_queued_progress : 2
formtrig_frontier_updates : 2
formtrig_typed_execs : 1
formtrig_typed_finds : 1
formtrig_stability_checks : 1
formtrig_stability_failures : 0
STATS
cat > "$work_dir/trigger_vs_nontrigger_progress.jsonl" <<'PROGRESS'
{"event":"calibrated_frontier","reason":"initial_frontier_seed","reached":true,"triggered":false,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":3,"source_flags":2,"observed_source_flags":2}
{"event":"saved_progress","reason":"lifted-feature improvement","reached":true,"triggered":false,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":2,"source_flags":2,"observed_source_flags":2}
{"event":"saved_progress","reason":"triggered","reached":true,"triggered":true,"lifted":true,"components":1,"actionable_components":1,"atom_signals":1,"role_bits":1,"d_f":0,"source_flags":2,"observed_source_flags":2}
PROGRESS
"$work_dir/formtrig_progress_summary" "$work_dir/trigger_vs_nontrigger_stats" \
  "$work_dir/trigger_vs_nontrigger_progress.jsonl" \
  > "$work_dir/trigger_vs_nontrigger_summary.json"
if ! grep -q '"saved_triggered_progress_events": 1' \
  "$work_dir/trigger_vs_nontrigger_summary.json" ||
   ! grep -q '"saved_non_trigger_progress_events": 1' \
  "$work_dir/trigger_vs_nontrigger_summary.json" ||
   ! grep -q '"non_trigger_progress_events": 1' \
  "$work_dir/trigger_vs_nontrigger_summary.json"; then
  echo "progress summary did not split trigger and non-trigger progress" >&2
  cat "$work_dir/trigger_vs_nontrigger_summary.json" >&2
  exit 76
fi
"$work_dir/formtrig_campaign_diagnose" \
  "$work_dir/trigger_vs_nontrigger_summary.json" - \
  > "$work_dir/trigger_vs_nontrigger_diagnosis.json"
if ! grep -q '"has_non_trigger_progress": true' \
  "$work_dir/trigger_vs_nontrigger_diagnosis.json"; then
  echo "campaign diagnosis did not report non-trigger progress" >&2
  cat "$work_dir/trigger_vs_nontrigger_diagnosis.json" >&2
  exit 77
fi

cat > "$work_dir/observed_manual_summary.json" <<'SUMMARY'
{
  "execs_done": 1,
  "formtrig_seen_execs": 1,
  "formtrig_reached_execs": 1,
  "spec_lifted_events": 1,
  "manual_lifted_events": 0,
  "heuristic_lifted_events": 0,
  "observed_manual_lifted_events": 1,
  "observed_heuristic_lifted_events": 0,
  "actionable_component_events": 1,
  "atom_signal_events": 1,
  "role_signal_events": 1,
  "d_f_spec_lifted_constant": false,
  "has_lifted_signal": true,
  "has_actionable_component": true,
  "has_atom_signal": true,
  "has_role_signal": true,
  "progress_status": "not_progressing",
  "limiting_reason": "no_progress_queued"
}
SUMMARY
"$work_dir/formtrig_campaign_diagnose" \
  "$work_dir/observed_manual_summary.json" - \
  > "$work_dir/observed_manual_diagnosis.json"
if ! grep -q '"diagnosis": "manual_target_lift_observed"' \
  "$work_dir/observed_manual_diagnosis.json"; then
  echo "campaign diagnosis did not reject observed manual lift attempts" >&2
  cat "$work_dir/observed_manual_diagnosis.json" >&2
  exit 69
fi

cat > "$work_dir/guard_only_event_map.csv" <<'CSV'
binding_id,atom_id,category,role,event_kind,site_id,event_id,mapping_status,collapsed_with,binding_tier,lift_allowed,reason,component_kind,priority,direction,value_mode,function,file,line,column,opcode,observe_window
1,1,binary-state-null,root_observe,7,101,0000000000000101,exact,0x00000000,B2,true,ok,3,10,higher,outcome,fn,t.c,10,1,icmp,any
2,1,binary-state-null,guard,7,102,0000000000000102,exact,0x00000000,B2,true,ok,5,20,higher,outcome,fn,t.c,11,1,icmp,any
3,1,binary-state-null,producer,8,103,0000000000000103,exact,0x00000000,B2,true,ok,6,30,higher,hit,fn,t.c,12,1,br,any
4,1,binary-state-null,opposite_producer,8,104,0000000000000104,exact,0x00000000,B2,true,ok,6,40,higher,absent,fn,t.c,13,1,br,any
5,1,binary-state-null,use,8,105,0000000000000105,exact,0x00000000,B2,true,ok,6,50,higher,hit,fn,t.c,14,1,br,any
CSV
cat > "$work_dir/guard_only_stats" <<'STATS'
execs_done : 4
corpus_count : 1
formtrig_seen_execs : 4
formtrig_reached_execs : 4
formtrig_triggered_execs : 0
formtrig_queued_progress : 0
formtrig_frontier_updates : 2
formtrig_typed_execs : 1
formtrig_typed_finds : 0
formtrig_stability_checks : 0
formtrig_stability_failures : 0
STATS
cat > "$work_dir/guard_only_progress.jsonl" <<'PROGRESS'
{"event":"calibrated_frontier","reason":"initial_frontier_seed","reached":true,"triggered":false,"lifted":true,"stable":1,"d_f":5,"d_f_spec_lifted":5,"components":5,"actionable_components":2,"atom_signals":1,"role_bits":55,"source_flags":2,"observed_source_flags":2,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":257,"context_hash":"101","value":0,"confidence":1},{"kind":5,"atom_id":1,"role":2,"priority":20,"flags":86,"source_id":258,"context_hash":"102","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":3,"priority":30,"flags":86,"source_id":259,"context_hash":"103","value":1,"confidence":1},{"kind":6,"atom_id":1,"role":5,"priority":40,"flags":86,"source_id":260,"context_hash":"104","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":50,"flags":86,"source_id":261,"context_hash":"105","value":1,"confidence":1}]}
{"event":"calibrated_frontier","reason":"root_aligned_state_transition","reached":true,"triggered":false,"lifted":true,"stable":1,"d_f":4,"d_f_spec_lifted":4,"components":5,"actionable_components":3,"atom_signals":1,"role_bits":55,"source_flags":2,"observed_source_flags":2,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":257,"context_hash":"101","value":0,"confidence":1},{"kind":5,"atom_id":1,"role":2,"priority":20,"flags":86,"source_id":258,"context_hash":"102","value":1,"confidence":1},{"kind":6,"atom_id":1,"role":3,"priority":30,"flags":86,"source_id":259,"context_hash":"103","value":1,"confidence":1},{"kind":6,"atom_id":1,"role":5,"priority":40,"flags":86,"source_id":260,"context_hash":"104","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":50,"flags":86,"source_id":261,"context_hash":"105","value":1,"confidence":1}]}
{"event":"frontier_reject","reason":"dominated_by_existing_frontier","reached":true,"triggered":false,"lifted":true,"stable":1,"d_f":5,"d_f_spec_lifted":5,"components":5,"actionable_components":2,"atom_signals":1,"role_bits":55,"source_flags":2,"observed_source_flags":2,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":257,"context_hash":"101","value":0,"confidence":1},{"kind":5,"atom_id":1,"role":2,"priority":20,"flags":86,"source_id":258,"context_hash":"102","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":3,"priority":30,"flags":86,"source_id":259,"context_hash":"103","value":1,"confidence":1},{"kind":6,"atom_id":1,"role":5,"priority":40,"flags":86,"source_id":260,"context_hash":"104","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":50,"flags":86,"source_id":261,"context_hash":"105","value":1,"confidence":1}]}
PROGRESS
"$work_dir/formtrig_progress_summary" "$work_dir/guard_only_stats" \
  "$work_dir/guard_only_progress.jsonl" \
  > "$work_dir/guard_only_summary.json"
if "$work_dir/formtrig_binding_signal_diagnose" \
  "$work_dir/guard_only_event_map.csv" "$work_dir/guard_only_progress.jsonl" \
  > "$work_dir/guard_only_signal_diagnosis.json"; then
  echo "binding signal diagnosis allowed guard-only binary lift" >&2
  cat "$work_dir/guard_only_signal_diagnosis.json" >&2
  exit 75
fi
if ! grep -q '"diagnosis": "guard_only_lift_signal"' \
  "$work_dir/guard_only_signal_diagnosis.json"; then
  echo "binding signal diagnosis did not identify guard-only lift" >&2
  cat "$work_dir/guard_only_signal_diagnosis.json" >&2
  exit 76
fi
"$work_dir/formtrig_campaign_diagnose" "$work_dir/guard_only_summary.json" \
  "$work_dir/guard_only_event_map.csv" - \
  "$work_dir/guard_only_signal_diagnosis.json" \
  > "$work_dir/guard_only_campaign_diagnosis.json"
if ! grep -q '"status": "not_ready"' \
  "$work_dir/guard_only_campaign_diagnosis.json"; then
  echo "campaign diagnosis marked guard-only lift ready" >&2
  cat "$work_dir/guard_only_campaign_diagnosis.json" >&2
  exit 77
fi
if ! grep -q '"diagnosis": "guard_only_lift_signal"' \
  "$work_dir/guard_only_campaign_diagnosis.json"; then
  echo "campaign diagnosis did not surface guard-only lift reason" >&2
  cat "$work_dir/guard_only_campaign_diagnosis.json" >&2
  exit 78
fi

cat > "$work_dir/variable_runtime_signal.jsonl" <<'JSONL'
{"reached":true,"crash_predicate":false,"D_F_spec_lifted":3,"uses_spec_lifted":true,"components":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":101,"context_hash":"0","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":20,"flags":86,"source_id":102,"context_hash":"0","value":1,"confidence":1}]}
{"reached":true,"crash_predicate":false,"D_F_spec_lifted":2,"uses_spec_lifted":true,"components":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":101,"context_hash":"0","value":1,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":20,"flags":86,"source_id":102,"context_hash":"0","value":1,"confidence":1}]}
JSONL
"$work_dir/formtrig_lift_signal_entropy" \
  "$work_dir/variable_runtime_signal.jsonl" \
  > "$work_dir/variable_runtime_signal_entropy.json"
if ! grep -q '"status": "pass"' \
  "$work_dir/variable_runtime_signal_entropy.json"; then
  echo "lift signal entropy audit did not accept variable signal" >&2
  cat "$work_dir/variable_runtime_signal_entropy.json" >&2
  exit 70
fi
if ! grep -q '"variable_components": 1' \
  "$work_dir/variable_runtime_signal_entropy.json"; then
  echo "lift signal entropy audit did not find variable component" >&2
  cat "$work_dir/variable_runtime_signal_entropy.json" >&2
  exit 71
fi
if ! grep -q '"variable_actionable_components": 1' \
  "$work_dir/variable_runtime_signal_entropy.json"; then
  echo "lift signal entropy audit did not find variable actionable component" >&2
  cat "$work_dir/variable_runtime_signal_entropy.json" >&2
  exit 71
fi

cat > "$work_dir/constant_scalar_variable_component.jsonl" <<'JSONL'
{"reached":true,"crash_predicate":false,"D_F_spec_lifted":3,"uses_spec_lifted":true,"components":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":101,"context_hash":"0","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":20,"flags":86,"source_id":102,"context_hash":"0","value":1,"confidence":1}]}
{"reached":true,"crash_predicate":false,"D_F_spec_lifted":3,"uses_spec_lifted":true,"components":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":101,"context_hash":"0","value":1,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":20,"flags":86,"source_id":102,"context_hash":"0","value":1,"confidence":1}]}
JSONL
"$work_dir/formtrig_lift_signal_entropy" \
  "$work_dir/constant_scalar_variable_component.jsonl" \
  > "$work_dir/constant_scalar_variable_component_entropy.json"
if ! grep -q '"status": "pass"' \
  "$work_dir/constant_scalar_variable_component_entropy.json"; then
  echo "lift signal entropy audit rejected variable component behind constant scalar D_F" >&2
  cat "$work_dir/constant_scalar_variable_component_entropy.json" >&2
  exit 72
fi
if ! grep -q '"diagnosis": "constant_scalar_d_f_variable_components"' \
  "$work_dir/constant_scalar_variable_component_entropy.json"; then
  echo "lift signal entropy audit did not explain constant scalar/variable component split" >&2
  cat "$work_dir/constant_scalar_variable_component_entropy.json" >&2
  exit 73
fi

cat > "$work_dir/constant_runtime_signal.jsonl" <<'JSONL'
{"reached":true,"crash_predicate":false,"D_F_spec_lifted":3,"uses_spec_lifted":true,"components":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":101,"context_hash":"0","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":20,"flags":86,"source_id":102,"context_hash":"0","value":1,"confidence":1}]}
{"reached":true,"crash_predicate":false,"D_F_spec_lifted":3,"uses_spec_lifted":true,"components":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":86,"source_id":101,"context_hash":"0","value":0,"confidence":1},{"kind":6,"atom_id":1,"role":6,"priority":20,"flags":86,"source_id":102,"context_hash":"0","value":1,"confidence":1}]}
JSONL
if "$work_dir/formtrig_lift_signal_entropy" \
  "$work_dir/constant_runtime_signal.jsonl" \
  > "$work_dir/constant_runtime_signal_entropy.json"; then
  echo "lift signal entropy audit accepted constant lifted component vector" >&2
  cat "$work_dir/constant_runtime_signal_entropy.json" >&2
  exit 74
fi
if ! grep -q '"constant_components": 2' \
  "$work_dir/constant_runtime_signal_entropy.json"; then
  echo "lift signal entropy audit did not report constant components" >&2
  cat "$work_dir/constant_runtime_signal_entropy.json" >&2
  exit 75
fi

cat > "$work_dir/site_map.tsv" <<'SITEMAP'
101	cmp	known_tc	7	icmp	bench/known_tc.c	42	11
102	branch	known_tc	8	br	bench/known_tc.c	42	19
103	branch	known_tc	9	br	bench/known_tc.c	42	27
104	branch	known_tc	10	br	bench/known_tc.c	42	35
105	cmp	ambiguous_tc	5	icmp	bench/ambig.c	77	3
106	cmp	ambiguous_tc	6	icmp	bench/ambig.c	77	3
201	binary	helper	3	add	bench/helper.c	9	5
SITEMAP

large_site_map="$work_dir/large_site_map.tsv"
: > "$large_site_map"
for i in $(seq 1 9000); do
  printf '%s\tcmp\tfiller\t1\ticmp\tbench/filler.c\t1\t1\n' "$i" \
    >> "$large_site_map"
done
printf '9101\tcmp\tlate_tc\t17\ticmp\tbench/late.c\t4242\t9\n' \
  >> "$large_site_map"
"$work_dir/formtrig_site_map" --file late.c --line 4242 --kind cmp \
  --emit binding-context \
  --tc-id late_context_smoke \
  --tc-category numeric-margin \
  --tc-expr 'late == 1' \
  --atom 1 \
  --atom-kind numeric-margin \
  --atom-expr 'late == 1' \
  --atom-root late \
  "$large_site_map" > "$work_dir/late_binding_context.json"
if ! grep -q '"site_id": 9101' "$work_dir/late_binding_context.json"; then
  echo "site-map binding-context dropped matched rows after early map prefix" >&2
  cat "$work_dir/late_binding_context.json" >&2
  exit 76
fi

cat > "$work_dir/canary_binding_spec.yml" <<'SPEC'
tc_id: canary_smoke
tc:
  category: numeric-margin
  expression: canary_smoke exposed
atoms:
  - id: 1
    expr: canary_smoke exposed
    kind: numeric-margin
    root: canary_smoke
bindings:
  - id: canary_root
    atom: 1
    role: root_observe
    expr: selected canary label observed
    observe_at:
      kind: canary
      label: canary_smoke
    component: boundary_margin
    priority: 10
    direction: higher
    value_mode: hit
    value: 1.0
    confidence: 0.8
SPEC
"$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/canary_binding.lift" \
  "$work_dir/canary_binding_spec.yml"
if ! grep -q 'role_component 13 .* root_observe 3 1 10 higher hit 1.0 0.8' \
  "$work_dir/canary_binding.lift"; then
  echo "BindingSpec compiler did not emit a canary root_observe binding" >&2
  cat "$work_dir/canary_binding.lift" >&2
  exit 63
fi
if "$work_dir/formtrig_lift_spec_audit" --category numeric \
  "$work_dir/canary_binding.lift" > "$work_dir/canary_lift_audit.csv"; then
  echo "lift spec audit allowed canary hit as stateful B1 root" >&2
  cat "$work_dir/canary_lift_audit.csv" >&2
  exit 64
fi
if ! grep -q 'missing_stateful_root_observe' \
  "$work_dir/canary_lift_audit.csv"; then
  echo "lift spec audit did not explain canary hit rejection" >&2
  cat "$work_dir/canary_lift_audit.csv" >&2
  exit 64
fi
if "$work_dir/formtrig_binding_map" --category numeric \
  --site-map "$work_dir/site_map.tsv" \
  --normalized-spec "$work_dir/canary_binding.normalized" \
  "$work_dir/canary_binding.lift" \
  > "$work_dir/canary_runtime_event_map.csv"; then
  echo "runtime event-map gate accepted canary hit as lifted root state" >&2
  cat "$work_dir/canary_runtime_event_map.csv" >&2
  exit 65
fi
if ! grep -q 'numeric-margin,root_observe,13,.*exact,0x00000000,B0,false,missing_stateful_root_observe' \
  "$work_dir/canary_runtime_event_map.csv"; then
  echo "runtime event-map gate did not explain canary hit rejection" >&2
  cat "$work_dir/canary_runtime_event_map.csv" >&2
  exit 65
fi
canary_site_id="$(awk '$1 == "role_component" { print $3; exit }' \
  "$work_dir/canary_binding.lift")"
if [[ -z "$canary_site_id" ]]; then
  echo "compiled canary lift spec did not contain a site id" >&2
  cat "$work_dir/canary_binding.lift" >&2
  exit 66
fi
cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra \
  -Wno-unused-parameter -Werror -DFORMTRIG_USE_AFL_MAP_FALLBACK=1 \
  "$repo_root/formtrig/tests/canary_binding_smoke.c" \
  "$repo_root/formtrig/runtime/formtrig_runtime.c" \
  -o "$work_dir/canary_binding_smoke" -lrt -lm
FORMTRIG_TARGET_BUG=canary_smoke \
  FORMTRIG_TARGET_SITE_IDS="$canary_site_id" \
  FORMTRIG_LIFT_SPEC="$work_dir/canary_binding.lift" \
  "$work_dir/canary_binding_smoke"

cat > "$work_dir/bad_canary_binding_spec.yml" <<'SPEC'
tc_id: bad_canary_smoke
tc:
  category: numeric-margin
  expression: canary_smoke exposed
atoms:
  - id: 1
    expr: canary_smoke exposed
    kind: numeric-margin
    root: canary_smoke
bindings:
  - id: canary_root_oracle
    atom: 1
    role: root_observe
    expr: selected canary label observed
    observe_at:
      kind: canary
      label: canary_smoke
    component: boundary_margin
    priority: 10
    direction: higher
    value_mode: outcome
    value: 1.0
    confidence: 0.8
SPEC
if "$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/bad_canary_binding.lift" \
  "$work_dir/bad_canary_binding_spec.yml" 2>"$work_dir/bad_canary.err"; then
  echo "BindingSpec compiler allowed canary outcome oracle leakage" >&2
  cat "$work_dir/bad_canary_binding.lift" >&2
  exit 67
fi
if ! grep -q 'canary binding may only use value_mode=hit' \
  "$work_dir/bad_canary.err"; then
  echo "BindingSpec compiler did not explain canary oracle leakage rejection" >&2
  cat "$work_dir/bad_canary.err" >&2
  exit 68
fi

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

ambig_site_ids="$("$work_dir/formtrig_site_map" --file ambig.c --line 77 \
  --kind cmp --inst-no 6 --emit ids "$work_dir/site_map.tsv")"
if [[ "$ambig_site_ids" != "106" ]]; then
  echo "site-map tool did not use inst_no to disambiguate source line" >&2
  echo "ambig_site_ids=$ambig_site_ids" >&2
  exit 57
fi

"$work_dir/formtrig_site_map" --file ambig.c --line 77 --kind cmp \
  --inst-no 6 --emit binding-spec \
  --tc-id inst_disambiguation_smoke \
  --tc-category numeric-margin \
  --tc-expr 'root == 7' \
  --atom 1 \
  --atom-kind numeric-margin \
  --atom-expr 'root == 7' \
  --atom-root root \
  --role root_observe \
  --component boundary_margin \
  --priority 10 \
  --direction lower \
  --value-mode distance_to_c \
  --value 42 \
  --observe-window pre_reach \
  "$work_dir/site_map.tsv" > "$work_dir/inst_disambiguated_binding.yml"
"$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/inst_disambiguated_binding.lift" \
  "$work_dir/inst_disambiguated_binding.yml"
if ! grep -q 'role_component 7 106 root_observe 3 1 10 lower distance_to_c 42 1 pre_reach' \
  "$work_dir/inst_disambiguated_binding.lift"; then
  echo "BindingSpec compiler did not preserve inst_no and distance_to_c" >&2
  cat "$work_dir/inst_disambiguated_binding.yml" >&2
  cat "$work_dir/inst_disambiguated_binding.lift" >&2
  exit 58
fi

cat > "$work_dir/stale_inst_binding.yml" <<'SPEC'
tc_id: stale_inst_rebind_smoke
tc:
  category: numeric-margin
  expression: root == 42
atoms:
  - id: 1
    expr: root == 42
    kind: numeric-margin
    root: root
bindings:
  - id: stale_inst_root
    atom: 1
    role: root_observe
    expr: root == 42
    observe_at:
      kind: binary
      function: helper
      file: helper.c
      line: 9
      inst_no: 999
      opcode: add
      column: 5
    component: boundary_margin
    priority: 10
    direction: lower
    value_mode: distance_to_c
    value: 42
    confidence: 1
SPEC
"$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/stale_inst_binding.lift" \
  "$work_dir/stale_inst_binding.yml" 2>"$work_dir/stale_inst_binding.err"
if ! grep -q 'role_component 11 201 root_observe 3 1 10 lower distance_to_c 42 1' \
  "$work_dir/stale_inst_binding.lift"; then
  echo "BindingSpec compiler did not rebind a stale inst_no by stable source location" >&2
  cat "$work_dir/stale_inst_binding.err" >&2
  cat "$work_dir/stale_inst_binding.lift" >&2
  exit 59
fi
if ! grep -q 'relaxed_inst_no' "$work_dir/stale_inst_binding.err"; then
  echo "BindingSpec compiler did not audit relaxed inst_no rebinding" >&2
  cat "$work_dir/stale_inst_binding.err" >&2
  exit 60
fi

cat > "$work_dir/bad_same_object_binding.yml" <<'SPEC'
tc_id: bad_same_object_relation_smoke
tc:
  category: compound-sequence-lifecycle
  expression: free(obj) before use(obj)
atoms:
  - id: 1
    expr: free(obj) before use(obj)
    kind: compound-sequence-lifecycle
    root: obj
bindings:
  - id: object_identity_without_relation
    atom: 1
    role: same_object
    expr: obj
    observe_at:
      kind: binary
      site_id: 201
    component: object_identity
    priority: 40
    direction: higher
    value_mode: a
SPEC
if "$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/bad_same_object_binding.lift" \
  "$work_dir/bad_same_object_binding.yml" 2>"$work_dir/bad_same_object.err"; then
  echo "BindingSpec compiler allowed same_object without a relation" >&2
  cat "$work_dir/bad_same_object_binding.lift" >&2
  exit 87
fi
if ! grep -q 'same_object binding is missing relation_from' \
  "$work_dir/bad_same_object.err"; then
  echo "BindingSpec compiler did not explain missing same_object relation fields" >&2
  cat "$work_dir/bad_same_object.err" >&2
  exit 88
fi

cat > "$work_dir/same_object_binding.yml" <<'SPEC'
tc_id: same_object_relation_smoke
tc:
  category: compound-sequence-lifecycle
  expression: free(obj) before use(obj)
atoms:
  - id: 1
    expr: free(obj) before use(obj)
    kind: compound-sequence-lifecycle
    root: obj
bindings:
  - id: lifecycle_event
    atom: 1
    role: lifecycle_event
    expr: free(obj)
    observe_at:
      kind: branch
      site_id: 102
    component: lifecycle_prefix
    priority: 20
    direction: higher
    value_mode: hit
  - id: use_event
    atom: 1
    role: use
    expr: use(obj)
    observe_at:
      kind: branch
      site_id: 103
    component: producer_use
    priority: 30
    direction: higher
    value_mode: hit
  - id: object_identity
    atom: 1
    role: same_object
    expr: obj
    observe_at:
      kind: binary
      site_id: 201
    component: object_identity
    priority: 40
    direction: higher
    value_mode: a
    relation_from: lifecycle_event
    relation_to: use
    object_expr: obj
SPEC
"$work_dir/formtrig_binding_spec_compile" --site-map "$work_dir/site_map.tsv" \
  --out "$work_dir/same_object_binding.lift" \
  "$work_dir/same_object_binding.yml"
if ! grep -q 'same_object_relation 1 lifecycle_event use obj' \
  "$work_dir/same_object_binding.lift"; then
  echo "BindingSpec compiler did not emit same_object relation metadata" >&2
  cat "$work_dir/same_object_binding.lift" >&2
  exit 89
fi

cat > "$work_dir/binary_lift_spec.txt" <<'SPEC'
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 guard 5 1 20 higher hit 1.0 1.0
role_component 8 103 desired_producer 6 1 30 higher hit 1.0 1.0
role_component 8 104 use 6 1 40 higher hit 1.0 1.0
SPEC

cat > "$work_dir/lifecycle_same_object_hit_spec.txt" <<'SPEC'
atom_category 1 compound-sequence-lifecycle
role_component 7 101 root_observe 3 1 10 higher outcome 1.0 1.0
role_component 8 102 lifecycle_event 7 1 20 higher hit 1.0 1.0
role_component 8 103 use 6 1 30 higher hit 1.0 1.0
role_component 11 201 same_object 8 1 40 higher hit 1.0 1.0
SPEC
cat > "$work_dir/lifecycle_same_object_value_spec.txt" <<'SPEC'
atom_category 1 compound-sequence-lifecycle
role_component 7 101 root_observe 3 1 10 higher outcome 1.0 1.0
role_component 8 102 lifecycle_event 7 1 20 higher hit 1.0 1.0
role_component 8 103 use 6 1 30 higher hit 1.0 1.0
role_component 11 201 same_object 8 1 40 higher a 1.0 1.0
same_object_relation 1 lifecycle_event use loop
SPEC
cat > "$work_dir/lifecycle_same_object_no_relation_spec.txt" <<'SPEC'
atom_category 1 compound-sequence-lifecycle
role_component 7 101 root_observe 3 1 10 higher outcome 1.0 1.0
role_component 8 102 lifecycle_event 7 1 20 higher hit 1.0 1.0
role_component 8 103 use 6 1 30 higher hit 1.0 1.0
role_component 11 201 same_object 8 1 40 higher a 1.0 1.0
SPEC
if "$work_dir/formtrig_lift_spec_audit" --category lifecycle \
  "$work_dir/lifecycle_same_object_hit_spec.txt" \
  > "$work_dir/lifecycle_same_object_hit_audit.csv"; then
  echo "lift spec audit allowed lifecycle same_object without object value" >&2
  cat "$work_dir/lifecycle_same_object_hit_audit.csv" >&2
  exit 77
fi
if ! grep -q 'missing_stateful_same_object' \
  "$work_dir/lifecycle_same_object_hit_audit.csv"; then
  echo "lift spec audit did not explain non-stateful same_object rejection" >&2
  cat "$work_dir/lifecycle_same_object_hit_audit.csv" >&2
  exit 78
fi
if "$work_dir/formtrig_binding_map" --category lifecycle \
  --site-map "$work_dir/site_map.tsv" \
  "$work_dir/lifecycle_same_object_hit_spec.txt" \
  > "$work_dir/lifecycle_same_object_hit_map.csv"; then
  echo "runtime event-map gate allowed lifecycle same_object without object value" >&2
  cat "$work_dir/lifecycle_same_object_hit_map.csv" >&2
  exit 79
fi
if ! grep -q 'missing_stateful_same_object' \
  "$work_dir/lifecycle_same_object_hit_map.csv"; then
  echo "runtime event-map gate did not explain non-stateful same_object rejection" >&2
  cat "$work_dir/lifecycle_same_object_hit_map.csv" >&2
  exit 80
fi
if "$work_dir/formtrig_lift_spec_audit" --category lifecycle \
  "$work_dir/lifecycle_same_object_no_relation_spec.txt" \
  > "$work_dir/lifecycle_same_object_no_relation_audit.csv"; then
  echo "lift spec audit allowed lifecycle same_object without a relation" >&2
  cat "$work_dir/lifecycle_same_object_no_relation_audit.csv" >&2
  exit 83
fi
if ! grep -q 'missing_same_object_relation' \
  "$work_dir/lifecycle_same_object_no_relation_audit.csv"; then
  echo "lift spec audit did not explain missing same_object relation" >&2
  cat "$work_dir/lifecycle_same_object_no_relation_audit.csv" >&2
  exit 84
fi
if "$work_dir/formtrig_binding_map" --category lifecycle \
  --site-map "$work_dir/site_map.tsv" \
  "$work_dir/lifecycle_same_object_no_relation_spec.txt" \
  > "$work_dir/lifecycle_same_object_no_relation_map.csv"; then
  echo "runtime event-map gate allowed lifecycle same_object without relation" >&2
  cat "$work_dir/lifecycle_same_object_no_relation_map.csv" >&2
  exit 85
fi
if ! grep -q 'missing_same_object_relation' \
  "$work_dir/lifecycle_same_object_no_relation_map.csv"; then
  echo "runtime event-map gate did not explain missing same_object relation" >&2
  cat "$work_dir/lifecycle_same_object_no_relation_map.csv" >&2
  exit 86
fi
"$work_dir/formtrig_lift_spec_audit" --category lifecycle \
  "$work_dir/lifecycle_same_object_value_spec.txt" \
  > "$work_dir/lifecycle_same_object_value_audit.csv"
if ! grep -q '1,compound-sequence-lifecycle,B3,true' \
  "$work_dir/lifecycle_same_object_value_audit.csv"; then
  echo "lift spec audit rejected lifecycle same_object with object value" >&2
  cat "$work_dir/lifecycle_same_object_value_audit.csv" >&2
  exit 81
fi
"$work_dir/formtrig_binding_map" --category lifecycle \
  --site-map "$work_dir/site_map.tsv" \
  "$work_dir/lifecycle_same_object_value_spec.txt" \
  > "$work_dir/lifecycle_same_object_value_map.csv"
if ! grep -q 'compound-sequence-lifecycle,same_object,11,201' \
  "$work_dir/lifecycle_same_object_value_map.csv"; then
  echo "runtime event-map gate rejected lifecycle same_object with object value" >&2
  cat "$work_dir/lifecycle_same_object_value_map.csv" >&2
  exit 82
fi

cat > "$work_dir/equality_repair_lift_spec.txt" <<'SPEC'
atom_category 1 equality-magic
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 repair_hook 2 1 50 higher hit 1.0 1.0
SPEC

cat > "$work_dir/mixed_atom_category_missing_spec.txt" <<'SPEC'
atom_category 1 equality-magic
atom_category 2 binary-state-null
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 root_observe 3 2 10 lower distance 1.0 1.0
SPEC

if "$work_dir/formtrig_binding_map" --category equality \
  --site-map "$work_dir/site_map.tsv" \
  "$work_dir/mixed_atom_category_missing_spec.txt" \
  > "$work_dir/mixed_atom_category_missing_map.csv"; then
  echo "per-atom category gate allowed an insufficient binary-null atom" >&2
  cat "$work_dir/mixed_atom_category_missing_map.csv" >&2
  exit 59
fi
if ! grep -q '1,equality-magic,root_observe.*B1,true,ok' \
  "$work_dir/mixed_atom_category_missing_map.csv"; then
  echo "per-atom category gate did not allow equality B1 atom" >&2
  cat "$work_dir/mixed_atom_category_missing_map.csv" >&2
  exit 60
fi
if ! grep -q '2,binary-state-null,root_observe.*B1,false,missing_root_or_use' \
  "$work_dir/mixed_atom_category_missing_map.csv"; then
  echo "per-atom category gate let binary-null atom use fallback equality tier" >&2
  cat "$work_dir/mixed_atom_category_missing_map.csv" >&2
  exit 61
fi

cat > "$work_dir/mixed_atom_category_bound_spec.txt" <<'SPEC'
atom_category 1 equality-magic
atom_category 2 binary-state-null
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 102 root_observe 3 2 10 lower distance 1.0 1.0
role_component 8 103 producer 6 2 20 higher hit 1.0 1.0
role_component 8 104 use 6 2 30 higher hit 1.0 1.0
SPEC

"$work_dir/formtrig_binding_map" --category equality \
  --site-map "$work_dir/site_map.tsv" \
  "$work_dir/mixed_atom_category_bound_spec.txt" \
  > "$work_dir/mixed_atom_category_bound_map.csv"
if ! grep -q '2,binary-state-null,root_observe.*B2,true,ok' \
  "$work_dir/mixed_atom_category_bound_map.csv"; then
  echo "per-atom category gate did not allow bound binary-null atom" >&2
  cat "$work_dir/mixed_atom_category_bound_map.csv" >&2
  exit 62
fi

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
  - id: input_influence_range
    atom: 1
    role: input_influence
    expr: bytes controlling the root/producer path
    observe_at:
      kind: branch
      function: known_tc
      file: known_tc.c
      line: 42
      column: 35
    component: input_influence
    priority: 50
    direction: higher
    value_mode: hit
    value: 1.0
    confidence: 0.75
    range_start: 0
    range_len: 4
    mutation_hint: delete
    mutation_value: 0
    mutation_hook: scripts/formtrig_hooks/png_plte_empty_hook.py
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
if ! grep -q 'range 8 104 0 4 0.75 delete 0' \
  "$work_dir/binary_binding_compiled.lift"; then
  echo "BindingSpec compiler did not emit event-bound input influence mutation hint" >&2
  cat "$work_dir/binary_binding_compiled.lift" >&2
  exit 59
fi
if ! grep -q 'mutation_hook scripts/formtrig_hooks/png_plte_empty_hook.py' \
  "$work_dir/binary_binding_compiled.lift"; then
  echo "BindingSpec compiler did not emit external mutation hook" >&2
  cat "$work_dir/binary_binding_compiled.lift" >&2
  exit 61
fi
"$work_dir/formtrig_binding_map" --category binary-null \
  --site-map "$work_dir/site_map.tsv" \
  --normalized-spec "$work_dir/binary_binding_compiled.normalized" \
  "$work_dir/binary_binding_compiled.lift" \
  > "$work_dir/binary_binding_compiled_runtime_event_map.csv"
if ! grep -q 'range 8 104 0 4 0.75 delete 0' \
  "$work_dir/binary_binding_compiled.normalized"; then
  echo "runtime event-map gate did not preserve event-bound input influence mutation hint" >&2
  cat "$work_dir/binary_binding_compiled.normalized" >&2
  exit 60
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

"$work_dir/formtrig_lift_spec_audit" --category equality \
  "$work_dir/equality_repair_lift_spec.txt" \
  > "$work_dir/equality_repair_lift_audit.csv"
if ! grep -q '1,equality-magic,B4,true' \
  "$work_dir/equality_repair_lift_audit.csv"; then
  echo "lift spec audit did not classify explicit repair_hook as B4 equality binding" >&2
  cat "$work_dir/equality_repair_lift_audit.csv" >&2
  exit 53
fi
"$work_dir/formtrig_binding_map" --category equality \
  --site-map "$work_dir/site_map.tsv" \
  --normalized-spec "$work_dir/equality_repair.normalized" \
  "$work_dir/equality_repair_lift_spec.txt" \
  > "$work_dir/equality_repair_runtime_event_map.csv"
if ! grep -q '1,equality-magic,repair_hook' \
  "$work_dir/equality_repair_runtime_event_map.csv"; then
  echo "runtime event-map gate did not preserve repair_hook role" >&2
  cat "$work_dir/equality_repair_runtime_event_map.csv" >&2
  exit 54
fi

cat > "$work_dir/binary_repair_bypass_lift_spec.txt" <<'SPEC'
atom_category 1 binary-state-null
role_component 7 101 root_observe 3 1 10 lower distance 1.0 1.0
role_component 8 104 use 6 1 40 higher hit 1.0 1.0
role_component 8 102 repair_hook 2 1 50 higher hit 1.0 1.0
SPEC
if "$work_dir/formtrig_lift_spec_audit" --category binary-null \
  "$work_dir/binary_repair_bypass_lift_spec.txt" \
  > "$work_dir/binary_repair_bypass_lift_audit.csv"; then
  echo "lift spec audit let repair_hook bypass binary producer/use binding" >&2
  cat "$work_dir/binary_repair_bypass_lift_audit.csv" >&2
  exit 55
fi
if ! grep -q 'missing_producer' \
  "$work_dir/binary_repair_bypass_lift_audit.csv"; then
  echo "lift spec audit did not explain binary repair_hook bypass rejection" >&2
  cat "$work_dir/binary_repair_bypass_lift_audit.csv" >&2
  exit 56
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
{"event":"frontier_accept","reason":"non_dominated_frontier_seed","triggered":false,"lifted":1,"source_flags":2,"observed_source_flags":2,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":85,"source_id":$root_source_id,"context_hash":"0000000000000000","value":4,"confidence":1}]}
PROGRESS
"$work_dir/formtrig_lift_feature_audit" "$work_dir/runtime_event_map.csv" \
  "$work_dir/progress_mapped.jsonl" > "$work_dir/lift_feature_audit_ok.json"
if ! grep -q '"status": "pass"' "$work_dir/lift_feature_audit_ok.json"; then
  echo "lift feature audit rejected mapped lifted component" >&2
  cat "$work_dir/lift_feature_audit_ok.json" >&2
  exit 24
fi
cat > "$work_dir/progress_unmapped_generic.jsonl" <<'PROGRESS'
{"event":"frontier_accept","reason":"non_dominated_frontier_seed","triggered":false,"lifted":1,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":21,"source_id":999999,"context_hash":"0000000000000000","value":4,"confidence":1}]}
PROGRESS
if ! "$work_dir/formtrig_lift_feature_audit" "$work_dir/runtime_event_map.csv" \
  "$work_dir/progress_unmapped_generic.jsonl" \
  > "$work_dir/lift_feature_audit_generic.json"; then
  echo "lift feature audit rejected non-spec lifted component" >&2
  cat "$work_dir/lift_feature_audit_generic.json" >&2
  exit 25
fi
cat > "$work_dir/progress_unmapped_spec.jsonl" <<'PROGRESS'
{"event":"frontier_accept","reason":"non_dominated_frontier_seed","triggered":false,"lifted":1,"source_flags":2,"component_values":[{"kind":3,"atom_id":1,"role":1,"priority":10,"flags":85,"source_id":999999,"context_hash":"0000000000000000","value":4,"confidence":1}]}
PROGRESS
if "$work_dir/formtrig_lift_feature_audit" "$work_dir/runtime_event_map.csv" \
  "$work_dir/progress_unmapped_spec.jsonl" \
  > "$work_dir/lift_feature_audit_bad.json"; then
  echo "lift feature audit allowed unmapped spec-driven lifted component" >&2
  cat "$work_dir/lift_feature_audit_bad.json" >&2
  exit 26
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

if ! grep -q 'missing_root_or_use' \
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
require_file "$work_dir/out/default/formtrig_seed_signal_entropy.json"
require_file "$work_dir/out/formtrig_mutation_hook.json"
if ! grep -q '"enabled": true' "$work_dir/out/formtrig_mutation_hook.json" ||
   ! grep -q '"source": "binding_spec"' \
     "$work_dir/out/formtrig_mutation_hook.json"; then
  echo "campaign did not archive BindingSpec mutation hook provenance" >&2
  cat "$work_dir/out/formtrig_mutation_hook.json" >&2
  exit 75
fi
if ! grep -q '"component_keys":' \
  "$work_dir/out/default/formtrig_seed_signal_entropy.json"; then
  echo "campaign did not archive seed lift signal entropy diagnostics" >&2
  cat "$work_dir/out/default/formtrig_seed_signal_entropy.json" >&2
  exit 74
fi
if ! awk '$1 != "range" && NF != 13 { exit 1 }' \
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
summary_observed_spec_lifted="$(json_number observed_spec_lifted_events "$summary")"

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

if [[ "${summary_observed_spec_lifted:-0}" -le 0 ]]; then
  echo "progress summary did not report observed spec-driven lifted source" >&2
  cat "$summary" >&2
  exit 57
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

mkdir -p "$work_dir/manifest_case"
cat > "$work_dir/manifest_case/native_manifest.txt" <<'MANIFEST'
target_id: native_afl_smoke
category: binary-null
seed_dir: ../in
out_dir: ../manifest_out
duration: 1
seed_preflight: require
binding_spec: ../binary_binding_spec.yml
site_map: ../site_map.tsv
target_site_ids: 101
target_cwd: ..
target_cmd: ./native_afl_role_target @@
MANIFEST
"$repo_root/scripts/run_formtrig_native_manifest.sh" \
  "$work_dir/manifest_case/native_manifest.txt" >/dev/null
require_file "$work_dir/manifest_out/default/formtrig_seed_readiness.json"
require_file "$work_dir/manifest_out/default/formtrig_diagnosis.json"
if ! grep -q '"status": "pass"' \
  "$work_dir/manifest_out/default/formtrig_seed_readiness.json"; then
  echo "manifest runner seed readiness did not pass" >&2
  cat "$work_dir/manifest_out/default/formtrig_seed_readiness.json" >&2
  exit 49
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
