#define _POSIX_C_SOURCE 200809L

#include "formtrig/formtrig_abi.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ATOMS 128u
#define MAX_UNIQUE_VALUES 32u
#define MAX_ROLES 11u

enum ft_category {
  FT_CATEGORY_GENERIC = 0,
  FT_CATEGORY_NUMERIC,
  FT_CATEGORY_EQUALITY,
  FT_CATEGORY_BINARY_NULL,
  FT_CATEGORY_LIFECYCLE
};

typedef struct role_summary {
  uint32_t bound;
  uint64_t samples;
  uint64_t candidate_samples;
  uint64_t calibration_samples;
  double values[MAX_UNIQUE_VALUES];
  uint32_t value_count;
  double candidate_values[MAX_UNIQUE_VALUES];
  uint32_t candidate_value_count;
  double calibration_values[MAX_UNIQUE_VALUES];
  uint32_t calibration_value_count;
  double min_value;
  double max_value;
  double candidate_min;
  double candidate_max;
  uint32_t flags_or;
  double max_confidence;
} role_summary_t;

typedef struct atom_summary {
  uint32_t atom_id;
  enum ft_category category;
  uint32_t roles_bound;
  uint32_t lift_allowed;
  role_summary_t roles[MAX_ROLES];
} atom_summary_t;

typedef struct signal_diag {
  atom_summary_t atoms[MAX_ATOMS];
  uint32_t atom_count;
  uint64_t progress_events;
  uint64_t candidate_events;
  uint64_t calibration_events;
  uint64_t accepted_progress_events;
  uint64_t accepted_triggered_progress_events;
  uint64_t accepted_non_trigger_progress_events;
  uint64_t triggered_events;
  uint64_t spec_role_samples;
  uint64_t spec_role_candidate_samples;
  uint64_t spec_df_samples;
  uint64_t spec_df_candidate_samples;
  uint64_t spec_df_triggered_candidate_samples;
  uint64_t spec_df_non_trigger_candidate_samples;
  uint64_t spec_df_calibration_samples;
  double spec_df_min;
  double spec_df_candidate_min;
  double spec_df_triggered_candidate_min;
  double spec_df_non_trigger_candidate_min;
  double spec_df_calibration_min;
  double spec_df_candidate_values[MAX_UNIQUE_VALUES];
  uint32_t spec_df_candidate_value_count;
  double spec_df_triggered_candidate_values[MAX_UNIQUE_VALUES];
  uint32_t spec_df_triggered_candidate_value_count;
  double spec_df_non_trigger_candidate_values[MAX_UNIQUE_VALUES];
  uint32_t spec_df_non_trigger_candidate_value_count;
  double spec_df_calibration_values[MAX_UNIQUE_VALUES];
  uint32_t spec_df_calibration_value_count;
} signal_diag_t;

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s <formtrig_runtime_event_map.csv> "
          "<formtrig_progress.jsonl>\n",
          argv0);
}

static const char *json_find_key(const char *line, const char *key) {
  char pattern[128];
  int written = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
  if (written <= 0 || (size_t)written >= sizeof(pattern)) return NULL;
  return strstr(line, pattern);
}

static int json_u64_field(const char *line, const char *key, uint64_t *out) {
  const char *p = json_find_key(line, key);
  if (!p || !out) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  char *end = NULL;
  errno = 0;
  unsigned long long v = strtoull(p, &end, 0);
  if (errno || end == p) return 0;
  *out = (uint64_t)v;
  return 1;
}

static int json_bool_field(const char *line, const char *key, int *out) {
  const char *p = json_find_key(line, key);
  if (!p || !out) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  if (!strncmp(p, "true", 4)) {
    *out = 1;
    return 1;
  }
  if (!strncmp(p, "false", 5)) {
    *out = 0;
    return 1;
  }
  if (*p == '1' || *p == '0') {
    *out = *p == '1';
    return 1;
  }
  return 0;
}

