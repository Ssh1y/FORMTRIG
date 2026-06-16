# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-16T17:52:46+00:00`
Mode: `dry-run`
Target: `TIF012` / `tiff_read_rgba_fuzzer`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer`

## Selected Steps

- `fuzzer_build`: `FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out PROGRAM=tiff_read_rgba_fuzzer SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/libtiff bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native/build.sh`
- `target_fetch`: `TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/libtiff bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/libtiff/fetch.sh`
- `apply_patches`: `TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/libtiff bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/apply_patches.sh`
- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_INSTRUMENT_LEVEL=balanced FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out PROGRAM=tiff_read_rgba_fuzzer SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/libtiff bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native/instrument.sh`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/TIF012/out/afl/tiff_read_rgba_fuzzer @@`
