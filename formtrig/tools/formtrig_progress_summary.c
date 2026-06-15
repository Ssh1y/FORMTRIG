#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <errno.h>
#include <float.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_REASON_BUCKETS 64u

typedef struct reason_bucket {
  char reason[96];
  uint64_t count;
} reason_bucket_t;

typedef struct summary {
  uint64_t progress_events;
  uint64_t saved_progress_events;
  uint64_t saved_triggered_progress_events;
  uint64_t saved_non_trigger_progress_events;
  uint64_t calibrated_frontier_events;
  uint64_t frontier_accept_events;
  uint64_t frontier_progress_accept_events;
  uint64_t frontier_reject_events;
  uint64_t stability_confirmed_events;
  uint64_t stability_reject_events;
  uint64_t typed_skip_events;
  uint64_t typed_skip_not_replay_stable_events;
  uint64_t typed_stage_start_events;
  uint64_t typed_stage_end_events;
  uint64_t triggered_events;
  uint64_t reached_events;
  uint64_t lifted_events;
  uint64_t stable_events;
  uint64_t component_events;
  uint64_t actionable_component_events;
  uint64_t atom_signal_events;
  uint64_t role_signal_events;
  uint64_t d_f_count;
  uint64_t d_f_spec_lifted_count;
  uint64_t d_f_heuristic_lifted_count;
  uint64_t d_f_manual_lifted_count;
  uint64_t used_d_f_spec_lifted_count;
  uint64_t used_d_f_heuristic_lifted_count;
  uint64_t used_d_f_manual_lifted_count;
  uint64_t observed_d_f_spec_lifted_count;
  uint64_t observed_d_f_heuristic_lifted_count;
  uint64_t observed_d_f_manual_lifted_count;
  uint64_t spec_lifted_events;
  uint64_t heuristic_lifted_events;
  uint64_t manual_lifted_events;
  uint64_t observed_spec_lifted_events;
  uint64_t observed_heuristic_lifted_events;
  uint64_t observed_manual_lifted_events;
  double d_f_min;
  double d_f_max;
  double d_f_spec_lifted_min;
  double d_f_spec_lifted_max;
  uint64_t execs_done;
  uint64_t corpus_count;
  uint64_t afl_saved_crashes;
  uint64_t formtrig_seen_execs;
  uint64_t formtrig_reached_execs;
  uint64_t formtrig_triggered_execs;
  uint64_t formtrig_queued_progress;
  uint64_t formtrig_frontier_updates;
  uint64_t formtrig_typed_execs;
  uint64_t formtrig_typed_finds;
  uint64_t formtrig_stability_checks;
  uint64_t formtrig_stability_failures;
  uint64_t formtrig_progress_log_events;
  uint64_t formtrig_saved_progress_log_seen;
  uint64_t formtrig_saved_triggered_log_seen;
  uint64_t formtrig_saved_non_trigger_log_seen;
  uint64_t formtrig_progress_log_dropped;
  reason_bucket_t reasons[MAX_REASON_BUCKETS];
  reason_bucket_t accept_reasons[MAX_REASON_BUCKETS];
  reason_bucket_t reject_reasons[MAX_REASON_BUCKETS];
  reason_bucket_t stability_reasons[MAX_REASON_BUCKETS];
  uint32_t reason_count;
  uint32_t accept_reason_count;
  uint32_t reject_reason_count;
  uint32_t stability_reason_count;
} summary_t;

static void usage(const char *argv0) {
  fprintf(stderr, "usage: %s <fuzzer_stats> <formtrig_progress.jsonl>\n",
          argv0);
}

static int read_u64_field(const char *line, const char *key, uint64_t *out) {
  size_t n = strlen(key);
  const char *p = line;
  while (*p == ' ' || *p == '\t') p++;
  if (strncmp(p, key, n)) return 0;
  p += n;
  while (*p == ' ' || *p == '\t') p++;
  if (*p != ':') return 0;
  p++;
  while (*p == ' ' || *p == '\t') p++;
  char *end = NULL;
  errno = 0;
  unsigned long long v = strtoull(p, &end, 10);
  if (errno || end == p) return 0;
  *out = (uint64_t)v;
  return 1;
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
  char *end = NULL;
  errno = 0;
  unsigned long long v = strtoull(p, &end, 10);
  if (errno || end == p) return 0;
  *out = (uint64_t)v;
  return 1;
}

