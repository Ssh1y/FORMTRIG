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

  setenv("FORMTRIG_PUBLISH_EAGER", "1", 1);
  formtrig_reset();
  formtrig_target_hit("site");
  formtrig_record_direct_margin(1.0, "direct");
  __formtrig_log_arith(777u, 1u, 20u, 17u, 37u, 64u);
  formtrig_finalize();

  formtrig_shm_record_t *rec =
      (formtrig_shm_record_t *)(void *)(area + FORMTRIG_SHM_OFFSET);
  if (rec->magic != FORMTRIG_SHM_MAGIC ||
      rec->version != FORMTRIG_SHM_VERSION)
    return 3;
  int found = 0;
  for (uint32_t i = 0; i < rec->component_count; i++) {
    if (rec->components[i].atom_id == 1 &&
        rec->components[i].role == FORMTRIG_ROLE_ROOT_OBSERVE &&
        rec->components[i].kind == FORMTRIG_COMPONENT_BOUNDARY_MARGIN &&
        (rec->components[i].flags & FORMTRIG_COMPONENT_SPEC_LIFTED) &&
        rec->components[i].value == 5.0)
      found = 1;
  }
  if (!found) return 4;
  if (rec->d_f_spec_lifted != 5.0 || rec->d_f_lifted != 5.0 ||
      rec->d_f != 5.0)
    return 5;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 6;
  if ((rec->source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED) != 0) return 7;
  if (rec->hot_range_count == 0 || rec->hot_ranges[0].start != 2 ||
      rec->hot_ranges[0].len != 3 ||
      rec->hot_ranges[0].hint_kind != FORMTRIG_MUTATION_HINT_SET_BYTE ||
      rec->hot_ranges[0].hint_value != 65)
    return 8;

  free(area);
  return 0;
}
