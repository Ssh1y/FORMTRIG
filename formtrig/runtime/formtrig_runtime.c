#include "formtrig/formtrig_runtime.h"

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define FORMTRIG_INF 1.0e300
#define FORMTRIG_RING_CAP 4096u
#define FORMTRIG_OBJECT_CAP 256u
#define FORMTRIG_LIFT_WINDOW 4096u
#define FORMTRIG_SINK_LOOKBACK 128u
#define FORMTRIG_DEBUG_CANDIDATE_CAP 64u
#define FORMTRIG_PROVENANCE_CAP 512u
#define FORMTRIG_VALUE_PROVENANCE_CAP 256u
#define FORMTRIG_TARGET_SITE_CAP 64u
#define FORMTRIG_PROBE_SPEC_CAP 256u
#define FORMTRIG_U64_SATURATED 9007199254740991.0

#define FORMTRIG_DIRECT_MEM 1u
#define FORMTRIG_DIRECT_DIV 2u
#define FORMTRIG_DIRECT_ARITH 3u
#define FORMTRIG_DIRECT_MANUAL 4u

#define FORMTRIG_SPEC_EVENT 1u
#define FORMTRIG_SPEC_PHASE 2u
#define FORMTRIG_SPEC_RANGE 3u

#define FORMTRIG_SPEC_VALUE_CONST 0u
#define FORMTRIG_SPEC_VALUE_DISTANCE 1u
#define FORMTRIG_SPEC_VALUE_HIT 2u
#define FORMTRIG_SPEC_VALUE_OUTCOME 3u
#define FORMTRIG_SPEC_VALUE_NOT_OUTCOME 4u
#define FORMTRIG_SPEC_VALUE_A 5u
#define FORMTRIG_SPEC_VALUE_B 6u
#define FORMTRIG_SPEC_VALUE_C 7u

#define FORMTRIG_SPEC_WILDCARD UINT32_MAX

extern unsigned char *__afl_area_ptr __attribute__((weak));

uint8_t __formtrig_active = 0;
uint8_t __formtrig_pre_reach_enabled = 0;
uint8_t __formtrig_suppress = 0;

typedef struct {
  uint32_t kind;
  uint32_t site_id;
  uint32_t input_start;
  uint32_t input_len;
  uint64_t a;
  uint64_t b;
  uint64_t c;
  double distance;
  uint8_t is_write;
  uint8_t has_dynamic_producer;
  uint8_t after_reach;
  uint8_t site_class;
} formtrig_event_t;

typedef struct {
  uintptr_t base;
  size_t size;
  int live;
} formtrig_object_t;

typedef struct {
  uintptr_t base;
  size_t size;
  uint32_t input_start;
  uint32_t input_len;
  uint8_t live;
} formtrig_provenance_t;

typedef struct {
  uint64_t value;
  uint32_t input_start;
  uint32_t input_len;
  uint8_t live;
} formtrig_value_provenance_t;

typedef struct {
  uint32_t kind;
  uint32_t site_id;
  uint32_t predicate;
  uint32_t linked_count;
  uint64_t a;
  uint64_t b;
  double distance;
  uint8_t outcome;
  uint8_t after_reach;
  uint8_t mode;
} formtrig_df_source_t;

typedef struct {
  uint32_t site_id;
  uint32_t predicate;
  uint32_t reason;
  uint32_t input_start;
  uint32_t input_len;
  uint64_t a;
  uint64_t b;
  double distance;
  uint8_t outcome;
  uint8_t after_reach;
} formtrig_lift_candidate_t;

typedef struct {
  uint8_t kind;
  uint32_t event_kind;
  uint32_t site_id;
  uint32_t component_kind;
  uint32_t atom_id;
  uint32_t priority;
  uint32_t direction_flag;
  uint32_t value_mode;
  uint32_t phase_index;
  uint32_t phase_prefix;
  uint32_t range_start;
  uint32_t range_len;
  uint64_t source_id;
  uint64_t context_hash;
  double value;
  double confidence;
} formtrig_probe_spec_t;

typedef struct {
  int reached;
  int crash_predicate;
  int binary_sink;
  int manual_lifted;
  int manual_direct;
  uint8_t d_f_direct_kind;
  uint32_t target_hit_count;
  double d_t;
  double d_f_direct;
  double d_f_lifted;
  formtrig_df_source_t df_source;
  uint32_t lift_candidate_count;
  uint32_t lift_linked_count;
  uint32_t lift_reject_pointer_count;
  uint32_t lift_reject_zero_count;
  uint32_t lift_reject_noslice_count;
  uint32_t lift_reject_prereach_count;
  uint32_t lift_sink_site_id;
  uint32_t lift_load_site_id;
  uint32_t lift_store_site_id;
  uint64_t lift_sink_ptr;
  uint8_t lift_load_in_live_object;
  formtrig_lift_candidate_t lift_candidates[FORMTRIG_DEBUG_CANDIDATE_CAP];
  uint32_t lift_debug_candidate_count;
  uint64_t trace_signature;
  uintptr_t input_base;
  size_t input_len;
  uint32_t target_epoch_start;
  formtrig_event_t ring[FORMTRIG_RING_CAP];
  uint32_t ring_count;
  formtrig_object_t objects[FORMTRIG_OBJECT_CAP];
  formtrig_provenance_t provenance[FORMTRIG_PROVENANCE_CAP];
  uint32_t provenance_next;
  uint32_t provenance_count;
  formtrig_value_provenance_t value_provenance[FORMTRIG_VALUE_PROVENANCE_CAP];
  uint32_t value_provenance_next;
  uint32_t value_provenance_count;
  formtrig_hot_range_t hot_ranges[FORMTRIG_MAX_HOT_RANGES];
  uint32_t hot_range_count;
  formtrig_progress_component_t components[FORMTRIG_MAX_PROGRESS_COMPONENTS];
  uint32_t component_count;
  int finalized;
} formtrig_state_t;

static formtrig_state_t g_state;
static int g_track_alloc_pre_reach = -1;
static int g_record_pre_reach_events = -1;
static int g_lift_crash_predicate = -1;
static int g_suppress_canary_events = -1;
static int g_source_objective = -1;
static int g_source_site_reach = -1;
static int g_target_from_canary = -1;
static int g_publish_eager = -1;
static uint32_t g_target_sites[FORMTRIG_TARGET_SITE_CAP];
static uint32_t g_target_site_count = UINT32_MAX;
static int g_debug_events = -1;
static int g_debug_predicate_snapshot = -1;
static uint32_t g_lift_window = 0;
static uint32_t g_sink_lookback = 0;
static uint32_t g_debug_event_window = 0;
static formtrig_shm_record_t *g_dedicated_shm_record = NULL;
static int g_dedicated_shm_checked = 0;
static formtrig_probe_spec_t g_probe_specs[FORMTRIG_PROBE_SPEC_CAP];
static uint32_t g_probe_spec_count = 0;
static int g_probe_specs_loaded = 0;

static void apply_probe_specs_to_event(const formtrig_event_t *event);
static void reset_probe_spec_runtime_state(void);

static int env_truthy(const char *env) {
  return env && (*env == '1' || *env == 'y' || *env == 'Y' || *env == 't' ||
                 *env == 'T');
}

static int track_alloc_pre_reach(void) {
  if (g_track_alloc_pre_reach >= 0) return g_track_alloc_pre_reach;
  const char *env = getenv("FORMTRIG_TRACK_ALLOC_PRE_REACH");
  g_track_alloc_pre_reach = env ? env_truthy(env) : 0;
  return g_track_alloc_pre_reach;
}

static int record_pre_reach_events(void) {
  if (g_record_pre_reach_events >= 0) return g_record_pre_reach_events;
  const char *env = getenv("FORMTRIG_PRE_REACH_EVENTS");
  g_record_pre_reach_events = env ? env_truthy(env) : 0;
  return g_record_pre_reach_events;
}

static int source_objective_enabled(void);

static void refresh_pre_reach_gate(void) {
  __formtrig_pre_reach_enabled =
      (uint8_t)((record_pre_reach_events() || source_objective_enabled()) ? 1 : 0);
}

static int lift_crash_predicate(void) {
  if (g_lift_crash_predicate >= 0) return g_lift_crash_predicate;
  g_lift_crash_predicate = env_truthy(getenv("FORMTRIG_LIFT_CRASH_PREDICATE"));
  return g_lift_crash_predicate;
}

int formtrig_suppress_canary_events(void) {
  if (g_suppress_canary_events >= 0) return g_suppress_canary_events;
  const char *env = getenv("FORMTRIG_SUPPRESS_CANARY_EVENTS");
  g_suppress_canary_events = env ? env_truthy(env) : 0;
  return g_suppress_canary_events;
}

static int source_objective_enabled(void) {
  if (g_source_objective >= 0) return g_source_objective;
  const char *env = getenv("FORMTRIG_SOURCE_OBJECTIVE");
  g_source_objective = env ? env_truthy(env) : 1;
  return g_source_objective;
}

static int source_site_reach_enabled(void) {
  if (g_source_site_reach >= 0) return g_source_site_reach;
  const char *env = getenv("FORMTRIG_SOURCE_SITE_REACH");
  g_source_site_reach = env ? env_truthy(env) : 1;
  return g_source_site_reach;
}

static int source_site_label(const char *label) {
  return label && strcmp(label, "site") == 0;
}

int formtrig_target_from_canary(void) {
  if (g_target_from_canary >= 0) return g_target_from_canary;
  const char *env = getenv("FORMTRIG_TARGET_FROM_CANARY");
  g_target_from_canary = env ? env_truthy(env) : 1;
  return g_target_from_canary;
}

static void parse_target_sites(void) {
  if (g_target_site_count != UINT32_MAX) return;
  g_target_site_count = 0;
  const char *env = getenv("FORMTRIG_TARGET_SITE_IDS");
  if (!env || !*env) return;

  const char *p = env;
  while (*p && g_target_site_count < FORMTRIG_TARGET_SITE_CAP) {
    char *end = NULL;
    unsigned long value = strtoul(p, &end, 0);
    if (end == p) break;
    if (value > 0 && value <= UINT32_MAX)
      g_target_sites[g_target_site_count++] = (uint32_t)value;
    p = end;
    while (*p == ',' || *p == ':' || *p == ';' || *p == ' ' || *p == '\t')
      p++;
  }
}

static int target_site_matches(uint32_t site_id) {
  if (!site_id) return 0;
  parse_target_sites();
  for (uint32_t i = 0; i < g_target_site_count; i++)
    if (g_target_sites[i] == site_id) return 1;
  return 0;
}

static int source_target_site_mode(void) {
  parse_target_sites();
  return source_objective_enabled() && g_target_site_count > 0;
}

static int publish_eager(void) {
  if (g_publish_eager >= 0) return g_publish_eager;
  const char *env = getenv("FORMTRIG_PUBLISH_EAGER");
  g_publish_eager = env ? env_truthy(env) : 0;
  return g_publish_eager;
}

static void maybe_target_site_hit(uint32_t site_id) {
  if (!source_site_reach_enabled()) return;
  if (!g_state.reached && target_site_matches(site_id))
    formtrig_target_hit("site");
}

static int debug_events(void) {
  if (g_debug_events >= 0) return g_debug_events;
  g_debug_events = env_truthy(getenv("FORMTRIG_DEBUG_EVENTS"));
  return g_debug_events;
}

static int debug_predicate_snapshot(void) {
  if (g_debug_predicate_snapshot >= 0) return g_debug_predicate_snapshot;
  g_debug_predicate_snapshot =
      env_truthy(getenv("FORMTRIG_DEBUG_PREDICATE_SNAPSHOT"));
  return g_debug_predicate_snapshot;
}

static uint32_t lift_window(void) {
  if (g_lift_window) return g_lift_window;
  const char *env = getenv("FORMTRIG_LIFT_WINDOW");
  if (env && *env) {
    unsigned long value = strtoul(env, NULL, 10);
    if (value > 0 && value <= FORMTRIG_RING_CAP)
      g_lift_window = (uint32_t)value;
  }
  if (!g_lift_window) g_lift_window = FORMTRIG_LIFT_WINDOW;
  if (g_lift_window > FORMTRIG_RING_CAP) g_lift_window = FORMTRIG_RING_CAP;
  return g_lift_window;
}

static uint32_t debug_event_window(void) {
  if (g_debug_event_window) return g_debug_event_window;
  const char *env = getenv("FORMTRIG_DEBUG_EVENT_WINDOW");
  if (env && *env) {
    unsigned long value = strtoul(env, NULL, 10);
    if (value > 0 && value <= FORMTRIG_RING_CAP)
      g_debug_event_window = (uint32_t)value;
  }
  if (!g_debug_event_window) g_debug_event_window = 32u;
  if (g_debug_event_window > FORMTRIG_RING_CAP)
    g_debug_event_window = FORMTRIG_RING_CAP;
  return g_debug_event_window;
}

