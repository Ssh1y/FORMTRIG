#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

seed_dir=""
out_dir=""
target_bug=""
category="generic"
site_map=""
duration="30"
seed_preflight="require"
seed_preflight_max="32"
seed_preflight_timeout="2"
aflpp_dir="${AFLPP_DIR:-$repo_root/experiments/aflplusplus/AFLplusplus}"
candidate_kind="auto"
max_candidates="0"
target_site_ids=""
declare -a candidates=()
declare -a candidate_dirs=()
declare -a extra_afl_args=()

usage() {
  cat >&2 <<EOF
usage: $0 --in DIR --out DIR --target-bug LABEL --site-map FILE [options] -- TARGET [ARGS...]

Runs a deterministic BindingSpec/lift-spec candidate sweep. Each candidate is
fed through the existing FORMTRIG static gates, seed readiness, short AFL++
campaign, lifted-feature provenance audit, and binding-signal diagnosis.

required:
  --candidate FILE       candidate BindingSpec or FORMTRIG_LIFT_SPEC, repeatable
  or --candidate-dir DIR directory containing *.yaml, *.yml, *.lift, *.txt

options:
  --category NAME        numeric|equality|binary-null|lifecycle|generic
  --candidate-kind K     auto|binding-spec|lift-spec (default: auto)
  --duration SEC         AFL++ -V per-candidate budget (default: 30)
  --seed-preflight M     off|warn|require (default: require)
  --seed-preflight-max N       max seeds replayed before campaign (default: 32)
  --seed-preflight-timeout SEC per-seed replay timeout (default: 2)
  --target-site-ids IDS  comma-separated runtime target site ids
  --aflpp-dir DIR        AFL++ checkout/build directory
  --afl-arg ARG          extra afl-fuzz argument, repeatable
  --max-candidates N     stop after N candidates, 0 means unlimited

outputs:
  OUT/summary.tsv
  OUT/summary.jsonl
  OUT/candidates/<N_NAME>/{run.log, default/formtrig_diagnosis.json, ...}
EOF
}

require_path() {
  if [[ ! -e "$1" ]]; then
    echo "missing required path: $1" >&2
    exit 2
  fi
}

json_value() {
  local file="$1"
  local expr="$2"
  local default_value="${3:-}"
  if [[ -s "$file" ]]; then
    jq -r "$expr // \"$default_value\"" "$file" 2>/dev/null || \
      printf '%s\n' "$default_value"
  else
    printf '%s\n' "$default_value"
  fi
}

json_number() {
  local file="$1"
  local expr="$2"
  local default_value="${3:-0}"
  if [[ -s "$file" ]]; then
    jq -r "$expr // $default_value" "$file" 2>/dev/null || \
      printf '%s\n' "$default_value"
  else
    printf '%s\n' "$default_value"
  fi
}

run_log_diagnosis() {
  local file="$1"
  if [[ ! -s "$file" ]]; then
    printf '%s\n' "campaign_failed"
  elif grep -q 'source mapping is missing' "$file"; then
    printf '%s\n' "binding_source_mapping_missing"
  elif grep -q 'BindingSpec compilation failed' "$file"; then
    printf '%s\n' "binding_spec_compile_failed"
  elif grep -q 'lift binding audit failed' "$file"; then
    printf '%s\n' "lift_binding_audit_failed"
  elif grep -q 'runtime event-map binding gate failed' "$file"; then
    printf '%s\n' "runtime_event_map_gate_failed"
  elif grep -q 'FORMTRIG seed readiness failed' "$file"; then
    printf '%s\n' "seed_readiness_failed"
  elif grep -q 'lifted feature provenance audit failed' "$file"; then
    printf '%s\n' "lift_feature_provenance_failed"
  elif grep -q 'mutation hook is not executable' "$file"; then
    printf '%s\n' "mutation_hook_not_executable"
  else
    printf '%s\n' "campaign_failed"
  fi
}

