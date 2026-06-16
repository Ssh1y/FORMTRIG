# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-16T18:23:23+00:00`
Mode: `execute`
Target: `TIF012` / `tiff_read_rgba_fuzzer`
Instrumentation entry: `runner`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer`

## Selected Steps

- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_AFL_CC=/usr/bin/clang-15 FORMTRIG_AFL_CXX=/usr/bin/clang++-15 FORMTRIG_INSTRUMENT_LEVEL=balanced FORMTRIG_LLVM_CONFIG=/usr/bin/llvm-config-15 FORMTRIG_MAGMA_CXX_STDLIB=libstdc++ FORMTRIG_PASS_CXX=/usr/bin/clang++-15 FORMTRIG_RUNTIME_CC=/usr/bin/clang-15 FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out PROGRAM=tiff_read_rgba_fuzzer SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/libtiff bash /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/runner_instrument_target.sh`
- `refresh_asset_discovery`: `/usr/bin/python3 tools/discover_magma_native_assets.py --search-root /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012 --search-root artifacts/formtrig_native_readiness --search-root experiments/magma_workspace`
- `refresh_validation_worklist`: `/usr/bin/python3 tools/plan_magma_binding_validation.py --assets artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer @@`

## Execution

- `fuzzer_fetch`: `skipped`
- `fuzzer_build`: `skipped`
- `target_preinstall`: `skipped`
- `target_fetch`: `skipped`
- `apply_patches`: `skipped`
- `instrument_target`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/logs/instrument_target.log`
- `refresh_asset_discovery`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/logs/refresh_asset_discovery.log`
- `refresh_validation_worklist`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/logs/refresh_validation_worklist.log`
