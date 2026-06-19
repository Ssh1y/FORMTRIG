#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "formtrig/formtrig_runtime.h"

unsigned char *__afl_area_ptr;

static int line_count(const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) return 0;

  int lines = 0;
  int ch = 0;
  while ((ch = fgetc(f)) != EOF) {
    if (ch == '\n') lines++;
  }
  fclose(f);
  return lines;
}

static void record_spec_role(uint64_t source_id) {
  formtrig_record_role_component(
      FORMTRIG_COMPONENT_PRODUCER_USE, 1, FORMTRIG_ROLE_ROOT_OBSERVE, 25,
      FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED |
          FORMTRIG_COMPONENT_SPEC_LIFTED,
      source_id, 1001, 1.0, 0.9);
}

int main(void) {
  const char *snapshot_path = getenv("FORMTRIG_SNAPSHOT_LOG");
  const char *exit_path = getenv("FORMTRIG_LOG");
  if (!snapshot_path || !*snapshot_path || !exit_path || !*exit_path) return 2;

  unsigned char *area =
      (unsigned char *)calloc(1, FORMTRIG_SHM_OFFSET + FORMTRIG_SHM_SIZE);
  if (!area) return 3;
  __afl_area_ptr = area;

  remove(snapshot_path);
  remove(exit_path);

  setenv("FORMTRIG_PUBLISH_EAGER", "1", 1);
  unsetenv("FORMTRIG_ALLOW_MANUAL_LIFT");
  unsetenv("FORMTRIG_ALLOW_HEURISTIC_LIFT");

  formtrig_reset();
  formtrig_target_hit("snapshot_site");
  if (line_count(snapshot_path) != 0) return 4;

  record_spec_role(101);
  if (line_count(snapshot_path) != 1) return 5;

  formtrig_reset();
  formtrig_target_hit("snapshot_site");
  if (line_count(snapshot_path) != 1) return 6;

  record_spec_role(102);
  if (line_count(snapshot_path) != 2) return 7;
  if (line_count(exit_path) != 0) return 8;

  formtrig_finalize();
  if (line_count(exit_path) != 1) return 9;
  if (line_count(snapshot_path) != 3) return 10;

  free(area);
  return 0;
}