candidate_arg_kind() {
  local file="$1"
  case "$candidate_kind" in
    binding-spec)
      printf '%s\n' "--binding-spec"
      ;;
    lift-spec)
      printf '%s\n' "--lift-spec"
      ;;
    auto)
      case "$file" in
        *.yaml|*.yml)
          printf '%s\n' "--binding-spec"
          ;;
        *)
          printf '%s\n' "--lift-spec"
          ;;
      esac
      ;;
    *)
      echo "--candidate-kind must be auto, binding-spec, or lift-spec" >&2
      exit 2
      ;;
  esac
}

safe_name() {
  local base
  base="$(basename "$1")"
  base="${base//[^A-Za-z0-9_.-]/_}"
  printf '%s' "$base"
}

candidate_score() {
  local diagnosis="$1"
  local experiment_ready="$2"
  local pretrigger_guidance="$3"
  local has_progress="$4"
  local queued="$5"
  local triggered="$6"
  local has_non_trigger="$7"
  local non_trigger_progress="$8"
  local binding_status="$9"
  local binding_diag="${10}"
  local lift_delta_only_on_triggered="${11}"
  local semantic_candidate_roles="${12}"
  local exit_code="${13}"

  local score=0
  if [[ "$exit_code" != "0" ]]; then
    score=$((score - 1000))
  fi
  if [[ "$experiment_ready" != "true" ]]; then
    score=$((score - 250000))
  fi
  if [[ "$binding_status" == "fail" ]]; then
    score=$((score - 50000))
  fi
  if [[ "$triggered" != "0" && "$triggered" != "false" ]]; then
    score=$((score + 100000))
  fi
  if [[ "$pretrigger_guidance" == "true" ]]; then
    score=$((score + 300000))
  fi
  if [[ "$lift_delta_only_on_triggered" == "true" ]]; then
    score=$((score - 100000))
  fi
  if [[ "$queued" != "0" && "$queued" != "false" ]]; then
    score=$((score + 90000))
  fi
  if [[ "$has_non_trigger" == "true" ]]; then
    score=$((score + 95000))
  elif [[ "$non_trigger_progress" != "0" &&
          "$non_trigger_progress" != "false" ]]; then
    score=$((score + 95000))
  fi
  if [[ "$has_progress" == "true" ]]; then
    score=$((score + 80000))
  fi
  if [[ "$experiment_ready" == "true" ]]; then
    score=$((score + 4000))
  fi
  if [[ "$binding_status" == "pass" ]]; then
    score=$((score + 2000))
  fi
  if [[ "$semantic_candidate_roles" =~ ^[0-9]+$ ]]; then
    score=$((score + semantic_candidate_roles * 200))
  fi
  case "$binding_diag" in
    role_signal_progress_observed|no_new_non_dominated_progress)
      score=$((score + 1000))
      ;;
    guard_only_lift_signal|constant_lift_signal|producer_root_use_constant)
      score=$((score - 50000))
      ;;
    producer_not_observed_in_candidates|no_candidate_role_signal)
      score=$((score - 750))
      ;;
    mutations_lose_best_lifted_state)
      score=$((score - 300))
      ;;
    typed_mutation_no_lift_delta)
      score=$((score - 250))
      ;;
    no_valid_hot_range)
      score=$((score - 650))
      ;;
  esac
  if [[ "$diagnosis" == "triggered" ]]; then
    score=$((score + 100000))
  fi
  if [[ "$diagnosis" == "typed_mutation_no_lift_delta" ]]; then
    score=$((score + 250))
  fi
  if [[ "$diagnosis" == "no_valid_hot_range" ]]; then
    score=$((score - 650))
  fi
  printf '%s\n' "$score"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --in)
      seed_dir="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --target-bug)
      target_bug="${2:-}"
      shift 2
      ;;
    --category)
      category="${2:-}"
      shift 2
      ;;
    --site-map)
      site_map="${2:-}"
      shift 2
      ;;
    --candidate)
      candidates+=("${2:-}")
      shift 2
      ;;
    --candidate-dir)
      candidate_dirs+=("${2:-}")
      shift 2
      ;;
    --candidate-kind)
      candidate_kind="${2:-}"
      shift 2
      ;;
    --duration)
      duration="${2:-}"
      shift 2
      ;;
    --seed-preflight)
      seed_preflight="${2:-}"
      shift 2
      ;;
    --seed-preflight-max)
      seed_preflight_max="${2:-}"
      shift 2
      ;;
    --seed-preflight-timeout)
      seed_preflight_timeout="${2:-}"
      shift 2
      ;;
    --target-site-ids)
      target_site_ids="${2:-}"
      shift 2
      ;;
    --aflpp-dir)
      aflpp_dir="${2:-}"
      shift 2
      ;;
    --afl-arg)
      extra_afl_args+=("${2:-}")
      shift 2
      ;;
    --max-candidates)
      max_candidates="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$seed_dir" || -z "$out_dir" || -z "$target_bug" ||
      -z "$site_map" || $# -eq 0 ]]; then
  usage
  exit 2