static uint32_t sink_lookback(void) {
  if (g_sink_lookback) return g_sink_lookback;
  const char *env = getenv("FORMTRIG_SINK_LOOKBACK");
  if (env && *env) {
    unsigned long value = strtoul(env, NULL, 10);
    if (value > 0 && value <= FORMTRIG_RING_CAP)
      g_sink_lookback = (uint32_t)value;
  }
  if (!g_sink_lookback) g_sink_lookback = FORMTRIG_SINK_LOOKBACK;
  if (g_sink_lookback > FORMTRIG_RING_CAP)
    g_sink_lookback = FORMTRIG_RING_CAP;
  return g_sink_lookback;
}

static void add_hot_range(uint32_t start, uint32_t len, double influence) {
  if (!len) return;

  uint64_t end = (uint64_t)start + (uint64_t)len;
  for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
    formtrig_hot_range_t *r = &g_state.hot_ranges[i];
    uint64_t r_end = (uint64_t)r->start + (uint64_t)r->len;
    if (end <= r->start || r_end <= start) continue;
    uint32_t new_start = start < r->start ? start : r->start;
    uint64_t new_end = end > r_end ? end : r_end;
    r->start = new_start;
    r->len = new_end > UINT32_MAX ? UINT32_MAX - new_start
                                   : (uint32_t)(new_end - new_start);
    if (influence > r->influence) r->influence = influence;
    return;
  }

  if (g_state.hot_range_count >= FORMTRIG_MAX_HOT_RANGES) return;
  formtrig_hot_range_t *r = &g_state.hot_ranges[g_state.hot_range_count++];
  r->start = start;
  r->len = len;
  r->influence = influence;
}

static void prioritize_hot_range(uint32_t start, uint32_t len, double influence) {
  if (!len) return;
  add_hot_range(start, len, influence);

  uint64_t end = (uint64_t)start + (uint64_t)len;
  for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
    formtrig_hot_range_t *r = &g_state.hot_ranges[i];
    uint64_t r_end = (uint64_t)r->start + (uint64_t)r->len;
    if (end <= r->start || r_end <= start) continue;
    if (influence > r->influence) r->influence = influence;
    if (i > 0) {
      formtrig_hot_range_t saved = *r;
      memmove(&g_state.hot_ranges[1], &g_state.hot_ranges[0],
              sizeof(g_state.hot_ranges[0]) * i);
      g_state.hot_ranges[0] = saved;
    }
    return;
  }
}

static int range_overlaps(uintptr_t a_base, size_t a_size, uintptr_t b_base,
                          size_t b_size, uintptr_t *overlap_start,
                          uintptr_t *overlap_end) {
  if (!a_size || !b_size) return 0;
  uintptr_t a_end = a_base + a_size;
  uintptr_t b_end = b_base + b_size;
  if (a_end < a_base || b_end < b_base) return 0;
  if (a_end <= b_base || b_end <= a_base) return 0;
  *overlap_start = a_base > b_base ? a_base : b_base;
  *overlap_end = a_end < b_end ? a_end : b_end;
  return *overlap_end > *overlap_start;
}

static void remember_memory_provenance(uintptr_t ptr, size_t size,
                                       uint32_t input_start,
                                       uint32_t input_len) {
  if (!ptr || !size || !input_len || !g_state.input_len) return;
  if (input_start >= g_state.input_len) return;
  if ((uint64_t)input_start + input_len > g_state.input_len)
    input_len = (uint32_t)(g_state.input_len - input_start);
  if (!input_len) return;

  for (uint32_t i = 0; i < g_state.provenance_count; i++) {
    formtrig_provenance_t *p = &g_state.provenance[i];
    if (!p->live) continue;
    if (p->base == ptr && p->size == size) {
      p->input_start = input_start;
      p->input_len = input_len;
      return;
    }
  }

  uint32_t slot = g_state.provenance_next++ % FORMTRIG_PROVENANCE_CAP;
  if (g_state.provenance_count < FORMTRIG_PROVENANCE_CAP)
    g_state.provenance_count++;
  formtrig_provenance_t *p = &g_state.provenance[slot];
  p->base = ptr;
  p->size = size;
  p->input_start = input_start;
  p->input_len = input_len;
  p->live = 1;
}

static void remember_value_provenance(uint64_t value, uint32_t input_start,
                                      uint32_t input_len) {
  if (!input_len || value == 0) return;

  uint32_t slot =
      g_state.value_provenance_next++ % FORMTRIG_VALUE_PROVENANCE_CAP;
  if (g_state.value_provenance_count < FORMTRIG_VALUE_PROVENANCE_CAP)
    g_state.value_provenance_count++;
  formtrig_value_provenance_t *p = &g_state.value_provenance[slot];
  p->value = value;
  p->input_start = input_start;
  p->input_len = input_len;
  p->live = 1;
}

static int lookup_value_provenance(uint64_t value, uint32_t *input_start,
                                   uint32_t *input_len) {
  if (value == 0) return 0;
  for (uint32_t n = 0; n < g_state.value_provenance_count; n++) {
    uint32_t idx =
        (g_state.value_provenance_next + FORMTRIG_VALUE_PROVENANCE_CAP - 1u -
         n) %
        FORMTRIG_VALUE_PROVENANCE_CAP;
    formtrig_value_provenance_t *p = &g_state.value_provenance[idx];
    if (!p->live || p->value != value) continue;
    *input_start = p->input_start;
    *input_len = p->input_len;
    return 1;
  }
  return 0;
}

static int record_input_access(uintptr_t ptr, size_t size,
                               uint32_t *first_start,
                               uint32_t *first_len) {
  int found = 0;
  uintptr_t overlap_start = 0;
  uintptr_t overlap_end = 0;

  if (!g_state.input_base || !g_state.input_len || !size) return 0;

  if (range_overlaps(ptr, size, g_state.input_base, g_state.input_len,
                     &overlap_start, &overlap_end)) {
    uint32_t start = (uint32_t)(overlap_start - g_state.input_base);
    uint32_t len = (uint32_t)(overlap_end - overlap_start);
    add_hot_range(start, len, 1.0);
    if (first_start && !found) *first_start = start;
    if (first_len && !found) *first_len = len;
    found = 1;
  }

  for (uint32_t i = 0; i < g_state.provenance_count; i++) {
    formtrig_provenance_t *p = &g_state.provenance[i];
    if (!p->live) continue;
    if (!range_overlaps(ptr, size, p->base, p->size, &overlap_start,
                        &overlap_end))
      continue;

    uint64_t prov_off = (uint64_t)(overlap_start - p->base);
    if (prov_off >= p->input_len) continue;
    uint32_t start = p->input_start + (uint32_t)prov_off;
    uint32_t len = (uint32_t)(overlap_end - overlap_start);
    if ((uint64_t)start + len > g_state.input_len)
      len = (uint32_t)(g_state.input_len - start);
    if (!len) continue;
    add_hot_range(start, len, 1.0);
    if (first_start && !found) *first_start = start;
    if (first_len && !found) *first_len = len;
    found = 1;
  }

  return found;
}

static int address_in_live_object(uintptr_t ptr, size_t size) {
  if (!ptr || !size) return 0;
  for (uint32_t i = 0; i < FORMTRIG_OBJECT_CAP; i++) {
    if (!g_state.objects[i].live) continue;
    uintptr_t base = g_state.objects[i].base;
    uintptr_t end = base + g_state.objects[i].size;
    uintptr_t access_end = ptr + size;
    if (access_end < ptr || end < base) continue;
    if (ptr >= base && access_end <= end) return 1;
  }
  return 0;
}

static void propagate_transfer_provenance(uintptr_t dst, uintptr_t src,
                                          size_t size) {
  uintptr_t overlap_start = 0;
  uintptr_t overlap_end = 0;

  if (!dst || !src || !size || !g_state.input_len) return;

  if (range_overlaps(src, size, g_state.input_base, g_state.input_len,
                     &overlap_start, &overlap_end)) {
    uint32_t input_start = (uint32_t)(overlap_start - g_state.input_base);
    uint32_t input_len = (uint32_t)(overlap_end - overlap_start);
    uintptr_t dst_part = dst + (overlap_start - src);
    remember_memory_provenance(dst_part, input_len, input_start, input_len);
  }

  for (uint32_t i = 0; i < g_state.provenance_count; i++) {
    formtrig_provenance_t *p = &g_state.provenance[i];
    if (!p->live) continue;
    if (!range_overlaps(src, size, p->base, p->size, &overlap_start,
                        &overlap_end))
      continue;

    uint64_t prov_off = (uint64_t)(overlap_start - p->base);
    if (prov_off >= p->input_len) continue;
    uint32_t input_start = p->input_start + (uint32_t)prov_off;
    uint32_t input_len = (uint32_t)(overlap_end - overlap_start);
    if ((uint64_t)input_start + input_len > g_state.input_len)
      input_len = (uint32_t)(g_state.input_len - input_start);
    if (!input_len) continue;
    uintptr_t dst_part = dst + (overlap_start - src);
    remember_memory_provenance(dst_part, input_len, input_start, input_len);
  }
}

static int target_label_matches(const char *label) {
  const char *target = getenv("FORMTRIG_TARGET_BUG");
  if (!label || !*label) return 0;
  if (source_site_label(label)) return source_objective_enabled();
  if (!target || !*target) return 1;
  size_t n = strlen(target);
  return strncmp(label, target, n) == 0 && (label[n] == '\0' || label[n] == ':');
}

int formtrig_target_selected(const char *label) {
  return target_label_matches(label);
}

static uint64_t fnv_mix_u64(uint64_t sig, uint64_t value) {
  sig ^= value;
  sig *= 1099511628211ULL;
  return sig;
}

static void reset_state(formtrig_state_t *s) {
  memset(s, 0, sizeof(*s));
  s->d_t = FORMTRIG_INF;
  s->d_f_direct = FORMTRIG_INF;
  s->d_f_lifted = FORMTRIG_INF;
  s->trace_signature = 1469598103934665603ULL;
}

static double min_double(double a, double b) {
  return a < b ? a : b;
}

static double abs_i64_as_double(int64_t v) {
  if (v == INT64_MIN) return (double)INT64_MAX + 1.0;
  return v < 0 ? (double)-v : (double)v;
}

static double u64_to_double_saturated(uint64_t v) {
  return v > (uint64_t)9007199254740991ULL ? FORMTRIG_U64_SATURATED
                                           : (double)v;
}

static uint64_t distance_bucket_for_signature(double distance) {
  if (!isfinite(distance) || distance < 0.0) return 255u;
  if (distance == 0.0) return 0u;

  uint64_t bucket = 1u;
  while (distance > 1.0 && bucket < 254u) {
    distance /= 2.0;
    bucket++;
  }
  return bucket;
}

static int finite_distance(double distance) {
  return isfinite(distance) && distance >= 0.0 && distance < FORMTRIG_INF / 2.0;
}

static int informative_safety_distance(double distance) {
  return finite_distance(distance) && distance < FORMTRIG_U64_SATURATED;
}

static double cmp_flip_distance(const formtrig_event_t *event);
static int synthesize_live_pointer_producer_lift(void);

static void push_event_full_class_with_input(
    uint32_t kind, uint32_t site_id, uint64_t a, uint64_t b, uint64_t c,
    double distance, uint8_t is_write, uint8_t has_dynamic_producer,
    uint8_t site_class, uint32_t input_start, uint32_t input_len) {
  maybe_target_site_hit(site_id);
  if (__formtrig_suppress) return;
  int reached = g_state.reached;
  if (!reached && !record_pre_reach_events()) return;

  uint32_t slot = g_state.ring_count % FORMTRIG_RING_CAP;
  g_state.ring[slot].kind = kind;
  g_state.ring[slot].site_id = site_id;
  g_state.ring[slot].input_start = input_start;
  g_state.ring[slot].input_len = input_len;
  g_state.ring[slot].a = a;
  g_state.ring[slot].b = b;
  g_state.ring[slot].c = c;
  g_state.ring[slot].distance = distance;
  g_state.ring[slot].is_write = is_write;
  g_state.ring[slot].has_dynamic_producer = has_dynamic_producer;
  g_state.ring[slot].after_reach = (uint8_t)reached;
  g_state.ring[slot].site_class = site_class;
  g_state.ring_count++;

  if (!reached) return;

  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, kind);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, site_id);
  g_state.trace_signature =
      fnv_mix_u64(g_state.trace_signature, distance_bucket_for_signature(distance));
  apply_probe_specs_to_event(&g_state.ring[slot]);
}

static void push_event_full_class(uint32_t kind, uint32_t site_id, uint64_t a,
                                  uint64_t b, uint64_t c, double distance,
                                  uint8_t is_write,
                                  uint8_t has_dynamic_producer,
                                  uint8_t site_class) {
  push_event_full_class_with_input(kind, site_id, a, b, c, distance, is_write,
                                   has_dynamic_producer, site_class, 0, 0);
}

