#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "formtrig/formtrig_abi.h"

#define MAX_COMPONENTS 256u
#define MAX_UNIQUE_VALUES 32u

typedef struct component_key {
  uint64_t source_id;
  uint32_t kind;
  uint32_t atom_id;
  uint32_t role;
} component_key_t;

typedef struct component_summary {
  component_key_t key;
  uint64_t samples;
  uint32_t unique_count;
  double unique_values[MAX_UNIQUE_VALUES];
  double min_value;
  double max_value;
  double last_value;
  uint64_t actionable_samples;
  uint64_t spec_lifted_samples;
  uint32_t flags_or;
  uint32_t flags_and;
  double max_confidence;
} component_summary_t;

typedef struct signal_entropy {
  uint64_t runtime_records;
  uint64_t reached_records;
  uint64_t triggered_records;
  uint64_t rnt_records;
  uint64_t spec_lifted_records;
  uint64_t rnt_spec_lifted_records;
  uint64_t spec_df_samples;
  uint32_t spec_df_unique_count;
  double spec_df_unique_values[MAX_UNIQUE_VALUES];
  double spec_df_min;
  double spec_df_max;
  component_summary_t components[MAX_COMPONENTS];
  uint32_t component_count;
} signal_entropy_t;

static void usage(const char *argv0) {
  fprintf(stderr, "usage: %s <runtime.jsonl> [runtime.jsonl ...]\n", argv0);
}

static const char *json_find_key(const char *line, const char *key) {
  char pattern[128];
  int written = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
  if (written <= 0 || (size_t)written >= sizeof(pattern)) return NULL;
  return strstr(line, pattern);
}

