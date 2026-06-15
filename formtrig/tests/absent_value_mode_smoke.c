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

static int has_opposite_component_value(const formtrig_shm_record_t *rec,
                                        double value) {
  for (uint32_t i = 0; i < rec->component_count; i++) {
    const formtrig_progress_component_t *component = &rec->components[i];
    if (component->atom_id == 1 &&
        component->role == FORMTRIG_ROLE_OPPOSITE_PRODUCER &&
        component->kind == FORMTRIG_COMPONENT_PRODUCER_USE &&
        (component->flags & FORMTRIG_COMPONENT_SPEC_LIFTED) &&
        component->value == value)
      return 1;
  }
  return 0;
}

static int has_use_component(const formtrig_shm_record_t *rec) {
  for (uint32_t i = 0; i < rec->component_count; i++) {
    const formtrig_progress_component_t *component = &rec->components[i];
    if (component->atom_id == 1 && component->role == FORMTRIG_ROLE_USE &&
        component->source_id == 111u)
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
  formtrig_target_hit("site");
  __formtrig_log_branch(123u, 1u);
  formtrig_finalize();

  formtrig_shm_record_t *rec = current_record(area);
  if (!record_header_ok(rec)) return 3;
  if (!has_opposite_component_value(rec, 1.0)) return 4;
  if (!has_use_component(rec)) return 5;
  if (!atom_has_opposite_producer_satisfied(rec)) return 8;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 6;
  if ((rec->source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED) != 0) return 7;

  formtrig_reset();
  formtrig_target_hit("site");
  __formtrig_log_branch(123u, 1u);
  __formtrig_log_branch(999u, 1u);
  formtrig_finalize();

  rec = current_record(area);
  if (!record_header_ok(rec)) return 9;
  if (!has_opposite_component_value(rec, 0.0)) return 10;
  if (!has_use_component(rec)) return 11;
  if (atom_has_opposite_producer_satisfied(rec)) return 12;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 13;
  if ((rec->source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED) != 0) return 14;

  free(area);
  return 0;
}