static void push_event_full(uint32_t kind, uint32_t site_id, uint64_t a,
                            uint64_t b, uint64_t c, double distance,
                            uint8_t is_write,
                            uint8_t has_dynamic_producer) {
  push_event_full_class(kind, site_id, a, b, c, distance, is_write,
                        has_dynamic_producer, 0);
}

static void push_event(uint32_t kind, uint32_t site_id, uint64_t a, uint64_t b,
                       double distance) {
  push_event_full(kind, site_id, a, b, 0, distance, 0, 0);
}

static formtrig_event_t *event_at(uint32_t logical_index) {
  if (logical_index >= g_state.ring_count) return NULL;
  uint32_t oldest =
      g_state.ring_count > FORMTRIG_RING_CAP
          ? g_state.ring_count - FORMTRIG_RING_CAP
          : 0;
  if (logical_index < oldest) return NULL;
  return &g_state.ring[logical_index % FORMTRIG_RING_CAP];
}

static int value_links(uint64_t needle, const formtrig_event_t *producer) {
  if (needle == 0 || !producer) return 0;

  switch (producer->kind) {
    case 5u: /* malloc: produces base pointer and size */
    case 6u: /* free: consumes/identifies a prior object pointer */
      return needle == producer->a || needle == producer->b;
    case 9u: /* memory: produces/consumes address, size, and value */
      return needle == producer->a || needle == producer->b ||
             needle == producer->c;
    case 10u: /* div/mod: divisor is the safety-relevant producer */
      return needle == producer->a;
    case 11u: /* arithmetic: result is the producer; operands are dependencies */
      return needle == producer->c || needle == producer->a ||
             needle == producer->b;
    default:
      return 0;
  }
}

static uint8_t cmp_has_dynamic_slice(uint32_t cmp_index,
                                     const formtrig_event_t *cmp) {
  uint32_t oldest =
      cmp_index > lift_window() ? cmp_index - lift_window() : 0;
  for (uint32_t idx = cmp_index; idx-- > oldest;) {
    formtrig_event_t *producer = event_at(idx);
    if (!producer) continue;
    if (value_links(cmp->a, producer) || value_links(cmp->b, producer))
      return 1;
  }
  return 0;
}

static int cmp_is_null_pointer_distance(const formtrig_event_t *cmp) {
  if (!cmp) return 0;
  uint32_t predicate = (uint32_t)(cmp->c >> 32);
  if (predicate != 32u && predicate != 33u) return 0;

  if (cmp->a == 0 && cmp->b > 4096u) return 1;
  if (cmp->b == 0 && cmp->a > 4096u) return 1;
  return 0;
}

static uint64_t cmp_pointer_value(const formtrig_event_t *cmp) {
  if (!cmp_is_null_pointer_distance(cmp)) return 0;
  if (cmp->a == 0) return cmp->b;
  if (cmp->b == 0) return cmp->a;
  return 0;
}

static uint32_t cmp_predicate(const formtrig_event_t *cmp) {
  return cmp ? (uint32_t)(cmp->c >> 32) : 0;
}

static uint8_t cmp_outcome(const formtrig_event_t *cmp) {
  return cmp ? (uint8_t)(cmp->c & 0xffu) : 0;
}

static void remember_df_source(const formtrig_event_t *event, uint32_t linked,
                               uint8_t mode) {
  if (!event) return;
  g_state.df_source.kind = event->kind;
  g_state.df_source.site_id = event->site_id;
  g_state.df_source.predicate = cmp_predicate(event);
  g_state.df_source.linked_count = linked;
  g_state.df_source.a = event->a;
  g_state.df_source.b = event->b;
  g_state.df_source.distance = event->distance;
  g_state.df_source.outcome = cmp_outcome(event);
  g_state.df_source.after_reach = event->after_reach;
  g_state.df_source.mode = mode;
  if (event->input_len)
    prioritize_hot_range(event->input_start, event->input_len, 4.0);
}

static void remember_df_source_with_distance(const formtrig_event_t *event,
                                             uint32_t linked, uint8_t mode,
                                             double distance) {
  remember_df_source(event, linked, mode);
  if (event) g_state.df_source.distance = distance;
}

static void remember_source_target_safety_margin(uint32_t kind,
                                                 uint32_t site_id,
                                                 uint32_t predicate,
                                                 uint64_t a, uint64_t b,
                                                 double distance,
                                                 uint8_t outcome) {
  if (!source_target_site_mode() || !target_site_matches(site_id)) return;
  if (!g_state.reached || g_state.manual_lifted ||
      !informative_safety_distance(distance))
    return;
  if (g_state.d_f_lifted < FORMTRIG_INF / 2.0 &&
      distance > g_state.d_f_lifted)
    return;

  g_state.d_f_lifted = distance;
  g_state.df_source.kind = kind;
  g_state.df_source.site_id = site_id;
  g_state.df_source.predicate = predicate;
  g_state.df_source.linked_count = 1u;
  g_state.df_source.a = a;
  g_state.df_source.b = b;
  g_state.df_source.distance = distance;
  g_state.df_source.outcome = outcome;
  g_state.df_source.after_reach = 1u;
  g_state.df_source.mode = 9u;
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 19u);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, site_id);
  g_state.trace_signature =
      fnv_mix_u64(g_state.trace_signature,
                  distance_bucket_for_signature(distance));
}

static void remember_lift_candidate(const formtrig_event_t *event,
                                    uint32_t reason) {
  if (!event) return;
  if (g_state.lift_debug_candidate_count >= FORMTRIG_DEBUG_CANDIDATE_CAP) {
    memmove(&g_state.lift_candidates[0], &g_state.lift_candidates[1],
            sizeof(g_state.lift_candidates[0]) *
                (FORMTRIG_DEBUG_CANDIDATE_CAP - 1u));
    g_state.lift_debug_candidate_count = FORMTRIG_DEBUG_CANDIDATE_CAP - 1u;
  }
  formtrig_lift_candidate_t *c =
      &g_state.lift_candidates[g_state.lift_debug_candidate_count++];
  c->site_id = event->site_id;
  c->predicate = cmp_predicate(event);
  c->reason = reason;
  c->input_start = event->input_start;
  c->input_len = event->input_len;
  c->a = event->a;
  c->b = event->b;
  c->distance = event->distance;
  c->outcome = cmp_outcome(event);
  c->after_reach = event->after_reach;
}

static int cmp_is_usable_null_lift_source(uint32_t idx,
                                          const formtrig_event_t *event,
                                          int sink_satisfied,
                                          double *flip_distance) {
  if (!event || event->kind != 7u) return 0;
  if (cmp_is_null_pointer_distance(event)) return 0;
  if (event->site_class == 1u) {
    remember_lift_candidate(event, 6u);
    return 0;
  }
  double d = cmp_flip_distance(event);
  if (!finite_distance(d)) return 0;
  if (!sink_satisfied && d == 0.0) return 0;
  if (event->has_dynamic_producer != 2u || !event->input_len) {
    remember_lift_candidate(event, 7u);
    return 0;
  }
  if (!cmp_has_dynamic_slice(idx, event)) {
    remember_lift_candidate(event, 5u);
    return 0;
  }
  if (flip_distance) *flip_distance = d;
  return 1;
}

static int cmp_is_allocator_size_guard_between(uint32_t cmp_idx,
                                               const formtrig_event_t *cmp,
                                               uint64_t ptr_value,
                                               uint32_t end_idx) {
  if (!cmp || !ptr_value || cmp_idx >= end_idx) return 0;

  for (uint32_t idx = cmp_idx + 1u; idx < end_idx; idx++) {
    formtrig_event_t *event = event_at(idx);
    if (!event || event->kind != 5u) continue;
    if (event->a != ptr_value) continue;
    if (cmp->a == event->b || cmp->b == event->b) return 1;
  }

  return 0;
}

static const formtrig_event_t *latest_linked_null_cmp_before(
    uint32_t end_idx, int sink_satisfied, uint32_t *linked,
    double *selected_distance, uint64_t ptr_value) {
  uint32_t oldest =
      end_idx > lift_window() ? end_idx - lift_window() : 0;
  const formtrig_event_t *best_true = NULL;
  const formtrig_event_t *best_false = NULL;
  const formtrig_event_t *best_any = NULL;
  double best_true_distance = FORMTRIG_INF;
  double best_false_distance = FORMTRIG_INF;
  double best_any_distance = FORMTRIG_INF;
  if (linked) *linked = 0;

  for (uint32_t idx = oldest; idx < end_idx; idx++) {
    formtrig_event_t *event = event_at(idx);
    double d = FORMTRIG_INF;
    if (!cmp_is_usable_null_lift_source(idx, event, sink_satisfied, &d))
      continue;
    if (cmp_is_allocator_size_guard_between(idx, event, ptr_value, end_idx))
      continue;
    remember_lift_candidate(event, 0u);
    best_any = event;
    best_any_distance = d;
    if (cmp_outcome(event)) {
      best_true = event;
      best_true_distance = d;
    } else {
      best_false = event;
      best_false_distance = d;
    }
    if (linked) (*linked)++;
  }

  if (!sink_satisfied && best_false) {
    if (selected_distance) *selected_distance = best_false_distance;
    return best_false;
  }
  if (best_true) {
    if (selected_distance) *selected_distance = best_true_distance;
    return best_true;
  }
  if (best_false) {
    if (selected_distance) *selected_distance = best_false_distance;
    return best_false;
  }
  if (selected_distance) *selected_distance = best_any_distance;
  return best_any;
}

static const formtrig_event_t *latest_linked_null_cmp_between(
    uint32_t start_idx, uint32_t end_idx, int sink_satisfied, uint32_t *linked,
    double *selected_distance, uint64_t ptr_value) {
  const formtrig_event_t *best_any = NULL;
  const formtrig_event_t *best_false = NULL;
  double best_any_distance = FORMTRIG_INF;
  double best_false_distance = FORMTRIG_INF;
  if (linked) *linked = 0;
  if (end_idx <= start_idx) return NULL;

  uint32_t oldest =
      end_idx > lift_window() ? end_idx - lift_window() : 0;
  if (start_idx < oldest) start_idx = oldest;

  for (uint32_t idx = start_idx; idx < end_idx; idx++) {
    formtrig_event_t *event = event_at(idx);
    double d = FORMTRIG_INF;
    if (!cmp_is_usable_null_lift_source(idx, event, sink_satisfied, &d))
      continue;
    if (cmp_is_allocator_size_guard_between(idx, event, ptr_value, end_idx))
      continue;
    remember_lift_candidate(event, 0u);
    best_any = event;
    best_any_distance = d;
    if (!cmp_outcome(event)) {
      best_false = event;
      best_false_distance = d;
    }
    if (linked) (*linked)++;
  }

  if (!sink_satisfied && best_false) {
    if (selected_distance) *selected_distance = best_false_distance;
    return best_false;
  }
  if (selected_distance) *selected_distance = best_any_distance;
  return best_any;
}

