# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-17T15:27:39+00:00`
Mode: `execute`
Target: `PHP009` / `exif`
Instrumentation entry: `runner`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/afl/exif`

## Dependency Preflight

- `status`: `ok`
- `php_bison`: `ok` value=`bison`
- `php_re2c`: `ok` value=`re2c`
- `php_icu_pkg_config`: `ok` value=`icu-uc`

## Host Compatibility Patches

- `php_icu_breakiterator_operator_bool`: Old PHP ext/intl declares BreakIterator::operator== with UBool, but modern ICU headers use bool.
  files: `ext/intl/breakiterator/codepointiterator_internal.h`, `ext/intl/breakiterator/codepointiterator_internal.cpp`

## Selected Steps

- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_AFL_CC=/usr/bin/clang-15 FORMTRIG_AFL_CXX=/usr/bin/clang++-15 FORMTRIG_INSTRUMENT_LEVEL=balanced FORMTRIG_LLVM_CONFIG=/usr/bin/llvm-config-15 FORMTRIG_MAGMA_CXX_STDLIB=libstdc++ FORMTRIG_PASS_CXX=/usr/bin/clang++-15 FORMTRIG_RUNTIME_CC=/usr/bin/clang-15 FORMTRIG_SOURCE_DIR=/home/cwh/FORMTRIG/formtrig FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out PROGRAM=exif SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/php bash /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/runner_instrument_target.sh`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/afl/exif @@`

## Execution

- `fuzzer_fetch`: `skipped`
- `fuzzer_build`: `skipped`
- `target_preinstall`: `skipped`
- `target_fetch`: `skipped`
- `apply_patches`: `skipped`
- `instrument_target`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PHP009/logs/instrument_target.log`
