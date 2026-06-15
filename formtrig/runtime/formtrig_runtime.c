#define _POSIX_C_SOURCE 200809L

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
#define FORMTRIG_SPEC_VALUE_DISTANCE_TO_A 8u
#define FORMTRIG_SPEC_VALUE_DISTANCE_TO_B 9u
#define FORMTRIG_SPEC_VALUE_DISTANCE_TO_C 10u
#define FORMTRIG_SPEC_VALUE_ABSENT 11u

#define FORMTRIG_SPEC_WINDOW_POST_REACH 0u
#define FORMTRIG_SPEC_WINDOW_PRE_REACH 1u
#define FORMTRIG_SPEC_WINDOW_ANY 2u

#define FORMTRIG_SPEC_WILDCARD UINT32_MAX

#ifndef FORMTRIG_USE_AFL_MAP_FALLBACK
#define FORMTRIG_USE_AFL_MAP_FALLBACK 0
#endif

#if FORMTRIG_USE_AFL_MAP_FALLBACK
extern unsigned char *__afl_area_ptr __attribute__((weak));
#endif

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
  uint8_t reach_boundary;
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
  uint32_t role;
  uint32_t priority;
  uint32_t direction_flag;
  uint32_t value_mode;
  uint32_t phase_index;
  uint32_t phase_prefix;
  uint32_t range_start;
  uint32_t range_len;
  uint32_t mutation_hint;
  uint32_t mutation_value;
  uint32_t observe_window;
  uint32_t observed_count;
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
  int manual_api_lifted;
  int manual_direct;
  uint8_t d_f_direct_kind;
  uint32_t target_hit_count;
  double d_t;
  double d_f_direct;
  double d_f_lifted;
  double d_f_spec_lifted;
  double d_f_heuristic_lifted;
  double d_f_manual_lifted;
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
  formtrig_atom_signal_t atom_signals[FORMTRIG_MAX_ATOM_SIGNALS];
  uint32_t atom_signal_count;
  int finalized;
} formtrig_state_t;

static formtrig_state_t g_state;
static int g_track_alloc_pre_reach = -1;
static int g_record_pre_reach_events = -1;
static int g_record_all_pre_reach_events = -1;
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
static int g_allow_heuristic_lift = -1;
static int g_observe_heuristic_lift = -1;
static uint32_t g_lift_window = 0;
static uint32_t g_sink_lookback = 0;
static uint32_t g_debug_event_window = 0;
static formtrig_shm_record_t *g_dedicated_shm_record = NULL;
static int g_dedicated_shm_checked = 0;
static formtrig_probe_spec_t g_probe_specs[FORMTRIG_PROBE_SPEC_CAP];
static uint32_t g_probe_spec_count = 0;
static int g_probe_specs_loaded = 0;

static void apply_probe_specs_to_event(const formtrig_event_t *event);
static void ensure_probe_specs_loaded(void);
static int pre_reach_event_capture_enabled(uint32_t kind, uint32_t site_id);
static void reset_probe_spec_runtime_state(void);
static void remember_df_source_with_distance(const formtrig_event_t *event,
                                             uint32_t linked, uint8_t mode,
                                             double distance);

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
  g_record_pre_reach_events =
      env ? (env_truthy(env) || strcmp(env, "all") == 0 ||
             strcmp(env, "full") == 0 || strcmp(env, "raw") == 0)
          : 0;
  return g_record_pre_reach_events;
}

static int record_all_pre_reach_events(void) {
  if (g_record_all_pre_reach_events >= 0) return g_record_all_pre_reach_events;
  const char *env = getenv("FORMTRIG_PRE_REACH_EVENTS");
  g_record_all_pre_reach_events =
      env && (strcmp(env, "all") == 0 || strcmp(env, "full") == 0 ||
              strcmp(env, "raw") == 0);
  return g_record_all_pre_reach_events;
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

static int manual_lift_api_allowed(void) {
  return env_truthy(getenv("FORMTRIG_ALLOW_MANUAL_LIFT"));
}

static int heuristic_lift_allowed(void) {
  if (g_allow_heuristic_lift >= 0) return g_allow_heuristic_lift;
  g_allow_heuristic_lift =
      env_truthy(getenv("FORMTRIG_ALLOW_HEURISTIC_LIFT"));
  return g_allow_heuristic_lift;
}

static int heuristic_lift_observed(void) {
  if (heuristic_lift_allowed()) return 1;
  if (g_observe_heuristic_lift >= 0) return g_observe_heuristic_lift;
  g_observe_heuristic_lift =
      env_truthy(getenv("FORMTRIG_OBSERVE_HEURISTIC_LIFT"));
  return g_observe_heuristic_lift;
}

static int manual_component_requires_lift_permission(uint32_t kind,
                                                     uint32_t flags) {
  if (flags & FORMTRIG_COMPONENT_LIFTED) return 1;
  switch (kind) {
    case FORMTRIG_COMPONENT_LIFTED_DISTANCE:
    case FORMTRIG_COMPONENT_BOUNDARY_MARGIN:
    case FORMTRIG_COMPONENT_OPERAND_INFLUENCE:
    case FORMTRIG_COMPONENT_GUARD_PROGRESS:
    case FORMTRIG_COMPONENT_PRODUCER_USE:
    case FORMTRIG_COMPONENT_LIFECYCLE_PREFIX:
    case FORMTRIG_COMPONENT_OBJECT_IDENTITY:
    case FORMTRIG_COMPONENT_EVENT_PHASE:
      return 1;
    default:
      return 0;
  }
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

static void add_hot_range_hint(uint32_t start, uint32_t len, double influence,
                               uint32_t hint_kind, uint32_t hint_value) {
  if (!len) return;

  uint64_t end = (uint64_t)start + (uint64_t)len;
  for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
    formtrig_hot_range_t *r = &g_state.hot_ranges[i];
    uint64_t r_end = (uint64_t)r->start + (uint64_t)r->len;
    int exact = r->start == start && r->len == len;
    if (hint_kind || r->hint_kind) {
      if (!exact) continue;
    } else if (end <= r->start || r_end <= start) {
      continue;
    }
    uint32_t new_start = start < r->start ? start : r->start;
    uint64_t new_end = end > r_end ? end : r_end;
    r->start = new_start;
    r->len = new_end > UINT32_MAX ? UINT32_MAX - new_start
                                   : (uint32_t)(new_end - new_start);
    if (influence > r->influence) r->influence = influence;
    if (hint_kind && (influence >= r->influence || !r->hint_kind)) {
      r->hint_kind = hint_kind;
      r->hint_value = hint_value;
    }
    return;
  }

  if (g_state.hot_range_count >= FORMTRIG_MAX_HOT_RANGES) return;
  formtrig_hot_range_t *r = &g_state.hot_ranges[g_state.hot_range_count++];
  r->start = start;
  r->len = len;
  r->influence = influence;
  r->hint_kind = hint_kind;
  r->hint_value = hint_value;
}

static void add_hot_range(uint32_t start, uint32_t len, double influence) {
  add_hot_range_hint(start, len, influence, FORMTRIG_MUTATION_HINT_NONE, 0u);
}

static void prioritize_hot_range_hint(uint32_t start, uint32_t len,
                                      double influence, uint32_t hint_kind,
                                      uint32_t hint_value) {
  if (!len) return;
  add_hot_range_hint(start, len, influence, hint_kind, hint_value);

  uint64_t end = (uint64_t)start + (uint64_t)len;
  for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
    formtrig_hot_range_t *r = &g_state.hot_ranges[i];
    uint64_t r_end = (uint64_t)r->start + (uint64_t)r->len;
    int exact = r->start == start && r->len == len;
    if (hint_kind || r->hint_kind) {
      if (!exact) continue;
    } else if (end <= r->start || r_end <= start) {
      continue;
    }
    if (influence > r->influence) r->influence = influence;
    if (hint_kind && (influence >= r->influence || !r->hint_kind)) {
      r->hint_kind = hint_kind;
      r->hint_value = hint_value;
    }
    if (i > 0) {
      formtrig_hot_range_t saved = *r;
      memmove(&g_state.hot_ranges[1], &g_state.hot_ranges[0],
              sizeof(g_state.hot_ranges[0]) * i);
      g_state.hot_ranges[0] = saved;
    }
    return;
  }
}

