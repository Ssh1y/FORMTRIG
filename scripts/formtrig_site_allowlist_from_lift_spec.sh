#!/usr/bin/env bash
set -euo pipefail

lift_spec=""
target_site_ids=""
out_file=""

usage() {
  cat >&2 <<EOF
usage: $0 --lift-spec FILE --out FILE [--target-site-ids IDS]

Builds a compile-time FORMTRIG instrumentation site-id allowlist from a
normalized FORMTRIG lift-spec plus optional runtime target site ids.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lift-spec)
      lift_spec="${2:-}"
      shift 2
      ;;
    --target-site-ids)
      target_site_ids="${2:-}"
      shift 2
      ;;
    --out)
      out_file="${2:-}"
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

if [[ -z "$lift_spec" || -z "$out_file" ]]; then
  usage
  exit 2
fi
if [[ ! -e "$lift_spec" ]]; then
  echo "missing lift spec: $lift_spec" >&2
  exit 2
fi

mkdir -p "$(dirname "$out_file")"
tmp_file="$out_file.tmp.$$"
{
  if [[ -n "$target_site_ids" ]]; then
    printf '%s\n' "$target_site_ids" | tr ',;:' '\n'
  fi
  awk '
    /^[[:space:]]*#/ { next }
    NF < 3 { next }
    $1 == "role_component" || $1 == "role-event" || $1 == "role_event" ||
    $1 == "component" || $1 == "event" ||
    $1 == "phase" || $1 == "prefix" ||
    $1 == "range" || $1 == "hot_range" || $1 == "hot-range" {
      print $3
    }
  ' "$lift_spec"
} | awk '/^[0-9]+$/ && $1 > 0 { print $1 }' | sort -n -u > "$tmp_file"
mv "$tmp_file" "$out_file"
