#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct map_summary {
  uint64_t rows;
  uint64_t exact;
  uint64_t ambiguous;
  uint64_t missing;
  uint64_t lift_allowed;
  uint64_t lift_blocked;
  uint64_t semantic_role_collapse;
  uint64_t insufficient_binding;
} map_summary_t;

typedef struct diagnosis {
  char progress_status[64];
  char limiting_reason[96];
  char lift_feature_audit_status[32];
  char binding_signal_status[32];
  char binding_signal_diagnosis[96];
  uint64_t execs_done;
  uint64_t afl_saved_crashes;
  uint64_t formtrig_seen_execs;
  uint64_t formtrig_reached_execs;
  uint64_t formtrig_triggered_execs;
  uint64_t triggered_events;
  uint64_t terminal_triggered_execs;
  uint64_t formtrig_queued_progress;
  uint64_t saved_progress_events;
  uint64_t saved_triggered_progress_events;
  uint64_t saved_non_trigger_progress_events;
  uint64_t frontier_progress_accept_events;
  uint64_t typed_stage_start_events;
  uint64_t typed_skip_not_replay_stable_events;
  uint64_t spec_lifted_events;
  uint64_t heuristic_lifted_events;
  uint64_t manual_lifted_events;
  uint64_t observed_spec_lifted_events;
  uint64_t observed_heuristic_lifted_events;
  uint64_t observed_manual_lifted_events;
  uint64_t actionable_component_events;
  uint64_t atom_signal_events;
  uint64_t role_signal_events;
  int d_f_constant;
  int d_f_spec_lifted_constant;
  int has_lifted_signal;
  int has_actionable_component;
  int has_atom_signal;
  int has_role_signal;
  int lift_feature_audit_present;
  int lift_feature_audit_pass;
  int binding_signal_present;
  int binding_signal_pass;
  int triggered_candidate_lift_delta;
  int non_trigger_candidate_lift_delta;
  int lift_delta_only_on_triggered_candidates;
  map_summary_t map;
} diagnosis_t;

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s <formtrig_summary.json> "
          "[formtrig_runtime_event_map.csv] "
          "[formtrig_lift_feature_audit.json] "
          "[formtrig_binding_signal_diagnosis.json]\n",
          argv0);
}

static char *read_file(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) {
    perror(path);
    return NULL;
  }
  if (fseek(f, 0, SEEK_END) != 0) {
    fclose(f);
    return NULL;
  }
  long size = ftell(f);
  if (size < 0) {
    fclose(f);
    return NULL;
  }
  rewind(f);
  char *buf = (char *)calloc((size_t)size + 1u, 1u);
  if (!buf) {
    fclose(f);
    return NULL;
  }
  if (size && fread(buf, 1u, (size_t)size, f) != (size_t)size) {
    free(buf);
    fclose(f);
    return NULL;
  }
  fclose(f);
  return buf;
}

static const char *json_find_key(const char *json, const char *key) {
  char pattern[160];
  int written = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
  if (written <= 0 || (size_t)written >= sizeof(pattern)) return NULL;
  return strstr(json, pattern);
}

static int json_u64_field(const char *json, const char *key, uint64_t *out) {
  const char *p = json_find_key(json, key);
  if (!p || !out) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  char *end = NULL;
  errno = 0;
  unsigned long long v = strtoull(p, &end, 10);
  if (errno || end == p) return 0;
  *out = (uint64_t)v;
  return 1;
}

static int json_bool_field(const char *json, const char *key, int *out) {
  const char *p = json_find_key(json, key);
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
  return 0;
}

static int json_string_field(const char *json, const char *key, char *out,
                             size_t out_size) {
  const char *p = json_find_key(json, key);
  if (!p || !out || !out_size) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
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

static void copy_field(char *dst, size_t dst_size, const char *src) {
  if (!dst || !dst_size) return;
  if (!src) src = "";
  size_t i = 0;
  while (src[i] && i + 1u < dst_size) {
    dst[i] = src[i];
    i++;
  }
  dst[i] = '\0';
}

static int load_event_map(map_summary_t *m, const char *path) {
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
    char mapping_status[64] = {0};
    char lift_allowed[64] = {0};
    char reason[128] = {0};
    for (uint32_t col = 1; col <= 12u && p; col++) {
      p = csv_next_field(p, field, sizeof(field));
      if (col == 8u) copy_field(mapping_status, sizeof(mapping_status), field);
      if (col == 11u) copy_field(lift_allowed, sizeof(lift_allowed), field);
      if (col == 12u) copy_field(reason, sizeof(reason), field);
    }

    m->rows++;
    if (!strcmp(mapping_status, "exact")) m->exact++;
    if (!strcmp(mapping_status, "ambiguous")) m->ambiguous++;
    if (!strcmp(mapping_status, "missing")) m->missing++;
    if (!strcmp(lift_allowed, "true"))
      m->lift_allowed++;
    else
      m->lift_blocked++;
    if (strstr(reason, "semantic_role_collapse"))
      m->semantic_role_collapse++;
    if (strstr(reason, "insufficient_binding"))
      m->insufficient_binding++;
  }

  fclose(f);
  return 1;
}