static void prioritize_hot_range(uint32_t start, uint32_t len,
                                 double influence) {
  prioritize_hot_range_hint(start, len, influence,
                            FORMTRIG_MUTATION_HINT_NONE, 0u);
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

static uint32_t label_site_id(const char *label) {
  uint32_t hash = 2166136261u;
  if (!label) label = "";
  while (*label) {
    hash ^= (unsigned char)*label++;
    hash *= 16777619u;
  }
  return hash ? hash : 1u;
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
  s->d_f_spec_lifted = FORMTRIG_INF;
  s->d_f_heuristic_lifted = FORMTRIG_INF;
  s->d_f_manual_lifted = FORMTRIG_INF;
  s->trace_signature = 1469598103934665603ULL;
}

static double min_double(double a, double b) {
  return a < b ? a : b;
}

static int finite_lift(double distance) {
  return distance < FORMTRIG_INF / 2.0;
}

static double selected_lifted_distance(void) {
  double selected = FORMTRIG_INF;
  if (finite_lift(g_state.d_f_spec_lifted))
    selected = min_double(selected, g_state.d_f_spec_lifted);
  if (heuristic_lift_allowed() && finite_lift(g_state.d_f_heuristic_lifted))
    selected = min_double(selected, g_state.d_f_heuristic_lifted);
  if (manual_lift_api_allowed() && finite_lift(g_state.d_f_manual_lifted))
    selected = min_double(selected, g_state.d_f_manual_lifted);
  return selected;
}

static uint32_t selected_lifted_source_flags(void) {
  uint32_t flags = 0;
  if (finite_lift(g_state.d_f_spec_lifted))
    flags |= FORMTRIG_SOURCE_SPEC_LIFTED;
  if (heuristic_lift_allowed() && finite_lift(g_state.d_f_heuristic_lifted))
    flags |= FORMTRIG_SOURCE_HEURISTIC_LIFTED;
  if (manual_lift_api_allowed() && finite_lift(g_state.d_f_manual_lifted))
    flags |= FORMTRIG_SOURCE_MANUAL_TARGET;
  return flags;
}

static uint32_t component_lift_source_flags(void) {
  uint32_t flags = 0;
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    if (!(g_state.components[i].flags & FORMTRIG_COMPONENT_LIFTED)) continue;
    if (g_state.components[i].flags & FORMTRIG_COMPONENT_SPEC_LIFTED)
      flags |= FORMTRIG_SOURCE_SPEC_LIFTED;
    if (heuristic_lift_allowed() &&
        (g_state.components[i].flags & FORMTRIG_COMPONENT_HEURISTIC_LIFTED))
      flags |= FORMTRIG_SOURCE_HEURISTIC_LIFTED;
    if (manual_lift_api_allowed() &&
        (g_state.components[i].flags & FORMTRIG_COMPONENT_MANUAL_TARGET))
      flags |= FORMTRIG_SOURCE_MANUAL_TARGET;
  }
  return flags;
}

static uint32_t sanitize_manual_component_flags(uint32_t flags) {
  flags &= ~(FORMTRIG_COMPONENT_SPEC_LIFTED |
             FORMTRIG_COMPONENT_HEURISTIC_LIFTED);
  flags |= FORMTRIG_COMPONENT_MANUAL_TARGET;
  return flags;
}

static uint32_t runtime_lift_source_flags(void) {
  return selected_lifted_source_flags() | component_lift_source_flags();
}

static uint32_t observed_lift_source_flags(void) {
  uint32_t flags = 0;
  if (finite_lift(g_state.d_f_spec_lifted))
    flags |= FORMTRIG_SOURCE_SPEC_LIFTED;
  if (finite_lift(g_state.d_f_heuristic_lifted))
    flags |= FORMTRIG_SOURCE_HEURISTIC_LIFTED;
  if (finite_lift(g_state.d_f_manual_lifted) || g_state.manual_api_lifted)
    flags |= FORMTRIG_SOURCE_MANUAL_TARGET;
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    if (g_state.components[i].flags & FORMTRIG_COMPONENT_SPEC_LIFTED)
      flags |= FORMTRIG_SOURCE_SPEC_LIFTED;
    if (g_state.components[i].flags & FORMTRIG_COMPONENT_HEURISTIC_LIFTED)
      flags |= FORMTRIG_SOURCE_HEURISTIC_LIFTED;
    if (g_state.components[i].flags & FORMTRIG_COMPONENT_MANUAL_TARGET)
      flags |= FORMTRIG_SOURCE_MANUAL_TARGET;
  }
  return flags;
}

static void refresh_selected_lifted_distance(void) {
  g_state.d_f_lifted = selected_lifted_distance();
}

static void observe_manual_lift_api_attempt(void) {
  g_state.manual_api_lifted = 1;
}

