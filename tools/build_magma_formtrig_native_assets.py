#!/usr/bin/env python3
"""Build or plan FORMTRIG-native Magma target assets.

The tool intentionally defaults to dry-run planning. Use --execute to run the
Magma fetch/patch/instrument chain. A successful execution should leave the
expected executable under OUT/afl and the FORMTRIG site map under
OUT/formtrig_native/formtrig_sites.tsv; tools/discover_magma_native_assets.py
can then turn those files into validation assets.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MAGMA_ROOT = Path("experiments/magma_workspace/magma")
DEFAULT_OUT_ROOT = Path("artifacts/formtrig_native_readiness/magma_native_builds")


OPENJPEG_CONFIG_GLOBS = [
    "/usr/lib/*/openjpeg-*/OpenJPEGConfig.cmake",
    "/usr/lib/*/openjpeg-*/openjpeg-config.cmake",
    "/usr/local/lib/*/openjpeg-*/OpenJPEGConfig.cmake",
    "/usr/local/lib/openjpeg-*/OpenJPEGConfig.cmake",
    "/usr/share/openjpeg-*/OpenJPEGConfig.cmake",
]


TARGET_DEPENDENCY_REQUIREMENTS = {
    "poppler": [
        {
            "id": "poppler_cairo_pkg_config",
            "kind": "pkg_config",
            "name": "cairo",
            "apt_package_hints": ["libcairo2-dev"],
            "reason": "Poppler build enables Cairo support through pkg-config.",
        },
        {
            "id": "poppler_openjpeg_cmake_config",
            "kind": "path_glob",
            "patterns": OPENJPEG_CONFIG_GLOBS,
            "apt_package_hints": ["libopenjp2-7-dev"],
            "reason": "Poppler build enables the OpenJPEG JPX decoder.",
        },
        {
            "id": "poppler_tiff_pkg_config",
            "kind": "pkg_config",
            "name": "libtiff-4",
            "apt_package_hints": ["libtiff-dev"],
            "reason": "Poppler's selected utility build compiles TIFF writer support.",
        },
        {
            "id": "poppler_lcms_pkg_config",
            "kind": "pkg_config",
            "name": "lcms2",
            "apt_package_hints": ["liblcms2-dev"],
            "reason": "Poppler's selected utility build links Little CMS support.",
        },
    ],
    "php": [
        {
            "id": "php_bison",
            "kind": "command",
            "name": "bison",
            "apt_package_hints": ["bison"],
            "reason": "PHP buildconf/configure requires bison to generate parsers.",
        },
        {
            "id": "php_re2c",
            "kind": "command",
            "name": "re2c",
            "apt_package_hints": ["re2c"],
            "reason": "PHP builds generated scanners from source during native target builds.",
        },
        {
            "id": "php_icu_pkg_config",
            "kind": "pkg_config",
            "name": "icu-uc",
            "apt_package_hints": ["libicu-dev"],
            "reason": "The selected Magma PHP build enables intl support.",
        },
    ],
}


CANARY_HEADER = r"""#ifndef CANARY_H_
#define CANARY_H_
#ifdef __cplusplus
extern "C" {
#endif

#if defined(__x86_64__) || defined (__i386__)
#include "arch/x86.h"
#else
#include "arch/noarch.h"
#endif

#include "formtrig/formtrig_runtime.h"

extern void magma_log(const char *bug, int condition);

#define MAGMA_LOG(b,c) do { \
    const char *__ft_bug = (b); \
    if (formtrig_target_selected(__ft_bug)) { \
      if (formtrig_target_from_canary()) formtrig_target_hit(__ft_bug); \
      int __ft_sup = formtrig_suppress_canary_events(); \
      if (__ft_sup) formtrig_suppress_begin(); \
      int __ft_cond = (int)(c); \
      if (__ft_sup) formtrig_suppress_end(); \
      formtrig_crash_predicate(__ft_cond, __ft_bug); \
      magma_log(__ft_bug, __ft_cond); \
    } else { \
      magma_log(__ft_bug, 0); \
    } \
  } while (0)

#ifdef __cplusplus
#define MAGMA_LOG_V(b,c) ([&]() -> int { \
    const char *__ft_bug = (b); \
    if (formtrig_target_selected(__ft_bug)) { \
      if (formtrig_target_from_canary()) formtrig_target_hit(__ft_bug); \
      int __ft_sup = formtrig_suppress_canary_events(); \
      if (__ft_sup) formtrig_suppress_begin(); \
      int __ft_cond = (int)(c); \
      if (__ft_sup) formtrig_suppress_end(); \
      formtrig_crash_predicate(__ft_cond, __ft_bug); \
      magma_log(__ft_bug, __ft_cond); \
      return __ft_cond; \
    } \
    magma_log(__ft_bug, 0); \
    return 0; \
  }())
#else
#define MAGMA_LOG_V(b,c) ({ \
    const char *__ft_bug = (b); \
    int __ft_ret = 0; \
    if (formtrig_target_selected(__ft_bug)) { \
      if (formtrig_target_from_canary()) formtrig_target_hit(__ft_bug); \
      int __ft_sup = formtrig_suppress_canary_events(); \
      if (__ft_sup) formtrig_suppress_begin(); \
      __ft_ret = (int)(c); \
      if (__ft_sup) formtrig_suppress_end(); \
      formtrig_crash_predicate(__ft_ret, __ft_bug); \
      magma_log(__ft_bug, __ft_ret); \
    } else { \
      magma_log(__ft_bug, 0); \
    } \
    __ft_ret; \
  })
#endif

#define MAGMA_AND(a,b) magma_and((a),(b))
#define MAGMA_OR(a,b) magma_or((a),(b))

#ifdef __cplusplus
}
#endif
#endif
"""


OPENSSL_PKCS7_DECODE_FUZZER = r"""/*
 * FORMTRIG SSL011 validation runner.
 *
 * The stock OpenSSL asn1/cms fuzzers parse or serialize inputs but do not
 * exercise PKCS7_dataDecode, where Magma's SSL011 canary is logged. This
 * runner keeps the normal OpenSSL fuzz driver while making that workflow
 * explicit so the target can be used for BindingSpec validation.
 */

#include <limits.h>
#include <stdint.h>
#include <stddef.h>
#include <openssl/bio.h>
#include <openssl/crypto.h>
#include <openssl/err.h>
#include <openssl/pkcs7.h>
#include "fuzzer.h"

int FuzzerInitialize(int *argc, char ***argv)
{
    OPENSSL_init_crypto(OPENSSL_INIT_LOAD_CRYPTO_STRINGS, NULL);
    ERR_clear_error();
    CRYPTO_free_ex_index(0, -1);
    return 1;
}

int FuzzerTestOneInput(const uint8_t *buf, size_t len)
{
    BIO *in;
    BIO *decoded;
    PKCS7 *p7;

    if (len == 0 || len > INT_MAX)
        return 0;

    in = BIO_new_mem_buf(buf, (int)len);
    if (in == NULL)
        return 0;

    p7 = d2i_PKCS7_bio(in, NULL);
    if (p7 != NULL) {
        decoded = PKCS7_dataDecode(p7, NULL, NULL, NULL);
        if (decoded != NULL)
            BIO_free_all(decoded);
        PKCS7_free(p7);
    }

    BIO_free(in);
    ERR_clear_error();
    return 0;
}