static int json_double_field(const char *line, const char *key, double *out) {
  const char *p = json_find_key(line, key);
  if (!p || !out) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  if (!strncmp(p, "null", 4)) return 0;
  char *end = NULL;
  errno = 0;
  double v = strtod(p, &end);
  if (errno || end == p) return 0;
  *out = v;
  return 1;
}

static int json_string_field(const char *line, const char *key, char *out,
                             size_t out_size) {
  const char *p = json_find_key(line, key);
  if (!p || !out || !out_size) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  if (*p != '"') return 0;
  p++;
  size_t i = 0;
  while (*p && *p != '"') {
    if (*p == '\\' && p[1]) p++;
    if (i + 1u < out_size) out[i++] = *p;
    p++;
  }
  out[i] = '\0';
  return *p == '"';
}

static const char *csv_next_field(const char *p, char *out, size_t out_size) {
  if (!p || !out || !out_size) return NULL;
  size_t i = 0;
  while (*p && *p != ',' && *p != '\n' && *p != '\r') {
    if (i + 1u < out_size) out[i++] = *p;
    p++;
  }
  out[i] = '\0';
  if (*p == ',') return p + 1;
  return p;
}

static enum ft_category parse_category(const char *s) {
  if (!s) return FT_CATEGORY_GENERIC;
  if (!strcmp(s, "numeric") || !strcmp(s, "numeric-margin"))
    return FT_CATEGORY_NUMERIC;
  if (!strcmp(s, "equality") || !strcmp(s, "magic") ||
      !strcmp(s, "equality-magic"))
    return FT_CATEGORY_EQUALITY;
  if (!strcmp(s, "binary") || !strcmp(s, "binary-null") ||
      !strcmp(s, "binary-state-null"))
    return FT_CATEGORY_BINARY_NULL;
  if (!strcmp(s, "lifecycle") || !strcmp(s, "compound") ||
      !strcmp(s, "compound-sequence-lifecycle"))
    return FT_CATEGORY_LIFECYCLE;
  return FT_CATEGORY_GENERIC;
}

static const char *category_name(enum ft_category category) {
  switch (category) {
    case FT_CATEGORY_NUMERIC:
      return "numeric-margin";
    case FT_CATEGORY_EQUALITY:
      return "equality-magic";
    case FT_CATEGORY_BINARY_NULL:
      return "binary-state-null";
    case FT_CATEGORY_LIFECYCLE:
      return "compound-sequence-lifecycle";
    default:
      return "generic";
  }
}

static uint32_t parse_role(const char *s) {
  if (!s) return FORMTRIG_ROLE_UNKNOWN;
  if (!strcmp(s, "root_observe") || !strcmp(s, "root") || !strcmp(s, "1"))
    return FORMTRIG_ROLE_ROOT_OBSERVE;
  if (!strcmp(s, "guard") || !strcmp(s, "2")) return FORMTRIG_ROLE_GUARD;
  if (!strcmp(s, "producer") || !strcmp(s, "3"))
    return FORMTRIG_ROLE_PRODUCER;
  if (!strcmp(s, "desired_producer") || !strcmp(s, "desired-producer") ||
      !strcmp(s, "4"))
    return FORMTRIG_ROLE_DESIRED_PRODUCER;
  if (!strcmp(s, "opposite_producer") || !strcmp(s, "opposite-producer") ||
      !strcmp(s, "5"))
    return FORMTRIG_ROLE_OPPOSITE_PRODUCER;
  if (!strcmp(s, "use") || !strcmp(s, "6")) return FORMTRIG_ROLE_USE;
  if (!strcmp(s, "lifecycle_event") || !strcmp(s, "lifecycle") ||
      !strcmp(s, "7"))
    return FORMTRIG_ROLE_LIFECYCLE_EVENT;
  if (!strcmp(s, "same_object") || !strcmp(s, "same-object") ||
      !strcmp(s, "8"))
    return FORMTRIG_ROLE_SAME_OBJECT;
  if (!strcmp(s, "input_influence") || !strcmp(s, "input-influence") ||
      !strcmp(s, "9"))
    return FORMTRIG_ROLE_INPUT_INFLUENCE;
  if (!strcmp(s, "repair_hook") || !strcmp(s, "repair-hook") ||
      !strcmp(s, "10"))
    return FORMTRIG_ROLE_REPAIR_HOOK;
  return FORMTRIG_ROLE_UNKNOWN;
}