static void record_heuristic_lifted_distance(const formtrig_event_t *event,
                                             uint32_t linked, uint8_t mode,
                                             double distance) {
  if (!heuristic_lift_observed()) return;
  if (!finite_lift(distance)) return;
  if (distance < g_state.d_f_heuristic_lifted) {
    g_state.d_f_heuristic_lifted = distance;
    remember_df_source_with_distance(event, linked, mode, distance);
  }
  refresh_selected_lifted_distance();
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
  if (!reached && !pre_reach_event_capture_enabled(kind, site_id)) return;
  uint8_t reach_boundary =
      (uint8_t)(reached && target_site_matches(site_id) &&
                g_state.target_hit_count == 1u &&
                g_state.ring_count == g_state.target_epoch_start);

  formtrig_event_t local_event;
  memset(&local_event, 0, sizeof(local_event));
  local_event.kind = kind;
  local_event.site_id = site_id;
  local_event.input_start = input_start;
  local_event.input_len = input_len;
  local_event.a = a;
  local_event.b = b;
  local_event.c = c;
  local_event.distance = distance;
  local_event.is_write = is_write;
  local_event.has_dynamic_producer = has_dynamic_producer;
  local_event.after_reach = (uint8_t)reached;
  local_event.site_class = site_class;
  local_event.reach_boundary = reach_boundary;

  if (!reached && !record_all_pre_reach_events()) {
    apply_probe_specs_to_event(&local_event);
    return;
  }

  uint32_t slot = g_state.ring_count % FORMTRIG_RING_CAP;
  g_state.ring[slot] = local_event;
  g_state.ring_count++;

  if (!reached) {
    apply_probe_specs_to_event(&g_state.ring[slot]);
    return;
  }

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
  if (!heuristic_lift_observed()) return;
  if (!g_state.reached || g_state.manual_lifted ||
      !informative_safety_distance(distance))
    return;
  if (g_state.d_f_heuristic_lifted < FORMTRIG_INF / 2.0 &&
      distance > g_state.d_f_heuristic_lifted)
    return;

  g_state.d_f_heuristic_lifted = distance;
  refresh_selected_lifted_distance();
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

      record_heuristic_lifted_distance(source, linked, 6u, source_distance);
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
  if (!heuristic_lift_observed()) return;
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
    record_heuristic_lifted_distance(best_event, linked, 1u, best);
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
  if (!heuristic_lift_observed()) return 0;
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

  record_heuristic_lifted_distance(best_source, best_linked, 7u,
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
  if (!heuristic_lift_observed()) return 0;
  if (!source_target_site_mode() || !g_state.reached || g_state.manual_lifted)
    return 0;
  if (g_state.d_f_heuristic_lifted < FORMTRIG_INF / 2.0) return 0;

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

  record_heuristic_lifted_distance(best_event, 1u, 8u, best_distance);
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
  refresh_selected_lifted_distance();
  int spec_valid = g_state.d_f_spec_lifted < FORMTRIG_INF / 2.0;
  int lifted_valid = g_state.d_f_lifted < FORMTRIG_INF / 2.0;
  int direct_valid = g_state.d_f_direct < FORMTRIG_INF / 2.0;
  int spec_zero = spec_valid && g_state.d_f_spec_lifted == 0.0;
  int direct_zero = direct_valid && g_state.d_f_direct == 0.0;
  int lifted_zero = lifted_valid && g_state.d_f_lifted == 0.0;
  int spec_zero_confirmed = spec_zero && g_state.crash_predicate;
  int direct_zero_confirmed = direct_zero && g_state.crash_predicate;
  int lifted_zero_confirmed = lifted_zero && g_state.crash_predicate;
  /* A zero sub-signal is terminal only after the TC oracle confirms it. */
  double spec_df =
      spec_zero && !spec_zero_confirmed ? 1.0 : g_state.d_f_spec_lifted;
  double direct_df =
      direct_zero && !direct_zero_confirmed ? 1.0 : g_state.d_f_direct;
  double lifted_df =
      lifted_zero && !lifted_zero_confirmed ? 1.0 : g_state.d_f_lifted;

  /*
   * FORMTRIG-main is spec-driven: once BindingSpec-derived D_F exists, do not
   * collapse it with native/direct binary distances. Those distances remain
   * available as D_T/components for auditing and ablations.
   */
  if (spec_valid) return spec_df;

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
#if FORMTRIG_USE_AFL_MAP_FALLBACK
  if (&__afl_area_ptr == NULL || __afl_area_ptr == NULL) return NULL;
  return (formtrig_shm_record_t *)(void *)(__afl_area_ptr + FORMTRIG_SHM_OFFSET);
#else
  return NULL;
#endif
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
  rec->d_f_spec_lifted = -1.0;
  rec->d_f_heuristic_lifted = -1.0;
  rec->d_f_manual_lifted = -1.0;
  rec->source_flags = 0;
  rec->observed_source_flags = 0;
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

static uint32_t default_role_for_component(uint32_t kind) {
  switch (kind) {
    case FORMTRIG_COMPONENT_GUARD_PROGRESS:
      return FORMTRIG_ROLE_GUARD;
    case FORMTRIG_COMPONENT_PRODUCER_USE:
      return FORMTRIG_ROLE_PRODUCER;
    case FORMTRIG_COMPONENT_LIFECYCLE_PREFIX:
    case FORMTRIG_COMPONENT_EVENT_PHASE:
      return FORMTRIG_ROLE_LIFECYCLE_EVENT;
    case FORMTRIG_COMPONENT_OBJECT_IDENTITY:
      return FORMTRIG_ROLE_SAME_OBJECT;
    case FORMTRIG_COMPONENT_OPERAND_INFLUENCE:
      return FORMTRIG_ROLE_INPUT_INFLUENCE;
    default:
      return FORMTRIG_ROLE_UNKNOWN;
  }
}

static uint32_t role_bit(uint32_t role) {
  if (role == FORMTRIG_ROLE_UNKNOWN || role > 31u) return 0;
  return 1u << (role - 1u);
}

static int role_counts_for_spec_df(uint32_t role) {
  switch (role) {
    case FORMTRIG_ROLE_ROOT_OBSERVE:
    case FORMTRIG_ROLE_GUARD:
    case FORMTRIG_ROLE_PRODUCER:
    case FORMTRIG_ROLE_DESIRED_PRODUCER:
    case FORMTRIG_ROLE_OPPOSITE_PRODUCER:
    case FORMTRIG_ROLE_USE:
    case FORMTRIG_ROLE_LIFECYCLE_EVENT:
    case FORMTRIG_ROLE_SAME_OBJECT:
      return 1;
    default:
      return 0;
  }
}

static uint32_t expected_spec_role_bits_for_atom(uint32_t atom_id) {
  if (!atom_id) return 0;
  ensure_probe_specs_loaded();

  uint32_t bits = 0;
  for (uint32_t i = 0; i < g_probe_spec_count; i++) {
    const formtrig_probe_spec_t *spec = &g_probe_specs[i];
    if (spec->kind != FORMTRIG_SPEC_EVENT &&
        spec->kind != FORMTRIG_SPEC_PHASE)
      continue;
    if (spec->atom_id != atom_id) continue;

    uint32_t role = spec->role == FORMTRIG_ROLE_UNKNOWN
                        ? default_role_for_component(spec->component_kind)
                        : spec->role;
    if (role_counts_for_spec_df(role)) bits |= role_bit(role);
  }
  return bits;
}

static int component_matches_role(const formtrig_progress_component_t *component,
                                  uint32_t atom_id, uint32_t role) {
  return component && component->atom_id == atom_id &&
         component->role == role &&
         (component->flags & FORMTRIG_COMPONENT_SPEC_LIFTED);
}

static int component_value_satisfies_goal(
    const formtrig_progress_component_t *component) {
  if (!component || !isfinite(component->value)) return 0;

  if (component->flags & FORMTRIG_COMPONENT_HIGHER_IS_BETTER)
    return component->value > 0.0;
  if (component->flags & FORMTRIG_COMPONENT_LOWER_IS_BETTER)
    return component->value <= 0.0;
  return 0;
}

static int satisfied_spec_role_for_atom(uint32_t atom_id, uint32_t role) {
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    const formtrig_progress_component_t *component = &g_state.components[i];
    if (!component_matches_role(component, atom_id, role)) continue;
    if (component_value_satisfies_goal(component)) return 1;
  }
  return 0;
}

static double spec_role_graph_distance(void) {
  double best = FORMTRIG_INF;

  for (uint32_t i = 0; i < g_state.atom_signal_count; i++) {
    const formtrig_atom_signal_t *signal = &g_state.atom_signals[i];
    uint32_t expected = expected_spec_role_bits_for_atom(signal->atom_id);
    uint32_t required = 0;
    uint32_t missing = 0;

    for (uint32_t role = FORMTRIG_ROLE_ROOT_OBSERVE;
         role <= FORMTRIG_ROLE_SAME_OBJECT; role++) {
      if (!(expected & role_bit(role))) continue;
      if (!role_counts_for_spec_df(role)) continue;
      required++;
      if (!satisfied_spec_role_for_atom(signal->atom_id, role)) missing++;
    }

    if (required < 2) continue;
    if (!(signal->role_bits & expected)) continue;

    /*
     * Keep zero reserved for terminal TC satisfaction. For non-trigger
     * scheduling, a fully satisfied role graph is distance 1; each missing
     * BindingSpec role adds one step.
     */
    best = min_double(best, (double)missing + 1.0);
  }

  return best;
}

static void refresh_spec_role_graph_distance(void) {
  double role_df = spec_role_graph_distance();
  if (!finite_lift(role_df)) return;
  if (role_df < g_state.d_f_spec_lifted) {
    g_state.d_f_spec_lifted = role_df;
    refresh_selected_lifted_distance();
  }
}

static formtrig_atom_signal_t *atom_signal_slot(formtrig_atom_signal_t *signals,
                                                uint32_t *count,
                                                uint32_t atom_id) {
  if (!signals || !count || !atom_id) return NULL;
  for (uint32_t i = 0; i < *count; i++) {
    if (signals[i].atom_id == atom_id) return &signals[i];
  }
  if (*count >= FORMTRIG_MAX_ATOM_SIGNALS) return NULL;
  formtrig_atom_signal_t *slot = &signals[(*count)++];
  memset(slot, 0, sizeof(*slot));
  slot->atom_id = atom_id;
  return slot;
}

static void update_atom_signal_array(formtrig_atom_signal_t *signals,
                                     uint32_t *count, uint32_t atom_id,
                                     uint32_t role, uint32_t kind,
                                     uint64_t source_id, double value) {
  formtrig_atom_signal_t *signal = atom_signal_slot(signals, count, atom_id);
  if (!signal) return;

  signal->flags |= FORMTRIG_ATOM_SIGNAL_OBSERVED;
  signal->role_bits |= role_bit(role);
  if (source_id) signal->event_bits |= 1u << (source_id & 31u);

  uint32_t bucket = (uint32_t)distance_bucket_for_signature(value);
  switch (role) {
    case FORMTRIG_ROLE_ROOT_OBSERVE:
      signal->root_value_bucket = bucket;
      signal->flags |= FORMTRIG_ATOM_SIGNAL_HAS_ROOT_VALUE;
      break;
    case FORMTRIG_ROLE_GUARD:
      signal->guard_bits |= value > 0.0 ? 2u : 1u;
      break;
    case FORMTRIG_ROLE_PRODUCER:
      if (value > 0.0) signal->producer_bits |= 1u;
      break;
    case FORMTRIG_ROLE_DESIRED_PRODUCER:
      if (value > 0.0) signal->producer_bits |= 2u;
      break;
    case FORMTRIG_ROLE_OPPOSITE_PRODUCER:
      if (value > 0.0) signal->producer_bits |= 4u;
      break;
    case FORMTRIG_ROLE_USE:
      signal->use_bits |= value > 0.0 ? 2u : 1u;
      break;
    case FORMTRIG_ROLE_LIFECYCLE_EVENT:
      if (value > (double)signal->lifecycle_prefix)
        signal->lifecycle_prefix = (uint32_t)value;
      break;
    case FORMTRIG_ROLE_SAME_OBJECT:
      signal->object_id_bucket = bucket;
      signal->flags |= FORMTRIG_ATOM_SIGNAL_HAS_OBJECT_ID;
      break;
    case FORMTRIG_ROLE_INPUT_INFLUENCE:
      signal->event_bits |= 1u << ((kind + 17u) & 31u);
      break;
    case FORMTRIG_ROLE_REPAIR_HOOK:
      signal->event_bits |= 1u << ((kind + 23u) & 31u);
      break;
    default:
      break;
  }
}

static void state_record_component_role(uint32_t kind, uint32_t atom_id,
                                        uint32_t role, uint32_t priority,
                                        uint32_t flags, uint64_t source_id,
                                        uint64_t context_hash, double value,
                                        double confidence) {
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
  if (role == FORMTRIG_ROLE_UNKNOWN) role = default_role_for_component(kind);
  if (!source_id) source_id = component_source_id(kind, atom_id, priority);
  if (!context_hash) context_hash = component_source_id(kind, atom_id, priority);

  formtrig_progress_component_t *component =
      &g_state.components[g_state.component_count++];
  component->kind = kind;
  component->atom_id = atom_id;
  component->role = role;
  component->priority = priority;
  component->flags = flags | FORMTRIG_COMPONENT_TC_ROOTED;
  component->reserved = 0;
  component->source_id = source_id;
  component->context_hash = context_hash;
  component->value = value;
  component->confidence = confidence;
  update_atom_signal_array(g_state.atom_signals, &g_state.atom_signal_count,
                           atom_id, role, kind, source_id, value);

  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 20u);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, kind);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, role);
  g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, source_id);
  g_state.trace_signature =
      fnv_mix_u64(g_state.trace_signature, distance_bucket_for_signature(value));
}

