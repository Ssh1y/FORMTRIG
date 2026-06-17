# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-17T12:27:24+00:00`
Mode: `execute`
Target: `PDF003` / `pdfimages`
Instrumentation entry: `runner`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl/pdfimages`

## Dependency Preflight

- `status`: `missing`
- `poppler_cairo_pkg_config`: `missing` apt=`libcairo2-dev`
- `poppler_openjpeg_cmake_config`: `missing` apt=`libopenjp2-7-dev`
- install hint: `sudo apt-get install -y libcairo2-dev libopenjp2-7-dev`

## Selected Steps

- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_AFL_CC=/usr/bin/clang-15 FORMTRIG_AFL_CXX=/usr/bin/clang++-15 FORMTRIG_INSTRUMENT_LEVEL=balanced FORMTRIG_LLVM_CONFIG=/usr/bin/llvm-config-15 FORMTRIG_MAGMA_CXX_STDLIB=libstdc++ FORMTRIG_PASS_CXX=/usr/bin/clang++-15 FORMTRIG_RUNTIME_CC=/usr/bin/clang-15 FORMTRIG_SOURCE_DIR=/home/cwh/FORMTRIG/formtrig FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out PROGRAM=pdfimages SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/poppler bash /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/runner_instrument_target.sh`
- `refresh_asset_discovery`: `/usr/bin/python3 tools/discover_magma_native_assets.py --search-root /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003 --search-root artifacts/formtrig_native_readiness --search-root experiments/magma_workspace`
- `refresh_validation_worklist`: `/usr/bin/python3 tools/plan_magma_binding_validation.py --assets artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/PDF003/out/afl/pdfimages @@ /tmp/out`

## Execution

- `dependency_preflight`: `failed`

## Failure Summary

- `failed_step`: `dependency_preflight`
- `apt_package_hints`: `libcairo2-dev libopenjp2-7-dev`
- recent error lines:
  - `missing native build dependencies for poppler: libcairo2-dev libopenjp2-7-dev`