static int json_bool_field(const char *line, const char *key, int *out) {
  const char *p = json_find_key(line, key);
  if (!p || !out) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
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
  if (errno || end == p || !isfinite(v)) return 0;
  *out = v;
  return 1;
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

static int same_key(const component_key_t *a, const component_key_t *b) {
  return a->source_id == b->source_id && a->kind == b->kind &&
         a->atom_id == b->atom_id && a->role == b->role;
}

static int double_seen(const double *values, uint32_t count, double value) {
  for (uint32_t i = 0; i < count; i++)
    if (values[i] == value) return 1;
  return 0;
}

static void remember_unique(double *values, uint32_t *count, double value) {
  if (double_seen(values, *count, value)) return;
  if (*count < MAX_UNIQUE_VALUES) values[(*count)++] = value;
}

static int component_sample_is_actionable(const component_key_t *key,
                                          uint32_t flags, double value,
                                          double confidence) {
  if (!key || !key->atom_id) return 0;
  if (!isfinite(value) || confidence <= 0.0) return 0;
  if (!(flags & FORMTRIG_COMPONENT_TC_ROOTED)) return 0;
  if (!(flags & FORMTRIG_COMPONENT_LIFTED)) return 0;
  if (!(flags & FORMTRIG_COMPONENT_SPEC_LIFTED)) return 0;
  if (flags & FORMTRIG_COMPONENT_HEURISTIC_LIFTED) return 0;
  if (flags & FORMTRIG_COMPONENT_MANUAL_TARGET) return 0;
  if (flags & FORMTRIG_COMPONENT_INPUT_INFLUENCE) return 0;

  int lower = (flags & FORMTRIG_COMPONENT_LOWER_IS_BETTER) != 0;
  int higher = (flags & FORMTRIG_COMPONENT_HIGHER_IS_BETTER) != 0;
  if (lower == higher) return 0;
  if (lower && value < 0.0) return 0;
  if (higher && value <= 0.0) return 0;
  return 1;
}

static component_summary_t *component_slot(signal_entropy_t *s,
                                           const component_key_t *key) {
  for (uint32_t i = 0; i < s->component_count; i++)
    if (same_key(&s->components[i].key, key)) return &s->components[i];
  if (s->component_count >= MAX_COMPONENTS) return NULL;
  component_summary_t *slot = &s->components[s->component_count++];
  memset(slot, 0, sizeof(*slot));
  slot->key = *key;
  return slot;
}

static void record_component(signal_entropy_t *s, const component_key_t *key,
                             double value, uint32_t flags,
                             double confidence) {
  component_summary_t *component = component_slot(s, key);
  if (!component) return;
  if (!component->samples || value < component->min_value)
    component->min_value = value;
  if (!component->samples || value > component->max_value)
    component->max_value = value;
  if (!component->samples)
    component->flags_and = flags;
  else
    component->flags_and &= flags;
  component->flags_or |= flags;
  if (!component->samples || confidence > component->max_confidence)
    component->max_confidence = confidence;
  component->last_value = value;
  component->samples++;
  if (flags & FORMTRIG_COMPONENT_SPEC_LIFTED) component->spec_lifted_samples++;
  if (component_sample_is_actionable(key, flags, value, confidence))
    component->actionable_samples++;
  remember_unique(component->unique_values, &component->unique_count, value);
}

static void ingest_line(signal_entropy_t *s, const char *line) {
  int bool_value = 0;
  double df = 0.0;
  int reached = 0;
  int triggered = 0;
  int uses_spec = 0;

  s->runtime_records++;
  if (json_bool_field(line, "reached", &bool_value) && bool_value) {
    reached = 1;
    s->reached_records++;
  }
  if ((json_bool_field(line, "crash_predicate", &bool_value) && bool_value) ||
      (json_bool_field(line, "triggered", &bool_value) && bool_value)) {
    triggered = 1;
    s->triggered_records++;
  }
  if (json_bool_field(line, "uses_spec_lifted", &bool_value) && bool_value) {
    uses_spec = 1;
    s->spec_lifted_records++;
  }

  if (!reached || triggered) return;

  s->rnt_records++;
  if (uses_spec) s->rnt_spec_lifted_records++;

  if (json_double_field(line, "D_F_spec_lifted", &df)) {
    if (!s->spec_df_samples || df < s->spec_df_min) s->spec_df_min = df;
    if (!s->spec_df_samples || df > s->spec_df_max) s->spec_df_max = df;
    s->spec_df_samples++;
    remember_unique(s->spec_df_unique_values, &s->spec_df_unique_count, df);
  }

  const char *array = strstr(line, "\"components\":[");
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

    uint64_t kind = 0;
    uint64_t atom_id = 0;
    uint64_t role = 0;
    uint64_t source_id = 0;
    uint64_t flags = 0;
    double value = 0.0;
    double confidence = 0.0;
    if (!json_u64_field(object, "kind", &kind) ||
        !json_u64_field(object, "atom_id", &atom_id) ||
        !json_u64_field(object, "role", &role) ||
        !json_u64_field(object, "source_id", &source_id) ||
        !json_u64_field(object, "flags", &flags) ||
        !json_double_field(object, "confidence", &confidence) ||
        !json_double_field(object, "value", &value)) {
      p = end;
      continue;
    }

    component_key_t key;
    key.kind = (uint32_t)kind;
    key.atom_id = (uint32_t)atom_id;
    key.role = (uint32_t)role;
    key.source_id = source_id;
    record_component(s, &key, value, (uint32_t)flags, confidence);
    p = end;
  }
}

static int load_jsonl(signal_entropy_t *s, const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  char line[65536];
  while (fgets(line, sizeof(line), f)) {
    if (line[0] == '\0' || line[0] == '\n') continue;
    ingest_line(s, line);
  }
  fclose(f);
  return 1;
}

static void print_double_array(const double *values, uint32_t count) {
  printf("[");
  for (uint32_t i = 0; i < count; i++) {
    if (i) printf(", ");
    printf("%.17g", values[i]);
  }
  printf("]");
}

