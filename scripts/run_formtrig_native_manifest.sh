#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat >&2 <<EOF
usage: $0 <manifest.txt>

Runs a native FORMTRIG experiment from a line-oriented manifest.

Required manifest keys:
  target_id: LABEL
  category: numeric|equality|binary-null|lifecycle|generic
  seed_dir: DIR
  out_dir: DIR
  target_cmd: TARGET [ARGS...]   # may contain @@

Binding input:
  binding_spec: FILE
  site_map: FILE
  target_site_ids: IDS

Or generate a first-pass BindingSpec from one source site:
  site_map: FILE
  source_file: FILE_SUBSTRING
  source_line: N
  source_kind: cmp|branch|binary|...
  tc_expr: EXPR
  atom_id: N
  atom_kind: numeric-margin|equality-magic|binary-state-null|...
  atom_expr: EXPR
  atom_root: ROOT
  role: root_observe|guard|producer|use|...
  component: COMPONENT_NAME_OR_NUMBER
  priority: N
  direction: lower|higher
  value_mode: distance|hit|outcome|not_outcome|a|b|c

Optional manifest keys:
  duration: SEC                  # default 60
  afl_args: ARGS                 # extra AFL++ args, e.g. -t 5000
  aflpp_dir: DIR
  seed_preflight: off|warn|require
  seed_preflight_max: N
  seed_preflight_timeout: SEC
  source_function: FUNCTION
  target_cwd: DIR                 # working directory for target command
  tc_category: CATEGORY          # defaults to category
  value: X                       # default 1.0
  confidence: X                  # default 1.0
EOF
}

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 2
  fi
}

manifest="${1:-}"
if [[ -z "$manifest" || "${2:-}" != "" ]]; then
  usage
  exit 2
fi
require_file "$manifest"
manifest_dir="$(cd "$(dirname "$manifest")" && pwd)"

resolve_path() {
  local path="$1"
  if [[ -z "$path" || "$path" == /* ]]; then
    printf '%s' "$path"
  else
    printf '%s/%s' "$manifest_dir" "$path"
  fi
}

declare -A cfg
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(trim "$line")"
  [[ -z "$line" ]] && continue
  if [[ "$line" != *:* ]]; then
    echo "manifest line must be 'key: value': $line" >&2
    exit 2
  fi
  key="$(trim "${line%%:*}")"
  value="$(trim "${line#*:}")"
  if [[ -z "$key" ]]; then
    echo "manifest contains an empty key" >&2
    exit 2
  fi
  cfg["$key"]="$value"
done < "$manifest"

target_id="${cfg[target_id]:-}"
category="${cfg[category]:-}"
seed_dir="${cfg[seed_dir]:-}"
seed_dir="$(resolve_path "$seed_dir")"
out_dir="$(resolve_path "${cfg[out_dir]:-}")"
target_cmd="${cfg[target_cmd]:-}"
duration="${cfg[duration]:-60}"
afl_args="${cfg[afl_args]:-}"
aflpp_dir="$(resolve_path "${cfg[aflpp_dir]:-$repo_root/experiments/aflplusplus/AFLplusplus}")"
seed_preflight="${cfg[seed_preflight]:-warn}"
seed_preflight_max="${cfg[seed_preflight_max]:-32}"
seed_preflight_timeout="${cfg[seed_preflight_timeout]:-2}"
binding_spec="$(resolve_path "${cfg[binding_spec]:-}")"
site_map="$(resolve_path "${cfg[site_map]:-}")"
target_site_ids="${cfg[target_site_ids]:-}"
target_cwd="$(resolve_path "${cfg[target_cwd]:-$manifest_dir}")"

if [[ -z "$target_id" || -z "$category" || -z "$seed_dir" ||
      -z "$out_dir" || -z "$target_cmd" ]]; then
  usage
  exit 2
fi

require_file "$seed_dir"
mkdir -p "$out_dir/.formtrig"

if [[ -z "$binding_spec" ]]; then
  required_source_keys=(
    site_map source_file source_line source_kind tc_expr atom_id atom_kind
    atom_expr atom_root role component priority direction value_mode
  )
  for key in "${required_source_keys[@]}"; do
    if [[ -z "${cfg[$key]:-}" ]]; then
      echo "manifest needs binding_spec or source binding key: $key" >&2
      exit 2
    fi
  done
  require_file "$site_map"

  site_map_tool="$out_dir/.formtrig/formtrig_site_map"
  cc -std=c11 -I"$repo_root/formtrig/include" -Wall -Wextra -Werror \
    "$repo_root/formtrig/tools/formtrig_site_map.c" \
    -o "$site_map_tool"

  binding_spec="$out_dir/.formtrig/generated.binding.yaml"
  site_args=(
    --file "${cfg[source_file]}"
    --line "${cfg[source_line]}"
    --kind "${cfg[source_kind]}"
  )
  if [[ -n "${cfg[source_function]:-}" ]]; then
    site_args+=(--function "${cfg[source_function]}")
  fi
  "$site_map_tool" "${site_args[@]}" --emit binding-spec \
    --tc-id "$target_id" \
    --tc-category "${cfg[tc_category]:-$category}" \
    --tc-expr "${cfg[tc_expr]}" \
    --atom "${cfg[atom_id]}" \
    --atom-kind "${cfg[atom_kind]}" \
    --atom-expr "${cfg[atom_expr]}" \
    --atom-root "${cfg[atom_root]}" \
    --role "${cfg[role]}" \
    --component "${cfg[component]}" \
    --priority "${cfg[priority]}" \
    --direction "${cfg[direction]}" \
    --value-mode "${cfg[value_mode]}" \
    --value "${cfg[value]:-1.0}" \
    --confidence "${cfg[confidence]:-1.0}" \
    "$site_map" > "$binding_spec"

  if [[ -z "$target_site_ids" ]]; then
    target_site_ids="$("$site_map_tool" "${site_args[@]}" --emit ids \
      "$site_map")"
  fi
fi

if [[ -n "$binding_spec" ]]; then
  require_file "$binding_spec"
fi
if [[ -n "$site_map" ]]; then
  require_file "$site_map"
fi

require_file "$target_cwd"

read -r -a target_argv <<< "$target_cmd"
if [[ "${#target_argv[@]}" -eq 0 ]]; then
  echo "target_cmd expanded to an empty command" >&2
  exit 2
fi
read -r -a extra_afl_args <<< "$afl_args"

campaign_args=(
  --in "$seed_dir"
  --out "$out_dir"
  --target-bug "$target_id"
  --category "$category"
  --binding-spec "$binding_spec"
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

(
  cd "$target_cwd"
  "$repo_root/scripts/run_formtrig_aflpp_campaign.sh" \
    "${campaign_args[@]}" -- "${target_argv[@]}"
)

cat <<EOF
FORMTRIG native manifest complete
  manifest=$manifest
  out=$out_dir
  binding_spec=$binding_spec
  target_site_ids=$target_site_ids
EOF
