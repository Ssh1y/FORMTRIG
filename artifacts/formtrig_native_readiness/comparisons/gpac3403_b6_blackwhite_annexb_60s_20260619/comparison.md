# GPAC_3403 B6 Blackwhite Annex-B 60s Gate

Generated UTC: 2026-06-19T08:12:00Z

## Verdict

B6 fixes the B5 campaign plateau at the guidance level. The run does not reach terminal `_T`, but it does reach the missing `same_object` role online and lowers `D_F_spec_lifted` from the seed/calibration value 2 to candidate value 1.

## FORMTRIG Metrics

| metric | value |
|---|---:|
| duration | 60s |
| execs_done | 426 |
| corpus_count | 38 |
| terminal `_T` | 0 |
| queued progress | 1 |
| accepted non-trigger progress | 1 |
| typed execs/finds | 161/0 |
| `D_F_spec_lifted` min/max | 1/2 |
| candidate `D_F_spec_lifted` values | [2, 1] |
| same_object samples | 10 |
| same_object candidate samples | 10 |

## Seed And Hook

Seed: public Chromium `blackwhite_yuv444p-frame.hevc`, sha256 `a120df5b64e812e5b07c672bcb0ba2b712a346fd8d3997ab0d8e838dedc02d25`. This is a generic HEVC parser sample and is not GPAC_3403 PoC-derived.

Hook: `/home/cwh/FORMTRIG/scripts/formtrig_hooks/hevc_annexb_structure_hook.py` sha256 `8f22730aa4de7e2fcfbcf8df2a343ec84b5dae32a28fed738e1a40075cdcbeef`.

## Interpretation

This is not endpoint evidence. It is a repair gate showing that FORMTRIG can now guide the GPAC_3403 R2T last mile from `D_F=2` to `D_F=1` by sampling the previously missing `same_object` relation. The next required step is a matched 10m/2h B6 comparison and ablations.
