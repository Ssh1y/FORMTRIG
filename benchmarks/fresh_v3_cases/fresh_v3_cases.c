#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  unsigned char *data;
  size_t len;
} Input;

static unsigned char *read_input(const char *path, size_t *len_out) {
  FILE *f = path ? fopen(path, "rb") : stdin;
  if (!f) return NULL;
  size_t cap = 256;
  size_t len = 0;
  unsigned char *buf = (unsigned char *)malloc(cap);
  if (!buf) {
    if (f != stdin) fclose(f);
    return NULL;
  }
  for (;;) {
    if (len == cap) {
      cap *= 2;
      unsigned char *next = (unsigned char *)realloc(buf, cap);
      if (!next) {
        free(buf);
        if (f != stdin) fclose(f);
        return NULL;
      }
      buf = next;
    }
    size_t n = fread(buf + len, 1, cap - len, f);
    len += n;
    if (n == 0) break;
  }
  if (f != stdin) fclose(f);
  *len_out = len;
  return buf;
}

static int find_token(const Input *in, const char *token, size_t *off_out, size_t *len_out) {
  size_t n = strlen(token);
  for (size_t i = 0; i + n <= in->len; i++) {
    if (memcmp(in->data + i, token, n) == 0) {
      if (off_out) *off_out = i;
      if (len_out) *len_out = n;
      return 1;
    }
  }
  return 0;
}

static void print_hot_range(size_t start, size_t len, const char *event_id) {
  if (len == 0) return;
  printf("{\"start\":%zu,\"len\":%zu,\"confidence\":0.9,\"source\":\"fresh_v3\",\"runtime_event_id\":\"%s\"}", start, len, event_id);
}

static int run_anyof(const Input *in) {
  unsigned char tag = in->len ? in->data[0] : 0;
  int reached = 1;
  int triggered = tag == 'A' || tag == 'B';
  int d_a = tag > 'A' ? tag - 'A' : 'A' - tag;
  int d_b = tag > 'B' ? tag - 'B' : 'B' - tag;
  int dt = triggered ? 0 : (d_a < d_b ? d_a : d_b);
  printf("{\"reached\":%s,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,",
         reached ? "true" : "false", triggered ? "true" : "false", triggered ? "true" : "false", dt, dt);
  printf("\"trace_signature\":\"fresh_anyof:%02x\",\"root_state\":\"tag=%u;tag_char=%c\",",
         (unsigned)tag, (unsigned)tag, (tag >= 32 && tag < 127) ? tag : '?');
  printf("\"hot_ranges\":[");
  print_hot_range(0, in->len ? 1 : 0, "tag_byte");
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_numeric_margin(const Input *in) {
  unsigned char value = in->len ? in->data[0] : 0;
  int reached = 1;
  int triggered = value >= 80;
  int dt = triggered ? 0 : 80 - value;
  printf("{\"reached\":%s,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,",
         reached ? "true" : "false", triggered ? "true" : "false", triggered ? "true" : "false", dt, dt);
  printf("\"trace_signature\":\"fresh_numeric:%02x\",\"root_state\":\"byte0=%u;threshold=80;numeric_margin=%d\",",
         (unsigned)value, (unsigned)value, dt);
  printf("\"hot_ranges\":[");
  print_hot_range(0, in->len ? 1 : 0, "numeric_byte");
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_guarded_numeric_binary(const Input *in) {
  unsigned char hdr = in->len ? in->data[0] : 0;
  size_t obj_off = 0, obj_len = 0;
  int has_obj = find_token(in, "OBJ", &obj_off, &obj_len);
  int len_ok = in->len > 8;
  int reached = 1;
  int triggered = hdr == 'G' && len_ok && !has_obj;
  int dt = triggered ? 0 : 1;
  if (hdr != 'G') dt += hdr > 'G' ? hdr - 'G' : 'G' - hdr;
  if (!len_ok) dt += (int)(9 - in->len);
  printf("{\"reached\":%s,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,",
         reached ? "true" : "false", triggered ? "true" : "false", triggered ? "true" : "false", dt, dt);
  printf("\"trace_signature\":\"fresh_guarded:%02x:%zu:%d\",\"root_state\":\"hdr=%u;hdr_is_G=%d;input_len=%zu;len_gt_8=%d;obj_null=%d;producer_OBJ=%d\",",
         (unsigned)hdr, in->len, has_obj, (unsigned)hdr, hdr == 'G', in->len, len_ok, !has_obj, has_obj);
  printf("\"hot_ranges\":[");
  print_hot_range(0, in->len ? 1 : 0, "guard_header");
  if (has_obj) {
    printf(",");
    print_hot_range(obj_off, obj_len, "OBJ_region");
  }
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_same_object_lifecycle(const Input *in) {
  int created = 0, released = 0, used = 0;
  int create_id = -1, release_id = -2, use_id = -3;
  size_t release_off = 0, use_off = 0;
  for (size_t i = 0; i + 1 < in->len; i += 2) {
    unsigned char ev = in->data[i];
    int id = in->data[i + 1];
    if (ev == 'C') {
      created = 1;
      create_id = id;
    } else if (ev == 'R') {
      released = 1;
      release_id = id;
      release_off = i;
    } else if (ev == 'U') {
      used = 1;
      use_id = id;
      use_off = i;
    }
  }
  int same_object = created && released && used && create_id == release_id && release_id == use_id;
  int reached = used;
  int triggered = reached && same_object;
  int prefix = created + (created && released) + (created && released && used);
  int dt = triggered ? 0 : 1 + (same_object ? 0 : 1);
  printf("{\"reached\":%s,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,",
         reached ? "true" : "false", triggered ? "true" : "false", triggered ? "true" : "false", dt, dt);
  printf("\"trace_signature\":\"fresh_lifecycle:%d:%d:%d:%d\",\"root_state\":\"created=%d;released=%d;used=%d;lifecycle_prefix=%d;object_identity_confidence=%.1f;create_id=%d;release_id=%d;use_id=%d;next_event_reachability=%d;phase_novelty=%d\",",
         created, released, used, same_object, created, released, used, prefix, same_object ? 1.0 : 0.0, create_id, release_id, use_id, used ? 1 : 0, prefix);
  printf("\"hot_ranges\":[");
  if (released) print_hot_range(release_off, 2, "release_event");
  if (released && used) printf(",");
  if (used) print_hot_range(use_off, 2, "use_event");
  printf("]}\n");
  return triggered ? 1 : 0;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <anyof|guarded|lifecycle> [input]\n", argv[0]);
    return 2;
  }
  size_t len = 0;
  unsigned char *buf = read_input(argc > 2 ? argv[2] : NULL, &len);
  if (!buf) return 2;
  Input in = {buf, len};
  int rc = 2;
  if (strcmp(argv[1], "anyof") == 0) rc = run_anyof(&in);
  else if (strcmp(argv[1], "numeric") == 0) rc = run_numeric_margin(&in);
  else if (strcmp(argv[1], "guarded") == 0) rc = run_guarded_numeric_binary(&in);
  else if (strcmp(argv[1], "lifecycle") == 0) rc = run_same_object_lifecycle(&in);
  else fprintf(stderr, "unknown case: %s\n", argv[1]);
  free(buf);
  return rc;
}
