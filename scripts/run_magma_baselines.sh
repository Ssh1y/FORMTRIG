#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

target_id=""
inventory="$repo_root/artifacts/magma_canary_inventory.json"
out_dir=""
magma_dir="$repo_root/experiments/magma_workspace/magma"
seed_dir=""
durations="600,1800"
baselines="aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
poll="30"
reps="1"
rep_start="1"
rep_end=""
jobs="${FORMTRIG_JOBS:-1}"
run_build=1
run_sweeps=1
failed_jobs=0
target_repo_path=""
target_repo_backup=""
declare -a extra_fuzz_args=()

usage() {
  cat >&2 <<EOF
usage: $0 --target-id ID [options]

Builds and runs faithful AFL++-family Magma baselines for any target in the
Magma canary inventory, then harvests Magma monitor _T evidence through
tools/run_post_reach_baseline.py.

options:
  --target-id ID        Magma bug/target id, for example PNG007
  --inventory JSON      Magma canary inventory, default artifacts/magma_canary_inventory.json
  --out DIR             output directory, default /tmp/formtrig_<target>_baselines_<timestamp>
  --magma-dir DIR       Magma checkout/workspace
  --seed-dir DIR        seed directory; defaults to artifacts/rnt_corpus/<ID>/seeds if present,
                        otherwise the inventory initial_seed_corpus
  --durations LIST      comma/space-separated budgets in seconds, default 600,1800
  --baselines LIST      comma/space-separated baseline ids
  --reps N              repetitions per baseline/budget, default 1
  --rep-start N         first repetition to run, default 1
  --rep-end N           last repetition to run, default --reps
  --jobs N              concurrent baseline runs, default FORMTRIG_JOBS or 1
  --poll SEC            Magma monitor poll interval, default 30
  --afl-arg ARG         extra AFL++ argument passed through FUZZARGS; repeatable
  --no-build            skip captain build
  --no-sweeps           build only
EOF
}

require_path() {
  if [[ ! -e "$1" ]]; then
    echo "missing required path: $1" >&2
    exit 2
  fi
}

