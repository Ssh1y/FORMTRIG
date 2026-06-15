#define _POSIX_C_SOURCE 200809L

#include "formtrig/formtrig_abi.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_EVENT_IDS 1024u
#define MAX_UNMAPPED 64u

typedef struct audit_state {
  uint64_t event_ids[MAX_EVENT_IDS];
  uint32_t event_id_count;
  uint64_t progress_events;
  uint64_t accepted_events;
  uint64_t accepted_lifted_events;
  uint64_t lifted_components;
  uint64_t nonzero_lifted_components;
  uint64_t mapped_lifted_components;
  uint64_t unmapped_lifted_components;
  uint64_t spec_lifted_components;
  uint64_t spec_lifted_atom_components;
  uint64_t mapped_spec_lifted_components;
  uint64_t unmapped_spec_lifted_components;
  uint64_t heuristic_lifted_components;
  uint64_t manual_lifted_components;
  uint64_t observed_heuristic_lifted_events;
  uint64_t observed_manual_lifted_events;
  uint64_t accepted_unmapped_lifted_events;
  uint64_t accepted_without_mapped_lifted_events;
  uint64_t accepted_unmapped_spec_lifted_events;
  uint64_t accepted_without_mapped_spec_lifted_events;
  uint64_t accepted_heuristic_lifted_events;
  uint64_t accepted_manual_lifted_events;
  uint64_t unmapped_source_ids[MAX_UNMAPPED];
  uint32_t unmapped_source_id_count;
} audit_state_t;

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s <formtrig_runtime_event_map.csv> "
          "<formtrig_progress.jsonl>\n",
          argv0);
}

static int parse_u64(const char *s, int base, uint64_t *out) {
  if (!s || !out) return 0;
  char *end = NULL;
  errno = 0;
  unsigned long long v = strtoull(s, &end, base);
  if (errno || end == s) return 0;
  *out = (uint64_t)v;
  return 1;
}

static const char *csv_next_field(const char *p, char *out, size_t out_size) {
  if (!p || !out || !out_size) return NULL;
  size_t i = 0;
  while (*p && *p != ',' && *p != '\n' && *p != '\r') {
    if (i + 1 < out_size) out[i++] = *p;
    p++;
  }
  out[i] = '\0';
  if (*p == ',') return p + 1;
  return p;
}

static int event_id_known(const audit_state_t *s, uint64_t event_id) {
  for (uint32_t i = 0; i < s->event_id_count; i++)
    if (s->event_ids[i] == event_id) return 1;
  return 0;
}

static void remember_unmapped(audit_state_t *s, uint64_t source_id) {
  if (!source_id || event_id_known(s, source_id)) return;
  for (uint32_t i = 0; i < s->unmapped_source_id_count; i++)
    if (s->unmapped_source_ids[i] == source_id) return;
  if (s->unmapped_source_id_count < MAX_UNMAPPED)
    s->unmapped_source_ids[s->unmapped_source_id_count++] = source_id;
}

static int load_event_map(audit_state_t *s, const char *path) {
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
    uint64_t event_id = 0;
    for (uint32_t col = 1; col <= 7u && p; col++) {
      p = csv_next_field(p, field, sizeof(field));
      if (col == 7u && parse_u64(field, 16, &event_id)) {
        if (s->event_id_count < MAX_EVENT_IDS)
          s->event_ids[s->event_id_count++] = event_id;
      }
    }
  }

  fclose(f);
  return s->event_id_count > 0;
}

static const char *json_find_key(const char *line, const char *key) {
  char pattern[128];
  int written = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
  if (written <= 0 || (size_t)written >= sizeof(pattern)) return NULL;
  return strstr(line, pattern);
}

static int json_bool_field(const char *line, const char *key, int *out) {
  const char *p = json_find_key(line, key);
  if (!p) return 0;
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
  if (*p == '1') {
    *out = 1;
    return 1;
  }
  if (*p == '0') {
    *out = 0;
    return 1;
  }
  return 0;
}