static void state_record_component(uint32_t kind, uint32_t atom_id,
                                   uint32_t priority, uint32_t flags,
                                   uint64_t source_id, uint64_t context_hash,
                                   double value, double confidence) {
  state_record_component_role(kind, atom_id, FORMTRIG_ROLE_UNKNOWN, priority,
                              flags, source_id, context_hash, value,
                              confidence);
}

static void publish_component_role(formtrig_shm_record_t *rec, uint32_t kind,
                              uint32_t atom_id, uint32_t role, uint32_t priority,
                              uint32_t flags, uint64_t source_id,
                              uint64_t context_hash, double value,
                              double confidence) {
  if (!rec || rec->component_count >= FORMTRIG_MAX_PROGRESS_COMPONENTS) return;
  if (!isfinite(value) || value <= -FORMTRIG_INF / 2.0 ||
      value >= FORMTRIG_INF / 2.0)
    return;
  if (kind == FORMTRIG_COMPONENT_OPERAND_INFLUENCE)
    flags |= FORMTRIG_COMPONENT_INPUT_INFLUENCE;
  if (role == FORMTRIG_ROLE_UNKNOWN) role = default_role_for_component(kind);

  formtrig_progress_component_t *component =
      &rec->components[rec->component_count++];
  component->kind = kind;
  component->atom_id = atom_id;
  component->role = role;
  component->priority = priority;
  component->flags = flags | FORMTRIG_COMPONENT_TC_ROOTED;
  component->reserved = 0;
  component->source_id = source_id;
  component->context_hash = context_hash;
  component->value = value;
  component->confidence = confidence;
  update_atom_signal_array(rec->atom_signals, &rec->atom_signal_count, atom_id,
                           role, kind, source_id, value);
}