static const char *role_name(uint32_t role) {
  switch (role) {
    case FORMTRIG_ROLE_ROOT_OBSERVE:
      return "root_observe";
    case FORMTRIG_ROLE_GUARD:
      return "guard";
    case FORMTRIG_ROLE_PRODUCER:
      return "producer";
    case FORMTRIG_ROLE_DESIRED_PRODUCER:
      return "desired_producer";
    case FORMTRIG_ROLE_OPPOSITE_PRODUCER:
      return "opposite_producer";
    case FORMTRIG_ROLE_USE:
      return "use";
    case FORMTRIG_ROLE_LIFECYCLE_EVENT:
      return "lifecycle_event";
    case FORMTRIG_ROLE_SAME_OBJECT:
      return "same_object";
    case FORMTRIG_ROLE_INPUT_INFLUENCE:
      return "input_influence";
    case FORMTRIG_ROLE_REPAIR_HOOK:
      return "repair_hook";
    default:
      return "unknown";
  }
}

static uint32_t role_bit(uint32_t role) {
  if (role == FORMTRIG_ROLE_UNKNOWN || role > 31u) return 0u;
  return 1u << (role - 1u);
}

static atom_summary_t *atom_slot(signal_diag_t *d, uint32_t atom_id) {
  for (uint32_t i = 0; i < d->atom_count; i++)
    if (d->atoms[i].atom_id == atom_id) return &d->atoms[i];
  if (d->atom_count >= MAX_ATOMS) return NULL;
  atom_summary_t *atom = &d->atoms[d->atom_count++];
  memset(atom, 0, sizeof(*atom));
  atom->atom_id = atom_id;
  return atom;
}

static int double_seen(const double *values, uint32_t count, double value) {
  for (uint32_t i = 0; i < count; i++)
    if (values[i] == value) return 1;
  return 0;
}

static void remember_double(double *values, uint32_t *count, double value) {
  if (double_seen(values, *count, value)) return;
  if (*count < MAX_UNIQUE_VALUES) values[(*count)++] = value;
}

static const char *object_end(const char *p) {
  if (!p || *p != '{') return NULL;
  int depth = 0;
  for (; *p; p++) {
    if (*p == '{') depth++;
    if (*p == '}') {
      depth--;
      if (!depth) return p + 1;
    }
  }
  return NULL;
}

static int load_event_map(signal_diag_t *d, const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  char line[4096];
  uint32_t line_no = 0;
  while (fgets(line, sizeof(line), f)) {
    line_no++;
    if (line_no == 1 && strstr(line, "binding_id,")) continue;

    const char *p = line;
    char field[256];
    uint32_t atom_id = 0;
    enum ft_category category = FT_CATEGORY_GENERIC;
    uint32_t role = FORMTRIG_ROLE_UNKNOWN;
    int lift_allowed = 0;
    for (uint32_t col = 1; col <= 11u && p; col++) {
      p = csv_next_field(p, field, sizeof(field));
      if (col == 2u) atom_id = (uint32_t)strtoul(field, NULL, 10);
      if (col == 3u) category = parse_category(field);
      if (col == 4u) role = parse_role(field);
      if (col == 11u) lift_allowed = !strcmp(field, "true");
    }
    if (!atom_id || role >= MAX_ROLES) continue;
    atom_summary_t *atom = atom_slot(d, atom_id);
    if (!atom) continue;
    if (category != FT_CATEGORY_GENERIC) atom->category = category;
    atom->roles_bound |= role_bit(role);
    if (lift_allowed) atom->lift_allowed = 1u;
    atom->roles[role].bound = 1u;
  }

  fclose(f);
  return d->atom_count > 0;
}