void FuzzerCleanup(void)
{
}
"""


OPENSSL_PKCS7_BUILD_FRAGMENT = r"""
# FORMTRIG custom OpenSSL PKCS7 dataDecode fuzzer.
if [ -f "$TARGET/src/pkcs7_decode.c" ]; then
    "$CC" $CFLAGS -I. -Iinclude -Ifuzz -DOPENSSL_NO_FUZZ_LIBFUZZER \
        "$TARGET/src/pkcs7_decode.c" fuzz/driver.c \
        -o "$OUT/pkcs7_decode" \
        $LDFLAGS libcrypto.a $LIBS -ldl -pthread
fi
"""


PHP_EXIF_THUMBNAIL_CALL = r"""	zval args[3];

	args[0] = stream_zv;
	ZVAL_NULL(&args[1]);
	ZVAL_NULL(&args[2]);

	fuzzer_call_php_func_zval("exif_thumbnail", 3, args);
"""


POPPLER_OPENJPEG_PATCH_PY = r"""import re
import sys
from pathlib import Path


def patch_poppler_openjpeg_dir(text, openjpeg_dir):
    pattern = re.compile(
        r'(?m)^(?P<prefix>\s*EXTRA="\$EXTRA\s+-DOpenJPEG_DIR=)'
        r'(?P<value>[^"\n]*)(?P<quote>"?)$'
    )

    def replace(match):
        return f"{match.group('prefix')}{openjpeg_dir}\""

    return pattern.sub(replace, text)


def patch_poppler_freetype_optional_codecs(text):
    pattern = re.compile(
        r'(?m)^(?P<prefix>\./configure\s+--prefix="\$WORK"\s+--disable-shared)'
        r'(?P<rest>\s+PKG_CONFIG_PATH="\$WORK/lib/pkgconfig")$'
    )

    def replace(match):
        line = match.group(0)
        if "--with-bzip2=no" in line or "--with-brotli=no" in line:
            return line
        return (
            f"{match.group('prefix')} --with-bzip2=no --with-brotli=no"
            f"{match.group('rest')}"
        )

    return pattern.sub(replace, text)


def patch_poppler_pdf_fuzzer_guard(text):
    needle = '''$CXX $CXXFLAGS -std=c++11 -I"$WORK/poppler/cpp" -I"$TARGET/repo/cpp" \\
    "$TARGET/src/pdf_fuzzer.cc" -o "$OUT/pdf_fuzzer" \\
    "$WORK/poppler/cpp/libpoppler-cpp.a" "$WORK/poppler/libpoppler.a" \\
    "$WORK/lib/libfreetype.a" $LDFLAGS $LIBS -ljpeg -lz \\
    -lopenjp2 -lpng -ltiff -llcms2 -lm -lpthread -pthread
'''
    if 'if [ "${PROGRAM:-}" = "pdf_fuzzer" ]; then' in text:
        return text
    replacement = '''if [ "${PROGRAM:-}" = "pdf_fuzzer" ]; then
    $CXX $CXXFLAGS -std=c++11 -I"$WORK/poppler/cpp" -I"$TARGET/repo/cpp" \\
        "$TARGET/src/pdf_fuzzer.cc" -o "$OUT/pdf_fuzzer" \\
        "$WORK/poppler/cpp/libpoppler-cpp.a" "$WORK/poppler/libpoppler.a" \\
        "$WORK/lib/libfreetype.a" $LDFLAGS $LIBS -ljpeg -lz \\
        -lopenjp2 -lpng -ltiff -llcms2 -lm -lpthread -pthread
fi
'''
    return text.replace(needle, replacement)


build_sh = Path(sys.argv[1])
openjpeg_dir = sys.argv[2]
text = build_sh.read_text(encoding="utf-8")
patched = patch_poppler_openjpeg_dir(text, openjpeg_dir)
patched = patch_poppler_freetype_optional_codecs(patched)
patched = patch_poppler_pdf_fuzzer_guard(patched)
if patched != text:
    build_sh.write_text(patched, encoding="utf-8")
"""


def patch_poppler_openjpeg_dir_text(text: str, openjpeg_dir: str) -> str:
    pattern = re.compile(
        r'(?m)^(?P<prefix>\s*EXTRA="\$EXTRA\s+-DOpenJPEG_DIR=)'
        r'(?P<value>[^"\n]*)(?P<quote>"?)$'
    )

    def replace(match: re.Match[str]) -> str:
        return f"{match.group('prefix')}{openjpeg_dir}\""

    return pattern.sub(replace, text)


def patch_poppler_freetype_optional_codecs_text(text: str) -> str:
    pattern = re.compile(
        r'(?m)^(?P<prefix>\./configure\s+--prefix="\$WORK"\s+--disable-shared)'
        r'(?P<rest>\s+PKG_CONFIG_PATH="\$WORK/lib/pkgconfig")$'
    )

    def replace(match: re.Match[str]) -> str:
        line = match.group(0)
        if "--with-bzip2=no" in line or "--with-brotli=no" in line:
            return line
        return (
            f"{match.group('prefix')} --with-bzip2=no --with-brotli=no"
            f"{match.group('rest')}"
        )

    return pattern.sub(replace, text)


def patch_poppler_pdf_fuzzer_guard_text(text: str) -> str:
    needle = """$CXX $CXXFLAGS -std=c++11 -I"$WORK/poppler/cpp" -I"$TARGET/repo/cpp" \\
    "$TARGET/src/pdf_fuzzer.cc" -o "$OUT/pdf_fuzzer" \\
    "$WORK/poppler/cpp/libpoppler-cpp.a" "$WORK/poppler/libpoppler.a" \\
    "$WORK/lib/libfreetype.a" $LDFLAGS $LIBS -ljpeg -lz \\
    -lopenjp2 -lpng -ltiff -llcms2 -lm -lpthread -pthread
"""
    if 'if [ "${PROGRAM:-}" = "pdf_fuzzer" ]; then' in text:
        return text
    replacement = """if [ "${PROGRAM:-}" = "pdf_fuzzer" ]; then
    $CXX $CXXFLAGS -std=c++11 -I"$WORK/poppler/cpp" -I"$TARGET/repo/cpp" \\
        "$TARGET/src/pdf_fuzzer.cc" -o "$OUT/pdf_fuzzer" \\
        "$WORK/poppler/cpp/libpoppler-cpp.a" "$WORK/poppler/libpoppler.a" \\
        "$WORK/lib/libfreetype.a" $LDFLAGS $LIBS -ljpeg -lz \\
        -lopenjp2 -lpng -ltiff -llcms2 -lm -lpthread -pthread
