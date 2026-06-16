# Magma FORMTRIG Native Build Plan

This is a build/readiness artifact, not endpoint performance evidence.
A successful build should be followed by native asset discovery and a
BindingSpec validation sweep before any long-run benefit claim.

Generated: `2026-06-16T17:52:46+00:00`
Mode: `dry-run`
Target: `SSL015` / `asn1`
Expected site map: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/formtrig_native/formtrig_sites.tsv`
Expected executable: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/afl/asn1`

## Selected Steps

- `fuzzer_build`: `FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out PROGRAM=asn1 SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native/build.sh`
- `target_fetch`: `TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl/fetch.sh`
- `apply_patches`: `TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/apply_patches.sh`
- `instrument_target`: `CFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' CXXFLAGS='-include /home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma/src/canary.h -DMAGMA_ENABLE_CANARIES -g -O0' FORMTRIG_INSTRUMENT_LEVEL=balanced FUZZER=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native LD=/usr/bin/ld LDFLAGS='-g -L/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out' LIBS='-l:magma.o -lrt' MAGMA=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/magma OUT=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out PROGRAM=asn1 SHARED=/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/shared TARGET=/home/cwh/FORMTRIG/experiments/magma_workspace/magma/targets/openssl bash /home/cwh/FORMTRIG/experiments/magma_workspace/magma/fuzzers/formtrig_native/instrument.sh`

## Validation Asset

- `site_map`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/formtrig_native/formtrig_sites.tsv`
- `target_cwd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/afl`
- `target_cmd`: `/home/cwh/FORMTRIG/artifacts/formtrig_native_readiness/magma_native_builds/SSL015/out/afl/asn1 @@`