sync_formtrig_canary_runtime() {
  local support_dir="$magma_dir/magma"
  local canary_h="$support_dir/src/canary.h"
  if [[ ! -f "$canary_h" ]] ||
     ! grep -q 'formtrig/formtrig_runtime.h' "$canary_h"; then
    return
  fi

  local source_dir="${FORMTRIG_SOURCE_DIR:-$repo_root/formtrig}"
  require_path "$source_dir/include/formtrig/formtrig_runtime.h"
  require_path "$source_dir/include/formtrig/formtrig_abi.h"
  require_path "$source_dir/runtime/formtrig_runtime.c"

  rm -rf "$support_dir/formtrig"
  mkdir -p "$support_dir/formtrig/include" "$support_dir/formtrig/runtime"
  cp -a "$source_dir/include/formtrig" "$support_dir/formtrig/include/formtrig"
  cp -a "$source_dir/runtime/formtrig_runtime.c" \
    "$support_dir/formtrig/runtime/formtrig_runtime.c"

  python3 - "$support_dir/prebuild.sh" "$support_dir/build.sh" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path


def inject_after_storage(text: str) -> str:
    marker = 'FORMTRIG_CANARY_INCLUDE=()'
    if marker in text:
        return text
    needle = 'MAGMA_STORAGE="$SHARED/canaries.raw"\n'
    insert = '''MAGMA_STORAGE="$SHARED/canaries.raw"

FORMTRIG_CANARY_INCLUDE=()
if [ -d "$MAGMA/formtrig/include" ]; then
    FORMTRIG_CANARY_INCLUDE=(-I "$MAGMA/formtrig/include")
fi
'''
    if needle not in text:
        raise SystemExit("could not locate MAGMA_STORAGE assignment")
    return text.replace(needle, insert, 1)


def patch_prebuild(path: Path) -> None:
    text = inject_after_storage(path.read_text(encoding="utf-8"))
    text = text.replace(
        '-fPIC -I "$MAGMA/src/" -o "$OUT/pre_storage.o" $LDFLAGS',
        '-fPIC -I "$MAGMA/src/" "${FORMTRIG_CANARY_INCLUDE[@]}" '
        '-o "$OUT/pre_storage.o" $LDFLAGS',
    )
    text = text.replace(
        '"$OUT/pre_storage.o" -I "$MAGMA/src/" -o "$OUT/monitor" $LDFLAGS $LIBS',
        '"$OUT/pre_storage.o" -I "$MAGMA/src/" "${FORMTRIG_CANARY_INCLUDE[@]}" '
        '-o "$OUT/monitor" $LDFLAGS $LIBS',
    )
    path.write_text(text, encoding="utf-8")


def patch_build(path: Path) -> None:
    text = inject_after_storage(path.read_text(encoding="utf-8"))
    runtime_block = '''
FORMTRIG_RUNTIME_OBJECTS=()
if [ -f "$MAGMA/formtrig/runtime/formtrig_runtime.c" ]; then
    $CC $CFLAGS -D"MAGMA_STORAGE=\\"$MAGMA_STORAGE\\"" \\
        -c "$MAGMA/formtrig/runtime/formtrig_runtime.c" \\
        -fPIC -I "$MAGMA/src/" "${FORMTRIG_CANARY_INCLUDE[@]}" \\
        -o "$OUT/formtrig_runtime.o" $LDFLAGS
    FORMTRIG_RUNTIME_OBJECTS+=("$OUT/formtrig_runtime.o")
fi
'''
    if 'FORMTRIG_RUNTIME_OBJECTS=()' not in text:
        needle = '$CC $CFLAGS -D"MAGMA_STORAGE=\\"$MAGMA_STORAGE\\"" -c "$MAGMA/src/canary.c"'
        if needle not in text:
            raise SystemExit("could not locate canary.c compile command")
        text = text.replace(needle, runtime_block + "\n" + needle, 1)
    text = text.replace(
        '-fPIC -I "$MAGMA/src/" -o "$OUT/canary.o" $LDFLAGS',
        '-fPIC -I "$MAGMA/src/" "${FORMTRIG_CANARY_INCLUDE[@]}" '
        '-o "$OUT/canary.o" $LDFLAGS',
    )
    text = text.replace(
        '-fPIC -I "$MAGMA/src/" -o "$OUT/storage.o" $LDFLAGS',
        '-fPIC -I "$MAGMA/src/" "${FORMTRIG_CANARY_INCLUDE[@]}" '
        '-o "$OUT/storage.o" $LDFLAGS',
    )
    text = text.replace(
        '$LD -r "$OUT/canary.o" "$OUT/storage.o" -o "$OUT/magma.o"',
        '$LD -r "$OUT/canary.o" "$OUT/storage.o" '
        '"${FORMTRIG_RUNTIME_OBJECTS[@]}" -o "$OUT/magma.o"',
    )
    patched_rm = 'rm "$OUT/canary.o" "$OUT/storage.o" "${FORMTRIG_RUNTIME_OBJECTS[@]}"'
    if patched_rm not in text:
        text = text.replace('rm "$OUT/canary.o" "$OUT/storage.o"', patched_rm)
    path.write_text(text, encoding="utf-8")


patch_prebuild(Path(sys.argv[1]))
patch_build(Path(sys.argv[2]))
PY
}

prepare_clean_target_context() {
  target_repo_path="$magma_dir/targets/$magma_target/repo"
  if [[ ! -d "$target_repo_path/.git" ]]; then
    return
  fi
  if [[ -z "$(git -C "$target_repo_path" status --porcelain --untracked-files=normal)" ]]; then
    return
  fi

  target_repo_backup="$(mktemp -d "${TMPDIR:-/tmp}/formtrig_${target_id}_${magma_target}_repo.XXXXXX")"
  mv "$target_repo_path" "$target_repo_backup/repo"
}

