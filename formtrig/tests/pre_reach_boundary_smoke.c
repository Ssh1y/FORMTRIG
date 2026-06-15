#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdlib.h>

#include "formtrig/formtrig_runtime.h"

unsigned char *__afl_area_ptr;

int main(void) {
  unsigned char *area =
      (unsigned char *)calloc(1, FORMTRIG_SHM_OFFSET + FORMTRIG_SHM_SIZE);
  if (!area) return 2;
  __afl_area_ptr = area;

  formtrig_reset();
  __formtrig_log_arith(888u, 1u, 5u, 6u, 11u, 64u);
  formtrig_finalize();

  formtrig_shm_record_t *rec =
      (formtrig_shm_record_t *)(void *)(area + FORMTRIG_SHM_OFFSET);
  if (rec->magic != FORMTRIG_SHM_MAGIC ||
      rec->version != FORMTRIG_SHM_VERSION)
    return 3;
  if ((rec->flags & FORMTRIG_FLAG_REACHED) == 0) return 4;
  if (rec->target_hit_count != 1) return 5;
  if (rec->d_f_spec_lifted != 9.0) return 6;

  int found = 0;
  for (uint32_t i = 0; i < rec->component_count; i++) {
    if (rec->components[i].atom_id == 1 &&
        rec->components[i].role == FORMTRIG_ROLE_ROOT_OBSERVE &&
        rec->components[i].kind == FORMTRIG_COMPONENT_BOUNDARY_MARGIN &&
        (rec->components[i].flags & FORMTRIG_COMPONENT_SPEC_LIFTED) &&
        rec->components[i].value == 9.0)
      found = 1;
  }
  if (!found) return 7;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 8;

  free(area);
  return 0;
}