static void load_summary(diagnosis_t *d, const char *json) {
  (void)json_u64_field(json, "execs_done", &d->execs_done);
  (void)json_u64_field(json, "afl_saved_crashes", &d->afl_saved_crashes);
  (void)json_u64_field(json, "formtrig_seen_execs",
                       &d->formtrig_seen_execs);
  (void)json_u64_field(json, "formtrig_reached_execs",
                       &d->formtrig_reached_execs);
  (void)json_u64_field(json, "formtrig_triggered_execs",
                       &d->formtrig_triggered_execs);
  (void)json_u64_field(json, "triggered_events", &d->triggered_events);
  (void)json_u64_field(json, "terminal_triggered_execs",
                       &d->terminal_triggered_execs);
  if (!d->terminal_triggered_execs) {
    uint64_t runtime_triggered = d->formtrig_triggered_execs;
    if (d->triggered_events > runtime_triggered)
      runtime_triggered = d->triggered_events;
    d->terminal_triggered_execs = runtime_triggered + d->afl_saved_crashes;
  }
  (void)json_u64_field(json, "formtrig_queued_progress",
                       &d->formtrig_queued_progress);
  (void)json_u64_field(json, "saved_progress_events",
                       &d->saved_progress_events);
  (void)json_u64_field(json, "saved_triggered_progress_events",
                       &d->saved_triggered_progress_events);
  (void)json_u64_field(json, "saved_non_trigger_progress_events",
                       &d->saved_non_trigger_progress_events);
  (void)json_u64_field(json, "frontier_progress_accept_events",
                       &d->frontier_progress_accept_events);
  (void)json_u64_field(json, "typed_stage_start_events",
                       &d->typed_stage_start_events);
  (void)json_u64_field(json, "typed_skip_not_replay_stable_events",
                       &d->typed_skip_not_replay_stable_events);
  (void)json_u64_field(json, "spec_lifted_events", &d->spec_lifted_events);
  (void)json_u64_field(json, "heuristic_lifted_events",
                       &d->heuristic_lifted_events);
  (void)json_u64_field(json, "manual_lifted_events",
                       &d->manual_lifted_events);
  (void)json_u64_field(json, "observed_spec_lifted_events",
                       &d->observed_spec_lifted_events);
  (void)json_u64_field(json, "observed_heuristic_lifted_events",
                       &d->observed_heuristic_lifted_events);
  (void)json_u64_field(json, "observed_manual_lifted_events",
                       &d->observed_manual_lifted_events);
  (void)json_u64_field(json, "actionable_component_events",
                       &d->actionable_component_events);
  (void)json_u64_field(json, "atom_signal_events", &d->atom_signal_events);
  (void)json_u64_field(json, "role_signal_events", &d->role_signal_events);
  (void)json_bool_field(json, "d_f_constant", &d->d_f_constant);
  (void)json_bool_field(json, "d_f_spec_lifted_constant",
                        &d->d_f_spec_lifted_constant);
  (void)json_bool_field(json, "has_lifted_signal", &d->has_lifted_signal);
  (void)json_bool_field(json, "has_actionable_component",
                        &d->has_actionable_component);
  (void)json_bool_field(json, "has_atom_signal", &d->has_atom_signal);
  (void)json_bool_field(json, "has_role_signal", &d->has_role_signal);
  (void)json_string_field(json, "progress_status", d->progress_status,
                          sizeof(d->progress_status));
  (void)json_string_field(json, "limiting_reason", d->limiting_reason,
                          sizeof(d->limiting_reason));
}