static int synthesize_null_pointer_producer_lift(int sink_satisfied,
                                                int strict_reached_sink) {
  uint32_t newest = g_state.ring_count;
  uint32_t oldest =
      newest > lift_window() ? newest - lift_window() : 0;
  uint32_t sink_oldest = oldest;
  int saw_reached_null_sink = 0;

  if (strict_reached_sink && g_state.target_epoch_start < newest) {
    uint32_t lookback_start =
        g_state.target_epoch_start > sink_lookback()
            ? g_state.target_epoch_start - sink_lookback()
            : 0;
    if (lookback_start > sink_oldest) sink_oldest = lookback_start;
  }

  for (uint32_t cmp_idx = newest; cmp_idx-- > sink_oldest;) {
    formtrig_event_t *cmp = event_at(cmp_idx);
    if (!cmp || cmp->kind != 7u || !cmp_is_null_pointer_distance(cmp)) continue;
    if (strict_reached_sink && !cmp->after_reach &&
        (!g_state.target_epoch_start || cmp_idx >= g_state.target_epoch_start))
      continue;
    saw_reached_null_sink = 1;

    uint64_t ptr_value = cmp_pointer_value(cmp);
    if (!ptr_value) continue;

    uint32_t load_start = cmp_idx > 24u ? cmp_idx - 24u : oldest;
    formtrig_event_t *selected_load = NULL;
    uint32_t selected_load_idx = 0;
    int selected_load_score = -1;
    for (uint32_t load_idx = cmp_idx; load_idx-- > load_start;) {
      formtrig_event_t *load = event_at(load_idx);
      if (!load || load->kind != 9u || load->is_write) continue;
      if (load->c != ptr_value) continue;
      if (load->b != sizeof(void *) && load->b != 4u && load->b != 8u)
        continue;
      int score = address_in_live_object((uintptr_t)load->a, (size_t)load->b);
      if (score > selected_load_score) {
        selected_load = load;
        selected_load_idx = load_idx;
        selected_load_score = score;
        if (score > 0) break;
      }
    }

    if (selected_load) {
      formtrig_event_t *load = selected_load;
      uint32_t load_idx = selected_load_idx;

      uint32_t store_idx = load_idx;
      for (uint32_t idx = load_idx; idx-- > oldest;) {
        formtrig_event_t *store = event_at(idx);
        if (!store || store->kind != 9u || !store->is_write) continue;
        if (store->a != load->a) continue;
        store_idx = idx;
        break;
      }

      uint32_t linked = 0;
      double source_distance = FORMTRIG_INF;
      const formtrig_event_t *source = NULL;
      if (!sink_satisfied && ptr_value && store_idx >= load_idx) continue;

      if (!sink_satisfied && ptr_value) {
        source = latest_linked_null_cmp_before(store_idx, sink_satisfied,
                                               &linked, &source_distance,
                                               ptr_value);
      } else {
        if (store_idx < load_idx) {
          source = latest_linked_null_cmp_between(
              store_idx + 1u, load_idx, sink_satisfied, &linked,
              &source_distance, ptr_value);
        }
        if (!source)
          source = latest_linked_null_cmp_before(store_idx, sink_satisfied,
                                                 &linked, &source_distance,
                                                 ptr_value);
        if (!source)
          source = latest_linked_null_cmp_before(load_idx, sink_satisfied,
                                                 &linked, &source_distance,
                                                 ptr_value);
      }
      if (!source || !finite_distance(source_distance)) continue;

      g_state.lift_sink_site_id = cmp->site_id;
      g_state.lift_load_site_id = load->site_id;
      g_state.lift_store_site_id =
          store_idx < load_idx && event_at(store_idx) ? event_at(store_idx)->site_id : 0;
      g_state.lift_sink_ptr = ptr_value;
      g_state.lift_load_in_live_object = selected_load_score > 0 ? 1u : 0u;

      g_state.d_f_lifted = min_double(g_state.d_f_lifted, source_distance);
      if (g_state.d_f_lifted == source_distance)
        remember_df_source_with_distance(source, linked, 6u, source_distance);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 16u);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, cmp->site_id);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, load->site_id);
      g_state.trace_signature =
          fnv_mix_u64(g_state.trace_signature,
                      distance_bucket_for_signature(source_distance));
      return 1;
    }
  }

  return strict_reached_sink && saw_reached_null_sink ? -1 : 0;
}

static void synthesize_lifted_binary_distance(int sink_satisfied,
                                              int strict_reached_sink) {
  if (g_state.manual_lifted || !g_state.binary_sink) return;

  double best = FORMTRIG_INF;
  const formtrig_event_t *best_event = NULL;
  uint32_t linked = 0;
  uint32_t newest = g_state.ring_count;
  uint32_t oldest =
      newest > lift_window() ? newest - lift_window() : 0;

  g_state.lift_candidate_count = 0;
  g_state.lift_linked_count = 0;
  g_state.lift_reject_pointer_count = 0;
  g_state.lift_reject_zero_count = 0;
  g_state.lift_reject_noslice_count = 0;
  g_state.lift_reject_prereach_count = 0;
  g_state.lift_sink_site_id = 0;
  g_state.lift_load_site_id = 0;
  g_state.lift_store_site_id = 0;
  g_state.lift_sink_ptr = 0;
  g_state.lift_load_in_live_object = 0;
  g_state.lift_debug_candidate_count = 0;

  int null_lift =
      synthesize_null_pointer_producer_lift(sink_satisfied, strict_reached_sink);
  if (null_lift > 0) return;

  for (uint32_t idx = oldest; idx < newest; idx++) {
    formtrig_event_t *event = event_at(idx);
    if (!event || event->kind != 7u) continue;
    g_state.lift_candidate_count++;
    if (!finite_distance(event->distance)) {
      remember_lift_candidate(event, 2u);
      continue;
    }
    if (cmp_is_null_pointer_distance(event)) {
      g_state.lift_reject_pointer_count++;
      remember_lift_candidate(event, 3u);
      continue;
    }
    if (!sink_satisfied && event->distance == 0.0) {
      g_state.lift_reject_zero_count++;
      remember_lift_candidate(event, 4u);
      continue;
    }
    if (!cmp_has_dynamic_slice(idx, event)) {
      g_state.lift_reject_noslice_count++;
      remember_lift_candidate(event, 5u);
      continue;
    }
    remember_lift_candidate(event, 0u);
    linked++;
    g_state.lift_linked_count++;
    best_event = event;
    best = event->distance;
  }

  if (linked && finite_distance(best)) {
    g_state.d_f_lifted = min_double(g_state.d_f_lifted, best);
    if (g_state.d_f_lifted == best) remember_df_source(best_event, linked, 1u);
    g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 13u);
    g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, linked);
    g_state.trace_signature =
        fnv_mix_u64(g_state.trace_signature, distance_bucket_for_signature(best));
  }
}

static int event_loads_pointer_field(const formtrig_event_t *event) {
  if (!event || event->kind != 9u || event->is_write) return 0;
  if (event->b != sizeof(void *) && event->b != 4u && event->b != 8u)
    return 0;
  if (event->c <= 4096u) return 0;
  return address_in_live_object((uintptr_t)event->a, (size_t)event->b);
}

static int synthesize_live_pointer_producer_lift(void) {
  if (!source_objective_enabled() || !g_state.reached || g_state.manual_lifted)
    return 0;

  uint32_t newest = g_state.ring_count;
  if (!newest) return 0;
  uint32_t oldest =
      newest > lift_window() ? newest - lift_window() : 0;
  uint32_t scan_start = g_state.target_epoch_start > oldest
                            ? g_state.target_epoch_start
                            : oldest;

  const formtrig_event_t *best_source = NULL;
  double best_distance = FORMTRIG_INF;
  uint32_t best_linked = 0;
  uint32_t best_load_site = 0;
  uint32_t best_store_site = 0;
  uint64_t best_ptr = 0;

  for (uint32_t load_idx = scan_start; load_idx < newest; load_idx++) {
    formtrig_event_t *load = event_at(load_idx);
    if (!event_loads_pointer_field(load)) continue;

    uint32_t store_idx = load_idx;
    const formtrig_event_t *store_event = NULL;
    for (uint32_t idx = load_idx; idx-- > oldest;) {
      formtrig_event_t *store = event_at(idx);
      if (!store || store->kind != 9u || !store->is_write) continue;
      if (store->a != load->a || store->b != load->b) continue;
      store_idx = idx;
      store_event = store;
      break;
    }
    if (!store_event) continue;

    uint32_t linked = 0;
    double source_distance = FORMTRIG_INF;
    const formtrig_event_t *source =
        latest_linked_null_cmp_before(store_idx, 0, &linked, &source_distance,
                                      load->c);
    if (!source || !finite_distance(source_distance)) continue;

    if (source_distance < best_distance) {
      best_source = source;
      best_distance = source_distance;
      best_linked = linked;
      best_load_site = load->site_id;
      best_store_site = store_event->site_id;
      best_ptr = load->c;
    }
  }

  if (!best_source) return 0;

  g_state.lift_sink_site_id = 0;
  g_state.lift_load_site_id = best_load_site;
  g_state.lift_store_site_id = best_store_site;
  g_state.lift_sink_ptr = best_ptr;
  g_state.lift_load_in_live_object = 1u;
  g_state.lift_linked_count += best_linked;

  g_state.d_f_lifted = min_double(g_state.d_f_lifted, best_distance);
  if (g_state.d_f_lifted == best_distance)
    remember_df_source_with_distance(best_source, best_linked, 7u,
                                     best_distance);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 17u);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, best_load_site);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, best_store_site);
  g_state.trace_signature =
      fnv_mix_u64(g_state.trace_signature,
                  distance_bucket_for_signature(best_distance));
  return 1;
}

static uint64_t bit_mask(unsigned bit_width) {
  if (bit_width == 0) return 0;
  if (bit_width >= 64) return UINT64_MAX;
  return (1ULL << bit_width) - 1ULL;
}

static double cmp_distance(uint32_t predicate, uint64_t lhs, uint64_t rhs,
                           uint8_t outcome) {
  if (outcome) return 0.0;

  switch (predicate) {
    case 32: /* ICMP_EQ */
      return lhs > rhs ? u64_to_double_saturated(lhs - rhs)
                       : u64_to_double_saturated(rhs - lhs);
    case 33: /* ICMP_NE */
      return lhs == rhs ? 1.0 : 0.0;
    case 34: /* ICMP_UGT */
    case 38: /* ICMP_SGT, approximated on raw values */
      return lhs > rhs ? 0.0 : u64_to_double_saturated(rhs - lhs + 1ULL);
    case 35: /* ICMP_UGE */
    case 39: /* ICMP_SGE */
      return lhs >= rhs ? 0.0 : u64_to_double_saturated(rhs - lhs);
    case 36: /* ICMP_ULT */
    case 40: /* ICMP_SLT */
      return lhs < rhs ? 0.0 : u64_to_double_saturated(lhs - rhs + 1ULL);
    case 37: /* ICMP_ULE */
    case 41: /* ICMP_SLE */
      return lhs <= rhs ? 0.0 : u64_to_double_saturated(lhs - rhs);
    default:
      return outcome ? 0.0 : 1.0;
  }
}

static uint32_t negate_predicate(uint32_t predicate) {
  switch (predicate) {
    case 32: return 33; /* eq -> ne */
    case 33: return 32; /* ne -> eq */
    case 34: return 37; /* ugt -> ule */
    case 35: return 36; /* uge -> ult */
    case 36: return 35; /* ult -> uge */
    case 37: return 34; /* ule -> ugt */
    case 38: return 41; /* sgt -> sle */
    case 39: return 40; /* sge -> slt */
    case 40: return 39; /* slt -> sge */
    case 41: return 38; /* sle -> sgt */
    default: return 0;
  }
}

static double cmp_distance_to_true(uint32_t predicate, uint64_t lhs,
                                   uint64_t rhs) {
  return cmp_distance(predicate, lhs, rhs, 0);
}

static double cmp_flip_distance(const formtrig_event_t *event) {
  if (!event || event->kind != 7u) return FORMTRIG_INF;
  uint32_t predicate = cmp_predicate(event);
  uint32_t target_predicate =
      cmp_outcome(event) ? negate_predicate(predicate) : predicate;
  if (!target_predicate) return FORMTRIG_INF;
  return cmp_distance_to_true(target_predicate, event->a, event->b);
}

static int double_to_u64_exactish(double value, uint64_t *out) {
  if (value <= 0.0 || value >= 18446744073709551615.0) return 0;
  *out = (uint64_t)value;
  return 1;
}

static uint32_t arith_boundary_bits(const formtrig_event_t *event) {
  uint64_t distance;
  uint64_t sum;
  uint64_t mask;
  uint32_t bits = 0;

  if (!event || event->kind != 11u) return 0;
  if (!double_to_u64_exactish(event->distance, &distance)) return 0;
  if (UINT64_MAX - event->a < event->b) return 0;
  sum = event->a + event->b;
  if (UINT64_MAX - sum < distance || sum + distance == 0) return 0;
  mask = sum + distance - 1u;
  do {
    bits++;
    mask >>= 1;
  } while (mask);
  return bits;
}

static int post_reach_fallback_rank(const formtrig_event_t *event) {
  if (!event || !event->after_reach ||
      !informative_safety_distance(event->distance))
    return 1000;

  int input_linked = event->input_len || event->has_dynamic_producer == 2u;
  int target_site = target_site_matches(event->site_id);
  if (event->distance == 0.0) {
    if (target_site &&
        (event->kind == 7u || event->kind == 10u || event->kind == 11u))
      return input_linked ? 0 : 1;
    return 1000;
  }

  switch (event->kind) {
    case 7u:  /* compare */
      if (target_site) return input_linked ? 0 : 2;
      return input_linked ? 3 : 6;
    case 10u: /* div/mod */
      if (target_site) return input_linked ? 0 : 1;
      return input_linked ? 4 : 5;
    case 11u: { /* arithmetic */
      uint32_t bits = arith_boundary_bits(event);
      if (target_site) {
        if (!input_linked && bits > 0 && bits <= 16) return 5;
        return input_linked ? 0 : 1;
      }
      return input_linked ? 4 : 5;
    }
    case 9u: /* memory margin */
      if (event->distance <= 1.0) return 1000;
      return input_linked ? 7 : 8;
    case 8u: /* branch */
      return 9;
    default:
      return 1000;
  }
}