static int event_is_candidate(const char *event) {
  return !strcmp(event, "frontier_reject") ||
         !strcmp(event, "frontier_accept") ||
         !strcmp(event, "saved_progress");
}

static int event_is_calibration(const char *event, const char *reason) {
  return !strcmp(event, "calibrated_frontier") ||
         !strcmp(reason, "initial_frontier_seed");
}

static int event_is_progress_accept(const char *event, const char *reason) {
  if (!strcmp(event, "saved_progress")) return 1;
  if (strcmp(event, "frontier_accept")) return 0;
  return strcmp(reason, "initial_frontier_seed") &&
         strcmp(reason, "calibrated_frontier");
}

static void record_role(role_summary_t *role, double value, uint32_t flags,
                        double confidence, int candidate, int calibration) {
  if (!role->samples || value < role->min_value) role->min_value = value;
  if (!role->samples || value > role->max_value) role->max_value = value;
  role->samples++;
  role->flags_or |= flags;
  if (!role->max_confidence || confidence > role->max_confidence)
    role->max_confidence = confidence;
  remember_double(role->values, &role->value_count, value);

  if (candidate) {
    if (!role->candidate_samples || value < role->candidate_min)
      role->candidate_min = value;
    if (!role->candidate_samples || value > role->candidate_max)
      role->candidate_max = value;
    role->candidate_samples++;
    remember_double(role->candidate_values, &role->candidate_value_count,
                    value);
  }

  if (calibration) {
    role->calibration_samples++;
    remember_double(role->calibration_values, &role->calibration_value_count,
                    value);
  }
}

static int spec_role_component(uint64_t atom_id, uint64_t role, uint64_t flags,
                               double confidence) {
  if (!atom_id || role == FORMTRIG_ROLE_UNKNOWN || role >= MAX_ROLES)
    return 0;
  if (confidence <= 0.0) return 0;
  if (!(flags & FORMTRIG_COMPONENT_TC_ROOTED)) return 0;
  if (!(flags & FORMTRIG_COMPONENT_LIFTED)) return 0;
  if (!(flags & FORMTRIG_COMPONENT_SPEC_LIFTED)) return 0;
  if (flags & FORMTRIG_COMPONENT_HEURISTIC_LIFTED) return 0;
  if (flags & FORMTRIG_COMPONENT_MANUAL_TARGET) return 0;
  return 1;
}