static void publish_component(formtrig_shm_record_t *rec, uint32_t kind,
                              uint32_t atom_id, uint32_t priority,
                              uint32_t flags, uint64_t source_id,
                              uint64_t context_hash, double value,
                              double confidence) {
  publish_component_role(rec, kind, atom_id, FORMTRIG_ROLE_UNKNOWN, priority,
                         flags, source_id, context_hash, value, confidence);
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
  if (strcmp(token, "distance_to_a") == 0 ||
      strcmp(token, "distance-to-a") == 0 ||
      strcmp(token, "target_distance_a") == 0 ||
      strcmp(token, "target-distance-a") == 0 ||
      strcmp(token, "abs_to_a") == 0 || strcmp(token, "abs-to-a") == 0 ||
      strcmp(token, "8") == 0)
    return FORMTRIG_SPEC_VALUE_DISTANCE_TO_A;
  if (strcmp(token, "distance_to_b") == 0 ||
      strcmp(token, "distance-to-b") == 0 ||
      strcmp(token, "target_distance_b") == 0 ||
      strcmp(token, "target-distance-b") == 0 ||
      strcmp(token, "abs_to_b") == 0 || strcmp(token, "abs-to-b") == 0 ||
      strcmp(token, "9") == 0)
    return FORMTRIG_SPEC_VALUE_DISTANCE_TO_B;
  if (strcmp(token, "distance_to_c") == 0 ||
      strcmp(token, "distance-to-c") == 0 ||
      strcmp(token, "target_distance_c") == 0 ||
      strcmp(token, "target-distance-c") == 0 ||
      strcmp(token, "abs_to_c") == 0 || strcmp(token, "abs-to-c") == 0 ||
      strcmp(token, "10") == 0)
    return FORMTRIG_SPEC_VALUE_DISTANCE_TO_C;
  if (strcmp(token, "absent") == 0 || strcmp(token, "not_hit") == 0 ||
      strcmp(token, "not-hit") == 0 || strcmp(token, "not_observed") == 0 ||
      strcmp(token, "not-observed") == 0 || strcmp(token, "11") == 0)
    return FORMTRIG_SPEC_VALUE_ABSENT;
  return UINT32_MAX;
}

static uint32_t parse_mutation_hint_token(const char *token) {
  if (!token || !*token) return FORMTRIG_MUTATION_HINT_NONE;
  uint32_t numeric = 0;
  if (parse_u32_token(token, &numeric)) return numeric;
  if (strcmp(token, "none") == 0 || strcmp(token, "default") == 0)
    return FORMTRIG_MUTATION_HINT_NONE;
  if (strcmp(token, "set_byte") == 0 || strcmp(token, "set-byte") == 0 ||
      strcmp(token, "byte") == 0)
    return FORMTRIG_MUTATION_HINT_SET_BYTE;
  if (strcmp(token, "clear") == 0 || strcmp(token, "zero") == 0)
    return FORMTRIG_MUTATION_HINT_CLEAR;
  if (strcmp(token, "fill") == 0)
    return FORMTRIG_MUTATION_HINT_FILL;
  if (strcmp(token, "delete") == 0 || strcmp(token, "delete_like") == 0 ||
      strcmp(token, "delete-like") == 0)
    return FORMTRIG_MUTATION_HINT_DELETE;
  if (strcmp(token, "insert_byte") == 0 || strcmp(token, "insert-byte") == 0 ||
      strcmp(token, "insert") == 0)
    return FORMTRIG_MUTATION_HINT_INSERT_BYTE;
  if (strcmp(token, "write_u16_le") == 0 ||
      strcmp(token, "write-u16-le") == 0 || strcmp(token, "u16le") == 0)
    return FORMTRIG_MUTATION_HINT_WRITE_U16_LE;
  if (strcmp(token, "write_u32_le") == 0 ||
      strcmp(token, "write-u32-le") == 0 || strcmp(token, "u32le") == 0)
    return FORMTRIG_MUTATION_HINT_WRITE_U32_LE;
  if (strcmp(token, "xor_byte") == 0 || strcmp(token, "xor-byte") == 0 ||
      strcmp(token, "xor") == 0)
    return FORMTRIG_MUTATION_HINT_XOR_BYTE;
  return UINT32_MAX;
}

static uint32_t parse_observe_window_token(const char *token) {
  if (!token || !*token) return UINT32_MAX;
  if (strcmp(token, "post_reach") == 0 || strcmp(token, "post-reach") == 0 ||
      strcmp(token, "after_reach") == 0 || strcmp(token, "after-reach") == 0 ||
      strcmp(token, "post") == 0 || strcmp(token, "0") == 0)
    return FORMTRIG_SPEC_WINDOW_POST_REACH;
  if (strcmp(token, "pre_reach") == 0 || strcmp(token, "pre-reach") == 0 ||
      strcmp(token, "before_reach") == 0 ||
      strcmp(token, "before-reach") == 0 || strcmp(token, "pre") == 0 ||
      strcmp(token, "1") == 0)
    return FORMTRIG_SPEC_WINDOW_PRE_REACH;
  if (strcmp(token, "any") == 0 || strcmp(token, "both") == 0 ||
      strcmp(token, "2") == 0)
    return FORMTRIG_SPEC_WINDOW_ANY;
  return UINT32_MAX;
}

static uint32_t parse_role_token(const char *token) {
  if (!token || !*token) return FORMTRIG_ROLE_UNKNOWN;
  if (strcmp(token, "root") == 0 || strcmp(token, "root_observe") == 0 ||
      strcmp(token, "root-observe") == 0 || strcmp(token, "1") == 0)
    return FORMTRIG_ROLE_ROOT_OBSERVE;
  if (strcmp(token, "guard") == 0 || strcmp(token, "2") == 0)
    return FORMTRIG_ROLE_GUARD;
  if (strcmp(token, "producer") == 0 || strcmp(token, "3") == 0)
    return FORMTRIG_ROLE_PRODUCER;
  if (strcmp(token, "desired_producer") == 0 ||
      strcmp(token, "desired-producer") == 0 || strcmp(token, "4") == 0)
    return FORMTRIG_ROLE_DESIRED_PRODUCER;
  if (strcmp(token, "opposite_producer") == 0 ||
      strcmp(token, "opposite-producer") == 0 || strcmp(token, "5") == 0)
    return FORMTRIG_ROLE_OPPOSITE_PRODUCER;
  if (strcmp(token, "use") == 0 || strcmp(token, "6") == 0)
    return FORMTRIG_ROLE_USE;
  if (strcmp(token, "lifecycle") == 0 ||
      strcmp(token, "lifecycle_event") == 0 ||
      strcmp(token, "lifecycle-event") == 0 || strcmp(token, "7") == 0)
    return FORMTRIG_ROLE_LIFECYCLE_EVENT;
  if (strcmp(token, "same_object") == 0 ||
      strcmp(token, "same-object") == 0 ||
      strcmp(token, "object_identity") == 0 ||
      strcmp(token, "object-identity") == 0 || strcmp(token, "8") == 0)
    return FORMTRIG_ROLE_SAME_OBJECT;
  if (strcmp(token, "input_influence") == 0 ||
      strcmp(token, "input-influence") == 0 || strcmp(token, "9") == 0)
    return FORMTRIG_ROLE_INPUT_INFLUENCE;
  if (strcmp(token, "repair_hook") == 0 ||
      strcmp(token, "repair-hook") == 0 || strcmp(token, "10") == 0)
    return FORMTRIG_ROLE_REPAIR_HOOK;
  return FORMTRIG_ROLE_UNKNOWN;
}

static char *next_spec_token(char **saveptr) {
  return strtok_r(NULL, " \t\r\n,", saveptr);
}