patch_target_build_helpers() {
  local build_sh="$magma_dir/targets/$magma_target/build.sh"
  if [[ ! -f "$build_sh" ]] || ! grep -q './autogen.sh' "$build_sh"; then
    return
  fi

  python3 - "$build_sh" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
changed = False
if (
    "FORMTRIG_POPPLER_DEFAULT_CONFIGURE_NATIVE" not in text
    and 'pushd "$TARGET/freetype2"' in text
    and 'if [ -n "$AFLGO_CONFIGURE_NATIVE" ]; then' in text
):
    poppler_configure = '''if [ -z "${AFLGO_CONFIGURE_NATIVE:-}" ]; then
    export AFLGO_CONFIGURE_NATIVE=1
    export AFLGO_CONFIGURE_CC="${AFLGO_CONFIGURE_CC:-clang}"
    export AFLGO_CONFIGURE_CXX="${AFLGO_CONFIGURE_CXX:-clang++}"
    export AFLGO_CONFIGURE_CFLAGS="${AFLGO_CONFIGURE_CFLAGS:-}"
    export AFLGO_CONFIGURE_CXXFLAGS="${AFLGO_CONFIGURE_CXXFLAGS:-}"
    export AFLGO_CONFIGURE_LDFLAGS="${AFLGO_CONFIGURE_LDFLAGS:-}"
    export AFLGO_CONFIGURE_LIBS="${AFLGO_CONFIGURE_LIBS:-}"
fi
# FORMTRIG_POPPLER_DEFAULT_CONFIGURE_NATIVE

'''
    text = text.replace(
        'if [ -n "$AFLGO_CONFIGURE_NATIVE" ]; then',
        poppler_configure + 'if [ -n "$AFLGO_CONFIGURE_NATIVE" ]; then',
        1,
    )
    changed = True
if "FORMTRIG_LOCAL_CONFIG_AUX" in text:
    if "FORMTRIG_CANARY_TARGET_CFLAGS" not in text:
        extra = '''if [ -d "$MAGMA/formtrig/include" ]; then
    export CFLAGS="${CFLAGS:-} -I$MAGMA/formtrig/include"
    export CXXFLAGS="${CXXFLAGS:-} -I$MAGMA/formtrig/include"
fi
# FORMTRIG_CANARY_TARGET_CFLAGS

'''
        text = text.replace('cd "$TARGET/repo"\n', extra + 'cd "$TARGET/repo"\n', 1)
        changed = True
    if "FORMTRIG_CONFIG_LOG_ON_FAILURE" not in text:
        text = text.replace(
            './configure --disable-shared --prefix="$WORK"',
            './configure --disable-shared --prefix="$WORK" || '
            '{ echo "FORMTRIG_CONFIG_LOG_ON_FAILURE"; cat config.log >&2; exit 1; }',
        )
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
    raise SystemExit(0)

needle = 'cd "$TARGET/repo"\n'
if needle not in text:
    cmake_needle = 'cmake "$TARGET/repo"'
    if cmake_needle in text and "FORMTRIG_CANARY_TARGET_CFLAGS" not in text:
        extra = '''if [ -d "$MAGMA/formtrig/include" ]; then
    export CFLAGS="${CFLAGS:-} -I$MAGMA/formtrig/include"
    export CXXFLAGS="${CXXFLAGS:-} -I$MAGMA/formtrig/include"
fi
# FORMTRIG_CANARY_TARGET_CFLAGS

'''
        text = text.replace(cmake_needle, extra + cmake_needle, 1)
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
    raise SystemExit(0)

insert = r'''
formtrig_config_aux=""
for candidate in /usr/share/misc /usr/share/automake-1.16 /usr/share/automake-1.15 /usr/share/autoconf/build-aux /usr/share/libtool/build-aux; do
    if [ -f "$candidate/config.guess" ] && [ -f "$candidate/config.sub" ]; then
        formtrig_config_aux="$candidate"
        break
    fi
done
if [ -n "$formtrig_config_aux" ]; then
    mkdir -p "$TARGET/.formtrig-build-aux"
    cat > "$TARGET/.formtrig-build-aux/wget" <<'FORMTRIG_WGET'
#!/bin/sh
out=""
prev=""
for arg in "$@"; do
    if [ "$prev" = "-O" ]; then
        out="$arg"
    fi
    prev="$arg"
done
case " $* " in
    *config.guess*)
        [ -n "$out" ] || out="config.guess"
        cp "$FORMTRIG_LOCAL_CONFIG_AUX/config.guess" "$out"
        exit $?
        ;;
    *config.sub*)
        [ -n "$out" ] || out="config.sub"
        cp "$FORMTRIG_LOCAL_CONFIG_AUX/config.sub" "$out"
        exit $?
        ;;
esac
exec /usr/bin/wget "$@"
FORMTRIG_WGET
    chmod +x "$TARGET/.formtrig-build-aux/wget"
    export FORMTRIG_LOCAL_CONFIG_AUX="$formtrig_config_aux"
    export PATH="$TARGET/.formtrig-build-aux:$PATH"
fi

if [ -d "$MAGMA/formtrig/include" ]; then
    export CFLAGS="${CFLAGS:-} -I$MAGMA/formtrig/include"
    export CXXFLAGS="${CXXFLAGS:-} -I$MAGMA/formtrig/include"
fi
# FORMTRIG_CANARY_TARGET_CFLAGS

'''
text = text.replace(needle, insert + needle, 1)
text = text.replace(
    './configure --disable-shared --prefix="$WORK"',
    './configure --disable-shared --prefix="$WORK" || '
    '{ echo "FORMTRIG_CONFIG_LOG_ON_FAILURE"; cat config.log >&2; exit 1; }',
)
path.write_text(text, encoding="utf-8")
PY
}