static int json_double_field(const char *line, const char *key, double *out) {
  const char *p = json_find_key(line, key);
  if (!p) return 0;
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
    if (i + 1 < out_size) out[i++] = *p;
    p++;
  }
  out[i] = '\0';
  return *p == '"';
}

static void add_reason_bucket(reason_bucket_t *buckets, uint32_t *count,
                              const char *reason) {
  if (!reason || !*reason) reason = "unknown";
  for (uint32_t i = 0; i < *count; i++) {
    if (!strcmp(buckets[i].reason, reason)) {
      buckets[i].count++;
      return;
    }
  }
  if (*count >= MAX_REASON_BUCKETS) return;
  reason_bucket_t *bucket = &buckets[(*count)++];
  snprintf(bucket->reason, sizeof(bucket->reason), "%s", reason);
  bucket->count = 1;
}

static void add_reason(summary_t *s, const char *reason) {
  add_reason_bucket(s->reasons, &s->reason_count, reason);
}

static uint64_t reason_count(const reason_bucket_t *buckets, uint32_t count,
                             const char *reason) {
  for (uint32_t i = 0; i < count; i++)
    if (!strcmp(buckets[i].reason, reason)) return buckets[i].count;
  return 0;
}

static void ingest_stats_line(summary_t *s, const char *line) {
  (void)read_u64_field(line, "execs_done", &s->execs_done);
  (void)read_u64_field(line, "corpus_count", &s->corpus_count);
  (void)read_u64_field(line, "saved_crashes", &s->afl_saved_crashes);
  (void)read_u64_field(line, "formtrig_seen_execs", &s->formtrig_seen_execs);
  (void)read_u64_field(line, "formtrig_reached_execs",
                       &s->formtrig_reached_execs);
  (void)read_u64_field(line, "formtrig_triggered_execs",
                       &s->formtrig_triggered_execs);
  (void)read_u64_field(line, "formtrig_queued_progress",
                       &s->formtrig_queued_progress);
  (void)read_u64_field(line, "formtrig_frontier_updates",
                       &s->formtrig_frontier_updates);
  (void)read_u64_field(line, "formtrig_typed_execs",
                       &s->formtrig_typed_execs);
  (void)read_u64_field(line, "formtrig_typed_finds",
                       &s->formtrig_typed_finds);
  (void)read_u64_field(line, "formtrig_stability_checks",
                       &s->formtrig_stability_checks);
  (void)read_u64_field(line, "formtrig_stability_failures",
                       &s->formtrig_stability_failures);
  (void)read_u64_field(line, "formtrig_progress_log_events",
                       &s->formtrig_progress_log_events);
  (void)read_u64_field(line, "formtrig_saved_progress_log_seen",
                       &s->formtrig_saved_progress_log_seen);
  (void)read_u64_field(line, "formtrig_saved_triggered_log_seen",
                       &s->formtrig_saved_triggered_log_seen);
  (void)read_u64_field(line, "formtrig_saved_non_trigger_log_seen",
                       &s->formtrig_saved_non_trigger_log_seen);
  (void)read_u64_field(line, "formtrig_progress_log_dropped",
                       &s->formtrig_progress_log_dropped);
}