static void load_lift_audit(diagnosis_t *d, const char *json) {
  d->lift_feature_audit_present = 1;
  if (json_string_field(json, "status", d->lift_feature_audit_status,
                        sizeof(d->lift_feature_audit_status)) &&
      !strcmp(d->lift_feature_audit_status, "pass")) {
    d->lift_feature_audit_pass = 1;
  }
}

static void load_binding_signal(diagnosis_t *d, const char *json) {
  d->binding_signal_present = 1;
  if (json_string_field(json, "status", d->binding_signal_status,
                        sizeof(d->binding_signal_status)) &&
      !strcmp(d->binding_signal_status, "pass")) {
    d->binding_signal_pass = 1;
  }
  (void)json_string_field(json, "diagnosis", d->binding_signal_diagnosis,
                          sizeof(d->binding_signal_diagnosis));
  (void)json_bool_field(json, "triggered_candidate_lift_delta",
                        &d->triggered_candidate_lift_delta);
  (void)json_bool_field(json, "non_trigger_candidate_lift_delta",
                        &d->non_trigger_candidate_lift_delta);
  (void)json_bool_field(json, "lift_delta_only_on_triggered_candidates",
                        &d->lift_delta_only_on_triggered_candidates);
}

static int has_queued_progress(const diagnosis_t *d) {
  return d->formtrig_queued_progress || d->saved_progress_events;
}

static int has_frontier_progress(const diagnosis_t *d) {
  return d->frontier_progress_accept_events != 0;
}

static int has_non_trigger_progress(const diagnosis_t *d) {
  return d->saved_non_trigger_progress_events ||
         d->frontier_progress_accept_events;
}

static int has_tc_rooted_progress(const diagnosis_t *d) {
  return d->terminal_triggered_execs || has_queued_progress(d) ||
         has_frontier_progress(d);
}

static int pretrigger_lift_guidance_ready(const diagnosis_t *d) {
  return has_non_trigger_progress(d) || d->non_trigger_candidate_lift_delta;
}

static const char *primary_diagnosis(const diagnosis_t *d) {
  if (d->manual_lifted_events) return "manual_target_lift_used";
  if (d->heuristic_lifted_events) return "heuristic_lift_used";
  if (d->observed_manual_lifted_events) return "manual_target_lift_observed";
  if (d->observed_heuristic_lifted_events)
    return "heuristic_lift_observed";
  if (d->map.semantic_role_collapse) return "semantic_role_collapse";
  if (d->map.insufficient_binding) return "insufficient_binding";
  if (d->map.missing || d->map.ambiguous) return "binding_not_runtime_grounded";
  if (d->lift_feature_audit_present && !d->lift_feature_audit_pass)
    return "lift_feature_provenance_failed";
  if (d->terminal_triggered_execs || !strcmp(d->progress_status, "triggered"))
    return "triggered";
  if (!d->formtrig_reached_execs &&
      !strcmp(d->limiting_reason, "target_not_reached"))
    return "seed_does_not_reach_target";
  if (!d->formtrig_seen_execs) return "no_formtrig_runtime_signal";
  if (!d->formtrig_reached_execs) return "seed_does_not_reach_target";
  if (!d->spec_lifted_events) return "no_spec_lifted_signal";
  if (!d->has_actionable_component || !d->actionable_component_events)
    return "no_actionable_lifted_component";
  if (!d->has_atom_signal || !d->atom_signal_events) return "no_atom_signal";
  if (!d->has_role_signal || !d->role_signal_events) return "no_role_signal";
  if (!strcmp(d->limiting_reason, "no_valid_hot_range"))
    return "no_valid_hot_range";
  if (!strcmp(d->limiting_reason, "typed_mutation_no_lift_delta"))
    return "typed_mutation_no_lift_delta";
  if (d->d_f_spec_lifted_constant) return "constant_lift_signal";
  if (d->d_f_constant) return "constant_final_d_f";
  if (has_non_trigger_progress(d)) return "queued_tc_rooted_progress";
  if (has_queued_progress(d)) return "queued_trigger_progress";
  if (has_frontier_progress(d)) return "frontier_tc_rooted_progress_not_saved";
  if (d->binding_signal_present && !d->binding_signal_pass &&
      d->binding_signal_diagnosis[0])
    return d->binding_signal_diagnosis;
  if (!strcmp(d->limiting_reason, "typed_stage_parent_not_replay_stable") ||
      (d->typed_skip_not_replay_stable_events && !d->typed_stage_start_events))
    return "typed_stage_parent_not_replay_stable";
  if (!strcmp(d->limiting_reason, "high_priority_regression"))
    return "higher_priority_component_regressed";
  if (!strcmp(d->limiting_reason, "dominance_rejected"))
    return "no_new_non_dominated_progress";
  if (!strcmp(d->limiting_reason, "typed_mutation_not_run"))
    return "typed_mutation_not_run";
  return d->limiting_reason[0] ? d->limiting_reason : "not_progressing";
}

