# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-17T12:31:50+00:00`
Mode: `execute`
Target: `SSL011` / `asn1`
Instrumentation entry: `runner`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out/afl/asn1`

## Dependency Preflight

- `status`: `not_required`

## Selected Steps

- `target_fetch`: `TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl/fetch.sh`
- `apply_patches`: `TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/apply_patches.sh`
- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_AFL_CC=/usr/bin/clang-15 FORMTRIG_AFL_CXX=/usr/bin/clang++-15 FORMTRIG_INSTRUMENT_LEVEL=balanced FORMTRIG_LLVM_CONFIG=/usr/bin/llvm-config-15 FORMTRIG_MAGMA_CXX_STDLIB=libstdc++ FORMTRIG_PASS_CXX=/usr/bin/clang++-15 FORMTRIG_RUNTIME_CC=/usr/bin/clang-15 FORMTRIG_SOURCE_DIR=/home/cwh/FORMTRIG/formtrig FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out PROGRAM=asn1 SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/runner_instrument_target.sh`
- `refresh_asset_discovery`: `/usr/bin/python3 tools/discover_magma_native_assets.py --search-root /home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011 --search-root artifacts/formtrig_native_readiness --search-root experiments/magma_workspace`
- `refresh_validation_worklist`: `/usr/bin/python3 tools/plan_magma_binding_validation.py --assets artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/out/afl/asn1 @@`

## Execution

- `fuzzer_fetch`: `skipped`
- `fuzzer_build`: `skipped`
- `target_preinstall`: `skipped`
- `target_fetch`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/logs/target_fetch.log`
- `apply_patches`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/logs/apply_patches.log`
- `instrument_target`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/logs/instrument_target.log`
- `refresh_asset_discovery`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/logs/refresh_asset_discovery.log`
- `refresh_validation_worklist`: `ok` log=`/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL011/logs/refresh_validation_worklist.log`