static void print_json(const signal_entropy_t *s) {
  uint32_t constant_components = 0;
  uint32_t variable_components = 0;
  uint32_t spec_component_keys = 0;
  uint32_t actionable_component_keys = 0;
  uint32_t constant_actionable_components = 0;
  uint32_t variable_actionable_components = 0;
  for (uint32_t i = 0; i < s->component_count; i++) {
    int constant =
        s->components[i].samples > 1 && s->components[i].unique_count <= 1;
    int variable = s->components[i].unique_count > 1;
    if (s->components[i].samples > 1 && s->components[i].unique_count <= 1)
      constant_components++;
    if (s->components[i].unique_count > 1) variable_components++;
    if (s->components[i].spec_lifted_samples) spec_component_keys++;
    if (s->components[i].actionable_samples) {
      actionable_component_keys++;
      if (constant) constant_actionable_components++;
      if (variable) variable_actionable_components++;
    }
  }
  int constant_df = s->spec_df_samples > 1 && s->spec_df_unique_count <= 1;
  int pass = variable_actionable_components > 0;
  const char *diagnosis = "variable_actionable_lifted_components";
  if (!pass && !s->component_count)
    diagnosis = "no_lifted_components";
  else if (!pass && !actionable_component_keys)
    diagnosis = "no_actionable_lifted_components";
  else if (!pass)
    diagnosis = "constant_actionable_lifted_components";
  else if (constant_df)
    diagnosis = "constant_scalar_d_f_variable_components";

  printf("{\n");
  printf("  \"status\": \"%s\",\n", pass ? "pass" : "fail");
  printf("  \"diagnosis\": \"%s\",\n", diagnosis);
  printf("  \"runtime_records\": %llu,\n",
         (unsigned long long)s->runtime_records);
  printf("  \"reached_records\": %llu,\n",
         (unsigned long long)s->reached_records);
  printf("  \"triggered_records\": %llu,\n",
         (unsigned long long)s->triggered_records);
  printf("  \"rnt_records\": %llu,\n",
         (unsigned long long)s->rnt_records);
  printf("  \"spec_lifted_records\": %llu,\n",
         (unsigned long long)s->spec_lifted_records);
  printf("  \"rnt_spec_lifted_records\": %llu,\n",
         (unsigned long long)s->rnt_spec_lifted_records);
  printf("  \"spec_d_f_samples\": %llu,\n",
         (unsigned long long)s->spec_df_samples);
  printf("  \"spec_d_f_unique\": %u,\n", s->spec_df_unique_count);
  printf("  \"spec_d_f_constant\": %s,\n",
         constant_df ? "true" : "false");
  if (s->spec_df_samples) {
    printf("  \"spec_d_f_min\": %.17g,\n", s->spec_df_min);
    printf("  \"spec_d_f_max\": %.17g,\n", s->spec_df_max);
  } else {
    printf("  \"spec_d_f_min\": null,\n");
    printf("  \"spec_d_f_max\": null,\n");
  }
  printf("  \"component_keys\": %u,\n", s->component_count);
  printf("  \"spec_component_keys\": %u,\n", spec_component_keys);
  printf("  \"actionable_component_keys\": %u,\n", actionable_component_keys);
  printf("  \"constant_components\": %u,\n", constant_components);
  printf("  \"variable_components\": %u,\n", variable_components);
  printf("  \"constant_actionable_components\": %u,\n",
         constant_actionable_components);
  printf("  \"variable_actionable_components\": %u,\n",
         variable_actionable_components);
  printf("  \"components\": [\n");
  for (uint32_t i = 0; i < s->component_count; i++) {
    const component_summary_t *c = &s->components[i];
    printf("    {\"kind\":%u,\"atom_id\":%u,\"role\":%u,",
           c->key.kind, c->key.atom_id, c->key.role);
    printf("\"source_id\":%llu,\"samples\":%llu,",
           (unsigned long long)c->key.source_id,
           (unsigned long long)c->samples);
    printf("\"spec_lifted_samples\":%llu,\"actionable_samples\":%llu,",
           (unsigned long long)c->spec_lifted_samples,
           (unsigned long long)c->actionable_samples);
    printf("\"flags_or\":%u,\"flags_and\":%u,\"max_confidence\":%.17g,",
           c->flags_or, c->flags_and, c->max_confidence);
    printf("\"unique_values\":%u,\"constant\":%s,",
           c->unique_count,
           (c->samples > 1 && c->unique_count <= 1) ? "true" : "false");
    printf("\"min\":%.17g,\"max\":%.17g,\"values\":",
           c->min_value, c->max_value);
    print_double_array(c->unique_values, c->unique_count);
    printf("}%s\n", i + 1u == s->component_count ? "" : ",");
  }
  printf("  ]\n");
  printf("}\n");
}

int main(int argc, char **argv) {
  if (argc < 2) {
    usage(argv[0]);
    return 2;
  }

  signal_entropy_t s;
  memset(&s, 0, sizeof(s));
  for (int i = 1; i < argc; i++)
    if (!load_jsonl(&s, argv[i])) return 2;

  print_json(&s);
  uint32_t variable_actionable_components = 0;
  for (uint32_t i = 0; i < s.component_count; i++) {
    if (s.components[i].actionable_samples &&
        s.components[i].unique_count > 1)
      variable_actionable_components++;
  }
  return variable_actionable_components ? 0 : 1;
}
