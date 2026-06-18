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

static int run_case(unsigned char *area, uint8_t root_outcome,
                    uint8_t observe_desired, uint8_t observe_opposite,
                    double expected_df) {
  formtrig_reset();
  formtrig_target_hit("site");
  __formtrig_log_cmp(201u, 32u, 0x1000u, 0u, root_outcome);
  __formtrig_log_branch(202u, 1u);
  if (observe_desired) __formtrig_log_branch(204u, 1u);
  if (observe_opposite) __formtrig_log_branch(203u, 1u);
  formtrig_finalize();

  formtrig_shm_record_t *rec = current_record(area);
  if (!record_header_ok(rec)) return 10;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 11;
  if (rec->d_f_spec_lifted != expected_df) return 12;
  if (rec->d_f != expected_df) return 13;
  return 0;
}

static int run_distance_case(unsigned char *area, uint64_t root_distance,
                             double expected_df) {
  formtrig_reset();
  formtrig_target_hit("site");
  __formtrig_log_cmp(301u, 41u, root_distance, 0u,
                     root_distance == 0u ? 1u : 0u);
  __formtrig_log_branch(302u, 1u);
  formtrig_finalize();

  formtrig_shm_record_t *rec = current_record(area);
  if (!record_header_ok(rec)) return 10;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 11;
  if (rec->d_f_spec_lifted != expected_df) return 12;
  if (rec->d_f != expected_df) return 13;
  return 0;
}

int main(void) {
  unsigned char *area =
      (unsigned char *)calloc(1, FORMTRIG_SHM_OFFSET + FORMTRIG_SHM_SIZE);
  if (!area) return 2;
  __afl_area_ptr = area;

  int rc = run_case(area, 0u, 1u, 0u, 2.0);
  if (rc) return rc;

  rc = run_case(area, 1u, 0u, 0u, 2.0);
  if (rc) return rc + 20;

  rc = run_case(area, 1u, 1u, 0u, 1.0);
  if (rc) return rc + 40;

  rc = run_case(area, 1u, 1u, 1u, 2.0);
  if (rc) return rc + 60;

  rc = run_distance_case(area, 3u, 3.0);
  if (rc) return rc + 80;

  free(area);
  return 0;
}