static int parse_probe_spec_tail(char **saveptr, formtrig_probe_spec_t *spec) {
  char *token = next_spec_token(saveptr);
  if (!token) return 1;

  uint32_t window = parse_observe_window_token(token);
  if (window != UINT32_MAX) {
    spec->observe_window = window;
    return 1;
  }

  if (!parse_u64_token(token, &spec->source_id)) return 0;

  token = next_spec_token(saveptr);
  if (!token) return 1;
  window = parse_observe_window_token(token);
  if (window != UINT32_MAX) {
    spec->observe_window = window;
    return 1;
  }

  if (!parse_u64_token(token, &spec->context_hash)) return 0;

  token = next_spec_token(saveptr);
  if (!token) return 1;
  window = parse_observe_window_token(token);
  if (window == UINT32_MAX) return 0;
  spec->observe_window = window;
  return 1;
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

  if (strcmp(op, "role_component") == 0 || strcmp(op, "role-event") == 0 ||
      strcmp(op, "role_event") == 0) {
    char *event_kind = next_spec_token(&saveptr);
    char *site_id = next_spec_token(&saveptr);
    char *role = next_spec_token(&saveptr);
    char *component_kind = next_spec_token(&saveptr);
    char *atom_id = next_spec_token(&saveptr);
    char *priority = next_spec_token(&saveptr);
    char *direction = next_spec_token(&saveptr);
    char *value_mode = next_spec_token(&saveptr);
    char *value = next_spec_token(&saveptr);
    char *confidence = next_spec_token(&saveptr);

    spec.kind = FORMTRIG_SPEC_EVENT;
    spec.role = parse_role_token(role);
    if (spec.role == FORMTRIG_ROLE_UNKNOWN ||
        !parse_u32_token(event_kind, &spec.event_kind) ||
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

    if (!parse_probe_spec_tail(&saveptr, &spec)) return;

    g_probe_specs[g_probe_spec_count++] = spec;
    return;
  }

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
    spec.role = FORMTRIG_ROLE_UNKNOWN;
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

    if (!parse_probe_spec_tail(&saveptr, &spec)) return;

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
    spec.role = FORMTRIG_ROLE_LIFECYCLE_EVENT;
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

    if (!parse_probe_spec_tail(&saveptr, &spec)) return;
    if (!spec.context_hash) spec.context_hash = spec.source_id;
    if (!spec.source_id) spec.source_id = spec.context_hash;

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
    char *mutation_hint = next_spec_token(&saveptr);
    char *mutation_value = next_spec_token(&saveptr);

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
    if (mutation_hint) {
      spec.mutation_hint = parse_mutation_hint_token(mutation_hint);
      if (spec.mutation_hint == UINT32_MAX) return;
    }
    if (mutation_value &&
        !parse_u32_token(mutation_value, &spec.mutation_value))
      return;
    if (!parse_probe_spec_tail(&saveptr, &spec)) return;

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
    g_probe_specs[i].observed_count = 0;
    if (g_probe_specs[i].kind == FORMTRIG_SPEC_RANGE &&
        g_probe_specs[i].event_kind == FORMTRIG_SPEC_WILDCARD &&
        g_probe_specs[i].site_id == FORMTRIG_SPEC_WILDCARD) {
      prioritize_hot_range_hint(g_probe_specs[i].range_start,
                                g_probe_specs[i].range_len,
                                g_probe_specs[i].value,
                                g_probe_specs[i].mutation_hint,
                                g_probe_specs[i].mutation_value);
    }
  }
}

static int probe_spec_matches(const formtrig_probe_spec_t *spec,
                              const formtrig_event_t *event) {
  if (!spec || !event) return 0;
  if (spec->observe_window == FORMTRIG_SPEC_WINDOW_POST_REACH &&
      !event->after_reach)
    return 0;
  if (spec->observe_window == FORMTRIG_SPEC_WINDOW_PRE_REACH &&
      event->after_reach && !event->reach_boundary)
    return 0;
  if (event->kind == 1u || event->kind == 2u) return 0;
  if (spec->event_kind != FORMTRIG_SPEC_WILDCARD &&
      spec->event_kind != event->kind)
    return 0;
  if (spec->site_id != FORMTRIG_SPEC_WILDCARD &&
      spec->site_id != event->site_id)
    return 0;
  return 1;
}

static int pre_reach_event_capture_enabled(uint32_t kind, uint32_t site_id) {
  if (!record_pre_reach_events()) return 0;
  if (record_all_pre_reach_events()) return 1;

  formtrig_event_t event;
  memset(&event, 0, sizeof(event));
  event.kind = kind;
  event.site_id = site_id;
  event.after_reach = 0;

  ensure_probe_specs_loaded();
  for (uint32_t i = 0; i < g_probe_spec_count; i++) {
    formtrig_probe_spec_t *spec = &g_probe_specs[i];
    if (spec->kind != FORMTRIG_SPEC_EVENT &&
        spec->kind != FORMTRIG_SPEC_PHASE &&
        spec->kind != FORMTRIG_SPEC_RANGE)
      continue;
    if (probe_spec_matches(spec, &event)) return 1;
  }
  return 0;
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
    case FORMTRIG_SPEC_VALUE_DISTANCE_TO_A:
      return fabs(u64_to_double_saturated(event->a) - spec->value);
    case FORMTRIG_SPEC_VALUE_DISTANCE_TO_B:
      return fabs(u64_to_double_saturated(event->b) - spec->value);
    case FORMTRIG_SPEC_VALUE_DISTANCE_TO_C:
      return fabs(u64_to_double_saturated(event->c) - spec->value);
    case FORMTRIG_SPEC_VALUE_ABSENT:
      return 0.0;
    default:
      return FORMTRIG_INF;
  }
}

static void state_record_component_best_role(uint32_t kind, uint32_t atom_id,
                                             uint32_t role, uint32_t priority,
                                             uint32_t flags, uint64_t source_id,
                                             uint64_t context_hash,
                                             double value,
                                             double confidence) {
  if (!isfinite(value) || value < 0.0 || value >= FORMTRIG_INF / 2.0)
    return;
  if (role == FORMTRIG_ROLE_UNKNOWN) role = default_role_for_component(kind);
  if (!source_id) source_id = component_source_id(kind, atom_id, priority);
  if (!context_hash) context_hash = component_source_id(kind, atom_id, priority);

  for (uint32_t i = 0; i < g_state.component_count; i++) {
    formtrig_progress_component_t *component = &g_state.components[i];
    if (component->kind != kind || component->atom_id != atom_id ||
        component->role != role ||
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
      update_atom_signal_array(g_state.atom_signals, &g_state.atom_signal_count,
                               atom_id, role, kind, source_id, value);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, 20u);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, kind);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, role);
      g_state.trace_signature = fnv_mix_u64(g_state.trace_signature, source_id);
      g_state.trace_signature = fnv_mix_u64(
          g_state.trace_signature, distance_bucket_for_signature(value));
    }
    return;
  }

  state_record_component_role(kind, atom_id, role, priority, flags, source_id,
                              context_hash, value, confidence);
}