static int synthesize_post_reach_margin_fallback(void) {
  if (!source_target_site_mode() || !g_state.reached || g_state.manual_lifted)
    return 0;
  if (g_state.d_f_lifted < FORMTRIG_INF / 2.0) return 0;

  uint32_t newest = g_state.ring_count;
  if (!newest) return 0;
  uint32_t oldest =
      newest > lift_window() ? newest - lift_window() : 0;
  uint32_t scan_start = g_state.target_epoch_start > oldest
                            ? g_state.target_epoch_start
                            : oldest;

  const formtrig_event_t *best_event = NULL;
  double best_distance = FORMTRIG_INF;
  int best_rank = 1000;

  for (uint32_t idx = scan_start; idx < newest; idx++) {
    formtrig_event_t *event = event_at(idx);
    int rank = post_reach_fallback_rank(event);
    if (rank >= 1000) continue;
    if (rank > best_rank) continue;
    if (rank == best_rank) {
      uint32_t event_bits = arith_boundary_bits(event);
      uint32_t best_bits = arith_boundary_bits(best_event);
      if (event_bits || best_bits) {
        if (event_bits < best_bits) continue;
        if (event_bits == best_bits && event->distance >= best_distance)
          continue;
      } else if (event->distance >= best_distance) {
        continue;
      }
    }
    best_event = event;
    best_distance = event->distance;
    best_rank = rank;
  }

  if (!best_event || !finite_distance(best_distance)) return 0;

  g_state.d_f_lifted = best_distance;
  remember_df_source_with_distance(best_event, 1u, 8u, best_distance);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 18u);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature,
                                        (uint64_t)(uint32_t)best_rank);
  g_state.trace_signature =
      fnv_mix_u64(g_state.trace_signature,
                  distance_bucket_for_signature(best_distance));
  return 1;
}

static double final_df(void) {
  double df = FORMTRIG_INF;
  int lifted_valid = g_state.d_f_lifted < FORMTRIG_INF / 2.0;
  int direct_valid = g_state.d_f_direct < FORMTRIG_INF / 2.0;
  int direct_zero = direct_valid && g_state.d_f_direct == 0.0;
  int lifted_zero = lifted_valid && g_state.d_f_lifted == 0.0;
  int direct_zero_confirmed =
      direct_zero && (g_state.manual_direct || g_state.crash_predicate);
  int lifted_zero_confirmed =
      lifted_zero && (g_state.manual_lifted || g_state.crash_predicate);
  /* A zero sub-signal is terminal only after the TC oracle confirms it. */
  double direct_df =
      direct_zero && !direct_zero_confirmed ? 1.0 : g_state.d_f_direct;
  double lifted_df =
      lifted_zero && !lifted_zero_confirmed ? 1.0 : g_state.d_f_lifted;

  if (g_state.binary_sink) {
    if (lifted_valid)
      df = min_double(df, lifted_df);
    else if (g_state.manual_direct && direct_valid)
      df = min_double(df, direct_df);
  } else {
    if (direct_valid && g_state.d_f_direct_kind != FORMTRIG_DIRECT_MEM)
      df = min_double(df, direct_df);
    if (lifted_valid)
      df = min_double(df, lifted_df);
    if (df >= FORMTRIG_INF / 2.0 && direct_valid)
      df = min_double(df, direct_df);
  }

  if (df >= FORMTRIG_INF / 2.0)
    return g_state.reached ? 1.0 : FORMTRIG_INF;

  return df;
}

static formtrig_shm_record_t *dedicated_shm_record(void) {
  if (!g_dedicated_shm_checked) {
    g_dedicated_shm_checked = 1;
    const char *path = getenv(FORMTRIG_SHM_ENV_VAR);
    if (path && path[0]) {
      int fd = shm_open(path, O_RDWR, 0);
      if (fd >= 0) {
        void *map = mmap(NULL, FORMTRIG_SHM_SIZE, PROT_READ | PROT_WRITE,
                         MAP_SHARED, fd, 0);
        close(fd);
        if (map != MAP_FAILED)
          g_dedicated_shm_record = (formtrig_shm_record_t *)map;
      }
    }
  }

  return g_dedicated_shm_record;
}

static formtrig_shm_record_t *shm_record(void) {
  formtrig_shm_record_t *dedicated = dedicated_shm_record();
  if (dedicated) return dedicated;
  if (&__afl_area_ptr == NULL || __afl_area_ptr == NULL) return NULL;
  return (formtrig_shm_record_t *)(void *)(__afl_area_ptr + FORMTRIG_SHM_OFFSET);
}

static void clear_shm(void) {
  formtrig_shm_record_t *rec = shm_record();
  if (!rec) return;

  memset(rec, 0, sizeof(*rec));
  rec->magic = FORMTRIG_SHM_MAGIC;
  rec->version = FORMTRIG_SHM_VERSION;
  rec->d_t = FORMTRIG_INF;
  rec->d_f = FORMTRIG_INF;
  rec->d_f_lifted = -1.0;
  rec->trace_signature = 1469598103934665603ULL;
}

static uint64_t component_source_id(uint32_t kind, uint32_t site_id,
                                    uint32_t aux) {
  uint64_t sig = 1469598103934665603ULL;
  sig = fnv_mix_u64(sig, kind);
  sig = fnv_mix_u64(sig, site_id);
  sig = fnv_mix_u64(sig, aux);
  return sig;
}

static void state_record_component(uint32_t kind, uint32_t atom_id,
                                   uint32_t priority, uint32_t flags,
                                   uint64_t source_id, uint64_t context_hash,
                                   double value, double confidence) {
  if (g_state.component_count >= FORMTRIG_MAX_PROGRESS_COMPONENTS) return;
  if (!isfinite(value) || value <= -FORMTRIG_INF / 2.0 ||
      value >= FORMTRIG_INF / 2.0)
    return;

  uint32_t direction = flags & (FORMTRIG_COMPONENT_LOWER_IS_BETTER |
                                FORMTRIG_COMPONENT_HIGHER_IS_BETTER);
  if (direction != FORMTRIG_COMPONENT_LOWER_IS_BETTER &&
      direction != FORMTRIG_COMPONENT_HIGHER_IS_BETTER)
    return;

  if (confidence < 0.0) confidence = 0.0;
  if (confidence > 1.0) confidence = 1.0;
  if (kind == FORMTRIG_COMPONENT_OPERAND_INFLUENCE)
    flags |= FORMTRIG_COMPONENT_INPUT_INFLUENCE;
  if (!source_id) source_id = component_source_id(kind, atom_id, priority);
  if (!context_hash) context_hash = component_source_id(kind, atom_id, priority);

  formtrig_progress_component_t *component =
      &g_state.components[g_state.component_count++];
  component->kind = kind;
  component->atom_id = atom_id;
  component->priority = priority;
  component->flags = flags | FORMTRIG_COMPONENT_TC_ROOTED;
  component->source_id = source_id;
  component->context_hash = context_hash;
  component->value = value;
  component->confidence = confidence;

  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 20u);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, kind);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, source_id);
  g_state.trace_signature =
      fnv_mix_u64(g_state.trace_signature, distance_bucket_for_signature(value));
}

static void publish_component(formtrig_shm_record_t *rec, uint32_t kind,
                              uint32_t atom_id, uint32_t priority,
                              uint32_t flags, uint64_t source_id,
                              uint64_t context_hash, double value,
                              double confidence) {
  if (!rec || rec->component_count >= FORMTRIG_MAX_PROGRESS_COMPONENTS) return;
  if (!isfinite(value) || value <= -FORMTRIG_INF / 2.0 ||
      value >= FORMTRIG_INF / 2.0)
    return;
  if (kind == FORMTRIG_COMPONENT_OPERAND_INFLUENCE)
    flags |= FORMTRIG_COMPONENT_INPUT_INFLUENCE;

  formtrig_progress_component_t *component =
      &rec->components[rec->component_count++];
  component->kind = kind;
  component->atom_id = atom_id;
  component->priority = priority;
  component->flags = flags | FORMTRIG_COMPONENT_TC_ROOTED;
  component->source_id = source_id;
  component->context_hash = context_hash;
  component->value = value;
  component->confidence = confidence;
}

static int parse_u32_token(const char *token, uint32_t *out) {
  if (!token || !out) return 0;
  if (strcmp(token, "*") == 0) {
    *out = FORMTRIG_SPEC_WILDCARD;
    return 1;
  }
  char *end = NULL;
  unsigned long value = strtoul(token, &end, 0);
  if (end == token || *end != '\0' || value > UINT32_MAX) return 0;
  *out = (uint32_t)value;
  return 1;
}

static int parse_u64_token(const char *token, uint64_t *out) {
  if (!token || !out) return 0;
  char *end = NULL;
  unsigned long long value = strtoull(token, &end, 0);
  if (end == token || *end != '\0') return 0;
  *out = (uint64_t)value;
  return 1;
}

static int parse_double_token(const char *token, double *out) {
  if (!token || !out) return 0;
  char *end = NULL;
  double value = strtod(token, &end);
  if (end == token || *end != '\0' || !isfinite(value)) return 0;
  *out = value;
  return 1;
}

static uint32_t parse_direction_token(const char *token) {
  if (!token) return 0;
  if (strcmp(token, "lower") == 0 || strcmp(token, "lt") == 0 ||
      strcmp(token, "-") == 0 || strcmp(token, "1") == 0)
    return FORMTRIG_COMPONENT_LOWER_IS_BETTER;
  if (strcmp(token, "higher") == 0 || strcmp(token, "gt") == 0 ||
      strcmp(token, "+") == 0 || strcmp(token, "2") == 0)
    return FORMTRIG_COMPONENT_HIGHER_IS_BETTER;
  return 0;
}

static uint32_t parse_value_mode_token(const char *token) {
  if (!token) return UINT32_MAX;
  if (strcmp(token, "const") == 0 || strcmp(token, "value") == 0 ||
      strcmp(token, "0") == 0)
    return FORMTRIG_SPEC_VALUE_CONST;
  if (strcmp(token, "distance") == 0 || strcmp(token, "dist") == 0 ||
      strcmp(token, "1") == 0)
    return FORMTRIG_SPEC_VALUE_DISTANCE;
  if (strcmp(token, "hit") == 0 || strcmp(token, "2") == 0)
    return FORMTRIG_SPEC_VALUE_HIT;
  if (strcmp(token, "outcome") == 0 || strcmp(token, "3") == 0)
    return FORMTRIG_SPEC_VALUE_OUTCOME;
  if (strcmp(token, "not_outcome") == 0 || strcmp(token, "not-outcome") == 0 ||
      strcmp(token, "4") == 0)
    return FORMTRIG_SPEC_VALUE_NOT_OUTCOME;
  if (strcmp(token, "a") == 0 || strcmp(token, "5") == 0)
    return FORMTRIG_SPEC_VALUE_A;
  if (strcmp(token, "b") == 0 || strcmp(token, "6") == 0)
    return FORMTRIG_SPEC_VALUE_B;
  if (strcmp(token, "c") == 0 || strcmp(token, "7") == 0)
    return FORMTRIG_SPEC_VALUE_C;
  return UINT32_MAX;
}

static char *next_spec_token(char **saveptr) {
  return strtok_r(NULL, " \t\r\n,", saveptr);
}

