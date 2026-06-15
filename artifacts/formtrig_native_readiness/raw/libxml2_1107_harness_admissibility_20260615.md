# Harness Admissibility Audit: LIBXML2_1107

- Status: `inadmissible_core_evidence`
- Core evidence allowed: `false`
- Summary: Not admissible as core FORMTRIG R2T evidence because the harness exposes an artificial trigger-control knob.

## Flags

- `critical` `direct_input_allocation_failure_switch`: Harness exposes allocation failure as an input byte switch
  The harness appears to map input byte 0 to a malloc-failure index, then returns NULL when the allocation counter matches that value. This collapses the real R2T search into a small artificial knob.
  - line 10: `static unsigned char g_fail_malloc_at = 0;`
  - line 11: `static unsigned int g_malloc_count = 0;`
  - line 14: `  g_malloc_count++;`
  - line 15: `  if (g_fail_malloc_at != 0 && g_malloc_count == g_fail_malloc_at)`
  - line 16: `    return NULL;`
  - line 39: `    return NULL;`
  - line 42: `    return NULL;`
  - line 47: `    return NULL;`
  - line 53: `    return NULL;`
  - line 74: `  g_fail_malloc_at = buf[0];`
- `high` `binding_depends_on_harness_semantics`: BindingSpec uses harness-level semantics
  At least one binding role is grounded in the replay harness rather than the vulnerable library's natural parser state. This may still be useful for smoke tests, but it is not admissible as core evidence that FORMTRIG solves natural binary-trigger guidance.
  - line 36: `    expr: 'the harness-selected malloc failure index is closest to the xmlStrdup allocation for ret->string'`
  - line 39: `      function: 'hook_malloc'`
  - line 40: `      file: 'benchmarks/cve_harnesses/libxml2_regexp_strdup_fail_replay.c'`
  - line 70: `    expr: 'harness allocation-failure guard checks whether the input-selected fail count is enabled'`
  - line 73: `      function: 'hook_malloc'`
  - line 74: `      file: 'benchmarks/cve_harnesses/libxml2_regexp_strdup_fail_replay.c'`
  - line 90: `      function: 'hook_malloc'`
  - line 91: `      file: 'benchmarks/cve_harnesses/libxml2_regexp_strdup_fail_replay.c'`
- `high` `one_byte_terminal_mutation_hint`: BindingSpec contains a one-byte set-byte mutation hint
  A one-byte mutation hint can be valid as a typed mutator hint, but combined with a harness allocation-failure switch it effectively names the terminal knob.
  - line 101: `    range_start: 0`
  - line 102: `    range_len: 1`
  - line 103: `    mutation_hint: 'set_byte'`
  - line 104: `    mutation_value: 2`
- `medium` `tiny_seed_space`: Seed corpus contains only tiny inputs
  Tiny RNT seeds are not invalid by themselves, but they are a warning sign when the trigger is also exposed through a direct one-byte harness control.
  - seed path `artifacts/rnt_corpus/LIBXML2_1107/seeds`, max_size=2

## Recommendations

- Do not count this target as core evidence for solving natural R2T guidance.
- Keep it only as a native pipeline, BindingSpec, or crash-accounting sanity case.
- Replace it with targets where the input naturally drives parser state, length, magic, structure, or lifecycle constraints.