static void record_probe_component(const formtrig_probe_spec_t *spec,
                                   const formtrig_event_t *event,
                                   double value) {
  uint64_t source_id = spec->source_id;
  uint64_t context_hash = spec->context_hash;
  uint32_t site_id = event ? event->site_id : spec->site_id;
  if (!source_id) {
    if (spec->kind == FORMTRIG_SPEC_PHASE)
      source_id = component_source_id(spec->component_kind, spec->atom_id,
                                      spec->priority);
    else
      source_id = component_source_id(spec->component_kind, site_id,
                                      spec->atom_id);
  }
  if (!context_hash)
    context_hash = component_source_id(spec->component_kind, spec->atom_id,
                                       spec->priority);

  uint32_t flags = spec->direction_flag | FORMTRIG_COMPONENT_LIFTED |
                   FORMTRIG_COMPONENT_SPEC_LIFTED;
  state_record_component_best_role(spec->component_kind, spec->atom_id,
                                   spec->role, spec->priority, flags,
                                   source_id, context_hash, value,
                                   spec->confidence);
  refresh_spec_role_graph_distance();
  if ((spec->direction_flag & FORMTRIG_COMPONENT_LOWER_IS_BETTER) &&
      value < g_state.d_f_spec_lifted) {
    g_state.d_f_spec_lifted = value;
    refresh_selected_lifted_distance();
    if (event) remember_df_source_with_distance(event, 1u, 10u, value);
  }
  if (event && event->input_len)
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
    spec->observed_count++;

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
      prioritize_hot_range_hint(spec->range_start, spec->range_len, spec->value,
                                spec->mutation_hint, spec->mutation_value);
    }
  }
}

static void record_absent_probe_components(void) {
  ensure_probe_specs_loaded();
  if (!g_probe_spec_count || !g_state.reached) return;

  for (uint32_t i = 0; i < g_probe_spec_count; i++) {
    formtrig_probe_spec_t *spec = &g_probe_specs[i];
    if (spec->kind != FORMTRIG_SPEC_EVENT ||
        spec->value_mode != FORMTRIG_SPEC_VALUE_ABSENT ||
        spec->observed_count)
      continue;

    double value = spec->value > 0.0 ? spec->value : 1.0;
    record_probe_component(spec, NULL, value);
  }
}

static void publish_shm(void) {
  if (!g_state.reached) return;
  if (!g_state.finalized && !g_state.crash_predicate && !publish_eager())
    return;

  record_absent_probe_components();
  refresh_spec_role_graph_distance();
  refresh_selected_lifted_distance();

  formtrig_shm_record_t *rec = shm_record();
  if (!rec) return;

  memset(rec, 0, sizeof(*rec));
  rec->magic = FORMTRIG_SHM_MAGIC;
  rec->version = FORMTRIG_SHM_VERSION;
  rec->flags = 0;
  if (g_state.reached) rec->flags |= FORMTRIG_FLAG_REACHED;
  if (g_state.crash_predicate) rec->flags |= FORMTRIG_FLAG_CRASH_PREDICATE;
  uint32_t source_flags = runtime_lift_source_flags();
  if (source_flags) rec->flags |= FORMTRIG_FLAG_LIFTED;
  if (source_flags & FORMTRIG_SOURCE_SPEC_LIFTED)
    rec->flags |= FORMTRIG_FLAG_SPEC_LIFTED;
  if (source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED)
    rec->flags |= FORMTRIG_FLAG_HEURISTIC_LIFTED;
  if (source_flags & FORMTRIG_SOURCE_MANUAL_TARGET)
    rec->flags |= FORMTRIG_FLAG_MANUAL_LIFTED;
  rec->source_flags = source_flags;
  rec->observed_source_flags = observed_lift_source_flags();
  rec->target_hit_count = g_state.target_hit_count;
  rec->trace_signature = g_state.trace_signature;
  rec->d_t = g_state.d_t < FORMTRIG_INF / 2.0
                 ? g_state.d_t
                 : (g_state.reached ? 1.0 : FORMTRIG_INF);
  rec->d_f = final_df();
  rec->d_f_lifted = g_state.d_f_lifted < FORMTRIG_INF / 2.0
                        ? g_state.d_f_lifted
                        : -1.0;
  rec->d_f_spec_lifted = g_state.d_f_spec_lifted < FORMTRIG_INF / 2.0
                             ? g_state.d_f_spec_lifted
                             : -1.0;
  rec->d_f_heuristic_lifted =
      g_state.d_f_heuristic_lifted < FORMTRIG_INF / 2.0
          ? g_state.d_f_heuristic_lifted
          : -1.0;
  rec->d_f_manual_lifted = g_state.d_f_manual_lifted < FORMTRIG_INF / 2.0
                               ? g_state.d_f_manual_lifted
                               : -1.0;
  rec->hot_range_count = g_state.hot_range_count;
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    formtrig_progress_component_t *component = &g_state.components[i];
    publish_component_role(rec, component->kind, component->atom_id,
                           component->role, component->priority,
                           component->flags, component->source_id,
                           component->context_hash, component->value,
                           component->confidence);
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
        FORMTRIG_COMPONENT_LOWER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED |
            ((source_flags & FORMTRIG_SOURCE_SPEC_LIFTED)
                 ? FORMTRIG_COMPONENT_SPEC_LIFTED
                 : 0u) |
            ((source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED)
                 ? FORMTRIG_COMPONENT_HEURISTIC_LIFTED
                 : 0u) |
            ((source_flags & FORMTRIG_SOURCE_MANUAL_TARGET)
                 ? FORMTRIG_COMPONENT_MANUAL_TARGET
                 : 0u),
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
    uint32_t lifted_source_flag =
        g_state.df_source.mode == 10u
            ? FORMTRIG_COMPONENT_SPEC_LIFTED
            : (g_state.df_source.mode == 3u ? FORMTRIG_COMPONENT_MANUAL_TARGET
                                            : FORMTRIG_COMPONENT_HEURISTIC_LIFTED);
    publish_component(
        rec, FORMTRIG_COMPONENT_BOUNDARY_MARGIN, 0u, 20u,
        FORMTRIG_COMPONENT_LOWER_IS_BETTER | FORMTRIG_COMPONENT_LIFTED |
            lifted_source_flag,
        component_source_id(FORMTRIG_COMPONENT_BOUNDARY_MARGIN,
                            g_state.df_source.site_id,
                            g_state.df_source.kind),
        component_source_id(FORMTRIG_COMPONENT_BOUNDARY_MARGIN,
                            g_state.df_source.site_id,
                            g_state.df_source.kind),
        g_state.df_source.distance,
        g_state.df_source.linked_count ? 0.9 : 0.5);
  }

  if (g_state.hot_range_count && heuristic_lift_observed()) {
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
              FORMTRIG_COMPONENT_INPUT_INFLUENCE |
              FORMTRIG_COMPONENT_HEURISTIC_LIFTED,
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

  fprintf(f, ",\"D_F_spec_lifted\":");
  if (g_state.d_f_spec_lifted < FORMTRIG_INF / 2.0)
    fprintf(f, "%.17g", g_state.d_f_spec_lifted);
  else
    fprintf(f, "null");

  fprintf(f, ",\"D_F_heuristic_lifted\":");
  if (g_state.d_f_heuristic_lifted < FORMTRIG_INF / 2.0)
    fprintf(f, "%.17g", g_state.d_f_heuristic_lifted);
  else
    fprintf(f, "null");

  fprintf(f, ",\"D_F_manual_lifted\":");
  if (g_state.d_f_manual_lifted < FORMTRIG_INF / 2.0)
    fprintf(f, "%.17g", g_state.d_f_manual_lifted);
  else
    fprintf(f, "null");

  uint32_t source_flags = runtime_lift_source_flags();
  uint32_t observed_source_flags = observed_lift_source_flags();
  fprintf(f, ",\"lift_source_flags\":%" PRIu32, source_flags);
  fprintf(f, ",\"observed_lift_source_flags\":%" PRIu32,
          observed_source_flags);

  fprintf(f,
          ",\"trace_signature\":\"0x%016" PRIx64
          "\",\"target_hit_count\":%" PRIu32 ",\"hot_byte_ranges\":[",
          g_state.trace_signature, g_state.target_hit_count);

  for (uint32_t i = 0; i < g_state.hot_range_count; i++) {
    if (i) fputc(',', f);
    fprintf(f, "{\"start\":%" PRIu32 ",\"len\":%" PRIu32
               ",\"influence\":%.17g,\"hint_kind\":%" PRIu32
               ",\"hint_value\":%" PRIu32 "}",
            g_state.hot_ranges[i].start, g_state.hot_ranges[i].len,
            g_state.hot_ranges[i].influence, g_state.hot_ranges[i].hint_kind,
            g_state.hot_ranges[i].hint_value);
  }

  fprintf(f, "],\"components\":[");
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    formtrig_progress_component_t *component = &g_state.components[i];
    if (i) fputc(',', f);
    fprintf(f,
            "{\"kind\":%" PRIu32 ",\"atom_id\":%" PRIu32
            ",\"role\":%" PRIu32 ",\"priority\":%" PRIu32
            ",\"flags\":%" PRIu32 ",\"source_id\":%" PRIu64
            ",\"context_hash\":\"0x%016" PRIx64
            "\",\"value\":%.17g,\"confidence\":%.17g}",
            component->kind, component->atom_id, component->role,
            component->priority, component->flags, component->source_id,
            component->context_hash, component->value, component->confidence);
  }

  fprintf(f, "],\"feature_source_event_ids\":[");
  for (uint32_t i = 0; i < g_state.component_count; i++) {
    formtrig_progress_component_t *component = &g_state.components[i];
    if (i) fputc(',', f);
    fprintf(f, "%" PRIu64, component->source_id);
  }

  fprintf(f,
          "],\"uses_trigger_oracle\":false,"
          "\"uses_target_id_specific_rule\":%s,"
          "\"uses_runtime_heuristic\":%s,"
          "\"uses_spec_lifted\":%s,"
          "\"uses_manual_target\":%s,"
          "\"observed_runtime_heuristic\":%s,"
          "\"observed_manual_target\":%s",
          (source_flags & FORMTRIG_SOURCE_MANUAL_TARGET) ? "true" : "false",
          (source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED) ? "true" : "false",
          (source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) ? "true" : "false",
          (source_flags & FORMTRIG_SOURCE_MANUAL_TARGET) ? "true" : "false",
          (observed_source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED) ? "true"
                                                                    : "false",
          (observed_source_flags & FORMTRIG_SOURCE_MANUAL_TARGET) ? "true"
                                                                 : "false");

  fprintf(f, ",\"atom_signals\":[");
  for (uint32_t i = 0; i < g_state.atom_signal_count; i++) {
    formtrig_atom_signal_t *signal = &g_state.atom_signals[i];
    if (i) fputc(',', f);
    fprintf(f,
            "{\"atom_id\":%" PRIu32 ",\"role_bits\":%" PRIu32
            ",\"event_bits\":%" PRIu32 ",\"lifecycle_prefix\":%" PRIu32
            ",\"root_value_bucket\":%" PRIu32
            ",\"object_id_bucket\":%" PRIu32
            ",\"guard_bits\":%" PRIu32 ",\"producer_bits\":%" PRIu32
            ",\"use_bits\":%" PRIu32 ",\"flags\":%" PRIu32 "}",
            signal->atom_id, signal->role_bits, signal->event_bits,
            signal->lifecycle_prefix, signal->root_value_bucket,
            signal->object_id_bucket, (uint32_t)signal->guard_bits,
            (uint32_t)signal->producer_bits, (uint32_t)signal->use_bits,
            (uint32_t)signal->flags);
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
  push_event(FORMTRIG_EVENT_TARGET_HIT, g_state.target_hit_count, 0, 0, 0.0);
  g_state.target_epoch_start = g_state.ring_count;
  publish_shm();
}