static void load_probe_spec_line(char *line) {
  char *comment = strchr(line, '#');
  if (comment) *comment = '\0';

  char *saveptr = NULL;
  char *op = strtok_r(line, " \t\r\n,", &saveptr);
  if (!op || !*op) return;
  if (g_probe_spec_count >= FORMTRIG_PROBE_SPEC_CAP) return;

  formtrig_probe_spec_t spec;
  memset(&spec, 0, sizeof(spec));
  spec.confidence = 1.0;

  if (strcmp(op, "component") == 0 || strcmp(op, "event") == 0) {
    char *event_kind = next_spec_token(&saveptr);
    char *site_id = next_spec_token(&saveptr);
    char *component_kind = next_spec_token(&saveptr);
    char *atom_id = next_spec_token(&saveptr);
    char *priority = next_spec_token(&saveptr);
    char *direction = next_spec_token(&saveptr);
    char *value_mode = next_spec_token(&saveptr);
    char *value = next_spec_token(&saveptr);
    char *confidence = next_spec_token(&saveptr);

    spec.kind = FORMTRIG_SPEC_EVENT;
    if (!parse_u32_token(event_kind, &spec.event_kind) ||
        !parse_u32_token(site_id, &spec.site_id) ||
        !parse_u32_token(component_kind, &spec.component_kind) ||
        !parse_u32_token(atom_id, &spec.atom_id) ||
        !parse_u32_token(priority, &spec.priority))
      return;
    spec.direction_flag = parse_direction_token(direction);
    spec.value_mode = parse_value_mode_token(value_mode);
    if (!spec.direction_flag || spec.value_mode == UINT32_MAX) return;
    if (value && !parse_double_token(value, &spec.value)) return;
    if (confidence && !parse_double_token(confidence, &spec.confidence))
      return;

    char *source_id = next_spec_token(&saveptr);
    char *context_hash = next_spec_token(&saveptr);
    if (source_id && !parse_u64_token(source_id, &spec.source_id)) return;
    if (context_hash && !parse_u64_token(context_hash, &spec.context_hash))
      return;

    g_probe_specs[g_probe_spec_count++] = spec;
    return;
  }

  if (strcmp(op, "phase") == 0 || strcmp(op, "prefix") == 0) {
    char *event_kind = next_spec_token(&saveptr);
    char *site_id = next_spec_token(&saveptr);
    char *component_kind = next_spec_token(&saveptr);
    char *atom_id = next_spec_token(&saveptr);
    char *priority = next_spec_token(&saveptr);
    char *phase_index = next_spec_token(&saveptr);
    char *confidence = next_spec_token(&saveptr);

    spec.kind = FORMTRIG_SPEC_PHASE;
    spec.direction_flag = FORMTRIG_COMPONENT_HIGHER_IS_BETTER;
    spec.value_mode = FORMTRIG_SPEC_VALUE_HIT;
    if (!parse_u32_token(event_kind, &spec.event_kind) ||
        !parse_u32_token(site_id, &spec.site_id) ||
        !parse_u32_token(component_kind, &spec.component_kind) ||
        !parse_u32_token(atom_id, &spec.atom_id) ||
        !parse_u32_token(priority, &spec.priority) ||
        !parse_u32_token(phase_index, &spec.phase_index))
      return;
    if (!spec.phase_index) return;
    if (confidence && !parse_double_token(confidence, &spec.confidence))
      return;

    char *context_hash = next_spec_token(&saveptr);
    if (context_hash && !parse_u64_token(context_hash, &spec.context_hash))
      return;

    g_probe_specs[g_probe_spec_count++] = spec;
    return;
  }

  if (strcmp(op, "range") == 0 || strcmp(op, "hot_range") == 0 ||
      strcmp(op, "hot-range") == 0) {
    char *event_kind = next_spec_token(&saveptr);
    char *site_id = next_spec_token(&saveptr);
    char *start = next_spec_token(&saveptr);
    char *len = next_spec_token(&saveptr);
    char *influence = next_spec_token(&saveptr);

    spec.kind = FORMTRIG_SPEC_RANGE;
    spec.value = 1.0;
    if (!parse_u32_token(event_kind, &spec.event_kind) ||
        !parse_u32_token(site_id, &spec.site_id) ||
        !parse_u32_token(start, &spec.range_start) ||
        !parse_u32_token(len, &spec.range_len))
      return;
    if (spec.range_start == FORMTRIG_SPEC_WILDCARD ||
        spec.range_len == FORMTRIG_SPEC_WILDCARD || !spec.range_len)
      return;
    if (influence && !parse_double_token(influence, &spec.value)) return;
    if (!isfinite(spec.value) || spec.value <= 0.0) return;

    g_probe_specs[g_probe_spec_count++] = spec;
  }
}

static void ensure_probe_specs_loaded(void) {
  if (g_probe_specs_loaded) return;
  g_probe_specs_loaded = 1;

  const char *path = getenv("FORMTRIG_LIFT_SPEC");
  if (!path || !*path) return;

  FILE *f = fopen(path, "r");
  if (!f) return;

  char line[512];
  while (fgets(line, sizeof(line), f))
    load_probe_spec_line(line);

  fclose(f);
}

static void reset_probe_spec_runtime_state(void) {
  ensure_probe_specs_loaded();
  for (uint32_t i = 0; i < g_probe_spec_count; i++) {
    g_probe_specs[i].phase_prefix = 0;
    if (g_probe_specs[i].kind == FORMTRIG_SPEC_RANGE &&
        g_probe_specs[i].event_kind == FORMTRIG_SPEC_WILDCARD &&
        g_probe_specs[i].site_id == FORMTRIG_SPEC_WILDCARD) {
      prioritize_hot_range(g_probe_specs[i].range_start,
                           g_probe_specs[i].range_len,
                           g_probe_specs[i].value);
    }
  }
}

static int probe_spec_matches(const formtrig_probe_spec_t *spec,
                              const formtrig_event_t *event) {
  if (!spec || !event || !event->after_reach) return 0;
  if (event->kind == 1u || event->kind == 2u) return 0;
  if (spec->event_kind != FORMTRIG_SPEC_WILDCARD &&
      spec->event_kind != event->kind)
    return 0;
  if (spec->site_id != FORMTRIG_SPEC_WILDCARD &&
      spec->site_id != event->site_id)
    return 0;
  return 1;
}

static double probe_spec_event_value(const formtrig_probe_spec_t *spec,
                                     const formtrig_event_t *event) {
  switch (spec->value_mode) {
    case FORMTRIG_SPEC_VALUE_CONST:
      return spec->value;
    case FORMTRIG_SPEC_VALUE_DISTANCE:
      return event->distance;
    case FORMTRIG_SPEC_VALUE_HIT:
      return 1.0;
    case FORMTRIG_SPEC_VALUE_OUTCOME:
      return event->kind == 7u || event->kind == 8u
                 ? (double)(event->kind == 7u ? cmp_outcome(event) : event->a)
                 : 0.0;
    case FORMTRIG_SPEC_VALUE_NOT_OUTCOME:
      return event->kind == 7u || event->kind == 8u
                 ? ((event->kind == 7u ? cmp_outcome(event) : event->a) ? 0.0
                                                                        : 1.0)
                 : 0.0;
    case FORMTRIG_SPEC_VALUE_A:
      return u64_to_double_saturated(event->a);
    case FORMTRIG_SPEC_VALUE_B:
      return u64_to_double_saturated(event->b);
    case FORMTRIG_SPEC_VALUE_C:
      return u64_to_double_saturated(event->c);
    default:
      return FORMTRIG_INF;
  }
}

static void state_record_component_best(uint32_t kind, uint32_t atom_id,
                                        uint32_t priority, uint32_t flags,
                                        uint64_t source_id,
                                        uint64_t context_hash, double value,
                                        double confidence) {
  if (!isfinite(value) || value < 0.0 || value >= FORMTRIG_INF / 2.0)
    return;
  if (!source_id) source_id = component_source_id(kind, atom_id, priority);
  if (!context_hash) context_hash = component_source_id(kind, atom_id, priority);

  for (uint32_t i = 0; i < g_state.component_count; i++) {
    formtrig_progress_component_t *component = &g_state.components[i];
    if (component->kind != kind || component->atom_id != atom_id ||
        component->source_id != source_id ||
        component->context_hash != context_hash)
      continue;

    int changed = 0;
    if ((flags & FORMTRIG_COMPONENT_LOWER_IS_BETTER) &&
        value < component->value) {
      component->value = value;
      changed = 1;
    }
    if ((flags & FORMTRIG_COMPONENT_HIGHER_IS_BETTER) &&
        value > component->value) {
      component->value = value;
      changed = 1;
    }
    if (confidence > component->confidence) {
      component->confidence = confidence;
      changed = 1;
    }
    if (changed) {
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 20u);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, kind);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, source_id);
      g_state.trace_signature = fnv_mix_u64(
          g_state.trace_signature, distance_bucket_for_signature(value));
    }
    return;
  }

  state_record_component(kind, atom_id, priority, flags, source_id,
                         context_hash, value, confidence);
}

static void record_probe_component(const formtrig_probe_spec_t *spec,
                                   const formtrig_event_t *event,
                                   double value) {
  uint64_t source_id = spec->source_id;
  uint64_t context_hash = spec->context_hash;
  if (!source_id) {
    if (spec->kind == FORMTRIG_SPEC_PHASE)
      source_id = component_source_id(spec->component_kind, spec->atom_id,
                                      spec->priority);
    else
      source_id = component_source_id(spec->component_kind, event->site_id,
                                      spec->atom_id);
  }
  if (!context_hash)
    context_hash = component_source_id(spec->component_kind, spec->atom_id,
                                       spec->priority);

  uint32_t flags = spec->direction_flag | FORMTRIG_COMPONENT_LIFTED;
  state_record_component_best(spec->component_kind, spec->atom_id,
                              spec->priority, flags, source_id, context_hash,
                              value, spec->confidence);
  g_state.manual_lifted = 1;
  if (event->input_len)
    prioritize_hot_range(event->input_start, event->input_len, 3.0);
}

static int probe_phase_same_group(const formtrig_probe_spec_t *a,
                                  const formtrig_probe_spec_t *b) {
  return a && b && a->kind == FORMTRIG_SPEC_PHASE &&
         b->kind == FORMTRIG_SPEC_PHASE &&
         a->component_kind == b->component_kind &&
         a->atom_id == b->atom_id && a->priority == b->priority &&
         a->context_hash == b->context_hash;
}

static uint32_t probe_phase_group_prefix(const formtrig_probe_spec_t *spec) {
  uint32_t prefix = 0;
  for (uint32_t i = 0; i < g_probe_spec_count; i++)
    if (probe_phase_same_group(spec, &g_probe_specs[i]) &&
        g_probe_specs[i].phase_prefix > prefix)
      prefix = g_probe_specs[i].phase_prefix;
  return prefix;
}

static void probe_phase_set_group_prefix(const formtrig_probe_spec_t *spec,
                                         uint32_t prefix) {
  for (uint32_t i = 0; i < g_probe_spec_count; i++)
    if (probe_phase_same_group(spec, &g_probe_specs[i]))
      g_probe_specs[i].phase_prefix = prefix;
}

static void apply_probe_specs_to_event(const formtrig_event_t *event) {
  ensure_probe_specs_loaded();
  if (!g_probe_spec_count || !event) return;

  for (uint32_t i = 0; i < g_probe_spec_count; i++) {
    formtrig_probe_spec_t *spec = &g_probe_specs[i];
    if (!probe_spec_matches(spec, event)) continue;

    if (spec->kind == FORMTRIG_SPEC_EVENT) {
      double value = probe_spec_event_value(spec, event);
      record_probe_component(spec, event, value);
      continue;
    }

    if (spec->kind == FORMTRIG_SPEC_PHASE) {
      uint32_t prefix = probe_phase_group_prefix(spec);
      if (prefix + 1u == spec->phase_index) {
        probe_phase_set_group_prefix(spec, spec->phase_index);
        record_probe_component(spec, event, (double)spec->phase_index);
      }
      continue;
    }

    if (spec->kind == FORMTRIG_SPEC_RANGE) {
      prioritize_hot_range(spec->range_start, spec->range_len, spec->value);
    }
  }
}

static void publish_shm(void) {
  if (!g_state.reached) return;
  if (!g_state.finalized && !g_state.crash_predicate && !publish_eager())
    return;

  formtrig_shm_record_t *rec = shm_record();
  if (!rec) return;

  memset(rec, 0, sizeof(*rec));
  rec->magic = FORMTRIG_SHM_MAGIC;
  rec->version = FORMTRIG_SHM_VERSION;
  rec->flags = 0;
  if (g_state.reached) rec->flags |= FORMTRIG_FLAG_REACHED;
  if (g_state.crash_predicate) rec->flags |= FORMTRIG_FLAG_CRASH_PREDICATE;
  if (g_state.d_f_lifted < FORMTRIG_INF / 2.0) rec->flags |= FORMTRIG_FLAG_LIFTED;
  rec->target_hit_count = g_state.target_hit_count;
  rec->trace_signature = g_state.trace_signature;
  rec->d_t = g_state.d_t < FORMTRIG_INF / 2.0
                 ? g_state.d_t
                 : (g_state.reached ? 1.0 : FORMTRIG_INF);
  rec->d_f = final_df();
  rec->d_f_lifted = g_state.d_f_lifted < FORMTRIG_INF / 2.0
                        ? g_state.d_f_lifted
                        : -1.0;
  rec->hot_range_count = g_state.hot_range_count;
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    formtrig_progress_component_t *component = &g_state.components[i];
    if (component->flags & FORMTRIG_COMPONENT_LIFTED)
      rec->flags |= FORMTRIG_FLAG_LIFTED;
    publish_component(rec, component->kind, component->atom_id,
                      component->priority, component->flags,
                      component->source_id, component->context_hash,
                      component->value, component->confidence);
  }
  if (g_state.df_source.mode) {
    rec->source.kind = g_state.df_source.kind;
    rec->source.site_id = g_state.df_source.site_id;
    rec->source.predicate = g_state.df_source.predicate;
    rec->source.outcome = g_state.df_source.outcome;
    rec->source.after_reach = g_state.df_source.after_reach;
    rec->source.mode = g_state.df_source.mode;
    rec->source.linked_count = g_state.df_source.linked_count;
    rec->source.a = g_state.df_source.a;
    rec->source.b = g_state.df_source.b;
    rec->source.distance = g_state.df_source.distance;
  }
  memcpy(rec->hot_ranges, g_state.hot_ranges,
         sizeof(formtrig_hot_range_t) * g_state.hot_range_count);

  if (rec->d_t < FORMTRIG_INF / 2.0) {
    publish_component(
        rec, FORMTRIG_COMPONENT_NATIVE_DISTANCE, 0u, 10u,
        FORMTRIG_COMPONENT_LOWER_IS_BETTER | FORMTRIG_COMPONENT_NATIVE,
        component_source_id(FORMTRIG_COMPONENT_NATIVE_DISTANCE,
                            g_state.df_source.site_id,
                            g_state.df_source.predicate),
        component_source_id(FORMTRIG_COMPONENT_NATIVE_DISTANCE,
                            g_state.df_source.site_id,
                            g_state.df_source.predicate),
        rec->d_t, 1.0);
  }

  if (g_state.d_f_lifted < FORMTRIG_INF / 2.0) {
    publish_component(
        rec, FORMTRIG_COMPONENT_LIFTED_DISTANCE, 0u, 10u,
        FORMTRIG_COMPONENT_LOWER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED,
        component_source_id(FORMTRIG_COMPONENT_LIFTED_DISTANCE,
                            g_state.df_source.site_id,
                            g_state.df_source.mode),
        component_source_id(FORMTRIG_COMPONENT_LIFTED_DISTANCE,
                            g_state.df_source.site_id,
                            g_state.df_source.mode),
        g_state.d_f_lifted, 1.0);
  }

  if (g_state.df_source.mode && g_state.df_source.mode != 4u &&
      g_state.df_source.distance < FORMTRIG_INF / 2.0) {
    publish_component(
        rec, FORMTRIG_COMPONENT_BOUNDARY_MARGIN, 0u, 20u,
        FORMTRIG_COMPONENT_LOWER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED,
        component_source_id(FORMTRIG_COMPONENT_BOUNDARY_MARGIN,
                            g_state.df_source.site_id,
                            g_state.df_source.kind),
        component_source_id(FORMTRIG_COMPONENT_BOUNDARY_MARGIN,
                            g_state.df_source.site_id,
                            g_state.df_source.kind),
        g_state.df_source.distance,
        g_state.df_source.linked_count ? 0.9 : 0.5);
  }

  if (g_state.hot_range_count) {
    double max_influence = 0.0;
    uint32_t best_start = 0u;
    uint32_t best_len = 0u;
    for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
      if (g_state.hot_ranges[i].influence > max_influence) {
        max_influence = g_state.hot_ranges[i].influence;
        best_start = g_state.hot_ranges[i].start;
        best_len = g_state.hot_ranges[i].len;
      }
    }
    if (max_influence > 0.0) {
      publish_component(
          rec, FORMTRIG_COMPONENT_OPERAND_INFLUENCE, 0u, 40u,
          FORMTRIG_COMPONENT_HIGHER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED |
              FORMTRIG_COMPONENT_INPUT_INFLUENCE,
          component_source_id(FORMTRIG_COMPONENT_OPERAND_INFLUENCE,
                              best_start, best_len),
          component_source_id(FORMTRIG_COMPONENT_OPERAND_INFLUENCE,
                              best_start, best_len),
          max_influence, 0.8);
    }
  }
}