patch_target_canary_include_flags() {
  local build_sh="$magma_dir/targets/$magma_target/build.sh"
  if [[ ! -f "$build_sh" ]]; then
    return
  fi

  python3 - "$build_sh" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "FORMTRIG_CANARY_TARGET_CFLAGS"
if marker in text:
    raise SystemExit(0)
needle = 'cd "$TARGET/repo"\n'
if needle not in text:
    raise SystemExit(0)
insert = '''if [ -d "$MAGMA/formtrig/include" ]; then
    export CFLAGS="${CFLAGS:-} -I$MAGMA/formtrig/include"
    export CXXFLAGS="${CXXFLAGS:-} -I$MAGMA/formtrig/include"
fi
# FORMTRIG_CANARY_TARGET_CFLAGS

'''
path.write_text(text.replace(needle, insert + needle, 1), encoding="utf-8")
PY
}

patch_php_host_compatibility() {
  local build_sh="$magma_dir/targets/$magma_target/build.sh"
  if [[ "$magma_target" != "php" ]] || [[ ! -f "$build_sh" ]]; then
    return
  fi

  python3 - "$build_sh" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "FORMTRIG_PHP_ICU_BOOL_HOST_COMPAT"
legacy_future = "from __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n"
dedup_marker = "FORMTRIG_PHP_DEDUP_FUZZING_ENGINE"
dedup_old = '    PHP_TARGET_FUZZING_ENGINE="${PHP_LIB_FUZZING_ENGINE:--Wall $PHP_TARGET_LIBS}"'
dedup_new = '    PHP_TARGET_FUZZING_ENGINE="${PHP_LIB_FUZZING_ENGINE:--Wall}"\n    # ' + dedup_marker
insert = r'''
# FORMTRIG_PHP_ICU_BOOL_HOST_COMPAT
if [ "$(basename "$TARGET")" = "php" ]; then
    python3 - "$TARGET/repo" <<'FORMTRIG_PHP_ICU'
import re
import sys
from pathlib import Path


repo = Path(sys.argv[1])


def expected_icu_operator_return():
    header = Path("/usr/include/unicode/brkiter.h")
    if header.exists():
        text = header.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            r"virtual\s+(UBool|bool)\s+operator==\s*"
            r"\(\s*const\s+BreakIterator\s*&[^)]*\)\s*const",
            text,
        )
        if match:
            return match.group(1)
    return "bool"


expected = expected_icu_operator_return()
# FORMTRIG_PHP_ICU_EXPECTED_RETURN
replacements = [
    (
        "ext/intl/breakiterator/codepointiterator_internal.h",
        [
            "virtual UBool operator==(const BreakIterator& that) const;",
            "virtual bool operator==(const BreakIterator& that) const;",
        ],
        "virtual {} operator==(const BreakIterator& that) const;".format(expected),
    ),
    (
        "ext/intl/breakiterator/codepointiterator_internal.cpp",
        [
            "UBool CodePointBreakIterator::operator==(const BreakIterator& that) const",
            "bool CodePointBreakIterator::operator==(const BreakIterator& that) const",
        ],
        "{} CodePointBreakIterator::operator==(const BreakIterator& that) const".format(expected),
    ),
]
changed = []
for relpath, candidates, desired in replacements:
    source = repo / relpath
    if not source.exists():
        continue
    text = source.read_text(encoding="utf-8")
    updated = text
    for old in candidates:
        updated = updated.replace(old, desired)
    if desired not in updated:
        raise SystemExit("expected ICU operator signature not found: {}".format(source))
    if updated != text:
        source.write_text(updated, encoding="utf-8")
        changed.append(str(source))
if changed:
    print(
        "FORMTRIG host-compat: synchronized PHP ICU {} operator== in {}".format(
            expected, ", ".join(changed)
        ),
        file=sys.stderr,
    )
FORMTRIG_PHP_ICU
fi

'''
if marker in text:
    updated = text.replace(legacy_future, "import sys\nfrom pathlib import Path\n")
    if dedup_marker not in updated and dedup_old in updated:
        updated = updated.replace(dedup_old, dedup_new, 1)
    if "FORMTRIG_PHP_ICU_EXPECTED_RETURN" not in updated:
        pattern = (
            r"\n?# FORMTRIG_PHP_ICU_BOOL_HOST_COMPAT\n"
            r"if \[ \"\$\(basename \"\$TARGET\"\)\" = \"php\" \]; then\n"
            r"    python3 - \"\$TARGET/repo\" <<'FORMTRIG_PHP_ICU'\n"
            r".*?\nFORMTRIG_PHP_ICU\nfi\n\n"
        )
        updated, count = re.subn(pattern, lambda _match: "\n" + insert, updated, count=1, flags=re.S)
        if count != 1:
            raise SystemExit("could not refresh existing PHP ICU host-compat block")
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    raise SystemExit(0)
needle = 'cd "$TARGET/repo"\n'
if needle not in text:
    raise SystemExit("could not locate target repo cd in PHP build.sh")
updated = text.replace(needle, needle + insert, 1)
if dedup_marker not in updated and dedup_old in updated:
    updated = updated.replace(dedup_old, dedup_new, 1)
path.write_text(updated, encoding="utf-8")
PY
}