void formtrig_crash_predicate(int satisfied, const char *label) {
  if (!target_label_matches(label)) return;
  push_event_full(FORMTRIG_EVENT_CANARY, label_site_id(label),
                  satisfied ? 1u : 0u, 0, 0, satisfied ? 0.0 : 1.0, 0, 0);
  if (lift_crash_predicate()) g_state.binary_sink = 1;
  if (satisfied) {
    g_state.crash_predicate = 1;
    g_state.d_t = 0.0;
  } else if (g_state.reached && g_state.d_t >= FORMTRIG_INF / 2.0) {
    g_state.d_t = 1.0;
  }
  push_event(FORMTRIG_EVENT_CRASH_PREDICATE, satisfied ? 1u : 0u, 0, 0,
             satisfied ? 0.0 : 1.0);
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
  (void)kind;
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
  (void)kind;
  observe_manual_lift_api_attempt();
  publish_shm();
  if (!manual_lift_api_allowed()) return;
  if (distance < 0.0) distance = 0.0;
  g_state.d_f_manual_lifted = distance;
  refresh_selected_lifted_distance();
  g_state.manual_lifted = 1;
  g_state.manual_api_lifted = 1;
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
  push_event(FORMTRIG_EVENT_MANUAL_LIFT, 0, 0, 0, distance);
  publish_shm();
}

void formtrig_record_progress_component(uint32_t kind, uint32_t atom_id,
                                        uint32_t priority, uint32_t flags,
                                        uint64_t source_id,
                                        uint64_t context_hash, double value,
                                        double confidence) {
  observe_manual_lift_api_attempt();
  publish_shm();
  if (!manual_lift_api_allowed()) return;
  uint32_t manual_lifted = manual_component_requires_lift_permission(kind, flags);
  flags = sanitize_manual_component_flags(flags);
  state_record_component(kind, atom_id, priority, flags, source_id,
                         context_hash, value, confidence);
  if (manual_lifted) {
    g_state.manual_lifted = 1;
    g_state.manual_api_lifted = 1;
  }
  publish_shm();
}

void formtrig_record_role_component(uint32_t kind, uint32_t atom_id,
                                    uint32_t role, uint32_t priority,
                                    uint32_t flags, uint64_t source_id,
                                    uint64_t context_hash, double value,
                                    double confidence) {
  observe_manual_lift_api_attempt();
  publish_shm();
  if (!manual_lift_api_allowed()) return;
  uint32_t manual_lifted = manual_component_requires_lift_permission(kind, flags);
  flags = sanitize_manual_component_flags(flags);
  state_record_component_role(kind, atom_id, role, priority, flags, source_id,
                              context_hash, value, confidence);
  if (manual_lifted) {
    g_state.manual_lifted = 1;
    g_state.manual_api_lifted = 1;
  }
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
  if (!__formtrig_active && !track_alloc_pre_reach() &&
      !pre_reach_event_capture_enabled(5u, site_id))
    return ptr;
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
  if (!__formtrig_active && !track_alloc_pre_reach() &&
      !pre_reach_event_capture_enabled(6u, site_id)) {
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
  if (!active && !pre_reach_event_capture_enabled(7u, site_id)) return;
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
  if (!active && !pre_reach_event_capture_enabled(8u, site_id)) return;
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
  if (!active && !pre_reach_event_capture_enabled(9u, site_id)) return;
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
  if (!active && !pre_reach_event_capture_enabled(15u, site_id)) return;
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
  if (!active && !pre_reach_event_capture_enabled(10u, site_id)) return;
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
  if (!active && !pre_reach_event_capture_enabled(11u, site_id)) return;
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