static void json_write_escaped(FILE *f, const char *s) {
  fputc('"', f);
  if (s) {
    for (; *s; s++) {
      if (*s == '"' || *s == '\\') fputc('\\', f);
      fputc(*s, f);
    }
  }
  fputc('"', f);
}

static void write_jsonl(void) {
  const char *path = getenv("FORMTRIG_LOG");
  if (!path || !*path) return;

  FILE *f = NULL;
  if (strcmp(path, "-") == 0) {
    f = stdout;
  } else {
    f = fopen(path, "a");
    if (!f) return;
  }

  double d_t = g_state.d_t < FORMTRIG_INF / 2.0
                   ? g_state.d_t
                   : (g_state.reached ? 1.0 : FORMTRIG_INF);
  double d_f = final_df();

  fprintf(f,
          "{\"reached\":%s,\"crash_predicate\":%s,"
          "\"D_T\":%.17g,\"D_F\":%.17g,\"D_F_lifted\":",
          g_state.reached ? "true" : "false",
          g_state.crash_predicate ? "true" : "false", d_t, d_f);

  if (g_state.d_f_lifted < FORMTRIG_INF / 2.0)
    fprintf(f, "%.17g", g_state.d_f_lifted);
  else
    fprintf(f, "null");

  fprintf(f,
          ",\"trace_signature\":\"0x%016" PRIx64
          "\",\"target_hit_count\":%" PRIu32 ",\"hot_byte_ranges\":[",
          g_state.trace_signature, g_state.target_hit_count);

  for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
    if (i) fputc(',', f);
    fprintf(f, "{\"start\":%" PRIu32 ",\"len\":%" PRIu32
               ",\"influence\":%.17g}",
            g_state.hot_ranges[i].start, g_state.hot_ranges[i].len,
            g_state.hot_ranges[i].influence);
  }

  fprintf(f, "],\"df_source\":");
  if (g_state.df_source.mode) {
    fprintf(f,
            "{\"mode\":%" PRIu32 ",\"kind\":%" PRIu32
            ",\"site_id\":%" PRIu32 ",\"predicate\":%" PRIu32
            ",\"outcome\":%" PRIu32 ",\"after_reach\":%s,"
            "\"distance\":%.17g,\"a\":%" PRIu64 ",\"b\":%" PRIu64
            ",\"linked_count\":%" PRIu32 "}",
            (uint32_t)g_state.df_source.mode, g_state.df_source.kind,
            g_state.df_source.site_id, g_state.df_source.predicate,
            (uint32_t)g_state.df_source.outcome,
            g_state.df_source.after_reach ? "true" : "false",
            g_state.df_source.distance, g_state.df_source.a, g_state.df_source.b,
            g_state.df_source.linked_count);
  } else {
    fprintf(f, "null");
  }

  fprintf(f,
          ",\"lift_stats\":{\"candidates\":%" PRIu32
          ",\"linked\":%" PRIu32 ",\"reject_pointer\":%" PRIu32
          ",\"reject_zero\":%" PRIu32 ",\"reject_noslice\":%" PRIu32
          ",\"reject_prereach\":%" PRIu32 "}",
          g_state.lift_candidate_count, g_state.lift_linked_count,
          g_state.lift_reject_pointer_count, g_state.lift_reject_zero_count,
          g_state.lift_reject_noslice_count, g_state.lift_reject_prereach_count);

  fprintf(f,
          ",\"lift_context\":{\"sink_site_id\":%" PRIu32
          ",\"load_site_id\":%" PRIu32 ",\"store_site_id\":%" PRIu32
          ",\"sink_ptr\":%" PRIu64 ",\"load_in_live_object\":%" PRIu32 "}",
          g_state.lift_sink_site_id, g_state.lift_load_site_id,
          g_state.lift_store_site_id, g_state.lift_sink_ptr,
          (uint32_t)g_state.lift_load_in_live_object);

  if (debug_events()) {
    fprintf(f, ",\"lift_candidates\":[");
    for (uint32_t i = 0; i < g_state.lift_debug_candidate_count; i++) {
      formtrig_lift_candidate_t *c = &g_state.lift_candidates[i];
      if (i) fputc(',', f);
      fprintf(f,
              "{\"site_id\":%" PRIu32 ",\"predicate\":%" PRIu32
              ",\"reason\":%" PRIu32 ",\"outcome\":%" PRIu32
              ",\"after_reach\":%s,\"distance\":%.17g,"
              "\"a\":%" PRIu64 ",\"b\":%" PRIu64
              ",\"input_start\":%" PRIu32 ",\"input_len\":%" PRIu32 "}",
              c->site_id, c->predicate, c->reason, (uint32_t)c->outcome,
              c->after_reach ? "true" : "false", c->distance, c->a, c->b,
              c->input_start, c->input_len);
    }
    fprintf(f, "]");

    fprintf(f, ",\"debug_events\":[");
    uint32_t newest = g_state.ring_count;
    uint32_t event_window = debug_event_window();
    uint32_t oldest = newest > event_window ? newest - event_window : 0;
    uint32_t written = 0;
    for (uint32_t idx = oldest; idx < newest; idx++) {
      formtrig_event_t *event = event_at(idx);
      if (!event) continue;
      if (written++) fputc(',', f);
      fprintf(f,
              "{\"kind\":%" PRIu32 ",\"site_id\":%" PRIu32
              ",\"distance\":%.17g,\"a\":%" PRIu64 ",\"b\":%" PRIu64
              ",\"c\":%" PRIu64 ",\"after_reach\":%s,"
              "\"is_write\":%" PRIu32 ",\"has_dynamic_producer\":%" PRIu32
              ",\"site_class\":%" PRIu32
              ",\"input_start\":%" PRIu32 ",\"input_len\":%" PRIu32 "}",
              event->kind, event->site_id, event->distance, event->a, event->b,
              event->c, event->after_reach ? "true" : "false",
              (uint32_t)event->is_write,
              (uint32_t)event->has_dynamic_producer,
              (uint32_t)event->site_class, event->input_start,
              event->input_len);
    }
    fprintf(f, "]");
  }

  fprintf(f, ",\"labels\":");
  json_write_escaped(f, "runtime");
  fprintf(f, "}\n");

  if (f != stdout) fclose(f);
}

static void on_exit_finalize(void) {
  formtrig_finalize();
}

__attribute__((constructor)) static void formtrig_ctor(void) {
  formtrig_reset();
  atexit(on_exit_finalize);
}

void formtrig_reset(void) {
  reset_state(&g_state);
  __formtrig_active = 0;
  refresh_pre_reach_gate();
  __formtrig_suppress = 0;
  clear_shm();
}

void formtrig_suppress_begin(void) {
  if (__formtrig_suppress < UINT8_MAX) __formtrig_suppress++;
}

void formtrig_suppress_end(void) {
  if (__formtrig_suppress > 0) __formtrig_suppress--;
}

void formtrig_target_hit(const char *label) {
  if (!target_label_matches(label)) return;
  if (source_site_label(label) && !source_site_reach_enabled()) return;
  g_state.reached = 1;
  __formtrig_active = 1;
  __formtrig_pre_reach_enabled = 1;
  g_state.target_hit_count++;
  push_event(1u, g_state.target_hit_count, 0, 0, 0.0);
  g_state.target_epoch_start = g_state.ring_count;
  publish_shm();
}

void formtrig_crash_predicate(int satisfied, const char *label) {
  if (!target_label_matches(label)) return;
  if (lift_crash_predicate()) g_state.binary_sink = 1;
  if (satisfied) {
    g_state.crash_predicate = 1;
    g_state.d_t = 0.0;
  } else if (g_state.reached && g_state.d_t >= FORMTRIG_INF / 2.0) {
    g_state.d_t = 1.0;
  }
  push_event(2u, satisfied ? 1u : 0u, 0, 0, satisfied ? 0.0 : 1.0);
  if (lift_crash_predicate()) synthesize_lifted_binary_distance(satisfied, 1);
  if (debug_predicate_snapshot()) write_jsonl();
  publish_shm();
}

void formtrig_record_direct_binary(int satisfied) {
  g_state.binary_sink = 1;
  g_state.d_t = min_double(g_state.d_t, satisfied ? 0.0 : 1.0);
  g_state.d_f_direct = min_double(g_state.d_f_direct, satisfied ? 0.0 : 1.0);
  if (!g_state.df_source.mode || g_state.d_f_direct <= g_state.df_source.distance) {
    g_state.df_source.kind = 3u;
    g_state.df_source.site_id = 0;
    g_state.df_source.predicate = 0;
    g_state.df_source.linked_count = 0;
    g_state.df_source.a = satisfied ? 1u : 0u;
    g_state.df_source.b = 0;
    g_state.df_source.distance = satisfied ? 0.0 : 1.0;
    g_state.df_source.outcome = satisfied ? 1u : 0u;
    g_state.df_source.after_reach = g_state.reached ? 1u : 0u;
    g_state.df_source.mode = 4u;
  }
  push_event(3u, 0, satisfied ? 1u : 0u, 0, satisfied ? 0.0 : 1.0);
  synthesize_lifted_binary_distance(satisfied, 0);
  publish_shm();
}

void formtrig_record_direct_margin(double distance, const char *kind) {
  if (distance < 0.0) distance = 0.0;
  g_state.d_f_direct = distance;
  g_state.d_f_direct_kind = FORMTRIG_DIRECT_MANUAL;
  g_state.manual_direct = 1;
  g_state.df_source.kind = 4u;
  g_state.df_source.site_id = 0;
  g_state.df_source.predicate = 0;
  g_state.df_source.linked_count = 0;
  g_state.df_source.a = 0;
  g_state.df_source.b = 0;
  g_state.df_source.distance = distance;
  g_state.df_source.outcome = distance == 0.0 ? 1u : 0u;
  g_state.df_source.after_reach = g_state.reached ? 1u : 0u;
  g_state.df_source.mode = 2u;
  push_event(4u, 0, 0, 0, distance);
  publish_shm();
}

void formtrig_record_lifted_distance(double distance, const char *kind) {
  if (distance < 0.0) distance = 0.0;
  g_state.d_f_lifted = distance;
  g_state.manual_lifted = 1;
  g_state.df_source.kind = 12u;
  g_state.df_source.site_id = 0;
  g_state.df_source.predicate = 0;
  g_state.df_source.linked_count = 0;
  g_state.df_source.a = 0;
  g_state.df_source.b = 0;
  g_state.df_source.distance = distance;
  g_state.df_source.outcome = distance == 0.0 ? 1u : 0u;
  g_state.df_source.after_reach = g_state.reached ? 1u : 0u;
  g_state.df_source.mode = 3u;
  push_event(12u, 0, 0, 0, distance);
  publish_shm();
}