restore_target_context() {
  if [[ -n "${target_repo_backup:-}" && -d "$target_repo_backup/repo" ]]; then
    if [[ -e "$target_repo_path" ]]; then
      rm -rf "$target_repo_path"
    fi
    mkdir -p "$(dirname "$target_repo_path")"
    mv "$target_repo_backup/repo" "$target_repo_path"
    rmdir "$target_repo_backup" 2>/dev/null || true
  fi
}

abs_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s\n' "$path"
  elif [[ -d "$path" ]]; then
    (cd "$path" && pwd)
  else
    local dir base
    dir="$(dirname "$path")"
    base="$(basename "$path")"
    (cd "$dir" && printf '%s/%s\n' "$(pwd)" "$base")
  fi
}

abs_repo_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s/%s\n' "$repo_root" "$path"
  fi
}

split_list() {
  printf '%s\n' "$1" | tr ', ' '\n' | awk 'NF { print }'
}

inventory_field() {
  local field="$1"
  python3 - "$inventory" "$target_id" "$field" <<'PY'
import json
import sys

path, target_id, field = sys.argv[1:4]
with open(path, encoding="utf-8") as handle:
    payload = json.load(handle)
for record in payload.get("records", []):
    if record.get("target_id") == target_id:
        value = record.get(field, "")
        print("" if value is None else value)
        raise SystemExit(0)
raise SystemExit(f"target_id not found in inventory: {target_id}")
PY
}

