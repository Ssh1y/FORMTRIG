#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdlib.h>

#include "formtrig/formtrig_runtime.h"

unsigned char *__afl_area_ptr;

static formtrig_shm_record_t *current_record(unsigned char *area) {
  return (formtrig_shm_record_t *)(void *)(area + FORMTRIG_SHM_OFFSET);
}

static int record_header_ok(const formtrig_shm_record_t *rec) {
  return rec->magic == FORMTRIG_SHM_MAGIC &&
         rec->version == FORMTRIG_SHM_VERSION;
}

static int has_role_value(const formtrig_shm_record_t *rec, uint32_t role,
                          double value) {
  for (uint32_t i = 0; i < rec->component_count; i++) {
    const formtrig_progress_component_t *component = &rec->components[i];
    if (component->atom_id == 1 && component->role == role &&
        (component->flags & FORMTRIG_COMPONENT_SPEC_LIFTED) &&
        component->value == value)
      return 1;
  }
  return 0;
}

static int atom_has_opposite_producer_satisfied(
    const formtrig_shm_record_t *rec) {
  for (uint32_t i = 0; i < rec->atom_signal_count; i++) {
    const formtrig_atom_signal_t *signal = &rec->atom_signals[i];
    if (signal->atom_id == 1)
      return (signal->producer_bits & 4u) != 0;
  }
  return 0;
}

int main(void) {
  unsigned char *area =
      (unsigned char *)calloc(1, FORMTRIG_SHM_OFFSET + FORMTRIG_SHM_SIZE);
  if (!area) return 2;
  __afl_area_ptr = area;

  formtrig_reset();
  __formtrig_log_branch(111u, 0u);
  formtrig_finalize();

  formtrig_shm_record_t *rec = current_record(area);
  if (!record_header_ok(rec)) return 3;
  if (rec->flags != 0) return 4;
  if (rec->component_count != 0) return 5;

  formtrig_reset();
  __formtrig_log_branch(111u, 1u);
  formtrig_finalize();

  rec = current_record(area);
  if (!record_header_ok(rec)) return 6;
  if ((rec->flags & FORMTRIG_FLAG_REACHED) != 0) return 7;
  if ((rec->flags & FORMTRIG_FLAG_SPEC_LIFTED) == 0) return 8;
  if (!has_role_value(rec, FORMTRIG_ROLE_GUARD, 1.0)) return 9;
  if (!has_role_value(rec, FORMTRIG_ROLE_OPPOSITE_PRODUCER, 1.0)) return 10;
  if (!atom_has_opposite_producer_satisfied(rec)) return 11;
  if (rec->d_f_spec_lifted != 1.0) return 12;

  formtrig_reset();
  __formtrig_log_branch(111u, 1u);
  __formtrig_log_branch(222u, 1u);
  formtrig_finalize();

  rec = current_record(area);
  if (!record_header_ok(rec)) return 13;
  if ((rec->flags & FORMTRIG_FLAG_REACHED) != 0) return 14;
  if ((rec->flags & FORMTRIG_FLAG_SPEC_LIFTED) == 0) return 15;
  if (!has_role_value(rec, FORMTRIG_ROLE_GUARD, 1.0)) return 16;
  if (!has_role_value(rec, FORMTRIG_ROLE_OPPOSITE_PRODUCER, 0.0)) return 17;
  if (atom_has_opposite_producer_satisfied(rec)) return 18;
  if (rec->d_f_spec_lifted != 2.0) return 19;

  free(area);
  return 0;
}
