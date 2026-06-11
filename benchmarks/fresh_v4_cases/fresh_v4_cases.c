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
  size_t cap = 256, len = 0;
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

static void print_range(size_t start, size_t len, const char *event_id, const char *source) {
  if (len == 0) return;
  printf("{\"start\":%zu,\"len\":%zu,\"confidence\":0.95,\"confidence_label\":\"verified\","
         "\"source\":\"%s\",\"runtime_event_id\":\"%s\"}",
         start, len, source, event_id);
}

static int abs_i(int value) { return value < 0 ? -value : value; }

static int run_numeric_actionable(const Input *in) {
  unsigned char value = in->len ? in->data[0] : 0;
  int triggered = value >= 200;
  int dt = triggered ? 0 : 200 - value;
  printf("{\"reached\":true,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,"
         "\"native_DT_a1\":%d,\"trace_signature\":\"v4_numeric:%u\","
         "\"target_context_hash\":\"T1_NUMERIC_ACTIONABLE\","
         "\"root_state\":\"byte0=%u;numeric_margin=%d;use_reached=1\","
         "\"hot_ranges\":[",
         triggered ? "true" : "false", triggered ? "true" : "false", dt, dt, dt, (unsigned)value, (unsigned)value, dt);
  print_range(0, in->len ? 1 : 0, "numeric_byte", "numeric_root");
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_equality_direct_anyof(const Input *in) {
  unsigned char tag = in->len ? in->data[0] : 0;
  int d_a = abs_i((int)tag - 'A');
  int d_b = abs_i((int)tag - 'B');
  int triggered = tag == 'A' || tag == 'B';
  int dt = triggered ? 0 : (d_a < d_b ? d_a : d_b);
  printf("{\"reached\":true,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,"
         "\"native_DT_a1\":%d,\"native_DT_a2\":%d,\"trace_signature\":\"v4_anyof:%u\","
         "\"target_context_hash\":\"T2_EQUALITY_DIRECT_ANYOF\","
         "\"root_state\":\"tag=%u;use_reached=1\","
         "\"hot_ranges\":[",
         triggered ? "true" : "false", triggered ? "true" : "false", dt, dt, d_a, d_b, (unsigned)tag, (unsigned)tag);
  print_range(0, in->len ? 1 : 0, "tag_byte", "equality_root");
  printf("]}\n");
  return triggered ? 1 : 0;
}

static unsigned checksum4(const Input *in) {
  unsigned sum = 0;
  for (size_t i = 2; i < in->len && i < 6; i++) sum = (sum + in->data[i]) & 0xffu;
  return sum;
}

static int run_equality_transformed(const Input *in) {
  int guard = in->len >= 6 && in->data[0] == 'T' && in->data[1] == 'X';
  unsigned sum = checksum4(in);
  int triggered = guard && sum == 0xc7u;
  int dt = guard ? abs_i((int)sum - 0xc7) : 255;
  printf("{\"reached\":true,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,"
         "\"native_DT_a1\":%d,\"native_DT_a2\":%d,\"trace_signature\":\"v4_xeq:%d:%u\","
         "\"target_context_hash\":\"T3_EQUALITY_TRANSFORMED\","
         "\"root_state\":\"hdr_TX=%d;checksum=%u;expected=199;use_reached=1\","
         "\"hot_ranges\":[",
         triggered ? "true" : "false", triggered ? "true" : "false", dt, dt,
         guard ? 0 : 1, dt, guard, sum, guard, sum);
  print_range(2, in->len > 2 ? (in->len - 2 < 4 ? in->len - 2 : 4) : 0, "checksum_region", "derived_checksum");
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_binary_null_lift(const Input *in) {
  unsigned char hdr = in->len ? in->data[0] : 0;
  size_t obj_off = 0, obj_len = 0;
  int has_obj = find_token(in, "OBJ", &obj_off, &obj_len);
  int guard = hdr == 'N' && in->len >= 8;
  int use_reached = guard;
  int triggered = guard && !has_obj;
  int dt = triggered ? 0 : 1;
  printf("{\"reached\":true,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,"
         "\"native_DT_a1\":%d,\"trace_signature\":\"v4_null:%u:%d\","
         "\"target_context_hash\":\"T4_BINARY_NULL_LIFT\","
         "\"root_state\":\"hdr_N=%d;input_len=%zu;producer_OBJ=%d;obj_null=%d;use_reached=%d\","
         "\"hot_ranges\":[",
         triggered ? "true" : "false", triggered ? "true" : "false", dt, dt, dt, (unsigned)hdr, has_obj,
         guard, in->len, has_obj, !has_obj, use_reached);
  if (has_obj) print_range(obj_off, obj_len, "OBJ_region", "producer_context");
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_guarded_binary(const Input *in) {
  unsigned char hdr = in->len ? in->data[0] : 0;
  size_t obj_off = 0, obj_len = 0;
  int has_obj = find_token(in, "OBJ", &obj_off, &obj_len);
  int guard = hdr == 'G';
  int use_reached = guard && in->len >= 8;
  int triggered = use_reached && !has_obj;
  int dt = triggered ? 0 : 1 + abs_i((int)hdr - 'G');
  printf("{\"reached\":true,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,"
         "\"native_DT_a1\":%d,\"native_DT_a2\":%d,\"trace_signature\":\"v4_guard:%u:%d\","
         "\"target_context_hash\":\"T5_GUARDED_BINARY\","
         "\"root_state\":\"hdr=%u;hdr_is_G=%d;producer_OBJ=%d;obj_null=%d;use_reached=%d;blocked_by_guard=%d\","
         "\"hot_ranges\":[",
         triggered ? "true" : "false", triggered ? "true" : "false", dt, dt,
         abs_i((int)hdr - 'G'), triggered ? 0 : 1, (unsigned)hdr, has_obj,
         (unsigned)hdr, guard, has_obj, !has_obj, use_reached, guard ? 0 : 1);
  print_range(0, in->len ? 1 : 0, "guard_header", "guard_context");
  if (has_obj) {
    printf(",");
    print_range(obj_off, obj_len, "OBJ_region", "producer_context");
  }
  printf("]}\n");
  return triggered ? 1 : 0;
}

static int run_same_object_lifecycle(const Input *in) {
  int created = 0, released = 0, used = 0;
  int create_id = -1, release_id = -2, use_id = -3;
  size_t create_off = 0, release_off = 0, use_off = 0;
  for (size_t i = 0; i + 1 < in->len; i += 2) {
    unsigned char ev = in->data[i];
    int id = in->data[i + 1];
    if (ev == 'C') { created = 1; create_id = id; create_off = i; }
    else if (ev == 'R') { released = 1; release_id = id; release_off = i; }
    else if (ev == 'U') { used = 1; use_id = id; use_off = i; }
  }
  int same = created && released && used && create_id == release_id && release_id == use_id;
  int prefix = created + (created && released) + (created && released && used);
  int triggered = used && same;
  int dt = triggered ? 0 : 1;
  printf("{\"reached\":%s,\"triggered\":%s,\"crash_predicate\":%s,\"D_T\":%d,\"D_F\":%d,"
         "\"native_DT_a1\":%d,\"trace_signature\":\"v4_life:%d:%d:%d:%d\","
         "\"target_context_hash\":\"T6_SAME_OBJECT_LIFECYCLE\","
         "\"root_state\":\"create=%d;release=%d;use=%d;create_id=%d;release_id=%d;use_id=%d;lifecycle_prefix=%d;object_identity_confidence=%.1f;next_event_reachability=%d;phase_novelty=%d;use_reached=%d\","
         "\"hot_ranges\":[",
         used ? "true" : "false", triggered ? "true" : "false", triggered ? "true" : "false", dt, dt, dt,
         created, released, used, same,
         created, released, used, create_id, release_id, use_id, prefix, same ? 1.0 : 0.0, used ? 1 : 0, prefix, used);
  if (created) print_range(create_off, 2, "create_event", "lifecycle_event");
  if (released) { if (created) printf(","); print_range(release_off, 2, "release_event", "lifecycle_event"); }
  if (used) { if (created || released) printf(","); print_range(use_off, 2, "use_event", "lifecycle_event"); }
  printf("]}\n");
  return triggered ? 1 : 0;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <numeric|anyof|transformed|null|guarded|lifecycle> [input]\\n", argv[0]);
    return 2;
  }
  size_t len = 0;
  unsigned char *buf = read_input(argc > 2 ? argv[2] : NULL, &len);
  if (!buf) return 2;
  Input in = {buf, len};
  int rc = 2;
  if (strcmp(argv[1], "numeric") == 0) rc = run_numeric_actionable(&in);
  else if (strcmp(argv[1], "anyof") == 0) rc = run_equality_direct_anyof(&in);
  else if (strcmp(argv[1], "transformed") == 0) rc = run_equality_transformed(&in);
  else if (strcmp(argv[1], "null") == 0) rc = run_binary_null_lift(&in);
  else if (strcmp(argv[1], "guarded") == 0) rc = run_guarded_binary(&in);
  else if (strcmp(argv[1], "lifecycle") == 0) rc = run_same_object_lifecycle(&in);
  else fprintf(stderr, "unknown case: %s\\n", argv[1]);
  free(buf);
  return rc;
}