void formtrig_record_progress_component(uint32_t kind, uint32_t atom_id,
                                        uint32_t priority, uint32_t flags,
                                        uint64_t source_id,
                                        uint64_t context_hash, double value,
                                        double confidence) {
  state_record_component(kind, atom_id, priority, flags, source_id,
                         context_hash, value, confidence);
  if (flags & FORMTRIG_COMPONENT_LIFTED) g_state.manual_lifted = 1;
  publish_shm();
}

void formtrig_record_oob_margin(int64_t index, int64_t length, int64_t access_size) {
  double d = 0.0;
  if (length <= 0 || access_size <= 0) {
    d = 0.0;
  } else if (index < 0) {
    d = 0.0;
  } else if (index + access_size > length) {
    d = 0.0;
  } else {
    int64_t right = length - (index + access_size);
    int64_t left = index;
    int64_t m = left < right ? left : right;
    d = (double)m + 1.0;
  }
  formtrig_record_direct_margin(d, "oob");
}

void formtrig_record_divisor(int64_t divisor) {
  formtrig_record_direct_margin(abs_i64_as_double(divisor), "div_zero");
}

void formtrig_record_modular_add(uint64_t lhs, uint64_t rhs, unsigned bit_width) {
  uint64_t mask = bit_mask(bit_width);
  lhs &= mask;
  rhs &= mask;
  if (rhs > mask - lhs)
    formtrig_record_direct_margin(0.0, "mod_overflow");
  else
    formtrig_record_direct_margin(u64_to_double_saturated(mask - lhs - rhs + 1ULL),
                                  "mod_overflow");
}

void formtrig_record_null_sink(int is_null) {
  formtrig_record_direct_binary(is_null);
}

void formtrig_record_hot_range(uint32_t start, uint32_t len, double influence) {
  add_hot_range(start, len, influence);
  publish_shm();
}

void formtrig_register_input(const void *data, size_t len) {
  reset_state(&g_state);
  reset_probe_spec_runtime_state();
  __formtrig_active = 0;
  refresh_pre_reach_gate();
  __formtrig_suppress = 0;
  g_state.input_base = (uintptr_t)data;
  g_state.input_len = len;
  clear_shm();
}

void *__formtrig_malloc(size_t size, uint32_t site_id) {
  void *ptr = malloc(size);
  maybe_target_site_hit(site_id);
  if (__formtrig_suppress) return ptr;
  if (!__formtrig_active && !track_alloc_pre_reach()) return ptr;
  if (ptr) {
    for (uint32_t i = 0; i < FORMTRIG_OBJECT_CAP; i++) {
      if (!g_state.objects[i].live) {
        g_state.objects[i].base = (uintptr_t)ptr;
        g_state.objects[i].size = size;
        g_state.objects[i].live = 1;
        break;
      }
    }
  }
  push_event_full(5u, site_id, (uint64_t)(uintptr_t)ptr, (uint64_t)size, 0,
                  0.0, 0, 1);
  publish_shm();
  return ptr;
}

void __formtrig_free(void *ptr, uint32_t site_id) {
  maybe_target_site_hit(site_id);
  if (__formtrig_suppress) {
    free(ptr);
    return;
  }
  if (!__formtrig_active && !track_alloc_pre_reach()) {
    free(ptr);
    return;
  }
  for (uint32_t i = 0; i < FORMTRIG_OBJECT_CAP; i++) {
    if (g_state.objects[i].live && g_state.objects[i].base == (uintptr_t)ptr) {
      g_state.objects[i].live = 0;
      break;
    }
  }
  push_event_full(6u, site_id, (uint64_t)(uintptr_t)ptr, 0, 0, 0.0, 0, 1);
  publish_shm();
  free(ptr);
}

void __formtrig_log_cmp_ex(uint32_t site_id, uint32_t predicate, uint64_t lhs,
                           uint64_t rhs, uint8_t outcome,
                           uint32_t site_class) {
  if (__formtrig_suppress) {
    maybe_target_site_hit(site_id);
    return;
  }
  maybe_target_site_hit(site_id);
  int active = __formtrig_active;
  if (!active && !record_pre_reach_events()) return;
  uint32_t input_start = 0;
  uint32_t input_len = 0;
  uint32_t event_input_start = 0;
  uint32_t event_input_len = 0;
  uint8_t has_input = 0;
  if (lookup_value_provenance(lhs, &input_start, &input_len)) {
    add_hot_range(input_start, input_len, 1.0);
    event_input_start = input_start;
    event_input_len = input_len;
    has_input = 2u;
  }
  if (lookup_value_provenance(rhs, &input_start, &input_len)) {
    add_hot_range(input_start, input_len, 1.0);
    if (!event_input_len) {
      event_input_start = input_start;
      event_input_len = input_len;
    }
    has_input = 2u;
  }
  double d = cmp_distance(predicate, lhs, rhs, outcome);
  push_event_full_class_with_input(
      7u, site_id, lhs, rhs, ((uint64_t)predicate << 32) | outcome, d, 0,
      has_input, (uint8_t)(site_class & 0xffu), event_input_start,
      event_input_len);
  if (active) publish_shm();
}

void __formtrig_log_cmp(uint32_t site_id, uint32_t predicate, uint64_t lhs,
                        uint64_t rhs, uint8_t outcome) {
  __formtrig_log_cmp_ex(site_id, predicate, lhs, rhs, outcome, 0);
}

void __formtrig_log_branch(uint32_t site_id, uint8_t outcome) {
  if (__formtrig_suppress) {
    maybe_target_site_hit(site_id);
    return;
  }
  maybe_target_site_hit(site_id);
  int active = __formtrig_active;
  if (!active && !record_pre_reach_events()) return;
  push_event(8u, site_id, outcome, 0, outcome ? 0.0 : 1.0);
  if (active) publish_shm();
}

void __formtrig_log_mem_access(uint32_t site_id, const void *ptr, size_t size,
                               uint8_t is_write, uint64_t value) {
  if (__formtrig_suppress) {
    maybe_target_site_hit(site_id);
    return;
  }
  maybe_target_site_hit(site_id);
  int active = __formtrig_active;
  if (!active && !record_pre_reach_events()) return;
  uintptr_t p = (uintptr_t)ptr;
  uint32_t input_start = 0;
  uint32_t input_len = 0;
  int has_input = record_input_access(p, size, &input_start, &input_len);
  if (is_write) {
    uint32_t value_start = 0;
    uint32_t value_len = 0;
    if (lookup_value_provenance(value, &value_start, &value_len))
      remember_memory_provenance(p, size, value_start, value_len);
  } else if (has_input) {
    remember_value_provenance(value, input_start, input_len);
  }
  double best = FORMTRIG_INF;
  for (uint32_t i = 0; i < FORMTRIG_OBJECT_CAP; i++) {
    uintptr_t base = g_state.objects[i].base;
    if (!base) continue;
    uintptr_t end = base + g_state.objects[i].size;
    if (p >= base && p < end) {
      uintptr_t access_end = p + size;
      if (!g_state.objects[i].live || access_end > end) {
        best = 0.0;
      } else {
        uintptr_t left = p - base;
        uintptr_t right = end - access_end;
        uintptr_t m = left < right ? left : right;
        best = min_double(best, u64_to_double_saturated((uint64_t)m + 1ULL));
      }
    }
  }
  if (active && best < FORMTRIG_INF / 2.0 && !g_state.manual_direct) {
    g_state.d_f_direct = min_double(g_state.d_f_direct, best);
    if (g_state.d_f_direct == best) g_state.d_f_direct_kind = FORMTRIG_DIRECT_MEM;
  }
  if (active && best < FORMTRIG_INF / 2.0)
    remember_source_target_safety_margin(
        9u, site_id, is_write ? 1u : 0u, (uint64_t)p, (uint64_t)size, best,
        best == 0.0 ? 1u : 0u);
  push_event_full_class_with_input(
      9u, site_id, (uint64_t)p, (uint64_t)size, value,
      best < FORMTRIG_INF / 2.0 ? best : 1.0, is_write, has_input ? 2u : 1u,
      0, has_input ? input_start : 0, has_input ? input_len : 0);
  if (active) publish_shm();
}

void __formtrig_log_mem_transfer(uint32_t site_id, const void *dst,
                                 const void *src, size_t size) {
  if (__formtrig_suppress) {
    maybe_target_site_hit(site_id);
    return;
  }
  maybe_target_site_hit(site_id);
  int active = __formtrig_active;
  if (!active && !record_pre_reach_events()) return;
  uintptr_t d = (uintptr_t)dst;
  uintptr_t s = (uintptr_t)src;
  int bulk_input_setup =
      !active && g_state.input_base && s == g_state.input_base &&
      g_state.input_len > 64 && size >= g_state.input_len;
  if (!bulk_input_setup) {
    record_input_access(s, size, NULL, NULL);
    record_input_access(d, size, NULL, NULL);
  }
  propagate_transfer_provenance(d, s, size);
  push_event_full(15u, site_id, (uint64_t)d, (uint64_t)s, (uint64_t)size,
                  size ? (double)size : 0.0, 1, 1);
  if (active) publish_shm();
}

void __formtrig_log_div(uint32_t site_id, int64_t divisor) {
  if (__formtrig_suppress) {
    maybe_target_site_hit(site_id);
    return;
  }
  maybe_target_site_hit(site_id);
  int active = __formtrig_active;
  if (!active && !record_pre_reach_events()) return;
  double d = abs_i64_as_double(divisor);
  if (active && !g_state.manual_direct) {
    g_state.d_f_direct = min_double(g_state.d_f_direct, d);
    if (g_state.d_f_direct == d) g_state.d_f_direct_kind = FORMTRIG_DIRECT_DIV;
  }
  if (active)
    remember_source_target_safety_margin(
        10u, site_id, 0u, (uint64_t)divisor, 0u, d, divisor == 0 ? 1u : 0u);
  push_event_full(10u, site_id, (uint64_t)divisor, 0, 0, d, 0, 1);
  if (active) publish_shm();
}

void __formtrig_log_mod(uint32_t site_id, int64_t divisor) {
  __formtrig_log_div(site_id, divisor);
}

void __formtrig_log_arith(uint32_t site_id, uint32_t opcode, uint64_t lhs,
                          uint64_t rhs, uint64_t result, uint32_t bit_width) {
  if (__formtrig_suppress) {
    maybe_target_site_hit(site_id);
    return;
  }
  maybe_target_site_hit(site_id);
  int active = __formtrig_active;
  if (!active && !record_pre_reach_events()) return;
  double d = FORMTRIG_INF;
  uint64_t mask = bit_mask(bit_width);
  lhs &= mask;
  rhs &= mask;
  result &= mask;

  if (opcode != 1u && opcode != 2u && opcode != 3u) {
    if (active) publish_shm();
    return;
  }

  if (opcode == 1u) {
    d = rhs > mask - lhs ? 0.0
                         : u64_to_double_saturated(mask - lhs - rhs + 1ULL);
  } else if (opcode == 2u) {
    d = lhs < rhs ? 0.0 : u64_to_double_saturated(lhs - rhs + 1ULL);
  } else if (opcode == 3u) {
    if (lhs == 0 || rhs == 0)
      d = u64_to_double_saturated(mask);
    else
      d = lhs > mask / rhs ? 0.0
                           : u64_to_double_saturated(mask / rhs - lhs + 1ULL);
  }

  uint32_t input_start = 0;
  uint32_t input_len = 0;
  if (lookup_value_provenance(lhs, &input_start, &input_len) ||
      lookup_value_provenance(rhs, &input_start, &input_len))
    remember_value_provenance(result, input_start, input_len);

  if (active && d < FORMTRIG_INF / 2.0 && !g_state.manual_direct) {
    g_state.d_f_direct = min_double(g_state.d_f_direct, d);
    if (g_state.d_f_direct == d) g_state.d_f_direct_kind = FORMTRIG_DIRECT_ARITH;
  }
  if (active && d < FORMTRIG_INF / 2.0)
    remember_source_target_safety_margin(11u, site_id, opcode, lhs, rhs, d,
                                         d == 0.0 ? 1u : 0u);
  push_event_full(11u, site_id, lhs, rhs, result,
                  d < FORMTRIG_INF / 2.0 ? d : 1.0, 0, 1);
  if (active) publish_shm();
}

void formtrig_finalize(void) {
  if (g_state.finalized) return;
  g_state.finalized = 1;
  if (g_state.reached && !g_state.crash_predicate &&
      g_state.d_t >= FORMTRIG_INF / 2.0)
    g_state.d_t = 1.0;
  if (g_state.reached) {
    synthesize_live_pointer_producer_lift();
    synthesize_post_reach_margin_fallback();
  }
  publish_shm();
  write_jsonl();
}
