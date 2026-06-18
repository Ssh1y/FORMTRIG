# gpac3403_mp4_hook_ablation_60s_20260618

- target: `GPAC_3403`
- verdict: `mp4_hook_improves_typed_mutation_yield_without_endpoint_claim`
- budget: `60s`

## Attribution Readout

- MP4 hook increases typed finds from `8` to `14`.
- MP4 hook increases final corpus count from `180` to `207`.
- Both arms keep strict pre-trigger lifted guidance: `D_F` candidate values are `2, 3, 4`.
- Neither arm reaches `_T`, so this is mechanism evidence only.

Blocked or limited claims:
- one 60s repetition is not final evidence;
- no endpoint/TTE claim is established;
- the no-hook arm disables the external MP4 hook, but FORMTRIG's internal typed range stage still runs;
- matched AFL++/CmpLog/Redqueen baselines are still required.

## Arms

| label | hook source | terminal | execs | corpus | strict pre-trigger | accepted non-trigger | typed finds |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| mp4_hook | binding_spec | 0 | 7257 | 207 | true | 2 | 14 |
| no_external_hook | disabled_ablation | 0 | 7544 | 180 | true | 2 | 8 |