static void ingest_progress_line(summary_t *s, const char *line) {
  char event[96] = {0};
  char reason[96] = {0};
  int boolean_value = 0;
  uint64_t u64_value = 0;
  uint64_t source_flags = 0;
  uint64_t observed_source_flags = 0;
  double d_value = 0.0;
  int line_triggered = 0;

  s->progress_events++;
  (void)json_u64_field(line, "source_flags", &source_flags);
  (void)json_u64_field(line, "observed_source_flags", &observed_source_flags);
  if (json_bool_field(line, "triggered", &boolean_value) && boolean_value)
    line_triggered = 1;

  if (json_string_field(line, "event", event, sizeof(event))) {
    if (!strcmp(event, "saved_progress")) {
      s->saved_progress_events++;
      if (line_triggered)
        s->saved_triggered_progress_events++;
      else
        s->saved_non_trigger_progress_events++;
    }
    if (!strcmp(event, "frontier_accept")) s->frontier_accept_events++;
    if (!strcmp(event, "calibrated_frontier"))
      s->calibrated_frontier_events++;
    if (!strcmp(event, "frontier_reject")) s->frontier_reject_events++;
    if (!strcmp(event, "stability_confirmed")) s->stability_confirmed_events++;
    if (!strcmp(event, "stability_reject")) s->stability_reject_events++;
    if (!strcmp(event, "typed_skip")) s->typed_skip_events++;
    if (!strcmp(event, "typed_stage_start")) s->typed_stage_start_events++;
    if (!strcmp(event, "typed_stage_end")) s->typed_stage_end_events++;
  }

  if (json_string_field(line, "reason", reason, sizeof(reason))) {
    add_reason(s, reason);
    if (!strcmp(event, "typed_skip") && !strcmp(reason, "not_replay_stable"))
      s->typed_skip_not_replay_stable_events++;
    if (!strcmp(event, "frontier_accept") &&
        strcmp(reason, "initial_frontier_seed"))
      s->frontier_progress_accept_events++;
    if (!strcmp(event, "frontier_accept") || !strcmp(event, "saved_progress"))
      add_reason_bucket(s->accept_reasons, &s->accept_reason_count, reason);
    if (!strcmp(event, "frontier_reject"))
      add_reason_bucket(s->reject_reasons, &s->reject_reason_count, reason);
    if (!strcmp(event, "stability_confirmed") ||
        !strcmp(event, "stability_reject"))
      add_reason_bucket(s->stability_reasons, &s->stability_reason_count,
                        reason);
  }

  if (json_bool_field(line, "reached", &boolean_value) && boolean_value)
    s->reached_events++;
  if (line_triggered) s->triggered_events++;
  if (json_bool_field(line, "lifted", &boolean_value) && boolean_value)
    s->lifted_events++;
  if (json_bool_field(line, "stable", &boolean_value) && boolean_value)
    s->stable_events++;

  if (json_u64_field(line, "components", &u64_value) && u64_value > 0)
    s->component_events++;
  if (json_u64_field(line, "actionable_components", &u64_value) &&
      u64_value > 0)
    s->actionable_component_events++;
  if (json_u64_field(line, "atom_signals", &u64_value) && u64_value > 0)
    s->atom_signal_events++;
  if (strstr(line, "\"role_bits\":") && !strstr(line, "\"role_bits\":0"))
    s->role_signal_events++;

  if (json_double_field(line, "d_f", &d_value)) {
    if (s->d_f_count == 0 || d_value < s->d_f_min) s->d_f_min = d_value;
    if (s->d_f_count == 0 || d_value > s->d_f_max) s->d_f_max = d_value;
    s->d_f_count++;
  }

  if (json_double_field(line, "d_f_spec_lifted", &d_value) && d_value >= 0.0) {
    if (s->d_f_spec_lifted_count == 0 ||
        d_value < s->d_f_spec_lifted_min)
      s->d_f_spec_lifted_min = d_value;
    if (s->d_f_spec_lifted_count == 0 ||
        d_value > s->d_f_spec_lifted_max)
      s->d_f_spec_lifted_max = d_value;
    s->d_f_spec_lifted_count++;
    if (source_flags & 2u) s->used_d_f_spec_lifted_count++;
    if (observed_source_flags & 2u) s->observed_d_f_spec_lifted_count++;
  }
  if (json_double_field(line, "d_f_heuristic_lifted", &d_value) &&
      d_value >= 0.0) {
    s->d_f_heuristic_lifted_count++;
    if (source_flags & 4u) s->used_d_f_heuristic_lifted_count++;
    if (observed_source_flags & 4u) s->observed_d_f_heuristic_lifted_count++;
  }
  if (json_double_field(line, "d_f_manual_lifted", &d_value) &&
      d_value >= 0.0) {
    s->d_f_manual_lifted_count++;
    if (source_flags & 8u) s->used_d_f_manual_lifted_count++;
    if (observed_source_flags & 8u) s->observed_d_f_manual_lifted_count++;
  }

  if (source_flags & 2u) s->spec_lifted_events++;
  if (source_flags & 4u) s->heuristic_lifted_events++;
  if (source_flags & 8u) s->manual_lifted_events++;
  if (observed_source_flags & 2u) s->observed_spec_lifted_events++;
  if (observed_source_flags & 4u) s->observed_heuristic_lifted_events++;
  if (observed_source_flags & 8u) s->observed_manual_lifted_events++;
}

