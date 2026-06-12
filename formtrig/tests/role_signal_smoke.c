#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdlib.h>

#include "formtrig/formtrig_runtime.h"

unsigned char *__afl_area_ptr;

static int has_role(const formtrig_atom_signal_t *signal, uint32_t role) {
  return (signal->role_bits & (1u << (role - 1u))) != 0;
}

static int has_lifted_atom_component(const formtrig_shm_record_t *rec) {
  for (uint32_t i = 0; i < rec->component_count; i++) {
    if (rec->components[i].atom_id != 0 &&
        (rec->components[i].flags & FORMTRIG_COMPONENT_LIFTED))
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
  formtrig_reset();
  formtrig_target_hit("site");

  formtrig_record_role_component(
      FORMTRIG_COMPONENT_PRODUCER_USE, 1, FORMTRIG_ROLE_ROOT_OBSERVE, 25,
      FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED, 101,
      1001, 1.0, 0.9);

  formtrig_shm_record_t *rec =
      (formtrig_shm_record_t *)(void *)(area + FORMTRIG_SHM_OFFSET);
  if (rec->magic != FORMTRIG_SHM_MAGIC ||
      rec->version != FORMTRIG_SHM_VERSION)
    return 3;
  if (has_lifted_atom_component(rec) || rec->atom_signal_count != 0) return 4;

  setenv("FORMTRIG_ALLOW_MANUAL_LIFT", "1", 1);
  formtrig_reset();
  formtrig_target_hit("site");

  formtrig_record_role_component(
      FORMTRIG_COMPONENT_PRODUCER_USE, 1, FORMTRIG_ROLE_ROOT_OBSERVE, 25,
      FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED, 101,
      1001, 1.0, 0.9);
  formtrig_record_role_component(
      FORMTRIG_COMPONENT_PRODUCER_USE, 1, FORMTRIG_ROLE_DESIRED_PRODUCER, 30,
      FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED, 102,
      1001, 1.0, 0.9);
  formtrig_record_role_component(
      FORMTRIG_COMPONENT_PRODUCER_USE, 1, FORMTRIG_ROLE_USE, 30,
      FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED, 103,
      1001, 1.0, 0.9);

  if (rec->magic != FORMTRIG_SHM_MAGIC ||
      rec->version != FORMTRIG_SHM_VERSION)
    return 5;
  if (rec->component_count < 3 || rec->atom_signal_count < 1) return 6;
  if (rec->components[0].role != FORMTRIG_ROLE_ROOT_OBSERVE) return 7;
  if (rec->components[1].role != FORMTRIG_ROLE_DESIRED_PRODUCER) return 8;
  if (rec->components[2].role != FORMTRIG_ROLE_USE) return 9;

  const formtrig_atom_signal_t *signal = &rec->atom_signals[0];
  if (!has_role(signal, FORMTRIG_ROLE_ROOT_OBSERVE) ||
      !has_role(signal, FORMTRIG_ROLE_DESIRED_PRODUCER) ||
      !has_role(signal, FORMTRIG_ROLE_USE))
    return 10;
  if ((signal->producer_bits & 2u) == 0) return 11;
  if ((signal->use_bits & 2u) == 0) return 12;

  free(area);
  return 0;
}