static void ingest_progress_line(signal_diag_t *d, const char *line) {
  char event[96] = {0};
  char reason[96] = {0};
  double df = 0.0;
  int triggered = 0;
  int candidate = 0;
  int calibration = 0;

  d->progress_events++;
  (void)json_string_field(line, "event", event, sizeof(event));
  (void)json_string_field(line, "reason", reason, sizeof(reason));
  candidate = event_is_candidate(event);
  calibration = event_is_calibration(event, reason);
  if (candidate) d->candidate_events++;
  if (calibration) d->calibration_events++;
  if (json_bool_field(line, "triggered", &triggered) && triggered)
    d->triggered_events++;
  if (event_is_progress_accept(event, reason)) {
    d->accepted_progress_events++;
    if (triggered)
      d->accepted_triggered_progress_events++;
    else
      d->accepted_non_trigger_progress_events++;
  }

  if (json_double_field(line, "d_f_spec_lifted", &df) ||
      json_double_field(line, "D_F_spec_lifted", &df)) {
    if (!d->spec_df_samples || df < d->spec_df_min) d->spec_df_min = df;
    d->spec_df_samples++;
    if (candidate) {
      if (!d->spec_df_candidate_samples || df < d->spec_df_candidate_min)
        d->spec_df_candidate_min = df;
      d->spec_df_candidate_samples++;
      remember_double(d->spec_df_candidate_values,
                      &d->spec_df_candidate_value_count, df);
      if (triggered) {
        if (!d->spec_df_triggered_candidate_samples ||
            df < d->spec_df_triggered_candidate_min)
          d->spec_df_triggered_candidate_min = df;
        d->spec_df_triggered_candidate_samples++;
        remember_double(d->spec_df_triggered_candidate_values,
                        &d->spec_df_triggered_candidate_value_count, df);
      } else {
        if (!d->spec_df_non_trigger_candidate_samples ||
            df < d->spec_df_non_trigger_candidate_min)
          d->spec_df_non_trigger_candidate_min = df;
        d->spec_df_non_trigger_candidate_samples++;
        remember_double(d->spec_df_non_trigger_candidate_values,
                        &d->spec_df_non_trigger_candidate_value_count, df);
      }
    }
    if (calibration) {
      if (!d->spec_df_calibration_samples || df < d->spec_df_calibration_min)
        d->spec_df_calibration_min = df;
      d->spec_df_calibration_samples++;
      remember_double(d->spec_df_calibration_values,
                      &d->spec_df_calibration_value_count, df);
    }
  }

  const char *array = strstr(line, "\"component_values\":[");
  if (!array) return;
  const char *p = strchr(array, '[');
  if (!p) return;
  p++;

  while ((p = strstr(p, "{\"kind\"")) != NULL) {
    const char *end = object_end(p);
    if (!end) break;

    char object[2048];
    size_t n = (size_t)(end - p);
    if (n >= sizeof(object)) n = sizeof(object) - 1u;
    memcpy(object, p, n);
    object[n] = '\0';

    uint64_t atom_id = 0;
    uint64_t role = 0;
    uint64_t flags = 0;
    double value = 0.0;
    double confidence = 0.0;
    (void)json_u64_field(object, "atom_id", &atom_id);
    (void)json_u64_field(object, "role", &role);
    (void)json_u64_field(object, "flags", &flags);
    if (!json_double_field(object, "value", &value) ||
        !json_double_field(object, "confidence", &confidence) ||
        !spec_role_component(atom_id, role, flags, confidence)) {
      p = end;
      continue;
    }

    atom_summary_t *atom = atom_slot(d, (uint32_t)atom_id);
    if (atom && role < MAX_ROLES) {
      role_summary_t *slot = &atom->roles[role];
      record_role(slot, value, (uint32_t)flags, confidence, candidate,
                  calibration);
      d->spec_role_samples++;
      if (candidate) d->spec_role_candidate_samples++;
    }
    p = end;
  }
}

static int load_progress(signal_diag_t *d, const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }
  char line[65536];
  while (fgets(line, sizeof(line), f)) {
    if (line[0] == '\0' || line[0] == '\n') continue;
    ingest_progress_line(d, line);
  }
  fclose(f);
  return 1;
}

static uint32_t variable_role_mask(const atom_summary_t *atom, int candidate) {
  uint32_t mask = 0;
  for (uint32_t role = 1; role < MAX_ROLES; role++) {
    const role_summary_t *r = &atom->roles[role];
    uint32_t unique =
        candidate ? r->candidate_value_count : r->value_count;
    if (unique > 1u) mask |= role_bit(role);
  }
  return mask;
}

static uint32_t sampled_role_mask(const atom_summary_t *atom, int candidate) {
  uint32_t mask = 0;
  for (uint32_t role = 1; role < MAX_ROLES; role++) {
    const role_summary_t *r = &atom->roles[role];
    uint64_t samples = candidate ? r->candidate_samples : r->samples;
    if (samples) mask |= role_bit(role);
  }
  return mask;
}

static uint32_t producer_role_mask(void) {
  return role_bit(FORMTRIG_ROLE_PRODUCER) |
         role_bit(FORMTRIG_ROLE_DESIRED_PRODUCER) |
         role_bit(FORMTRIG_ROLE_OPPOSITE_PRODUCER);
}

static int candidate_loses_calibrated_best(const signal_diag_t *d) {
  return d->spec_df_candidate_samples && d->spec_df_calibration_samples &&
         d->spec_df_candidate_min > d->spec_df_calibration_min;
}

