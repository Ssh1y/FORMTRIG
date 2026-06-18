#!/usr/bin/env bash
set -euo pipefail

cat > "$MAGMA/src/canary.h" <<'EOF'
#ifndef CANARY_H_
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
EOF

native_work="$OUT/formtrig_native"
mkdir -p "$OUT/afl" "$native_work"
rm -f "$native_work/formtrig_sites.tsv"

if [ -n "${FORMTRIG_SOURCE_DIR:-}" ]; then
  if [ ! -d "$FORMTRIG_SOURCE_DIR/include/formtrig" ] ||      [ ! -f "$FORMTRIG_SOURCE_DIR/runtime/formtrig_runtime.c" ] ||      [ ! -f "$FORMTRIG_SOURCE_DIR/llvm/formtrig_pass.cpp" ]; then
    echo "FORMTRIG_SOURCE_DIR does not look like a FORMTRIG runtime tree: $FORMTRIG_SOURCE_DIR" >&2
    exit 2
  fi
  source_formtrig="$(cd "$FORMTRIG_SOURCE_DIR" && pwd -P)"
  for target_formtrig in "$FUZZER/formtrig" "$MAGMA/formtrig"; do
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
  done
  if [ ! -f "$FUZZER/formtrig/tools/prepare_native_build.py" ]; then
    echo "FORMTRIG fuzzer overlay is missing tools/prepare_native_build.py: $FUZZER/formtrig" >&2
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
for ((idx = 0; idx < ${#args[@]}; idx++)); do
  case "${args[$idx]}" in
    -O)
      if (( idx + 1 < ${#args[@]} )); then
        out="${args[$((idx + 1))]}"
      fi
      ;;
    -O*)
      out="${args[$idx]#-O}"
      ;;
  esac
done
last_index=$((${#args[@]} - 1))
url="${args[$last_index]}"
for file in config.guess config.sub; do
  if [[ "$url" == *"/$file" ]]; then
    src="${FORMTRIG_LOCAL_CONFIG_AUX}/$file"
    if [ -n "$out" ]; then
      cp "$src" "$out"
    else
      cat "$src"
    fi
    exit 0
  fi
done
if [ -n "${FORMTRIG_REAL_WGET:-}" ]; then
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
  --cc-compiler "${FORMTRIG_CC_COMPILER:-$FUZZER/repo/afl-clang-fast}"
  --cxx-compiler "${FORMTRIG_CXX_COMPILER:-$FUZZER/repo/afl-clang-fast++}"
  --runtime-cc "${FORMTRIG_RUNTIME_CC:-clang}"
  --instrument-level "${FORMTRIG_INSTRUMENT_LEVEL:-balanced}"
  --runtime-link-mode never
  --skip-pass-regex '(^|/)(magma/magma/src|magma/src)/'
  --skip-pass-regex '(^|/)(magma/magma/formtrig/runtime|magma/formtrig/runtime)/'
  --skip-pass-regex '(^|/)CMakeFiles/(CMakeScratch|CMakeTmp)/'
  --skip-pass-regex '(^|/)conftest\.(c|cc|cpp|cxx)$'
  --skip-pass-regex '(^|/)freetype2/src/tools/'
  --env AFL_QUIET=1
  --force
)
if [ -n "${FORMTRIG_AFL_CC:-}" ]; then
  prepare_args+=(--afl-cc "$FORMTRIG_AFL_CC")
fi
if [ -n "${FORMTRIG_AFL_CXX:-}" ]; then
  prepare_args+=(--afl-cxx "$FORMTRIG_AFL_CXX")
fi
if [ -n "${FORMTRIG_PASS_CXX:-}" ]; then
  prepare_args+=(--pass-cxx "$FORMTRIG_PASS_CXX")
fi
if [ -n "${FORMTRIG_LLVM_CONFIG:-}" ]; then
  prepare_args+=(--llvm-config "$FORMTRIG_LLVM_CONFIG")
fi

"${prepare_args[@]}"

# shellcheck disable=SC1090
source "$native_work/formtrig_build_env.sh"

driver="$FUZZER/repo/utils/aflpp_driver/libAFLDriver.a"
driver_lib=""
if [ "${FORMTRIG_MAGMA_LINK_AFL_DRIVER:-1}" != "0" ]; then
  driver_lib=" $driver"
fi
case "${FORMTRIG_MAGMA_CXX_STDLIB:-libc++}" in
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
  export AFLGO_CONFIGURE_NATIVE="${AFLGO_CONFIGURE_NATIVE:-1}"
  export AFLGO_CONFIGURE_CC="${AFLGO_CONFIGURE_CC:-${FORMTRIG_AFL_CC:-clang}}"
  export AFLGO_CONFIGURE_CXX="${AFLGO_CONFIGURE_CXX:-${FORMTRIG_AFL_CXX:-clang++}}"
  export AFLGO_CONFIGURE_CFLAGS="${AFLGO_CONFIGURE_CFLAGS:-}"
  export AFLGO_CONFIGURE_CXXFLAGS="${AFLGO_CONFIGURE_CXXFLAGS:-}"
  export AFLGO_CONFIGURE_LDFLAGS="${AFLGO_CONFIGURE_LDFLAGS:-}"
  export AFLGO_CONFIGURE_LIBS="${AFLGO_CONFIGURE_LIBS:-}"
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
            r"virtual\s+(UBool|bool)\s+operator==\s*"
            r"\(\s*const\s+BreakIterator\s*&[^)]*\)\s*const",
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
for rel, candidates, desired in replacements:
    path = repo / rel
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    updated = text
    for old in candidates:
        updated = updated.replace(old, desired)
    if desired not in updated:
        raise SystemExit("expected ICU operator signature not found: {}".format(path))
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        changed.append(rel)
if changed:
    print(
        "FORMTRIG host-compat: synchronized PHP ICU {} operator== in {}".format(
            expected, ", ".join(changed)
        )
    )
PY
fi

if [ "$(basename "$TARGET")" = "php" ] && [ "${PROGRAM:-}" = "exif_thumbnail" ]; then
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
call_needle = '	fuzzer_call_php_func_zval("exif_read_data", 1, &stream_zv);\n'
call_replacement = '''	zval args[3];

	args[0] = stream_zv;
	ZVAL_NULL(&args[1]);
	ZVAL_NULL(&args[2]);

	fuzzer_call_php_func_zval("exif_thumbnail", 3, args);
'''
if call_needle not in source:
    raise SystemExit("stock PHP fuzzer-exif.c call site was not found")
thumb.write_text(source.replace(call_needle, call_replacement, 1), encoding="utf-8")

config_text = config.read_text(encoding="utf-8")
target_line = "PHP_FUZZER_TARGET([exif_thumbnail], PHP_FUZZER_EXIF_THUMBNAIL_OBJS)"
if target_line not in config_text:
    needle = "    PHP_FUZZER_TARGET([exif], PHP_FUZZER_EXIF_OBJS)\n"
    if needle not in config_text:
        raise SystemExit("PHP fuzzer config exif target was not found")
    config.write_text(
        config_text.replace(needle, needle + "    " + target_line + "\n", 1),
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
    if needle not in makefile_text:
        raise SystemExit("PHP fuzzer Makefile exif rule was not found")
    makefile.write_text(makefile_text.replace(needle, replacement, 1), encoding="utf-8")
PY
fi

if [ "$(basename "$TARGET")" = "poppler" ]; then
  if [ -z "${FORMTRIG_OPENJPEG_DIR:-}" ]; then
    for cfg in /usr/lib/*/openjpeg-*/OpenJPEGConfig.cmake                /usr/lib/*/openjpeg-*/openjpeg-config.cmake                /usr/local/lib/*/openjpeg-*/OpenJPEGConfig.cmake                /usr/local/lib/openjpeg-*/OpenJPEGConfig.cmake                /usr/share/openjpeg-*/OpenJPEGConfig.cmake; do
      if [ -f "$cfg" ]; then
        export FORMTRIG_OPENJPEG_DIR="$(dirname "$cfg")"
        break
      fi
    done
  fi
  if [ -n "${FORMTRIG_OPENJPEG_DIR:-}" ]; then
    python3 - "$TARGET/build.sh" "$FORMTRIG_OPENJPEG_DIR" <<'PY'
import re
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
PY
  fi
fi

if [ "$(basename "$TARGET")" = "openssl" ] && [ "${PROGRAM:-}" = "pkcs7_decode" ]; then
  mkdir -p "$TARGET/src"
  cat > "$TARGET/src/pkcs7_decode.c" <<'EOF'
/*
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
EOF
  cat > "$native_work/openssl_pkcs7_decode_build.sh" <<'EOF'

# FORMTRIG custom OpenSSL PKCS7 dataDecode fuzzer.
if [ -f "$TARGET/src/pkcs7_decode.c" ]; then
    "$CC" $CFLAGS -I. -Iinclude -Ifuzz -DOPENSSL_NO_FUZZ_LIBFUZZER \
        "$TARGET/src/pkcs7_decode.c" fuzz/driver.c \
        -o "$OUT/pkcs7_decode" \
        $LDFLAGS libcrypto.a $LIBS -ldl -pthread
fi
EOF
  python3 - "$TARGET/build.sh" "$native_work/openssl_pkcs7_decode_build.sh" <<'PY'
import sys
from pathlib import Path

build_sh = Path(sys.argv[1])
fragment = Path(sys.argv[2]).read_text(encoding="utf-8").rstrip() + "\n"
text = build_sh.read_text(encoding="utf-8")
marker = "# FORMTRIG custom OpenSSL PKCS7 dataDecode fuzzer."
if marker not in text:
    build_sh.write_text(text.rstrip() + "\n\n" + fragment, encoding="utf-8")
PY
fi

export OUT="$OUT/afl"
export LDFLAGS="$LDFLAGS -L$OUT"

"$MAGMA/build.sh"
"$TARGET/build.sh"
