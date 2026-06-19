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

static double expected_df(void) {
  const char *value = getenv("FORMTRIG_EXPECT_DF");
  return value && *value == '1' ? 1.0 : 2.0;
}

int main(void) {
  unsigned char *area =
      (unsigned char *)calloc(1, FORMTRIG_SHM_OFFSET + FORMTRIG_SHM_SIZE);
  if (!area) return 2;
  __afl_area_ptr = area;

  const uint64_t object = 0x12345678u;
  setenv("FORMTRIG_PUBLISH_EAGER", "1", 1);
  formtrig_reset();
  formtrig_target_hit("site");

  __formtrig_log_cmp(102u, 32u, object, 0u, 1u);
  __formtrig_log_cmp(103u, 32u, object, 0u, 1u);
  __formtrig_log_cmp(201u, 32u, object, 0u, 1u);
  formtrig_finalize();

  formtrig_shm_record_t *rec = current_record(area);
  if (!record_header_ok(rec)) return 3;
  if ((rec->source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) == 0) return 4;
  if (rec->d_f_spec_lifted != expected_df()) return 5;
  if (rec->d_f != expected_df()) return 6;

  free(area);
  return 0;
}
