#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdlib.h>

#include "formtrig/formtrig_runtime.h"

unsigned char *__afl_area_ptr;

static int has_root_component(const formtrig_shm_record_t *rec) {
  for (uint32_t i = 0; i < rec->component_count; i++) {
    const formtrig_progress_component_t *component = &rec->components[i];
    if (component->atom_id == 1 &&
        component->role == FORMTRIG_ROLE_ROOT_OBSERVE &&
        (component->flags & FORMTRIG_COMPONENT_SPEC_LIFTED) &&
        component->value == 1.0)
      return 1;
  }
  return 0;
}

static int has_root_signal(const formtrig_shm_record_t *rec) {
  for (uint32_t i = 0; i < rec->atom_signal_count; i++) {
    const formtrig_atom_signal_t *signal = &rec->atom_signals[i];
    if (signal->atom_id == 1 &&
        (signal->role_bits & (1u << (FORMTRIG_ROLE_ROOT_OBSERVE - 1u))) &&
        (signal->flags & FORMTRIG_ATOM_SIGNAL_HAS_ROOT_VALUE))
      return 1;
  }
  return 0;
}

int main(void) {
  unsigned char *area =
      (unsigned char *)calloc(1, FORMTRIG_SHM_OFFSET + FORMTRIG_SHM_SIZE);
  if (!area) return 2;
  __afl_area_ptr = area;

  setenv("FORMTRIG_PUBLISH_EAGER", "1", 1);
  unsetenv("FORMTRIG_ALLOW_MANUAL_LIFT");
  unsetenv("FORMTRIG_ALLOW_HEURISTIC_LIFT");
  formtrig_reset();

  formtrig_crash_predicate(0, "canary_smoke");
  formtrig_finalize();

  formtrig_shm_record_t *rec =
      (formtrig_shm_record_t *)(void *)(area + FORMTRIG_SHM_OFFSET);
  if (rec->magic != FORMTRIG_SHM_MAGIC ||
      rec->version != FORMTRIG_SHM_VERSION)
    return 3;
  if ((rec->flags & FORMTRIG_FLAG_REACHED) == 0) return 4;
  if ((rec->flags & FORMTRIG_FLAG_CRASH_PREDICATE) != 0) return 5;
  if (rec->d_t != 1.0) return 6;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 7;
  if ((rec->source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED) != 0) return 8;
  if ((rec->source_flags & FORMTRIG_SOURCE_MANUAL_TARGET) != 0) return 9;
  if (!has_root_component(rec)) return 10;
  if (!has_root_signal(rec)) return 11;

  free(area);
  return 0;
}