static int df_bucket_has_delta(uint64_t samples, uint32_t unique_values,
                               double min_value,
                               const signal_diag_t *d) {
  if (!samples) return 0;
  if (unique_values > 1u) return 1;
  return d->spec_df_calibration_samples &&
         min_value < d->spec_df_calibration_min;
}

static int triggered_candidate_lift_delta(const signal_diag_t *d) {
  return df_bucket_has_delta(d->spec_df_triggered_candidate_samples,
                             d->spec_df_triggered_candidate_value_count,
                             d->spec_df_triggered_candidate_min, d);
}

static int non_trigger_candidate_lift_delta(const signal_diag_t *d) {
  return df_bucket_has_delta(d->spec_df_non_trigger_candidate_samples,
                             d->spec_df_non_trigger_candidate_value_count,
                             d->spec_df_non_trigger_candidate_min, d);
}

static const atom_summary_t *first_problem_atom(const signal_diag_t *d) {
  for (uint32_t i = 0; i < d->atom_count; i++) {
    if (d->atoms[i].category == FT_CATEGORY_BINARY_NULL ||
        d->atoms[i].category == FT_CATEGORY_LIFECYCLE)
      return &d->atoms[i];
  }
  return d->atom_count ? &d->atoms[0] : NULL;
}

static const char *diagnosis_for_atom(const signal_diag_t *d,
                                      const atom_summary_t *atom) {
  if (!atom) return "no_atom_binding";
  uint32_t variable_all = variable_role_mask(atom, 0);
  uint32_t variable_candidate = variable_role_mask(atom, 1);
  uint32_t sampled_candidate = sampled_role_mask(atom, 1);
  uint32_t guard = role_bit(FORMTRIG_ROLE_GUARD);
  uint32_t producer = producer_role_mask();
  uint32_t semantic_state =
      role_bit(FORMTRIG_ROLE_ROOT_OBSERVE) | producer |
      role_bit(FORMTRIG_ROLE_USE) | role_bit(FORMTRIG_ROLE_LIFECYCLE_EVENT) |
      role_bit(FORMTRIG_ROLE_SAME_OBJECT);

  if (!d->candidate_events) return "no_mutation_candidate_signal";
  if (!d->spec_role_samples) return "no_spec_role_signal";
  if (!d->spec_role_candidate_samples) return "no_candidate_role_signal";
  if (!variable_all) return "constant_lift_signal";
  if ((variable_all & ~guard) == 0u) return "guard_only_lift_signal";

  if ((atom->category == FT_CATEGORY_BINARY_NULL ||
       atom->category == FT_CATEGORY_LIFECYCLE) &&
      (variable_candidate & semantic_state) == 0u) {
    if (candidate_loses_calibrated_best(d))
      return "mutations_lose_best_lifted_state";
    if ((sampled_candidate & producer) == 0u)
      return "producer_not_observed_in_candidates";
    return "producer_root_use_constant";
  }

  if (candidate_loses_calibrated_best(d))
    return "mutations_lose_best_lifted_state";
  if (!d->accepted_non_trigger_progress_events)
    return "no_new_non_dominated_progress";
  return "role_signal_progress_observed";
}

static const char *primary_diagnosis(const signal_diag_t *d) {
  if (d->triggered_events) return "triggered";
  if (d->accepted_non_trigger_progress_events)
    return "role_signal_progress_observed";
  return diagnosis_for_atom(d, first_problem_atom(d));
}

static int signal_passes(const signal_diag_t *d, const char *diagnosis) {
  if (d->triggered_events || d->accepted_non_trigger_progress_events) return 1;
  if (!strcmp(diagnosis, "role_signal_progress_observed")) return 1;
  if (!strcmp(diagnosis, "no_new_non_dominated_progress")) return 1;
  return 0;
}

static void print_json_string(const char *s) {
  putchar('"');
  if (s) {
    for (; *s; s++) {
      if (*s == '"' || *s == '\\') putchar('\\');
      if ((unsigned char)*s < 0x20)
        printf("\\u%04x", (unsigned char)*s);
      else
        putchar(*s);
    }
  }
  putchar('"');
}