magma_fuzzer_for_baseline() {
  case "$1" in
    aflplusplus_vanilla)
      printf '%s\n' "aflplusplus_plain"
      ;;
    aflplusplus_cmplog|redqueen_operand)
      printf '%s\n' "aflplusplus"
      ;;
    *)
      echo "unsupported faithful Magma baseline: $1" >&2
      exit 2
      ;;
  esac
}

build_magma_fuzzer() {
  local fuzzer="$1"
  local build_env=(
    FUZZER="$fuzzer"
    TARGET="$magma_target"
    PROGRAM="$program"
    CANARY_MODE=1
    FORMTRIG_TARGET_BUG="$target_id"
  )
  if grep -q 'AFLGO_CONFIGURE_NATIVE' "$magma_dir/targets/$magma_target/build.sh"; then
    build_env+=(
      AFLGO_CONFIGURE_NATIVE=1
      AFLGO_CONFIGURE_CC="${FORMTRIG_BASELINE_CONFIGURE_CC:-clang}"
      AFLGO_CONFIGURE_CXX="${FORMTRIG_BASELINE_CONFIGURE_CXX:-clang++}"
      AFLGO_CONFIGURE_CFLAGS="${FORMTRIG_BASELINE_CONFIGURE_CFLAGS:-}"
      AFLGO_CONFIGURE_CXXFLAGS="${FORMTRIG_BASELINE_CONFIGURE_CXXFLAGS:-}"
      AFLGO_CONFIGURE_LDFLAGS="${FORMTRIG_BASELINE_CONFIGURE_LDFLAGS:-}"
      AFLGO_CONFIGURE_LIBS="${FORMTRIG_BASELINE_CONFIGURE_LIBS:-}"
    )
  fi
  (
    cd "$magma_dir"
    env "${build_env[@]}" ./tools/captain/build.sh
  ) > "$out_dir/build_${fuzzer}.log" 2>&1
}

copy_seed_corpus() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  find "$seed_dir" -maxdepth 1 -type f -exec cp {} "$dest/" \;
  if ! find "$dest" -maxdepth 1 -type f | grep -q .; then
    echo "seed corpus is empty after copy: $seed_dir" >&2
    exit 2
  fi
}

run_one_baseline() {
  local baseline="$1"
  local duration="$2"
  local rep="$3"
  local fuzzer
  fuzzer="$(magma_fuzzer_for_baseline "$baseline")"

  local suffix="${baseline}_${duration}s"
  if [[ "$reps" -gt 1 ]]; then
    suffix="${suffix}_rep${rep}"
  fi
  local shared="$out_dir/magma/$suffix"
  local run_out="$out_dir/runs/$suffix"
  mkdir -p "$shared" "$run_out"
  copy_seed_corpus "$shared/input_corpus"

  (
    cd "$magma_dir"
    FUZZER="$fuzzer" TARGET="$magma_target" PROGRAM="$program" \
      ARGS="$args_template" CANARY_MODE=1 SHARED="$shared" POLL="$poll" \
      TIMEOUT="${duration}s" MAGMA_INPUT_CORPUS=/magma_shared/input_corpus \
      FUZZARGS="${extra_fuzz_args[*]}" \
      MAGMA_SKIP_SEED_PRUNE=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 \
      FORMTRIG_TARGET_BUG="$target_id" ./tools/captain/start.sh
  ) > "$run_out/captain_stdout.log" 2> "$run_out/captain_stderr.log"

  "$repo_root/tools/run_post_reach_baseline.py" \
    --baseline "$baseline" \
    --target-id "$target_id" \
    --tc-category "$tc_category" \
    --seed-corpus "$seed_dir" \
    --out-dir "$run_out" \
    --budget-sec "$duration" \
    --rep "$rep" \
    --mode harvest \
    --existing-fuzzer-out "$shared/findings" \
    --magma-monitor-dir "$shared/monitor" \
    --magma-bug-id "$target_id" \
    --target-cmd "magma/captain $fuzzer $magma_target $program $args_template"
}