static int json_u64_field(const char *line, const char *key, uint64_t *out) {
  const char *p = json_find_key(line, key);
  if (!p) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  return parse_u64(p, 10, out);
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
    if (i + 1 < out_size) out[i++] = *p;
    p++;
  }
  out[i] = '\0';
  return *p == '"';
}

static int event_is_accepting(const char *event) {
  return !strcmp(event, "frontier_accept") ||
         !strcmp(event, "calibrated_frontier") ||
         !strcmp(event, "saved_progress");
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

static void ingest_progress_line(audit_state_t *s, const char *line) {
  char event[96] = {0};
  int triggered = 0;
  int lifted_line = 0;
  int accepted = 0;
  uint64_t line_mapped_lifted = 0;
  uint64_t line_unmapped_lifted = 0;
  uint64_t line_mapped_spec_lifted = 0;
  uint64_t line_unmapped_spec_lifted = 0;
  uint64_t source_flags = 0;
  uint64_t observed_source_flags = 0;

  s->progress_events++;
  if (json_string_field(line, "event", event, sizeof(event)))
    accepted = event_is_accepting(event);
  (void)json_bool_field(line, "triggered", &triggered);
  (void)json_bool_field(line, "lifted", &lifted_line);
  (void)json_u64_field(line, "source_flags", &source_flags);
  (void)json_u64_field(line, "observed_source_flags", &observed_source_flags);
  if (observed_source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED)
    s->observed_heuristic_lifted_events++;
  if (observed_source_flags & FORMTRIG_SOURCE_MANUAL_TARGET)
    s->observed_manual_lifted_events++;
  if (accepted) s->accepted_events++;
  if (accepted && lifted_line && !triggered) s->accepted_lifted_events++;
  if (accepted && !triggered &&
      (source_flags & FORMTRIG_SOURCE_HEURISTIC_LIFTED))
    s->accepted_heuristic_lifted_events++;
  if (accepted && !triggered && (source_flags & FORMTRIG_SOURCE_MANUAL_TARGET))
    s->accepted_manual_lifted_events++;

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
    uint64_t flags = 0;
    uint64_t source_id = 0;
    (void)json_u64_field(object, "atom_id", &atom_id);
    (void)json_u64_field(object, "flags", &flags);
    (void)json_u64_field(object, "source_id", &source_id);

    if ((flags & FORMTRIG_COMPONENT_LIFTED) != 0u) {
      int source_known = event_id_known(s, source_id);

      s->lifted_components++;
      if ((flags & FORMTRIG_COMPONENT_SPEC_LIFTED) != 0u)
        s->spec_lifted_components++;
      if ((flags & FORMTRIG_COMPONENT_HEURISTIC_LIFTED) != 0u)
        s->heuristic_lifted_components++;
      if ((flags & FORMTRIG_COMPONENT_MANUAL_TARGET) != 0u)
        s->manual_lifted_components++;

      if (atom_id != 0u) {
        s->nonzero_lifted_components++;
        if (source_known) {
          s->mapped_lifted_components++;
          line_mapped_lifted++;
        } else {
          s->unmapped_lifted_components++;
          line_unmapped_lifted++;
          remember_unmapped(s, source_id);
        }

        if ((flags & FORMTRIG_COMPONENT_SPEC_LIFTED) != 0u) {
          s->spec_lifted_atom_components++;
          if (source_known) {
            s->mapped_spec_lifted_components++;
            line_mapped_spec_lifted++;
          } else {
            s->unmapped_spec_lifted_components++;
            line_unmapped_spec_lifted++;
            remember_unmapped(s, source_id);
          }
        }
      }
    }

    p = end;
  }

  if (accepted && lifted_line && !triggered) {
    if (line_unmapped_lifted) s->accepted_unmapped_lifted_events++;
    if (!line_mapped_lifted) s->accepted_without_mapped_lifted_events++;
    if (line_unmapped_spec_lifted) s->accepted_unmapped_spec_lifted_events++;
    if ((source_flags & FORMTRIG_SOURCE_SPEC_LIFTED) &&
        !line_mapped_spec_lifted)
      s->accepted_without_mapped_spec_lifted_events++;
  }
}

