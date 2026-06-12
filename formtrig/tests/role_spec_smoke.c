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

  setenv("FORMTRIG_LIFT_SPEC", "/tmp/formtrig_role_spec.txt", 1);
  formtrig_reset();
  formtrig_target_hit("site");
  __formtrig_log_branch(123, 1);
  formtrig_finalize();

  formtrig_shm_record_t *rec =
      (formtrig_shm_record_t *)(void *)(area + FORMTRIG_SHM_OFFSET);
  if (rec->magic != FORMTRIG_SHM_MAGIC ||
      rec->version != FORMTRIG_SHM_VERSION)
    return 3;
  if (rec->component_count < 1 || rec->atom_signal_count < 1) return 4;
  if (rec->components[0].role != FORMTRIG_ROLE_GUARD) return 5;
  if ((rec->atom_signals[0].role_bits &
       (1u << (FORMTRIG_ROLE_GUARD - 1u))) == 0)
    return 6;
  if ((rec->atom_signals[0].guard_bits & 2u) == 0) return 7;

  free(area);
  return 0;
}