fi

require_path "$seed_dir"
require_path "$site_map"
require_path "$aflpp_dir/afl-fuzz"
if ! command -v jq >/dev/null 2>&1; then
  echo "missing required command: jq" >&2
  exit 2
fi
for candidate_dir in "${candidate_dirs[@]}"; do
  require_path "$candidate_dir"
  while IFS= read -r candidate; do
    candidates+=("$candidate")
  done < <(find "$candidate_dir" -maxdepth 1 -type f \
      \( -name '*.yaml' -o -name '*.yml' -o -name '*.lift' -o \
         -name '*.txt' \) | sort)
done

if [[ "${#candidates[@]}" -eq 0 ]]; then
  echo "no candidates provided" >&2
  exit 2
fi

mkdir -p "$out_dir/candidates"
summary_tmp="$out_dir/summary.unsorted.tsv"
summary_tsv="$out_dir/summary.tsv"
summary_jsonl="$out_dir/summary.jsonl"
: > "$summary_tmp"
: > "$summary_jsonl"
printf 'score\tindex\tcandidate\tstatus\texit_code\tdiagnosis\texperiment_ready\tpretrigger_lift_guidance_ready\thas_progress\thas_non_trigger_progress\tnon_trigger_progress\tqueued\ttriggered\tsaved_non_trigger\tsaved_triggered\texecs\treached\tbinding_signal_status\tbinding_signal_diagnosis\tcandidate_events\taccepted_non_trigger_progress\ttriggered_lift_delta\tnon_trigger_lift_delta\tlift_delta_only_on_triggered\tsemantic_candidate_variable_roles\tout_dir\n' \
  > "$summary_tmp"