static int load_progress(audit_state_t *s, const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  char line[65536];
  while (fgets(line, sizeof(line), f)) ingest_progress_line(s, line);
  fclose(f);
  return 1;
}

static void print_json(const audit_state_t *s, int pass) {
  printf("{\n");
  printf("  \"status\": \"%s\",\n", pass ? "pass" : "fail");
  printf("  \"runtime_event_ids\": %u,\n", s->event_id_count);
  printf("  \"progress_events\": %llu,\n",
         (unsigned long long)s->progress_events);
  printf("  \"accepted_events\": %llu,\n",
         (unsigned long long)s->accepted_events);
  printf("  \"accepted_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_lifted_events);
  printf("  \"lifted_components\": %llu,\n",
         (unsigned long long)s->lifted_components);
  printf("  \"nonzero_lifted_components\": %llu,\n",
         (unsigned long long)s->nonzero_lifted_components);
  printf("  \"mapped_lifted_components\": %llu,\n",
         (unsigned long long)s->mapped_lifted_components);
  printf("  \"unmapped_lifted_components\": %llu,\n",
         (unsigned long long)s->unmapped_lifted_components);
  printf("  \"spec_lifted_components\": %llu,\n",
         (unsigned long long)s->spec_lifted_components);
  printf("  \"spec_lifted_atom_components\": %llu,\n",
         (unsigned long long)s->spec_lifted_atom_components);
  printf("  \"mapped_spec_lifted_components\": %llu,\n",
         (unsigned long long)s->mapped_spec_lifted_components);
  printf("  \"unmapped_spec_lifted_components\": %llu,\n",
         (unsigned long long)s->unmapped_spec_lifted_components);
  printf("  \"heuristic_lifted_components\": %llu,\n",
         (unsigned long long)s->heuristic_lifted_components);
  printf("  \"manual_lifted_components\": %llu,\n",
         (unsigned long long)s->manual_lifted_components);
  printf("  \"observed_heuristic_lifted_events\": %llu,\n",
         (unsigned long long)s->observed_heuristic_lifted_events);
  printf("  \"observed_manual_lifted_events\": %llu,\n",
         (unsigned long long)s->observed_manual_lifted_events);
  printf("  \"accepted_unmapped_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_unmapped_lifted_events);
  printf("  \"accepted_without_mapped_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_without_mapped_lifted_events);
  printf("  \"accepted_unmapped_spec_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_unmapped_spec_lifted_events);
  printf("  \"accepted_without_mapped_spec_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_without_mapped_spec_lifted_events);
  printf("  \"accepted_heuristic_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_heuristic_lifted_events);
  printf("  \"accepted_manual_lifted_events\": %llu,\n",
         (unsigned long long)s->accepted_manual_lifted_events);
  printf("  \"unmapped_source_ids\": [");
  for (uint32_t i = 0; i < s->unmapped_source_id_count; i++) {
    if (i) printf(", ");
    printf("%llu", (unsigned long long)s->unmapped_source_ids[i]);
  }
  printf("]\n");
  printf("}\n");
}

int main(int argc, char **argv) {
  if (argc != 3) {
    usage(argv[0]);
    return 2;
  }

  audit_state_t s;
  memset(&s, 0, sizeof(s));
  if (!load_event_map(&s, argv[1])) return 2;
  if (!load_progress(&s, argv[2])) return 2;

  int pass = s.unmapped_spec_lifted_components == 0 &&
             s.accepted_unmapped_spec_lifted_events == 0 &&
             s.accepted_without_mapped_spec_lifted_events == 0 &&
             s.accepted_heuristic_lifted_events == 0 &&
             s.accepted_manual_lifted_events == 0;
  print_json(&s, pass);
  return pass ? 0 : 1;
}