fi
"""
    return text.replace(needle, replacement)


def patch_poppler_build_text(text: str, openjpeg_dir: str) -> str:
    return patch_poppler_pdf_fuzzer_guard_text(
        patch_poppler_freetype_optional_codecs_text(
            patch_poppler_openjpeg_dir_text(text, openjpeg_dir)
        )
    )


def php_exif_thumbnail_runner_text(exif_fuzzer_text: str) -> str:
    """Derive a thumbnail-enabled EXIF runner from PHP's stock exif fuzzer."""
    needle = '\tfuzzer_call_php_func_zval("exif_read_data", 1, &stream_zv);\n'
    if needle not in exif_fuzzer_text:
        raise ValueError("stock PHP fuzzer-exif.c call site was not found")
    return exif_fuzzer_text.replace(needle, PHP_EXIF_THUMBNAIL_CALL, 1)


def patch_php_fuzzer_config_for_exif_thumbnail_text(text: str) -> str:
    marker = "PHP_FUZZER_TARGET([exif_thumbnail], PHP_FUZZER_EXIF_THUMBNAIL_OBJS)"
    if marker in text:
        return text
    needle = "    PHP_FUZZER_TARGET([exif], PHP_FUZZER_EXIF_OBJS)\n"
    if needle not in text:
        return text
    return text.replace(needle, needle + f"    {marker}\n", 1)


def patch_php_build_for_exif_thumbnail_text(text: str) -> str:
    if "php-fuzz-exif_thumbnail" in text:
        return text
    return text.replace(
        "php-fuzz-json php-fuzz-exif php-fuzz-mbstring php-fuzz-unserialize php-fuzz-parser",
        (
            "php-fuzz-json php-fuzz-exif php-fuzz-exif_thumbnail "
            "php-fuzz-mbstring php-fuzz-unserialize php-fuzz-parser"
        ),
        1,
    )


def patch_php_fuzzer_makefile_for_exif_thumbnail_text(text: str) -> str:
    marker = "$(SAPI_FUZZER_PATH)/php-fuzz-exif_thumbnail:"
    if marker in text:
        return text
    needle = (
        "$(SAPI_FUZZER_PATH)/php-fuzz-exif: $(PHP_GLOBAL_OBJS) $(PHP_SAPI_OBJS) "
        "$(PHP_FUZZER_EXIF_OBJS)\n"
        "\t$(FUZZER_BUILD) $(PHP_FUZZER_EXIF_OBJS) -o $@\n"
    )
    replacement = (
        needle
        + "\n"
        + "$(SAPI_FUZZER_PATH)/php-fuzz-exif_thumbnail: "
        + "$(PHP_GLOBAL_OBJS) $(PHP_SAPI_OBJS) $(PHP_FUZZER_EXIF_THUMBNAIL_OBJS)\n"
        + "\t$(FUZZER_BUILD) $(PHP_FUZZER_EXIF_THUMBNAIL_OBJS) -o $@\n"
    )
    return text.replace(needle, replacement, 1)


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def quote_env(env: dict[str, str]) -> str:
    return " ".join(f"{key}={shlex.quote(value)}" for key, value in sorted(env.items()))


def default_program_args(configrc: Path, program: str) -> str:
    if configrc.parent.name == "openssl":
        return "-"
    return "@@"


def parse_program_args(configrc: Path, program: str) -> str:
    if not configrc.exists():
        return default_program_args(configrc, program)
    pattern = re.compile(rf"^{re.escape(program)}_ARGS=(.*)$")
    for raw in configrc.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value or default_program_args(configrc, program)
    return default_program_args(configrc, program)