idx=0
for candidate in "${candidates[@]}"; do
  idx=$((idx + 1))
  if [[ "$max_candidates" != "0" && "$idx" -gt "$max_candidates" ]]; then
    break
  fi
  require_path "$candidate"

  name="$(printf '%03d_%s' "$idx" "$(safe_name "$candidate")")"
  candidate_out="$out_dir/candidates/$name"
  mkdir -p "$candidate_out"
  arg_kind="$(candidate_arg_kind "$candidate")"

  campaign_args=(
    --in "$seed_dir"
    --out "$candidate_out"
    --target-bug "$target_bug"
    --category "$category"
    "$arg_kind" "$candidate"
    --site-map "$site_map"
    --duration "$duration"
    --seed-preflight "$seed_preflight"
    --seed-preflight-max "$seed_preflight_max"
    --seed-preflight-timeout "$seed_preflight_timeout"
    --aflpp-dir "$aflpp_dir"
  )
  if [[ -n "$target_site_ids" ]]; then
    campaign_args+=(--target-site-ids "$target_site_ids")
  fi
  for arg in "${extra_afl_args[@]}"; do
    campaign_args+=(--afl-arg "$arg")
  done

  set +e
  "$repo_root/scripts/run_formtrig_aflpp_campaign.sh" \
    "${campaign_args[@]}" -- "$@" \
    > "$candidate_out/run.log" 2>&1
  exit_code=$?
  set -e

  diagnosis_json="$candidate_out/default/formtrig_diagnosis.json"
  signal_json="$candidate_out/default/formtrig_binding_signal_diagnosis.json"
  diagnosis_json_for_jq="$diagnosis_json"
  signal_json_for_jq="$signal_json"
  if [[ ! -s "$diagnosis_json_for_jq" ]]; then
    diagnosis_json_for_jq="$candidate_out/.missing_diagnosis.json"
    printf 'null\n' > "$diagnosis_json_for_jq"
  fi
  if [[ ! -s "$signal_json_for_jq" ]]; then
    signal_json_for_jq="$candidate_out/.missing_binding_signal.json"
    printf 'null\n' > "$signal_json_for_jq"
  fi

  diagnosis_default="campaign_failed"
  if [[ ! -s "$diagnosis_json" && "$exit_code" != "0" ]]; then
    diagnosis_default="$(run_log_diagnosis "$candidate_out/run.log")"
  fi
  diagnosis="$(json_value "$diagnosis_json" '.diagnosis' "$diagnosis_default")"
  experiment_ready="$(json_value "$diagnosis_json" '.experiment_ready' "false")"
  pretrigger_guidance="$(json_value "$diagnosis_json" '.pretrigger_lift_guidance_ready' "false")"
  has_progress="$(json_value "$diagnosis_json" '.has_tc_rooted_progress' "false")"
  has_non_trigger="$(json_value "$diagnosis_json" '.has_non_trigger_progress' "false")"
  non_trigger_progress="$(json_number "$diagnosis_json" '.non_trigger_progress_events' "0")"
  queued="$(json_number "$diagnosis_json" '.formtrig_queued_progress' "0")"
  triggered="$(json_number "$diagnosis_json" '.terminal_triggered_execs' "0")"
  saved_non_trigger="$(json_number "$diagnosis_json" '.saved_non_trigger_progress_events' "0")"
  saved_triggered="$(json_number "$diagnosis_json" '.saved_triggered_progress_events' "0")"
  execs="$(json_number "$diagnosis_json" '.execs_done' "0")"
  reached="$(json_number "$diagnosis_json" '.formtrig_reached_execs' "0")"
  binding_status="$(json_value "$signal_json" '.status' "missing")"
  binding_diag="$(json_value "$signal_json" '.diagnosis' "missing")"
  candidate_events="$(json_number "$signal_json" '.candidate_events' "0")"
  accepted_non_trigger="$(json_number "$signal_json" '.accepted_non_trigger_progress_events' "0")"
  triggered_lift_delta="$(json_value "$signal_json" '.triggered_candidate_lift_delta' "false")"
  non_trigger_lift_delta="$(json_value "$signal_json" '.non_trigger_candidate_lift_delta' "false")"
  lift_delta_only_on_triggered="$(json_value "$signal_json" '.lift_delta_only_on_triggered_candidates' "false")"
  semantic_roles="$(json_number "$signal_json" '[.atoms[].candidate_variable_roles[]? | select(. != "guard" and . != "input_influence" and . != "repair_hook")] | unique | length' "0")"
  score="$(candidate_score "$diagnosis" "$experiment_ready" \
    "$pretrigger_guidance" "$has_progress" "$queued" "$triggered" \
    "$has_non_trigger" "$non_trigger_progress" "$binding_status" \
    "$binding_diag" "$lift_delta_only_on_triggered" "$semantic_roles" \
    "$exit_code")"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$score" "$idx" "$candidate" \
    "$(json_value "$diagnosis_json" '.status' "failed")" \
    "$exit_code" "$diagnosis" "$experiment_ready" "$pretrigger_guidance" \
    "$has_progress" "$has_non_trigger" "$non_trigger_progress" \
    "$queued" "$triggered" "$saved_non_trigger" "$saved_triggered" \
    "$execs" "$reached" \
    "$binding_status" "$binding_diag" "$candidate_events" \
    "$accepted_non_trigger" "$triggered_lift_delta" \
    "$non_trigger_lift_delta" "$lift_delta_only_on_triggered" \
    "$semantic_roles" "$candidate_out" \
    >> "$summary_tmp"

  jq -n \
    --arg candidate "$candidate" \
    --arg out_dir "$candidate_out" \
    --argjson index "$idx" \
    --argjson score "$score" \
    --argjson exit_code "$exit_code" \
    --arg diagnosis "$diagnosis" \
    --arg experiment_ready "$experiment_ready" \
    --arg pretrigger_guidance "$pretrigger_guidance" \
    --arg has_progress "$has_progress" \
    --arg has_non_trigger "$has_non_trigger" \
    --argjson non_trigger_progress "$non_trigger_progress" \
    --argjson queued "$queued" \
    --argjson triggered "$triggered" \
    --argjson saved_non_trigger "$saved_non_trigger" \
    --argjson saved_triggered "$saved_triggered" \
    --argjson execs "$execs" \
    --argjson reached "$reached" \
    --arg binding_signal_status "$binding_status" \
    --arg binding_signal_diagnosis "$binding_diag" \
    --argjson candidate_events "$candidate_events" \
    --argjson accepted_non_trigger_progress "$accepted_non_trigger" \
    --arg triggered_lift_delta "$triggered_lift_delta" \
    --arg non_trigger_lift_delta "$non_trigger_lift_delta" \
    --arg lift_delta_only_on_triggered "$lift_delta_only_on_triggered" \
    --argjson semantic_candidate_variable_roles "$semantic_roles" \
    --slurpfile diagnosis_json "$diagnosis_json_for_jq" \
    --slurpfile binding_signal_json "$signal_json_for_jq" \
    '{
      index: $index,
      score: $score,
      candidate: $candidate,
      out_dir: $out_dir,
      exit_code: $exit_code,
      diagnosis: $diagnosis,
      experiment_ready: ($experiment_ready == "true"),
      pretrigger_lift_guidance_ready: ($pretrigger_guidance == "true"),
      has_tc_rooted_progress: ($has_progress == "true"),
      has_non_trigger_progress: ($has_non_trigger == "true"),
      non_trigger_progress_events: $non_trigger_progress,
      queued_progress: $queued,
      triggered_execs: $triggered,
      saved_non_trigger_progress_events: $saved_non_trigger,
      saved_triggered_progress_events: $saved_triggered,
      execs_done: $execs,
      reached_execs: $reached,
      binding_signal_status: $binding_signal_status,
      binding_signal_diagnosis: $binding_signal_diagnosis,
      candidate_events: $candidate_events,
      accepted_non_trigger_progress_events: $accepted_non_trigger_progress,
      triggered_candidate_lift_delta: ($triggered_lift_delta == "true"),
      non_trigger_candidate_lift_delta: ($non_trigger_lift_delta == "true"),
      lift_delta_only_on_triggered_candidates: ($lift_delta_only_on_triggered == "true"),
      semantic_candidate_variable_roles: $semantic_candidate_variable_roles,
      diagnosis_json: ($diagnosis_json[0] // null),
      binding_signal_json: ($binding_signal_json[0] // null)
    }' >> "$summary_jsonl"

done

{
  head -n 1 "$summary_tmp"
  tail -n +2 "$summary_tmp" | sort -t $'\t' -k1,1nr -k2,2n
} > "$summary_tsv"

echo "FORMTRIG binding candidate sweep complete"
echo "  out=$out_dir"
echo "  summary=$summary_tsv"
echo "  summary_jsonl=$summary_jsonl"