wait_for_job_slot() {
  local max_jobs="$1"
  while (( $(jobs -pr | wc -l) >= max_jobs )); do
    if ! wait -n; then
      failed_jobs=1
    fi
  done
}

wait_for_all_jobs() {
  while (( $(jobs -pr | wc -l) > 0 )); do
    if ! wait -n; then
      failed_jobs=1
    fi
  done
  if [[ "$failed_jobs" != "0" ]]; then
    echo "one or more baseline jobs failed" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-id)
      target_id="${2:-}"
      shift 2
      ;;
    --inventory)
      inventory="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    --magma-dir)
      magma_dir="${2:-}"
      shift 2
      ;;
    --seed-dir)
      seed_dir="${2:-}"
      shift 2
      ;;
    --durations)
      durations="${2:-}"
      shift 2
      ;;
    --baselines)
      baselines="${2:-}"
      shift 2
      ;;
    --reps)
      reps="${2:-}"
      shift 2
      ;;
    --rep-start)
      rep_start="${2:-}"
      shift 2
      ;;
    --rep-end)
      rep_end="${2:-}"
      shift 2
      ;;
    --jobs)
      jobs="${2:-}"
      shift 2
      ;;
    --poll)
      poll="${2:-}"
      shift 2
      ;;
    --afl-arg)
      extra_fuzz_args+=("${2:-}")
      shift 2
      ;;
    --no-build)
      run_build=0
      shift
      ;;
    --no-sweeps)
      run_sweeps=0
      shift
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

if [[ -z "$target_id" ]]; then
  echo "--target-id is required" >&2
  usage
  exit 2
fi

inventory="$(abs_path "$inventory")"
magma_dir="$(abs_path "$magma_dir")"
require_path "$inventory"
require_path "$magma_dir/tools/captain/build.sh"
require_path "$magma_dir/tools/captain/start.sh"
if [[ "$run_build" == "1" ]]; then
  sync_formtrig_canary_runtime
fi

magma_target="$(inventory_field project)"
program="$(inventory_field program)"
args_template="$(inventory_field args_template)"
tc_category="$(inventory_field primary_tc_category)"
inventory_seed_corpus="$(inventory_field initial_seed_corpus)"
if [[ "$args_template" != *"@@"* ]]; then
  echo "inventory args_template must contain @@ for AFL substitution: $args_template" >&2
  exit 2
fi

if [[ -z "$out_dir" ]]; then
  out_dir="/tmp/formtrig_${target_id,,}_baselines_${timestamp}"
fi

if [[ -z "$seed_dir" ]]; then
  rnt_seed_dir="$repo_root/artifacts/rnt_corpus/$target_id/seeds"
  if [[ -d "$rnt_seed_dir" ]]; then
    seed_dir="$rnt_seed_dir"
  else
    seed_dir="$(abs_repo_path "$inventory_seed_corpus")"
  fi
fi

mkdir -p "$out_dir"
out_dir="$(abs_path "$out_dir")"
seed_dir="$(abs_path "$seed_dir")"
require_path "$seed_dir"

if ! [[ "$reps" =~ ^[0-9]+$ ]] || [[ "$reps" -lt 1 ]]; then
  echo "--reps must be a positive integer: $reps" >&2
  exit 2