static int read_lines(const char *path, void (*fn)(summary_t *, const char *),
                      summary_t *s) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  char line[8192];
  while (fgets(line, sizeof(line), f)) fn(s, line);
  fclose(f);
  return 1;
}

static void print_json_string(FILE *out, const char *s) {
  fputc('"', out);
  if (s) {
    for (; *s; s++) {
      if (*s == '"' || *s == '\\') fputc('\\', out);
      if ((unsigned char)*s < 0x20) {
        fprintf(out, "\\u%04x", (unsigned char)*s);
      } else {
        fputc(*s, out);
      }
    }
  }
  fputc('"', out);
}

static int summary_d_f_constant(const summary_t *s) {
  return s->d_f_count > 1 && s->d_f_min == s->d_f_max;
}

static int summary_spec_d_f_constant(const summary_t *s) {
  return s->used_d_f_spec_lifted_count > 1 &&
         s->d_f_spec_lifted_min == s->d_f_spec_lifted_max;
}

static int summary_has_queued_progress(const summary_t *s) {
  return s->formtrig_queued_progress || s->saved_progress_events;
}

static int summary_terminal_triggered(const summary_t *s) {
  return s->formtrig_triggered_execs || s->triggered_events ||
         s->afl_saved_crashes;
}

static uint64_t summary_terminal_triggered_count(const summary_t *s) {
  uint64_t runtime_triggered = s->formtrig_triggered_execs;
  if (s->triggered_events > runtime_triggered)
    runtime_triggered = s->triggered_events;
  return runtime_triggered + s->afl_saved_crashes;
}

static int summary_has_frontier_progress(const summary_t *s) {
  return s->frontier_progress_accept_events != 0;
}

static int summary_has_non_trigger_progress(const summary_t *s) {
  return s->saved_non_trigger_progress_events ||
         s->frontier_progress_accept_events;
}

static int summary_has_tc_rooted_progress(const summary_t *s) {
  return summary_terminal_triggered(s) || summary_has_queued_progress(s) ||
         summary_has_frontier_progress(s);
}

static const char *summary_progress_status(const summary_t *s) {
  if (summary_terminal_triggered(s)) return "triggered";
  if (summary_has_queued_progress(s)) return "progress_queued";
  if (summary_has_frontier_progress(s)) return "frontier_progress_observed";
  return "not_progressing";
}

