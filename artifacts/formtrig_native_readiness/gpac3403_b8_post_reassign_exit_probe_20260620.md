# GPAC_3403 B8 Post-Reassign Exit Probe

## What Changed

- Added `GPAC_3403.native_b8_post_reassign_exit_candidate.yml`.
- B8 keeps the B7 lifecycle/alias roles and adds post-reassign guards at:
  - `avc_ext.c:809` HEVC extractor error branch.
  - `avc_ext.c:844` `nal_size < 2` branch.
- Added `tools/analyze_gpac3403_post_reassign_path.py` to separate:
  - release -> reassign object equality,
  - pre-detach guard observed vs guard satisfied,
  - reassign -> cleanup object equality.
- Added op56-59 malformed extractor typed mutations.

## Static Gate

| item | value |
|---|---:|
| binding tier | B4 |
| lift allowed | true |
| exact runtime events | 14 |
| location-only events | 0 |
| role collapse | 0 |

## Probe Results

| window | reached/spec | _T | D_F values | endpoint crashes | HEVC/L-HEVC import | guard observed | guard satisfied | release=reassign | reassign=cleanup |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|
| op52-55 guard B8 | 9/9 | 0 | `[3.0]` | 0 | 16/16 | 1 | 0 | 9 | 0 |
| op56-59 malformed extractor | 9/9 | 0 | `[3.0]` | 0 | 16/16 | 0 | 0 | 9 | 0 |

## Interpretation

This is useful negative evidence. FORMTRIG is not stuck at parser entry: both probes keep HEVC and L-HEVC import alive, and reached records still prove `gf_isom_sample_del` release equals the buffer passed into `gf_bs_reassign_buffer`.

The missing piece is now narrower: no candidate satisfies the post-reassign pre-detach error path. op52-55 reaches the guard sites once, but both guard outcomes are false. op56-59 keeps import alive but does not preserve malformed extractor payloads into `process_extractor`.

Important claim boundary: the B8 `avc_ext.c:912` absent binding is only a weak proxy. It must not be claimed as proof that `gf_bs_get_content_no_truncate` was skipped, because the final get-content call happens before that branch.

## Next Action

Add a stronger detach/no-detach observable or a typed mutation family that preserves malformed extractor references into `gf_isom_nalu_sample_rewrite` after sample-buffer reassign. Candidates should not be treated as closer to `_T` until guard outcome becomes 1 or cleanup frees the same reassign-owned object.
