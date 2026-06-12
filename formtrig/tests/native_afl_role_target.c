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

static void record_binary_null_raw_events(const unsigned char *buf, size_t len,
                                          unsigned guard, int desired_state) {
  uint8_t guard32 = guard <= 32u;
  uint8_t desired = desired_state ? 1u : 0u;
  uint8_t opposite_bypassed = guard <= 16u;
  uint8_t use_reached = 1u;

  if (len) __formtrig_log_mem_access(100u, buf, 1u, 0u, guard);
  __formtrig_log_cmp_ex(101u, 37u, guard, 8u, (uint8_t)(guard <= 8u), 0u);
  __formtrig_log_branch(102u, guard32);
  __formtrig_log_branch(103u, desired);
  __formtrig_log_branch(104u, use_reached);
  __formtrig_log_branch(105u, opposite_bypassed);
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

  record_binary_null_raw_events(buf, len, guard, root == NULL);
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
