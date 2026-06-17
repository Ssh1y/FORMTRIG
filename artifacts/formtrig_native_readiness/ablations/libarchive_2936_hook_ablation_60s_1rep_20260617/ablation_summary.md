# libarchive_2936_hook_ablation_60s_1rep_20260617

- target: `LIBARCHIVE_2936`
- verdict: `target_specific_hook_accelerates_ablation_controls`
- primary hook label: `hooked`

## Attribution Readout

- target-specific hook is 21.45x faster than no-hook by first `_T`
- target-specific hook is 46.14x faster than generic-hook by first `_T`

Blocked or limited claims:
- ablation evidence is a smoke result until replicated
- controls also trigger, so this target remains weak SOTA-gap evidence

## Arms

| label | hook source | terminal | first _T | execs | strict pre-trigger | typed finds |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| hooked | binding_spec | 4 | 1.196 | 32 | true | 0 |
| nohook | disabled_ablation | 7 | 25.652 | 18532 | true | 8 |
| generic | cli_override | 1 | 55.178 | 44842 | true | 19 |

## Reasons

- `primary_hook_terminal_success`
- `nohook_control_also_triggers`
- `generic_hook_control_also_triggers`
- `low_replication`
- `primary_hook_faster_than_nohook_and_generic`