static void print_double_values(const double *values, uint32_t count) {
  putchar('[');
  for (uint32_t i = 0; i < count; i++) {
    if (i) putchar(',');
    printf("%.17g", values[i]);
  }
  putchar(']');
}

static void print_role_mask_names(uint32_t mask) {
  putchar('[');
  uint32_t printed = 0;
  for (uint32_t role = 1; role < MAX_ROLES; role++) {
    if ((mask & role_bit(role)) == 0u) continue;
    if (printed++) putchar(',');
    print_json_string(role_name(role));
  }
  putchar(']');
}

static void print_json(const signal_diag_t *d) {
  const char *diagnosis = primary_diagnosis(d);
  int pass = signal_passes(d, diagnosis);
  printf("{\n");
  printf("  \"status\": \"%s\",\n", pass ? "pass" : "fail");
  printf("  \"diagnosis\": ");
  print_json_string(diagnosis);
  printf(",\n");
  printf("  \"progress_events\": %llu,\n",
         (unsigned long long)d->progress_events);
  printf("  \"candidate_events\": %llu,\n",
         (unsigned long long)d->candidate_events);
  printf("  \"calibration_events\": %llu,\n",
         (unsigned long long)d->calibration_events);
  printf("  \"accepted_progress_events\": %llu,\n",
         (unsigned long long)d->accepted_progress_events);
  printf("  \"accepted_triggered_progress_events\": %llu,\n",
         (unsigned long long)d->accepted_triggered_progress_events);
  printf("  \"accepted_non_trigger_progress_events\": %llu,\n",
         (unsigned long long)d->accepted_non_trigger_progress_events);
  printf("  \"triggered_events\": %llu,\n",
         (unsigned long long)d->triggered_events);
  printf("  \"spec_role_samples\": %llu,\n",
         (unsigned long long)d->spec_role_samples);
  printf("  \"spec_role_candidate_samples\": %llu,\n",
         (unsigned long long)d->spec_role_candidate_samples);
  printf("  \"spec_d_f_samples\": %llu,\n",
         (unsigned long long)d->spec_df_samples);
  printf("  \"spec_d_f_candidate_samples\": %llu,\n",
         (unsigned long long)d->spec_df_candidate_samples);
  printf("  \"spec_d_f_triggered_candidate_samples\": %llu,\n",
         (unsigned long long)d->spec_df_triggered_candidate_samples);
  printf("  \"spec_d_f_non_trigger_candidate_samples\": %llu,\n",
         (unsigned long long)d->spec_df_non_trigger_candidate_samples);
  printf("  \"spec_d_f_calibration_samples\": %llu,\n",
         (unsigned long long)d->spec_df_calibration_samples);
  printf("  \"spec_d_f_candidate_min\": ");
  if (d->spec_df_candidate_samples)
    printf("%.17g", d->spec_df_candidate_min);
  else
    printf("null");
  printf(",\n");
  printf("  \"spec_d_f_triggered_candidate_min\": ");
  if (d->spec_df_triggered_candidate_samples)
    printf("%.17g", d->spec_df_triggered_candidate_min);
  else
    printf("null");
  printf(",\n");
  printf("  \"spec_d_f_non_trigger_candidate_min\": ");
  if (d->spec_df_non_trigger_candidate_samples)
    printf("%.17g", d->spec_df_non_trigger_candidate_min);
  else
    printf("null");
  printf(",\n");
  printf("  \"spec_d_f_calibration_min\": ");
  if (d->spec_df_calibration_samples)
    printf("%.17g", d->spec_df_calibration_min);
  else
    printf("null");
  printf(",\n");
  printf("  \"spec_d_f_candidate_values\": ");
  print_double_values(d->spec_df_candidate_values,
                      d->spec_df_candidate_value_count);
  printf(",\n");
  printf("  \"spec_d_f_triggered_candidate_values\": ");
  print_double_values(d->spec_df_triggered_candidate_values,
                      d->spec_df_triggered_candidate_value_count);
  printf(",\n");
  printf("  \"spec_d_f_non_trigger_candidate_values\": ");
  print_double_values(d->spec_df_non_trigger_candidate_values,
                      d->spec_df_non_trigger_candidate_value_count);
  printf(",\n");
  printf("  \"spec_d_f_calibration_values\": ");
  print_double_values(d->spec_df_calibration_values,
                      d->spec_df_calibration_value_count);
  printf(",\n");
  printf("  \"triggered_candidate_lift_delta\": %s,\n",
         triggered_candidate_lift_delta(d) ? "true" : "false");
  printf("  \"non_trigger_candidate_lift_delta\": %s,\n",
         non_trigger_candidate_lift_delta(d) ? "true" : "false");
  printf("  \"lift_delta_only_on_triggered_candidates\": %s,\n",
         (triggered_candidate_lift_delta(d) &&
          !non_trigger_candidate_lift_delta(d))
             ? "true"
             : "false");
  printf("  \"atoms\": [\n");
  for (uint32_t i = 0; i < d->atom_count; i++) {
    const atom_summary_t *atom = &d->atoms[i];
    printf("    {\n");
    printf("      \"atom_id\": %u,\n", atom->atom_id);
    printf("      \"category\": ");
    print_json_string(category_name(atom->category));
    printf(",\n");
    printf("      \"lift_allowed\": %s,\n",
           atom->lift_allowed ? "true" : "false");
    printf("      \"bound_roles\": ");
    print_role_mask_names(atom->roles_bound);
    printf(",\n");
    printf("      \"sampled_roles\": ");
    print_role_mask_names(sampled_role_mask(atom, 0));
    printf(",\n");
    printf("      \"candidate_sampled_roles\": ");
    print_role_mask_names(sampled_role_mask(atom, 1));
    printf(",\n");
    printf("      \"variable_roles\": ");
    print_role_mask_names(variable_role_mask(atom, 0));
    printf(",\n");
    printf("      \"candidate_variable_roles\": ");
    print_role_mask_names(variable_role_mask(atom, 1));
    printf(",\n");
    printf("      \"diagnosis\": ");
    print_json_string(diagnosis_for_atom(d, atom));
    printf(",\n");
    printf("      \"roles\": [\n");
    uint32_t emitted = 0;
    for (uint32_t role = 1; role < MAX_ROLES; role++) {
      const role_summary_t *r = &atom->roles[role];
      if (!r->bound && !r->samples) continue;
      if (emitted++) printf(",\n");
      printf("        {\"role\":");
      print_json_string(role_name(role));
      printf(",\"bound\":%s,\"samples\":%llu,",
             r->bound ? "true" : "false", (unsigned long long)r->samples);
      printf("\"candidate_samples\":%llu,\"calibration_samples\":%llu,",
             (unsigned long long)r->candidate_samples,
             (unsigned long long)r->calibration_samples);
      printf("\"unique_values\":%u,\"candidate_unique_values\":%u,",
             r->value_count, r->candidate_value_count);
      printf("\"values\":");
      print_double_values(r->values, r->value_count);
      printf(",\"candidate_values\":");
      print_double_values(r->candidate_values, r->candidate_value_count);
      printf(",\"flags_or\":%u,\"max_confidence\":%.17g}",
             r->flags_or, r->max_confidence);
    }
    printf("\n      ]\n");
    printf("    }%s\n", i + 1u == d->atom_count ? "" : ",");
  }
  printf("  ]\n");
  printf("}\n");
}

int main(int argc, char **argv) {
  if (argc != 3) {
    usage(argv[0]);
    return 2;
  }

  signal_diag_t d;
  memset(&d, 0, sizeof(d));
  if (!load_event_map(&d, argv[1])) return 2;
  if (!load_progress(&d, argv[2])) return 2;
  const char *diagnosis = primary_diagnosis(&d);
  int pass = signal_passes(&d, diagnosis);
  print_json(&d);
  return pass ? 0 : 1;
}
