#include "formtrig/formtrig_runtime.h"

#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned char *read_input(const char *path, size_t *len_out) {
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;

  size_t cap = 64;
  size_t len = 0;
  unsigned char *buf = (unsigned char *)malloc(cap);
  if (!buf) {
    fclose(f);
    return NULL;
  }

  for (;;) {
    if (len == cap) {
      cap *= 2;
      unsigned char *next = (unsigned char *)realloc(buf, cap);
      if (!next) {
        free(buf);
        fclose(f);
        return NULL;
      }
      buf = next;
    }
    size_t n = fread(buf + len, 1, cap - len, f);
    len += n;
    if (!n) break;
  }

  fclose(f);
  *len_out = len;
  return buf;
}

static void record_binary_null_lift(unsigned guard, int desired_state) {
  double margin = guard > 8u ? (double)(guard - 8u) : 0.0;
  uint32_t lower_lift =
      FORMTRIG_COMPONENT_LOWER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED;
  uint32_t higher_lift =
      FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED;

  formtrig_record_hot_range(0, 1, 1.0);
  formtrig_record_role_component(FORMTRIG_COMPONENT_BOUNDARY_MARGIN, 1,
                                 FORMTRIG_ROLE_ROOT_OBSERVE, 10, lower_lift,
                                 0x1001u, 0x5001u, margin, 1.0);
  formtrig_record_role_component(FORMTRIG_COMPONENT_GUARD_PROGRESS, 1,
                                 FORMTRIG_ROLE_GUARD, 20, higher_lift,
                                 0x1002u, 0x5001u, guard <= 32u ? 1.0 : 0.0,
                                 1.0);
  formtrig_record_role_component(FORMTRIG_COMPONENT_PRODUCER_USE, 1,
                                 FORMTRIG_ROLE_DESIRED_PRODUCER, 30,
                                 higher_lift, 0x1003u, 0x5001u,
                                 desired_state ? 1.0 : 0.0, 1.0);
  formtrig_record_role_component(FORMTRIG_COMPONENT_PRODUCER_USE, 1,
                                 FORMTRIG_ROLE_OPPOSITE_PRODUCER, 35,
                                 higher_lift, 0x1004u, 0x5001u,
                                 guard <= 16u ? 1.0 : 0.0, 0.8);
  formtrig_record_role_component(FORMTRIG_COMPONENT_PRODUCER_USE, 1,
                                 FORMTRIG_ROLE_USE, 40, higher_lift, 0x1005u,
                                 0x5001u, 1.0, 1.0);
}

int main(int argc, char **argv) {
  if (argc != 2) return 2;

  size_t len = 0;
  unsigned char *buf = read_input(argv[1], &len);
  if (!buf) return 2;

  formtrig_register_input(buf, len);
  formtrig_target_hit("native_afl_smoke:target");

  unsigned guard = len ? buf[0] : 255u;
  void *root = buf;
  if (guard <= 8u) root = NULL;

  record_binary_null_lift(guard, root == NULL);
  formtrig_record_direct_binary(root == NULL);

  if (root == NULL) {
    formtrig_crash_predicate(1, "native_afl_smoke:null");
    formtrig_finalize();
    free(buf);
    if (!getenv("FORMTRIG_NO_CRASH")) raise(SIGSEGV);
    return 0;
  }

  formtrig_crash_predicate(0, "native_afl_smoke:null");
  formtrig_finalize();
  free(buf);
  return 0;
}