static int campaign_ready(const diagnosis_t *d) {
  if (d->manual_lifted_events || d->heuristic_lifted_events) return 0;
  if (d->observed_manual_lifted_events || d->observed_heuristic_lifted_events)
    return 0;
  if (d->map.semantic_role_collapse || d->map.insufficient_binding ||
      d->map.missing || d->map.ambiguous)
    return 0;
  if (d->lift_feature_audit_present && !d->lift_feature_audit_pass) return 0;
  if (d->binding_signal_present && !d->binding_signal_pass) return 0;
  if (!d->formtrig_seen_execs || !d->formtrig_reached_execs) return 0;
  if (!d->spec_lifted_events || !d->has_actionable_component ||
      !d->has_atom_signal || !d->has_role_signal)
    return 0;
  if (d->d_f_spec_lifted_constant) return 0;
  return 1;
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

static void print_json(const diagnosis_t *d) {
  int ready = campaign_ready(d);
  const char *diag = primary_diagnosis(d);
  printf("{\n");
  printf("  \"status\": \"%s\",\n", ready ? "ready" : "not_ready");
  printf("  \"experiment_ready\": %s,\n", ready ? "true" : "false");
  printf("  \"has_tc_rooted_progress\": %s,\n",
         has_tc_rooted_progress(d) ? "true" : "false");
  printf("  \"has_queued_progress\": %s,\n",
         has_queued_progress(d) ? "true" : "false");
  printf("  \"has_frontier_progress\": %s,\n",
         has_frontier_progress(d) ? "true" : "false");
  printf("  \"has_non_trigger_progress\": %s,\n",
         has_non_trigger_progress(d) ? "true" : "false");
  printf("  \"pretrigger_lift_guidance_ready\": %s,\n",
         pretrigger_lift_guidance_ready(d) ? "true" : "false");
  printf("  \"triggered_candidate_lift_delta\": %s,\n",
         d->triggered_candidate_lift_delta ? "true" : "false");
  printf("  \"non_trigger_candidate_lift_delta\": %s,\n",
         d->non_trigger_candidate_lift_delta ? "true" : "false");
  printf("  \"lift_delta_only_on_triggered_candidates\": %s,\n",
         d->lift_delta_only_on_triggered_candidates ? "true" : "false");
  printf("  \"diagnosis\": ");
  print_json_string(diag);
  printf(",\n");
  printf("  \"progress_status\": ");
  print_json_string(d->progress_status);
  printf(",\n");
  printf("  \"limiting_reason\": ");
  print_json_string(d->limiting_reason);
  printf(",\n");
  printf("  \"execs_done\": %llu,\n", (unsigned long long)d->execs_done);
  printf("  \"formtrig_seen_execs\": %llu,\n",
         (unsigned long long)d->formtrig_seen_execs);
  printf("  \"formtrig_reached_execs\": %llu,\n",
         (unsigned long long)d->formtrig_reached_execs);
  printf("  \"formtrig_triggered_execs\": %llu,\n",
         (unsigned long long)d->formtrig_triggered_execs);
  printf("  \"triggered_events\": %llu,\n",
         (unsigned long long)d->triggered_events);
  printf("  \"afl_saved_crashes\": %llu,\n",
         (unsigned long long)d->afl_saved_crashes);
  printf("  \"terminal_triggered_execs\": %llu,\n",
         (unsigned long long)d->terminal_triggered_execs);
  printf("  \"formtrig_queued_progress\": %llu,\n",
         (unsigned long long)d->formtrig_queued_progress);
  printf("  \"saved_progress_events\": %llu,\n",
         (unsigned long long)d->saved_progress_events);
  printf("  \"saved_triggered_progress_events\": %llu,\n",
         (unsigned long long)d->saved_triggered_progress_events);
  printf("  \"saved_non_trigger_progress_events\": %llu,\n",
         (unsigned long long)d->saved_non_trigger_progress_events);
  printf("  \"frontier_progress_accept_events\": %llu,\n",
         (unsigned long long)d->frontier_progress_accept_events);
  printf("  \"non_trigger_progress_events\": %llu,\n",
         (unsigned long long)(d->saved_non_trigger_progress_events +
                              d->frontier_progress_accept_events));
  printf("  \"typed_stage_start_events\": %llu,\n",
         (unsigned long long)d->typed_stage_start_events);
  printf("  \"typed_skip_not_replay_stable_events\": %llu,\n",
         (unsigned long long)d->typed_skip_not_replay_stable_events);
  printf("  \"spec_lifted_events\": %llu,\n",
         (unsigned long long)d->spec_lifted_events);
  printf("  \"heuristic_lifted_events\": %llu,\n",
         (unsigned long long)d->heuristic_lifted_events);
  printf("  \"manual_lifted_events\": %llu,\n",
         (unsigned long long)d->manual_lifted_events);
  printf("  \"observed_spec_lifted_events\": %llu,\n",
         (unsigned long long)d->observed_spec_lifted_events);
  printf("  \"observed_heuristic_lifted_events\": %llu,\n",
         (unsigned long long)d->observed_heuristic_lifted_events);
  printf("  \"observed_manual_lifted_events\": %llu,\n",
         (unsigned long long)d->observed_manual_lifted_events);
  printf("  \"actionable_component_events\": %llu,\n",
         (unsigned long long)d->actionable_component_events);
  printf("  \"atom_signal_events\": %llu,\n",
         (unsigned long long)d->atom_signal_events);
  printf("  \"role_signal_events\": %llu,\n",
         (unsigned long long)d->role_signal_events);
  printf("  \"d_f_constant\": %s,\n", d->d_f_constant ? "true" : "false");
  printf("  \"d_f_spec_lifted_constant\": %s,\n",
         d->d_f_spec_lifted_constant ? "true" : "false");
  printf("  \"runtime_event_map\": {\n");
  printf("    \"rows\": %llu,\n", (unsigned long long)d->map.rows);
  printf("    \"exact\": %llu,\n", (unsigned long long)d->map.exact);
  printf("    \"ambiguous\": %llu,\n",
         (unsigned long long)d->map.ambiguous);
  printf("    \"missing\": %llu,\n", (unsigned long long)d->map.missing);
  printf("    \"lift_allowed\": %llu,\n",
         (unsigned long long)d->map.lift_allowed);
  printf("    \"lift_blocked\": %llu,\n",
         (unsigned long long)d->map.lift_blocked);
  printf("    \"semantic_role_collapse\": %llu,\n",
         (unsigned long long)d->map.semantic_role_collapse);
  printf("    \"insufficient_binding\": %llu\n",
         (unsigned long long)d->map.insufficient_binding);
  printf("  },\n");
  printf("  \"lift_feature_audit_status\": ");
  print_json_string(d->lift_feature_audit_present
                        ? d->lift_feature_audit_status
                        : "not_provided");
  printf(",\n");
  printf("  \"binding_signal_status\": ");
  print_json_string(d->binding_signal_present ? d->binding_signal_status
                                              : "not_provided");
  printf(",\n");
  printf("  \"binding_signal_diagnosis\": ");
  print_json_string(d->binding_signal_present ? d->binding_signal_diagnosis
                                              : "not_provided");
  printf("\n");
  printf("}\n");
}

int main(int argc, char **argv) {
  if (argc < 2 || argc > 5) {
    usage(argv[0]);
    return 2;
  }

  char *summary = read_file(argv[1]);
  if (!summary) return 2;

  diagnosis_t d;
  memset(&d, 0, sizeof(d));
  load_summary(&d, summary);
  free(summary);

  if (argc >= 3 && strcmp(argv[2], "-") != 0) {
    if (!load_event_map(&d.map, argv[2])) return 2;
  }
  if (argc >= 4 && strcmp(argv[3], "-") != 0) {
    char *audit = read_file(argv[3]);
    if (!audit) return 2;
    load_lift_audit(&d, audit);
    free(audit);
  }
  if (argc >= 5 && strcmp(argv[4], "-") != 0) {
    char *signal = read_file(argv[4]);
    if (!signal) return 2;
    load_binding_signal(&d, signal);
    free(signal);
  }

  print_json(&d);
  return 0;
}