fi
if [[ -z "$rep_end" ]]; then
  rep_end="$reps"
fi
if ! [[ "$rep_start" =~ ^[0-9]+$ ]] || [[ "$rep_start" -lt 1 ]]; then
  echo "--rep-start must be a positive integer: $rep_start" >&2
  exit 2
fi
if ! [[ "$rep_end" =~ ^[0-9]+$ ]] || [[ "$rep_end" -lt 1 ]]; then
  echo "--rep-end must be a positive integer: $rep_end" >&2
  exit 2
fi
if [[ "$rep_start" -gt "$rep_end" ]] || [[ "$rep_end" -gt "$reps" ]]; then
  echo "--rep-start/--rep-end must satisfy 1 <= start <= end <= --reps: start=$rep_start end=$rep_end reps=$reps" >&2
  exit 2
fi
if ! [[ "$jobs" =~ ^[0-9]+$ ]] || [[ "$jobs" -lt 1 ]]; then
  echo "--jobs must be a positive integer: $jobs" >&2
  exit 2
fi

{
  printf 'target_id=%s\n' "$target_id"
  printf 'magma_target=%s\n' "$magma_target"
  printf 'program=%s\n' "$program"
  printf 'args_template=%s\n' "$args_template"
  printf 'tc_category=%s\n' "$tc_category"
  printf 'out_dir=%s\n' "$out_dir"
  printf 'magma_dir=%s\n' "$magma_dir"
  printf 'seed_dir=%s\n' "$seed_dir"
  printf 'inventory=%s\n' "$inventory"
  printf 'baselines=%s\n' "$baselines"
  printf 'durations=%s\n' "$durations"
  printf 'reps=%s\n' "$reps"
  printf 'rep_start=%s\n' "$rep_start"
  printf 'rep_end=%s\n' "$rep_end"
  printf 'jobs=%s\n' "$jobs"
  printf 'poll=%s\n' "$poll"
  printf 'fuzz_args=%s\n' "${extra_fuzz_args[*]}"
} > "$out_dir/run_metadata.txt"

if [[ "$run_build" == "1" ]]; then
  prepare_clean_target_context
  patch_target_build_helpers
  patch_target_canary_include_flags
  patch_php_host_compatibility
  trap restore_target_context EXIT

  declare -A built_fuzzers=()
  while IFS= read -r baseline; do
    fuzzer="$(magma_fuzzer_for_baseline "$baseline")"
    if [[ -n "${built_fuzzers[$fuzzer]:-}" ]]; then
      continue
    fi
    built_fuzzers[$fuzzer]=1
    build_magma_fuzzer "$fuzzer"
  done < <(split_list "$baselines")
fi

if [[ "$run_sweeps" == "1" ]]; then
  while IFS= read -r duration; do
    for ((rep = rep_start; rep <= rep_end; rep++)); do
      while IFS= read -r baseline; do
        if [[ "$jobs" -gt 1 ]]; then
          wait_for_job_slot "$jobs"
          run_one_baseline "$baseline" "$duration" "$rep" &
        else
          run_one_baseline "$baseline" "$duration" "$rep"
        fi
      done < <(split_list "$baselines")
    done
  done < <(split_list "$durations")
  if [[ "$jobs" -gt 1 ]]; then
    wait_for_all_jobs
  fi

  python3 "$repo_root/tools/summarize_post_reach_baselines.py" \
    --root "$out_dir/runs" \
    --out-json "$out_dir/summary.json" \
    --out-tsv "$out_dir/summary.tsv"
fi

if [[ "$run_build" == "1" ]]; then
  restore_target_context
  trap - EXIT
fi

echo "$target_id Magma baseline flow complete"
echo "  out=$out_dir"
echo "  magma_target=$magma_target"
echo "  program=$program"
echo "  baselines=$baselines"
echo "  durations=$durations"
echo "  reps=$reps"
echo "  rep_start=$rep_start"
echo "  rep_end=$rep_end"
echo "  jobs=$jobs"