def repo_has_magma_log(repo: Path) -> bool:
    if not repo.exists():
        return False
    try:
        proc = subprocess.run(
            ["rg", "-q", "MAGMA_LOG", str(repo)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc.returncode == 0
    except FileNotFoundError:
        for root, dirnames, filenames in os.walk(repo):
            dirnames[:] = [name for name in dirnames if name != ".git"]
            for filename in filenames:
                path = Path(root) / filename
                try:
                    if "MAGMA_LOG" in path.read_text(encoding="utf-8", errors="ignore"):
                        return True
                except OSError:
                    continue
    return False


def git_repo_has_head(repo: Path) -> bool:
    if not repo.exists():
        return False
    expected = repo.resolve()
    top = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
    )
    if top.returncode != 0:
        return False
    try:
        if Path(top.stdout.strip()).resolve() != expected:
            return False
    except OSError:
        return False
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def target_fetch_command(fetch_sh: Path, target_repo: Path) -> list[str]:
    return [
        "bash",
        "-lc",
        "{} && git -C {} rev-parse --verify HEAD >/dev/null".format(
            shlex.quote(str(fetch_sh)),
            shlex.quote(str(target_repo)),
        ),
    ]


def pkg_config_exists(package: str) -> bool:
    if shutil.which("pkg-config") is None:
        return False
    proc = subprocess.run(
        ["pkg-config", "--exists", package],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def first_glob_match(patterns: list[str]) -> str:
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return ""


def dependency_preflight_for_target(
    target: str,
    *,
    pkg_exists=pkg_config_exists,
    cmd_exists=command_exists,
    glob_match=first_glob_match,
) -> dict[str, Any]:
    requirements = TARGET_DEPENDENCY_REQUIREMENTS.get(target, [])
    checks: list[dict[str, Any]] = []
    apt_hints: set[str] = set()
    missing = False
    for requirement in requirements:
        kind = requirement["kind"]
        if kind == "pkg_config":
            ok = bool(pkg_exists(requirement["name"]))
            value = requirement["name"] if ok else ""
        elif kind == "command":
            ok = bool(cmd_exists(requirement["name"]))
            value = requirement["name"] if ok else ""
        elif kind == "path_glob":
            value = str(glob_match(requirement["patterns"]))
            ok = bool(value)
        else:
            ok = True
            value = ""
        row = {
            "id": requirement["id"],
            "kind": kind,
            "status": "ok" if ok else "missing",
            "value": value,
            "reason": requirement["reason"],
            "apt_package_hints": requirement.get("apt_package_hints", []),
        }
        checks.append(row)
        if not ok:
            missing = True
            apt_hints.update(requirement.get("apt_package_hints", []))
    if not checks:
        status = "not_required"
    elif missing:
        status = "missing"
    else:
        status = "ok"
    return {
        "status": status,
        "target": target,
        "checks": checks,
        "apt_package_hints": sorted(apt_hints),
    }


def host_compatibility_patches_for_target(target: str) -> list[dict[str, Any]]:
    if target != "php":
        return []
    return [
        {
            "id": "php_icu_breakiterator_operator_return",
            "reason": "Old PHP ext/intl must match the host ICU BreakIterator::operator== return type.",
            "files": [
                "ext/intl/breakiterator/codepointiterator_internal.h",
                "ext/intl/breakiterator/codepointiterator_internal.cpp",
            ],
        }
    ]


def default_out_dir(target_id: str, target: str, program: str) -> Path:
    name = target_id or f"{target}_{program}"
    return DEFAULT_OUT_ROOT / name


def step(
    name: str,
    command: list[str],
    *,
    env: dict[str, str],
    selected: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "selected": selected,
        "reason": reason,
        "command": command,
        "shell": quote_env(env) + (" " if env else "") + shell_join(command),
        "env": env,
    }


def runner_instrument_script_text() -> str:
    canary = CANARY_HEADER.rstrip("\n")
    openssl_pkcs7_decode = OPENSSL_PKCS7_DECODE_FUZZER.rstrip("\n")
    openssl_pkcs7_build = OPENSSL_PKCS7_BUILD_FRAGMENT.rstrip("\n")
    poppler_openjpeg_patch = POPPLER_OPENJPEG_PATCH_PY.rstrip("\n")
    php_exif_thumbnail_call = PHP_EXIF_THUMBNAIL_CALL.rstrip("\n")
    return f"""#!/usr/bin/env bash
set -euo pipefail

cat > "$MAGMA/src/canary.h" <<'EOF'
{canary}
EOF

native_work="$OUT/formtrig_native"
mkdir -p "$OUT/afl" "$native_work"
rm -f "$native_work/formtrig_sites.tsv"

if [ -n "${{FORMTRIG_SOURCE_DIR:-}}" ]; then
  if [ ! -d "$FORMTRIG_SOURCE_DIR/include/formtrig" ] || \
     [ ! -f "$FORMTRIG_SOURCE_DIR/runtime/formtrig_runtime.c" ] || \
     [ ! -f "$FORMTRIG_SOURCE_DIR/llvm/formtrig_pass.cpp" ]; then
    echo "FORMTRIG_SOURCE_DIR does not look like a FORMTRIG runtime tree: $FORMTRIG_SOURCE_DIR" >&2
    exit 2
  fi
  source_formtrig="$(cd "$FORMTRIG_SOURCE_DIR" && pwd -P)"
  target_formtrig="$FUZZER/formtrig"
  mkdir -p "$target_formtrig"
  for rel in include runtime llvm binding_specs; do
    if [ -e "$source_formtrig/$rel" ]; then
      rm -rf "$target_formtrig/$rel"
      cp -a "$source_formtrig/$rel" "$target_formtrig/$rel"
    fi
  done
  if [ -f "$source_formtrig/logger_schema.md" ]; then
    cp -a "$source_formtrig/logger_schema.md" "$target_formtrig/logger_schema.md"
  fi
  if [ ! -f "$target_formtrig/tools/prepare_native_build.py" ]; then
    echo "FORMTRIG fuzzer overlay is missing tools/prepare_native_build.py: $target_formtrig" >&2
    exit 2
  fi
fi

real_wget="$(command -v wget || true)"
local_config_aux=""
for candidate in /usr/share/misc /usr/share/automake-1.16 /usr/share/autoconf/build-aux /usr/share/libtool/build-aux; do
  if [ -x "$candidate/config.guess" ] && [ -x "$candidate/config.sub" ]; then
    local_config_aux="$candidate"
    break
  fi
done
if [ -n "$local_config_aux" ]; then
  mkdir -p "$native_work/bin"
  cat > "$native_work/bin/wget" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

out=""
args=("$@")
for ((idx = 0; idx < ${{#args[@]}}; idx++)); do
  case "${{args[$idx]}}" in
    -O)
      if (( idx + 1 < ${{#args[@]}} )); then
        out="${{args[$((idx + 1))]}}"
      fi
      ;;
    -O*)
      out="${{args[$idx]#-O}}"
      ;;
  esac
done
last_index=$((${{#args[@]}} - 1))
url="${{args[$last_index]}}"
for file in config.guess config.sub; do
  if [[ "$url" == *"/$file" ]]; then
    src="${{FORMTRIG_LOCAL_CONFIG_AUX}}/$file"
    if [ -n "$out" ]; then
      cp "$src" "$out"
    else
      cat "$src"
    fi
    exit 0
  fi
done
if [ -n "${{FORMTRIG_REAL_WGET:-}}" ]; then
  exec "$FORMTRIG_REAL_WGET" "$@"
fi
echo "wget unavailable and URL is not a local config-aux file: $url" >&2
exit 127
EOF
  chmod +x "$native_work/bin/wget"
  export FORMTRIG_REAL_WGET="$real_wget"
  export FORMTRIG_LOCAL_CONFIG_AUX="$local_config_aux"
  export PATH="$native_work/bin:$PATH"
fi

prepare_args=(
  python3 "$FUZZER/formtrig/tools/prepare_native_build.py"
  --work-dir "$native_work"
  --cc-compiler "${{FORMTRIG_CC_COMPILER:-$FUZZER/repo/afl-clang-fast}}"
  --cxx-compiler "${{FORMTRIG_CXX_COMPILER:-$FUZZER/repo/afl-clang-fast++}}"
  --runtime-cc "${{FORMTRIG_RUNTIME_CC:-clang}}"
  --instrument-level "${{FORMTRIG_INSTRUMENT_LEVEL:-balanced}}"
  --runtime-link-mode never
  --skip-pass-regex '(^|/)(magma/magma/src|magma/src)/'
  --skip-pass-regex '(^|/)(magma/magma/formtrig/runtime|magma/formtrig/runtime)/'
  --skip-pass-regex '(^|/)CMakeFiles/(CMakeScratch|CMakeTmp)/'
  --skip-pass-regex '(^|/)conftest\\.(c|cc|cpp|cxx)$'
  --skip-pass-regex '(^|/)freetype2/src/tools/'
  --env AFL_QUIET=1
  --force
)
if [ -n "${{FORMTRIG_AFL_CC:-}}" ]; then
  prepare_args+=(--afl-cc "$FORMTRIG_AFL_CC")
fi
if [ -n "${{FORMTRIG_AFL_CXX:-}}" ]; then
  prepare_args+=(--afl-cxx "$FORMTRIG_AFL_CXX")
fi
if [ -n "${{FORMTRIG_PASS_CXX:-}}" ]; then
  prepare_args+=(--pass-cxx "$FORMTRIG_PASS_CXX")
fi
if [ -n "${{FORMTRIG_LLVM_CONFIG:-}}" ]; then
  prepare_args+=(--llvm-config "$FORMTRIG_LLVM_CONFIG")
fi

"${{prepare_args[@]}}"

# shellcheck disable=SC1090
source "$native_work/formtrig_build_env.sh"

driver="$FUZZER/repo/utils/aflpp_driver/libAFLDriver.a"
driver_lib=""
if [ "${{FORMTRIG_MAGMA_LINK_AFL_DRIVER:-1}}" != "0" ]; then
  driver_lib=" $driver"
fi
case "${{FORMTRIG_MAGMA_CXX_STDLIB:-libc++}}" in
  libc++)
    export LIBS="$LIBS -lc++ -lc++abi$driver_lib"
    export CXXFLAGS="$CXXFLAGS -stdlib=libc++"
    ;;
  libstdc++)
    export LIBS="$LIBS -lstdc++$driver_lib"
    ;;
  none)
    export LIBS="$LIBS$driver_lib"
    ;;
  *)
    echo "unsupported FORMTRIG_MAGMA_CXX_STDLIB=$FORMTRIG_MAGMA_CXX_STDLIB" >&2
    exit 2
    ;;
esac

if grep -q 'AFLGO_CONFIGURE_NATIVE' "$TARGET/build.sh"; then
  export AFLGO_CONFIGURE_NATIVE="${{AFLGO_CONFIGURE_NATIVE:-1}}"
  export AFLGO_CONFIGURE_CC="${{AFLGO_CONFIGURE_CC:-${{FORMTRIG_AFL_CC:-clang}}}}"
  export AFLGO_CONFIGURE_CXX="${{AFLGO_CONFIGURE_CXX:-${{FORMTRIG_AFL_CXX:-clang++}}}}"
  export AFLGO_CONFIGURE_CFLAGS="${{AFLGO_CONFIGURE_CFLAGS:-}}"
  export AFLGO_CONFIGURE_CXXFLAGS="${{AFLGO_CONFIGURE_CXXFLAGS:-}}"
  export AFLGO_CONFIGURE_LDFLAGS="${{AFLGO_CONFIGURE_LDFLAGS:-}}"
  export AFLGO_CONFIGURE_LIBS="${{AFLGO_CONFIGURE_LIBS:-}}"
fi

if [ "$(basename "$TARGET")" = "php" ]; then
  python3 - "$TARGET/repo" <<'PY'
import re
import sys
from pathlib import Path

repo = Path(sys.argv[1])


def expected_icu_operator_return():
    header = Path("/usr/include/unicode/brkiter.h")
    if header.exists():
        text = header.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            r"virtual\\s+(UBool|bool)\\s+operator==\\s*"
            r"\\(\\s*const\\s+BreakIterator\\s*&[^)]*\\)\\s*const",
            text,
        )
        if match:
            return match.group(1)
    return "bool"


expected = expected_icu_operator_return()
replacements = [
    (
        "ext/intl/breakiterator/codepointiterator_internal.h",
        [
            "virtual UBool operator==(const BreakIterator& that) const;",
            "virtual bool operator==(const BreakIterator& that) const;",
        ],
        "virtual {{}} operator==(const BreakIterator& that) const;".format(expected),
    ),
    (
        "ext/intl/breakiterator/codepointiterator_internal.cpp",
        [
            "UBool CodePointBreakIterator::operator==(const BreakIterator& that) const",
            "bool CodePointBreakIterator::operator==(const BreakIterator& that) const",
        ],
        "{{}} CodePointBreakIterator::operator==(const BreakIterator& that) const".format(expected),
    ),
]
changed = []
for rel, candidates, desired in replacements:
    path = repo / rel
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    updated = text
    for old in candidates:
        updated = updated.replace(old, desired)
    if desired not in updated:
        raise SystemExit("expected ICU operator signature not found: {{}}".format(path))
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        changed.append(rel)
if changed:
    print(
        "FORMTRIG host-compat: synchronized PHP ICU {{}} operator== in {{}}".format(
            expected, ", ".join(changed)
        )
    )
PY
fi

if [ "$(basename "$TARGET")" = "php" ] && [ "${{PROGRAM:-}}" = "exif_thumbnail" ]; then
  python3 - "$TARGET/repo" "$TARGET/build.sh" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1])
build_sh = Path(sys.argv[2])

stock = repo / "sapi/fuzzer/fuzzer-exif.c"
thumb = repo / "sapi/fuzzer/fuzzer-exif_thumbnail.c"
config = repo / "sapi/fuzzer/config.m4"
makefile = repo / "sapi/fuzzer/Makefile.frag"

source = stock.read_text(encoding="utf-8")
call_needle = '\tfuzzer_call_php_func_zval("exif_read_data", 1, &stream_zv);\\n'
call_replacement = '''{php_exif_thumbnail_call}
'''
if call_needle not in source:
    raise SystemExit("stock PHP fuzzer-exif.c call site was not found")
thumb.write_text(source.replace(call_needle, call_replacement, 1), encoding="utf-8")

config_text = config.read_text(encoding="utf-8")
target_line = "PHP_FUZZER_TARGET([exif_thumbnail], PHP_FUZZER_EXIF_THUMBNAIL_OBJS)"
if target_line not in config_text:
    needle = "    PHP_FUZZER_TARGET([exif], PHP_FUZZER_EXIF_OBJS)\\n"
    if needle not in config_text:
        raise SystemExit("PHP fuzzer config exif target was not found")
    config.write_text(
        config_text.replace(needle, needle + "    " + target_line + "\\n", 1),
        encoding="utf-8",
    )

build_text = build_sh.read_text(encoding="utf-8")
if "php-fuzz-exif_thumbnail" not in build_text:
    old = "php-fuzz-json php-fuzz-exif php-fuzz-mbstring php-fuzz-unserialize php-fuzz-parser"
    new = "php-fuzz-json php-fuzz-exif php-fuzz-exif_thumbnail php-fuzz-mbstring php-fuzz-unserialize php-fuzz-parser"
    if old not in build_text:
        raise SystemExit("PHP build.sh FUZZERS list was not found")
    build_sh.write_text(build_text.replace(old, new, 1), encoding="utf-8")

makefile_text = makefile.read_text(encoding="utf-8")
makefile_target = "$(SAPI_FUZZER_PATH)/php-fuzz-exif_thumbnail:"
if makefile_target not in makefile_text:
    needle = (
        "$(SAPI_FUZZER_PATH)/php-fuzz-exif: $(PHP_GLOBAL_OBJS) $(PHP_SAPI_OBJS) "
        "$(PHP_FUZZER_EXIF_OBJS)\\n"
        "\\t$(FUZZER_BUILD) $(PHP_FUZZER_EXIF_OBJS) -o $@\\n"
    )
    replacement = (
        needle
        + "\\n"
        + "$(SAPI_FUZZER_PATH)/php-fuzz-exif_thumbnail: "
        + "$(PHP_GLOBAL_OBJS) $(PHP_SAPI_OBJS) $(PHP_FUZZER_EXIF_THUMBNAIL_OBJS)\\n"
        + "\\t$(FUZZER_BUILD) $(PHP_FUZZER_EXIF_THUMBNAIL_OBJS) -o $@\\n"
    )
    if needle not in makefile_text:
        raise SystemExit("PHP fuzzer Makefile exif rule was not found")
    makefile.write_text(makefile_text.replace(needle, replacement, 1), encoding="utf-8")
PY
fi

if [ "$(basename "$TARGET")" = "poppler" ]; then
  if [ -z "${{FORMTRIG_OPENJPEG_DIR:-}}" ]; then
    for cfg in /usr/lib/*/openjpeg-*/OpenJPEGConfig.cmake \
               /usr/lib/*/openjpeg-*/openjpeg-config.cmake \
               /usr/local/lib/*/openjpeg-*/OpenJPEGConfig.cmake \
               /usr/local/lib/openjpeg-*/OpenJPEGConfig.cmake \
               /usr/share/openjpeg-*/OpenJPEGConfig.cmake; do
      if [ -f "$cfg" ]; then
        export FORMTRIG_OPENJPEG_DIR="$(dirname "$cfg")"
        break
      fi
    done
  fi
  if [ -n "${{FORMTRIG_OPENJPEG_DIR:-}}" ]; then
    python3 - "$TARGET/build.sh" "$FORMTRIG_OPENJPEG_DIR" <<'PY'
{poppler_openjpeg_patch}
PY
  fi
fi

if [ "$(basename "$TARGET")" = "openssl" ] && [ "${{PROGRAM:-}}" = "pkcs7_decode" ]; then
  mkdir -p "$TARGET/src"
  cat > "$TARGET/src/pkcs7_decode.c" <<'EOF'
{openssl_pkcs7_decode}
EOF
  cat > "$native_work/openssl_pkcs7_decode_build.sh" <<'EOF'
{openssl_pkcs7_build}
EOF
  python3 - "$TARGET/build.sh" "$native_work/openssl_pkcs7_decode_build.sh" <<'PY'
import sys
from pathlib import Path

build_sh = Path(sys.argv[1])
fragment = Path(sys.argv[2]).read_text(encoding="utf-8").rstrip() + "\\n"
text = build_sh.read_text(encoding="utf-8")
marker = "# FORMTRIG custom OpenSSL PKCS7 dataDecode fuzzer."
if marker not in text:
    build_sh.write_text(text.rstrip() + "\\n\\n" + fragment, encoding="utf-8")
PY
fi

export OUT="$OUT/afl"
export LDFLAGS="$LDFLAGS -L$OUT"

"$MAGMA/build.sh"
"$TARGET/build.sh"
"""


def write_runner_instrument_script(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(runner_instrument_script_text(), encoding="utf-8")
    path.chmod(0o755)


LINK_LIBRARY_PACKAGE_HINTS = {
    "c++": ["libc++-dev"],
    "c++abi": ["libc++abi-dev"],
    "jpeg": ["libjpeg-dev"],
    "lcms2": ["liblcms2-dev"],
    "lzma": ["liblzma-dev"],
    "tiff": ["libtiff-dev"],
}


def summarize_failure_log(log_path: Path, *, max_lines: int = 20) -> dict[str, Any]:
    if not log_path.exists():
        return {}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    missing_link_libraries = sorted(set(re.findall(r"cannot find -l([A-Za-z0-9_+.-]+)", text)))
    missing_files = sorted(
        set(
            match
            for match in re.findall(r"cannot find\s+(/[^:\s]+)", text)
            if not match.startswith("-l")
        )
    )
    interesting_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        lower = line.lower()
        if not line:
            continue
        if (
            "cannot find" in lower
            or "configure: error" in lower
            or "error:" in lower
            or "undefined reference" in lower
        ):
            if line not in interesting_lines:
                interesting_lines.append(line)
    packages: set[str] = set()
    for lib in missing_link_libraries:
        packages.update(LINK_LIBRARY_PACKAGE_HINTS.get(lib, []))
    for path in missing_files:
        match = re.search(r"/clang/([0-9]+)(?:\.|/)", path)
        if "libclang_rt." in path and match:
            packages.add(f"libclang-rt-{match.group(1)}-dev")
    summary: dict[str, Any] = {}
    if missing_link_libraries:
        summary["missing_link_libraries"] = missing_link_libraries
    if missing_files:
        summary["missing_files"] = missing_files
    if packages:
        summary["apt_package_hints"] = sorted(packages)
    if interesting_lines:
        summary["error_lines"] = interesting_lines[-max_lines:]
    tail_lines = [line.strip() for line in text.splitlines() if line.strip()][-max_lines:]
    if tail_lines:
        summary["tail_lines"] = tail_lines
    return summary


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    magma_root = args.magma_root.resolve()
    magma = magma_root / "magma"
    fuzzer = magma_root / "fuzzers" / args.fuzzer
    target = magma_root / "targets" / args.target
    out_dir = (args.out_dir or default_out_dir(args.target_id, args.target, args.program)).resolve()
    out = out_dir / "out"
    shared = out_dir / "shared"
    logs = out_dir / "logs"
    runner_instrument = out_dir / "runner_instrument_target.sh"
    site_map = out / "formtrig_native" / "formtrig_sites.tsv"
    target_cwd = out / "afl"
    executable = target_cwd / args.program
    args_template = args.args_template or parse_program_args(target / "configrc", args.program)
    target_cmd = f"{shlex.quote(str(executable))} {args_template}".strip()
    dependency_preflight = (
        {"status": "skipped", "target": args.target, "checks": [], "apt_package_hints": []}
        if args.skip_dependency_preflight
        else dependency_preflight_for_target(args.target)
    )
    host_compatibility_patches = host_compatibility_patches_for_target(args.target)

    common_env = {
        "FUZZER": str(fuzzer),
        "TARGET": str(target),
        "MAGMA": str(magma),
        "OUT": str(out),
        "SHARED": str(shared),
        "PROGRAM": args.program,
    }
    build_env = {
        **common_env,
        "LD": args.ld,
        "CFLAGS": " ".join(
            item
            for item in [
                f"-include {magma / 'src' / 'canary.h'}",
                "-DMAGMA_ENABLE_CANARIES",
                "-g",
                "-O0",
                args.extra_cflags,
            ]
            if item
        ),
        "CXXFLAGS": " ".join(
            item
            for item in [
                f"-include {magma / 'src' / 'canary.h'}",
                "-DMAGMA_ENABLE_CANARIES",
                "-g",
                "-O0",
                args.extra_cxxflags,
            ]
            if item
        ),
        "LIBS": " ".join(item for item in ["-l:magma.o", "-lrt", args.extra_libs] if item),
        "LDFLAGS": " ".join(item for item in ["-g", f"-L{out}", args.extra_ldflags] if item),
        "FORMTRIG_INSTRUMENT_LEVEL": args.instrument_level,
        "FORMTRIG_MAGMA_CXX_STDLIB": args.cxx_stdlib,
        "FORMTRIG_SOURCE_DIR": str((Path.cwd() / "formtrig").resolve()),
    }
    optional_env = {
        "FORMTRIG_CC_COMPILER": args.cc_compiler,
        "FORMTRIG_CXX_COMPILER": args.cxx_compiler,
        "FORMTRIG_AFL_CC": args.afl_cc,
        "FORMTRIG_AFL_CXX": args.afl_cxx,
        "FORMTRIG_PASS_CXX": args.pass_cxx,
        "FORMTRIG_LLVM_CONFIG": args.llvm_config,
        "FORMTRIG_RUNTIME_CC": args.runtime_cc,
    }
    build_env.update({key: value for key, value in optional_env.items() if value})
    if args.instrument_entry == "cli":
        build_env["FORMTRIG_MAGMA_LINK_AFL_DRIVER"] = "0"
    if args.formtrig_target_bug:
        build_env["FORMTRIG_TARGET_BUG"] = args.formtrig_target_bug

    fuzzer_repo = fuzzer / "repo"
    fuzzer_needs_fetch = args.force_fuzzer_fetch or not fuzzer_repo.exists()
    required_fuzzer_artifacts = [
        fuzzer_repo / "afl-clang-fast",
        fuzzer_repo / "afl-clang-fast++",
    ]
    if args.instrument_entry != "cli":
        required_fuzzer_artifacts.append(
            fuzzer_repo / "utils" / "aflpp_driver" / "libAFLDriver.a"
        )
    fuzzer_needs_build = args.force_fuzzer_build or not all(
        path.exists()
        for path in required_fuzzer_artifacts
    )
    target_repo = target / "repo"
    target_needs_fetch = args.force_target_fetch or not git_repo_has_head(target_repo)
    patches_needed = args.force_patches or target_needs_fetch or not repo_has_magma_log(target_repo)

    instrument_command = (
        ["bash", str(runner_instrument)]
        if args.instrument_entry in {"runner", "cli"}
        else ["bash", str(fuzzer / "instrument.sh")]
    )
    steps = [
        step(
            "fuzzer_fetch",
            ["bash", str(fuzzer / "fetch.sh")],
            env={"FUZZER": str(fuzzer)},
            selected=fuzzer_needs_fetch and not args.skip_fuzzer_fetch,
            reason="fuzzer repo missing or forced" if fuzzer_needs_fetch else "fuzzer repo already present",
        ),
        step(
            "fuzzer_build",
            ["bash", str(fuzzer / "build.sh")],
            env=common_env,
            selected=fuzzer_needs_build and not args.skip_fuzzer_build,
            reason="AFL++/driver artifacts missing or forced" if fuzzer_needs_build else "AFL++/driver artifacts already present",
        ),
        step(
            "target_preinstall",
            ["bash", str(target / "preinstall.sh")],
            env={"TARGET": str(target)},
            selected=args.run_preinstall,
            reason="explicit --run-preinstall requested",
        ),
        step(
            "target_fetch",
            target_fetch_command(target / "fetch.sh", target_repo),
            env={"TARGET": str(target)},
            selected=target_needs_fetch and not args.skip_target_fetch,
            reason="target repo missing or forced" if target_needs_fetch else "target repo already present",
        ),
        step(
            "apply_patches",
            ["bash", str(magma / "apply_patches.sh")],
            env={"TARGET": str(target)},
            selected=patches_needed and not args.skip_patches,
            reason="target repo lacks MAGMA_LOG markers or patches forced" if patches_needed else "target repo already has MAGMA_LOG markers",
        ),
        step(
            "instrument_target",
            instrument_command,
            env=build_env,
            selected=True,
            reason=f"build FORMTRIG-native target executable and site map via {args.instrument_entry}",
        ),
    ]

    refresh_commands: list[dict[str, Any]] = []
    if args.refresh_discovery:
        discovery_env: dict[str, str] = {}
        refresh_commands.append(
            step(
                "refresh_asset_discovery",
                [
                    sys.executable,
                    "tools/discover_magma_native_assets.py",
                    "--search-root",
                    str(out_dir),
                    "--search-root",
                    "artifacts/formtrig_native_readiness",
                    "--search-root",
                    "experiments/magma_workspace",
                ],
                env=discovery_env,
                selected=True,
                reason="explicit --refresh-discovery requested",
            )
        )
        refresh_commands.append(
            step(
                "refresh_validation_worklist",
                [
                    sys.executable,
                    "tools/plan_magma_binding_validation.py",
                    "--assets",
                    "artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json",
                ],
                env=discovery_env,
                selected=True,
                reason="explicit --refresh-discovery requested",
            )
        )

    return {
        "schema": "formtrig_magma_native_build_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "execute" if args.execute else "dry-run",
        "target_id": args.target_id,
        "target": args.target,
        "program": args.program,
        "inputs": {
            "magma_root": str(magma_root),
            "fuzzer": args.fuzzer,
            "instrument_level": args.instrument_level,
            "run_preinstall": args.run_preinstall,
            "skip_fuzzer_fetch": args.skip_fuzzer_fetch,
            "skip_fuzzer_build": args.skip_fuzzer_build,
            "skip_target_fetch": args.skip_target_fetch,
            "skip_patches": args.skip_patches,
            "refresh_discovery": args.refresh_discovery,
            "instrument_entry": args.instrument_entry,
            "cxx_stdlib": args.cxx_stdlib,
            "afl_cc": args.afl_cc,
            "afl_cxx": args.afl_cxx,
            "pass_cxx": args.pass_cxx,
            "llvm_config": args.llvm_config,
            "runtime_cc": args.runtime_cc,
            "skip_dependency_preflight": args.skip_dependency_preflight,
        },
        "paths": {
            "out_dir": str(out_dir),
            "out": str(out),
            "shared": str(shared),
            "logs": str(logs),
            "magma": str(magma),
            "fuzzer": str(fuzzer),
            "target": str(target),
            "site_map": str(site_map),
            "target_cwd": str(target_cwd),
            "executable": str(executable),
            "runner_instrument": str(runner_instrument),
        },
        "expected_validation_asset": {
            "target_id": args.target_id,
            "site_map": str(site_map),
            "target_cwd": str(target_cwd),
            "target_cmd": target_cmd,
            "program_args": args_template,
        },
        "dependency_preflight": dependency_preflight,
        "host_compatibility_patches": host_compatibility_patches,
        "steps": steps,
        "post_build_steps": refresh_commands,
    }


def run_step(row: dict[str, Any], *, cwd: Path, logs: Path) -> dict[str, Any]:
    if not row["selected"]:
        return {**row, "status": "skipped", "exit_code": None, "log": ""}
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"{row['name']}.log"
    env = os.environ.copy()
    env.update(row.get("env") or {})
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("$ " + row["shell"] + "\n")
        proc = subprocess.run(
            row["command"],
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    result = {
        **row,
        "status": "ok" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "log": str(log_path),
    }
    if proc.returncode != 0:
        summary = summarize_failure_log(log_path)
        if summary:
            result["failure_summary"] = summary
    return result


def execute_plan(plan: dict[str, Any], *, cwd: Path) -> dict[str, Any]:
    out = Path(plan["paths"]["out"])
    shared = Path(plan["paths"]["shared"])
    logs = Path(plan["paths"]["logs"])
    out.mkdir(parents=True, exist_ok=True)
    shared.mkdir(parents=True, exist_ok=True)
    executed_steps: list[dict[str, Any]] = []
    preflight = plan.get("dependency_preflight") or {}
    if preflight.get("status") == "missing":
        apt_hints = preflight.get("apt_package_hints") or []
        plan["executed_steps"] = [
            {
                "name": "dependency_preflight",
                "selected": True,
                "status": "failed",
                "exit_code": 2,
                "log": "",
                "failure_summary": {
                    "apt_package_hints": apt_hints,
                    "error_lines": [
                        "missing native build dependencies for "
                        f"{plan.get('target', '')}: {' '.join(apt_hints)}"
                    ],
                },
            }
        ]
        plan["failure_summary"] = {
            "failed_step": "dependency_preflight",
            "apt_package_hints": apt_hints,
            "error_lines": plan["executed_steps"][0]["failure_summary"]["error_lines"],
        }
        plan["status"] = "failed"
        return plan
    failed = False
    for row in plan["steps"]:
        result = run_step(row, cwd=cwd, logs=logs)
        executed_steps.append(result)
        if result["status"] == "failed":
            failed = True
            if result.get("failure_summary"):
                plan["failure_summary"] = {
                    "failed_step": result["name"],
                    **result["failure_summary"],
                }
            break
    if not failed:
        for row in plan["post_build_steps"]:
            result = run_step(row, cwd=cwd, logs=logs)
            executed_steps.append(result)
            if result["status"] == "failed":
                failed = True
                if result.get("failure_summary"):
                    plan["failure_summary"] = {
                        "failed_step": result["name"],
                        **result["failure_summary"],
                    }
                break
    plan["executed_steps"] = executed_steps
    plan["status"] = "failed" if failed else "executed"
    return plan


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    selected = [row for row in plan["steps"] + plan["post_build_steps"] if row["selected"]]
    lines = [
        "# Magma FORMTRIG Native Build Plan",
        "",
        "This is a build/readiness artifact, not endpoint performance evidence.",
        "A successful build should be followed by native asset discovery and a",
        "BindingSpec validation sweep before any long-run benefit claim.",
        "",
        f"Generated: `{plan['generated_at_utc']}`",
        f"Mode: `{plan['mode']}`",
        f"Target: `{plan['target_id'] or plan['target']}` / `{plan['program']}`",
        f"Instrumentation entry: `{plan['inputs']['instrument_entry']}`",
        f"Expected site map: `{plan['paths']['site_map']}`",
        f"Expected executable: `{plan['paths']['executable']}`",
        "",
        "## Dependency Preflight",
        "",
    ]
    preflight = plan.get("dependency_preflight") or {}
    lines.append(f"- `status`: `{preflight.get('status', 'unknown')}`")
    if preflight.get("checks"):
        for check in preflight["checks"]:
            line = f"- `{check['id']}`: `{check['status']}`"
            if check.get("value"):
                line += f" value=`{check['value']}`"
            if check.get("apt_package_hints") and check["status"] == "missing":
                line += " apt=`" + " ".join(check["apt_package_hints"]) + "`"
            lines.append(line)
    if preflight.get("apt_package_hints"):
        lines.append(
            "- install hint: `sudo apt-get install -y "
            + " ".join(preflight["apt_package_hints"])
            + "`"
        )
    patches = plan.get("host_compatibility_patches") or []
    if patches:
        lines.extend(["", "## Host Compatibility Patches", ""])
        for patch in patches:
            lines.append(f"- `{patch['id']}`: {patch['reason']}")
            if patch.get("files"):
                lines.append("  files: `" + "`, `".join(patch["files"]) + "`")
    lines.extend(
        [
            "",
            "## Selected Steps",
            "",
        ]
    )
    for row in selected:
        lines.append(f"- `{row['name']}`: `{row['shell']}`")
    if not selected:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Validation Asset",
            "",
            f"- `site_map`: `{plan['expected_validation_asset']['site_map']}`",
            f"- `target_cwd`: `{plan['expected_validation_asset']['target_cwd']}`",
            f"- `target_cmd`: `{plan['expected_validation_asset']['target_cmd']}`",
            "",
        ]
    )
    if plan.get("executed_steps"):
        lines.extend(["## Execution", ""])
        for row in plan["executed_steps"]:
            lines.append(
                f"- `{row['name']}`: `{row['status']}`"
                + (f" log=`{row['log']}`" if row.get("log") else "")
            )
        lines.append("")
    if plan.get("failure_summary"):
        summary = plan["failure_summary"]
        lines.extend(["## Failure Summary", ""])
        lines.append(f"- `failed_step`: `{summary.get('failed_step', '')}`")
        if summary.get("missing_link_libraries"):
            lines.append("- `missing_link_libraries`: `" + ", ".join(summary["missing_link_libraries"]) + "`")
        if summary.get("missing_files"):
            lines.append("- `missing_files`: `" + ", ".join(summary["missing_files"]) + "`")
        if summary.get("apt_package_hints"):
            lines.append("- `apt_package_hints`: `" + " ".join(summary["apt_package_hints"]) + "`")
        if summary.get("error_lines"):
            lines.append("- recent error lines:")
            for line in summary["error_lines"]:
                lines.append(f"  - `{line}`")
        elif summary.get("tail_lines"):
            lines.append("- recent log lines:")
            for line in summary["tail_lines"]:
                lines.append(f"  - `{line}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, help="Magma target directory name, e.g. poppler")
    parser.add_argument("--program", required=True, help="Magma program/fuzzer binary name")
    parser.add_argument("--target-id", default="", help="Optional TC id, e.g. PDF003")
    parser.add_argument("--magma-root", type=Path, default=DEFAULT_MAGMA_ROOT)
    parser.add_argument("--fuzzer", default="formtrig_native")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--args-template", default="", help="Override target args template; defaults to target configrc or @@")
    parser.add_argument("--instrument-level", default="balanced")
    parser.add_argument("--instrument-entry", choices=["runner", "fuzzer", "cli"], default="runner")
    parser.add_argument("--cxx-stdlib", choices=["libc++", "libstdc++", "none"], default="libc++")
    parser.add_argument("--cc-compiler", default="", help="Compiler/wrapper used by generated FORMTRIG CC")
    parser.add_argument("--cxx-compiler", default="", help="Compiler/wrapper used by generated FORMTRIG CXX")
    parser.add_argument("--afl-cc", default="", help="Set AFL_CC inside generated FORMTRIG wrappers")
    parser.add_argument("--afl-cxx", default="", help="Set AFL_CXX inside generated FORMTRIG wrappers")
    parser.add_argument("--pass-cxx", default="", help="C++ compiler used to build the FORMTRIG LLVM pass")
    parser.add_argument("--llvm-config", default="", help="llvm-config matching --pass-cxx and AFL backend clang")
    parser.add_argument("--runtime-cc", default="", help="C compiler used to build FORMTRIG runtime")
    parser.add_argument("--formtrig-target-bug", default="")
    parser.add_argument("--ld", default=shutil.which("ld") or "/usr/bin/ld")
    parser.add_argument("--extra-cflags", default="")
    parser.add_argument("--extra-cxxflags", default="")
    parser.add_argument("--extra-ldflags", default="")
    parser.add_argument("--extra-libs", default="")
    parser.add_argument("--run-preinstall", action="store_true")
    parser.add_argument("--skip-fuzzer-fetch", action="store_true")
    parser.add_argument("--skip-fuzzer-build", action="store_true")
    parser.add_argument("--skip-target-fetch", action="store_true")
    parser.add_argument("--skip-patches", action="store_true")
    parser.add_argument("--force-fuzzer-fetch", action="store_true")
    parser.add_argument("--force-fuzzer-build", action="store_true")
    parser.add_argument("--force-target-fetch", action="store_true")
    parser.add_argument("--force-patches", action="store_true")
    parser.add_argument(
        "--skip-dependency-preflight",
        action="store_true",
        help="Do not fail --execute early when known target build dependencies are missing.",
    )
    parser.add_argument("--refresh-discovery", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Run selected steps; default is dry-run planning")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args)
    out_dir = Path(plan["paths"]["out_dir"])
    out_json = args.out_json or (out_dir / "build_plan.json")
    out_md = args.out_md or (out_dir / "build_plan.md")
    if args.instrument_entry in {"runner", "cli"}:
        write_runner_instrument_script(Path(plan["paths"]["runner_instrument"]))
    if args.execute:
        plan = execute_plan(plan, cwd=Path.cwd())
    else:
        plan["status"] = "planned"
    write_json(out_json, plan)
    write_markdown(out_md, plan)
    print(json.dumps({"status": plan["status"], "out_json": str(out_json), "out_md": str(out_md)}, sort_keys=True))
    return 1 if plan["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