static const char *summary_limiting_reason(const summary_t *s) {
  if (summary_terminal_triggered(s)) return "terminal_triggered";
  if (summary_has_queued_progress(s)) return "none";
  if (summary_has_frontier_progress(s)) return "frontier_progress_not_queued";
  if (!s->formtrig_seen_execs && !s->progress_events)
    return "no_formtrig_signal";
  if (!s->formtrig_reached_execs && !s->reached_events)
    return "target_not_reached";
  if (!s->actionable_component_events)
    return "no_actionable_component";
  if (!s->atom_signal_events) return "no_atom_signal";
  if (!s->role_signal_events) return "no_role_signal";
  if (s->stability_reject_events || s->formtrig_stability_failures)
    return "progress_not_replay_stable";
  if (reason_count(s->reasons, s->reason_count, "no_valid_hot_range") &&
      !s->typed_stage_start_events)
    return "no_valid_hot_range";
  if (summary_spec_d_f_constant(s) &&
      (s->formtrig_typed_execs || s->typed_stage_start_events))
    return "typed_mutation_no_lift_delta";
  if (summary_spec_d_f_constant(s)) return "constant_spec_d_f";
  if (summary_d_f_constant(s)) return "constant_d_f";
  if (reason_count(s->reject_reasons, s->reject_reason_count,
                   "high_priority_regression"))
    return "high_priority_regression";
  if (reason_count(s->reject_reasons, s->reject_reason_count,
                   "dominated_by_existing_frontier") ||
      s->frontier_reject_events)
    return "dominance_rejected";
  if (s->typed_skip_not_replay_stable_events && !s->typed_stage_start_events)
    return "typed_stage_parent_not_replay_stable";
  if (!s->formtrig_typed_execs && !s->typed_stage_start_events)
    return "typed_mutation_not_run";
  return "no_progress_queued";
}

static void print_reason_object(const char *name, const reason_bucket_t *reasons,
                                uint32_t reason_count_value) {
  printf("  ");
  print_json_string(stdout, name);
  printf(": {");
  for (uint32_t i = 0; i < reason_count_value; i++) {
    if (i) printf(",");
    printf("\n    ");
    print_json_string(stdout, reasons[i].reason);
    printf(": %llu", (unsigned long long)reasons[i].count);
  }
  if (reason_count_value) printf("\n  ");
  printf("}");
}

