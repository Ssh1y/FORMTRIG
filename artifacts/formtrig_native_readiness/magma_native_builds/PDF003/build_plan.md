# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-17T12:16:49+00:00`
Mode: `execute`
Target: `PDF003` / `pdfimages`
Instrumentation entry: `runner`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl/pdfimages`

## Selected Steps

- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_AFL_CC=/usr/bin/clang-15 FORMTRIG_AFL_CXX=/usr/bin/clang++-15 FORMTRIG_INSTRUMENT_LEVEL=balanced FORMTRIG_LLVM_CONFIG=/usr/bin/llvm-config-15 FORMTRIG_MAGMA_CXX_STDLIB=libstdc++ FORMTRIG_PASS_CXX=/usr/bin/clang++-15 FORMTRIG_RUNTIME_CC=/usr/bin/clang-15 FORMTRIG_SOURCE_DIR=/home/cwh/FORMTRIG/formtrig FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out PROGRAM=pdfimages SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/poppler bash /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/runner_instrument_target.sh`
- `refresh_asset_discovery`: `/usr/bin/python3 tools/discover_magma_native_assets.py --search-root /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003 --search-root artifacts/formtrig_native_readiness --search-root experiments/magma_workspace`
- `refresh_validation_worklist`: `/usr/bin/python3 tools/plan_magma_binding_validation.py --assets artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl/pdfimages @@ /tmp/out`

## Execution

- `fuzzer_fetch`: `skipped`
- `fuzzer_build`: `skipped`
- `target_preinstall`: `skipped`
- `target_fetch`: `skipped`
- `apply_patches`: `skipped`
- `instrument_target`: `failed` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/logs/instrument_target.log`

## Failure Summary

- `failed_step`: `instrument_target`
- recent log lines:
  - `CMake Warning at CMakeLists.txt:256 (find_package):`
  - `By not providing "FindOpenJPEG.cmake" in CMAKE_MODULE_PATH this project has`
  - `asked CMake to find a package configuration file provided by "OpenJPEG",`
  - `but CMake did not find one.`
  - `Could not find a package configuration file provided by "OpenJPEG" with any`
  - `of the following names:`
  - `OpenJPEGConfig.cmake`
  - `openjpeg-config.cmake`
  - `Add the installation prefix of "OpenJPEG" to CMAKE_PREFIX_PATH or set`
  - `"OpenJPEG_DIR" to a directory containing one of the above files.  If`
  - `"OpenJPEG" provides a separate development package or SDK, be sure it has`
  - `been installed.`
  - `-- Could NOT find openjpeg2.`
  - `CMake Error at CMakeLists.txt:260 (message):`
  - `Install libopenjpeg2 before trying to build poppler.  You can also decide`
  - `to use the internal unmaintained JPX decoder or none at all.`
  - `Possible options are: -DENABLE_LIBOPENJPEG=openjpeg2,`
  - `-DENABLE_LIBOPENJPEG=none, -DENABLE_LIBOPENJPEG=unmaintained,`
  - `-- Configuring incomplete, errors occurred!`
  - `$ CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_AFL_CC=/usr/bin/clang-15 FORMTRIG_AFL_CXX=/usr/bin/clang++-15 FORMTRIG_INSTRUMENT_LEVEL=balanced FORMTRIG_LLVM_CONFIG=/usr/bin/llvm-config-15 FORMTRIG_MAGMA_CXX_STDLIB=libstdc++ FORMTRIG_PASS_CXX=/usr/bin/clang++-15 FORMTRIG_RUNTIME_CC=/usr/bin/clang-15 FORMTRIG_SOURCE_DIR=/home/cwh/FORMTRIG/formtrig FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out PROGRAM=pdfimages SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/poppler bash /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/runner_instrument_target.sh`