static void print_summary(const summary_t *s) {
  printf("{\n");
  printf("  \"execs_done\": %llu,\n", (unsigned long long)s->execs_done);
  printf("  \"corpus_count\": %llu,\n", (unsigned long long)s->corpus_count);
  printf("  \"afl_saved_crashes\": %llu,\n",
         (unsigned long long)s->afl_saved_crashes);
  printf("  \"formtrig_seen_execs\": %llu,\n",
         (unsigned long long)s->formtrig_seen_execs);
  printf("  \"formtrig_reached_execs\": %llu,\n",
         (unsigned long long)s->formtrig_reached_execs);
  printf("  \"formtrig_triggered_execs\": %llu,\n",
         (unsigned long long)s->formtrig_triggered_execs);
  printf("  \"terminal_triggered_execs\": %llu,\n",
         (unsigned long long)summary_terminal_triggered_count(s));
  printf("  \"formtrig_queued_progress\": %llu,\n",
         (unsigned long long)s->formtrig_queued_progress);
  printf("  \"formtrig_frontier_updates\": %llu,\n",
         (unsigned long long)s->formtrig_frontier_updates);
  printf("  \"formtrig_typed_execs\": %llu,\n",
         (unsigned long long)s->formtrig_typed_execs);
  printf("  \"formtrig_typed_finds\": %llu,\n",
         (unsigned long long)s->formtrig_typed_finds);
  printf("  \"formtrig_stability_checks\": %llu,\n",
         (unsigned long long)s->formtrig_stability_checks);
  printf("  \"formtrig_stability_failures\": %llu,\n",
         (unsigned long long)s->formtrig_stability_failures);
  printf("  \"formtrig_progress_log_events\": %llu,\n",
         (unsigned long long)s->formtrig_progress_log_events);
  printf("  \"formtrig_saved_progress_log_seen\": %llu,\n",
         (unsigned long long)s->formtrig_saved_progress_log_seen);
  printf("  \"formtrig_saved_triggered_log_seen\": %llu,\n",
         (unsigned long long)s->formtrig_saved_triggered_log_seen);
  printf("  \"formtrig_saved_non_trigger_log_seen\": %llu,\n",
         (unsigned long long)s->formtrig_saved_non_trigger_log_seen);
  printf("  \"formtrig_progress_log_dropped\": %llu,\n",
         (unsigned long long)s->formtrig_progress_log_dropped);
  printf("  \"progress_events\": %llu,\n",
         (unsigned long long)s->progress_events);
  printf("  \"saved_progress_events\": %llu,\n",
         (unsigned long long)s->saved_progress_events);
  printf("  \"saved_triggered_progress_events\": %llu,\n",
         (unsigned long long)s->saved_triggered_progress_events);
  printf("  \"saved_non_trigger_progress_events\": %llu,\n",
         (unsigned long long)s->saved_non_trigger_progress_events);
  printf("  \"calibrated_frontier_events\": %llu,\n",
         (unsigned long long)s->calibrated_frontier_events);
  printf("  \"frontier_accept_events\": %llu,\n",
         (unsigned long long)s->frontier_accept_events);
  printf("  \"frontier_progress_accept_events\": %llu,\n",
         (unsigned long long)s->frontier_progress_accept_events);
  printf("  \"non_trigger_progress_events\": %llu,\n",
         (unsigned long long)(s->saved_non_trigger_progress_events +
                              s->frontier_progress_accept_events));
  printf("  \"has_tc_rooted_progress\": %s,\n",
         summary_has_tc_rooted_progress(s) ? "true" : "false");
  printf("  \"has_queued_progress\": %s,\n",
         summary_has_queued_progress(s) ? "true" : "false");
  printf("  \"has_frontier_progress\": %s,\n",
         summary_has_frontier_progress(s) ? "true" : "false");
  printf("  \"has_non_trigger_progress\": %s,\n",
         summary_has_non_trigger_progress(s) ? "true" : "false");
  printf("  \"frontier_reject_events\": %llu,\n",
         (unsigned long long)s->frontier_reject_events);
  printf("  \"stability_confirmed_events\": %llu,\n",
         (unsigned long long)s->stability_confirmed_events);
  printf("  \"stability_reject_events\": %llu,\n",
         (unsigned long long)s->stability_reject_events);
  printf("  \"typed_skip_events\": %llu,\n",
         (unsigned long long)s->typed_skip_events);
  printf("  \"typed_skip_not_replay_stable_events\": %llu,\n",
         (unsigned long long)s->typed_skip_not_replay_stable_events);
  printf("  \"typed_stage_start_events\": %llu,\n",
         (unsigned long long)s->typed_stage_start_events);
  printf("  \"typed_stage_end_events\": %llu,\n",
         (unsigned long long)s->typed_stage_end_events);
  printf("  \"triggered_events\": %llu,\n",
         (unsigned long long)s->triggered_events);
  printf("  \"reached_events\": %llu,\n",
         (unsigned long long)s->reached_events);
  printf("  \"lifted_events\": %llu,\n", (unsigned long long)s->lifted_events);
  printf("  \"spec_lifted_events\": %llu,\n",
         (unsigned long long)s->spec_lifted_events);
  printf("  \"heuristic_lifted_events\": %llu,\n",
         (unsigned long long)s->heuristic_lifted_events);
  printf("  \"manual_lifted_events\": %llu,\n",
         (unsigned long long)s->manual_lifted_events);
  printf("  \"observed_spec_lifted_events\": %llu,\n",
         (unsigned long long)s->observed_spec_lifted_events);
  printf("  \"observed_heuristic_lifted_events\": %llu,\n",
         (unsigned long long)s->observed_heuristic_lifted_events);
  printf("  \"observed_manual_lifted_events\": %llu,\n",
         (unsigned long long)s->observed_manual_lifted_events);
  printf("  \"d_f_spec_lifted_count\": %llu,\n",
         (unsigned long long)s->d_f_spec_lifted_count);
  printf("  \"d_f_heuristic_lifted_count\": %llu,\n",
         (unsigned long long)s->d_f_heuristic_lifted_count);
  printf("  \"d_f_manual_lifted_count\": %llu,\n",
         (unsigned long long)s->d_f_manual_lifted_count);
  printf("  \"used_d_f_spec_lifted_count\": %llu,\n",
         (unsigned long long)s->used_d_f_spec_lifted_count);
  printf("  \"used_d_f_heuristic_lifted_count\": %llu,\n",
         (unsigned long long)s->used_d_f_heuristic_lifted_count);
  printf("  \"used_d_f_manual_lifted_count\": %llu,\n",
         (unsigned long long)s->used_d_f_manual_lifted_count);
  printf("  \"observed_d_f_spec_lifted_count\": %llu,\n",
         (unsigned long long)s->observed_d_f_spec_lifted_count);
  printf("  \"observed_d_f_heuristic_lifted_count\": %llu,\n",
         (unsigned long long)s->observed_d_f_heuristic_lifted_count);
  printf("  \"observed_d_f_manual_lifted_count\": %llu,\n",
         (unsigned long long)s->observed_d_f_manual_lifted_count);
  printf("  \"stable_events\": %llu,\n", (unsigned long long)s->stable_events);
  printf("  \"component_events\": %llu,\n",
         (unsigned long long)s->component_events);
  printf("  \"actionable_component_events\": %llu,\n",
         (unsigned long long)s->actionable_component_events);
  printf("  \"atom_signal_events\": %llu,\n",
         (unsigned long long)s->atom_signal_events);
  printf("  \"role_signal_events\": %llu,\n",
         (unsigned long long)s->role_signal_events);
  printf("  \"progress_status\": ");
  print_json_string(stdout, summary_progress_status(s));
  printf(",\n");
  printf("  \"limiting_reason\": ");
  print_json_string(stdout, summary_limiting_reason(s));
  printf(",\n");
  printf("  \"d_f_constant\": %s,\n",
         summary_d_f_constant(s) ? "true" : "false");
  printf("  \"d_f_spec_lifted_constant\": %s,\n",
         summary_spec_d_f_constant(s) ? "true" : "false");
  printf("  \"has_lifted_signal\": %s,\n",
         s->lifted_events ? "true" : "false");
  printf("  \"has_actionable_component\": %s,\n",
         s->actionable_component_events ? "true" : "false");
  printf("  \"has_atom_signal\": %s,\n",
         s->atom_signal_events ? "true" : "false");
  printf("  \"has_role_signal\": %s,\n",
         s->role_signal_events ? "true" : "false");
  if (s->d_f_count) {
    printf("  \"d_f_min\": %.17g,\n", s->d_f_min);
    printf("  \"d_f_max\": %.17g,\n", s->d_f_max);
  } else {
    printf("  \"d_f_min\": null,\n");
    printf("  \"d_f_max\": null,\n");
  }
  if (s->d_f_spec_lifted_count) {
    printf("  \"d_f_spec_lifted_min\": %.17g,\n", s->d_f_spec_lifted_min);
    printf("  \"d_f_spec_lifted_max\": %.17g,\n",
           s->d_f_spec_lifted_max);
  } else {
    printf("  \"d_f_spec_lifted_min\": null,\n");
    printf("  \"d_f_spec_lifted_max\": null,\n");
  }
  print_reason_object("reason_counts", s->reasons, s->reason_count);
  printf(",\n");
  print_reason_object("accept_reason_counts", s->accept_reasons,
                      s->accept_reason_count);
  printf(",\n");
  print_reason_object("reject_reason_counts", s->reject_reasons,
                      s->reject_reason_count);
  printf(",\n");
  print_reason_object("stability_reason_counts", s->stability_reasons,
                      s->stability_reason_count);
  printf("\n");
  printf("}\n");
}

int main(int argc, char **argv) {
  if (argc != 3) {
    usage(argv[0]);
    return 2;
  }

  summary_t s;
  memset(&s, 0, sizeof(s));
  s.d_f_min = DBL_MAX;
  s.d_f_max = -DBL_MAX;
  s.d_f_spec_lifted_min = DBL_MAX;
  s.d_f_spec_lifted_max = -DBL_MAX;

  if (!read_lines(argv[1], ingest_stats_line, &s)) return 2;
  if (!read_lines(argv[2], ingest_progress_line, &s)) return 2;
  print_summary(&s);
  return 0;
}
