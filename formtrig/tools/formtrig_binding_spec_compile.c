#define _POSIX_C_SOURCE 200809L

#include "formtrig/formtrig_abi.h"

#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ATOMS 128u
#define MAX_BINDINGS 512u

typedef enum section_kind {
  SECTION_NONE = 0,
  SECTION_TC,
  SECTION_ATOMS,
  SECTION_BINDINGS
} section_kind_t;

typedef struct site_row {
  uint32_t site_id;
  char kind[32];
  char function[160];
  uint32_t inst_no;
  char opcode[64];
  char file[256];
  uint32_t line;
  uint32_t column;
} site_row_t;

typedef struct atom_spec {
  uint32_t id;
  char expr[256];
  char kind[64];
  char root[128];
} atom_spec_t;

typedef struct binding_spec {
  char id[128];
  uint32_t atom_id;
  char role[64];
  char expr[256];
  char label[128];
  uint32_t event_kind;
  uint32_t site_id;
  uint32_t line;
  uint32_t inst_no;
  uint32_t column;
  uint32_t component_kind;
  uint32_t priority;
  uint32_t have_event_kind;
  uint32_t have_site_id;
  uint32_t have_line;
  uint32_t have_inst_no;
  uint32_t have_column;
  uint32_t have_component;
  uint32_t have_priority;
  char site_kind[32];
  char function[160];
  char opcode[64];
  char file[256];
  char direction[16];
  char value_mode[32];
  char value[64];
  char confidence[64];
  char phase_index[32];
  char observe_window[32];
  uint32_t range_start;
  uint32_t range_len;
  uint32_t have_range_start;
  uint32_t have_range_len;
  char mutation_hint[32];
  char mutation_value[64];
  char mutation_hook[512];
  char relation_from[64];
  char relation_to[64];
  char object_expr[128];
} binding_spec_t;

static char tc_id[128];
static char tc_category[64];
static char tc_expression[512];
static atom_spec_t atoms[MAX_ATOMS];
static uint32_t atom_count;
static binding_spec_t bindings[MAX_BINDINGS];
static uint32_t binding_count;
static site_row_t *sites;
static uint32_t site_count;
static uint32_t site_capacity;
static uint32_t error_count;

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s [--site-map site_map.tsv] [--out OUT] "
          "<binding_spec.yaml>\n",
          argv0);
}

static void copy_field(char *dst, size_t dst_size, const char *src) {
  if (!dst || !dst_size) return;
  if (!src) src = "";
  snprintf(dst, dst_size, "%s", src);
}

static char *trim(char *s) {
  while (*s && isspace((unsigned char)*s)) s++;
  char *end = s + strlen(s);
  while (end > s && isspace((unsigned char)end[-1])) *--end = '\0';
  return s;
}

static void strip_inline_comment(char *s) {
  char *start = s;
  int quote = 0;
  for (; *s; s++) {
    if ((*s == '"' || *s == '\'') && (s == start || s[-1] != '\\')) {
      if (!quote)
        quote = *s;
      else if (quote == *s)
        quote = 0;
    }
    if (*s == '#' && !quote) {
      *s = '\0';
      return;
    }
  }
}

static char *strip_quotes(char *s) {
  s = trim(s);
  size_t len = strlen(s);
  if (len >= 2u &&
      ((s[0] == '"' && s[len - 1u] == '"') ||
       (s[0] == '\'' && s[len - 1u] == '\''))) {
    s[len - 1u] = '\0';
    return s + 1;
  }
  return s;
}

static int parse_kv(char *line, char **key, char **value) {
  char *colon = strchr(line, ':');
  if (!colon) return 0;
  *colon = '\0';
  *key = trim(line);
  *value = strip_quotes(colon + 1);
  return **key != '\0';
}

static int parse_u32(const char *s, uint32_t *out) {
  if (!s || !*s || !out) return 0;
  char *end = NULL;
  errno = 0;
  unsigned long value = strtoul(s, &end, 0);
  if (errno || end == s || *trim(end) != '\0' || value > UINT32_MAX)
    return 0;
  *out = (uint32_t)value;
  return 1;
}

static int eq(const char *a, const char *b) {
  return a && b && strcmp(a, b) == 0;
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

static uint32_t event_kind_from_text(const char *s) {
  if (!s || !*s) return UINT32_MAX;
  uint32_t numeric = 0;
  if (parse_u32(s, &numeric)) return numeric;
  if (eq(s, "canary") || eq(s, "magma_canary") ||
      eq(s, "target_canary"))
    return FORMTRIG_EVENT_CANARY;
  if (eq(s, "cmp") || eq(s, "compare") || eq(s, "icmp")) return 7u;
  if (eq(s, "branch") || eq(s, "br")) return 8u;
  if (eq(s, "mem") || eq(s, "memory") || eq(s, "load") || eq(s, "store"))
    return 9u;
  if (eq(s, "div") || eq(s, "mod") || eq(s, "rem")) return 10u;
  if (eq(s, "arith") || eq(s, "binary") || eq(s, "add") ||
      eq(s, "sub") || eq(s, "mul"))
    return 11u;
  return UINT32_MAX;
}

static uint32_t component_kind_from_text(const char *s) {
  if (!s || !*s) return 0;
  uint32_t numeric = 0;
  if (parse_u32(s, &numeric)) return numeric;
  if (eq(s, "native_distance")) return FORMTRIG_COMPONENT_NATIVE_DISTANCE;
  if (eq(s, "lifted_distance")) return FORMTRIG_COMPONENT_LIFTED_DISTANCE;
  if (eq(s, "boundary_margin") || eq(s, "root_state"))
    return FORMTRIG_COMPONENT_BOUNDARY_MARGIN;
  if (eq(s, "operand_influence") || eq(s, "input_influence"))
    return FORMTRIG_COMPONENT_OPERAND_INFLUENCE;
  if (eq(s, "guard_progress") || eq(s, "guard"))
    return FORMTRIG_COMPONENT_GUARD_PROGRESS;
  if (eq(s, "producer_use") || eq(s, "producer") || eq(s, "use"))
    return FORMTRIG_COMPONENT_PRODUCER_USE;
  if (eq(s, "lifecycle_prefix") || eq(s, "lifecycle"))
    return FORMTRIG_COMPONENT_LIFECYCLE_PREFIX;
  if (eq(s, "object_identity") || eq(s, "same_object"))
    return FORMTRIG_COMPONENT_OBJECT_IDENTITY;
  if (eq(s, "event_phase") || eq(s, "phase"))
    return FORMTRIG_COMPONENT_EVENT_PHASE;
  return 0;
}

static int read_site_row(char *line, site_row_t *row) {
  char *fields[8] = {0};
  char *saveptr = NULL;
  for (uint32_t i = 0; i < 8u; i++) {
    fields[i] = strtok_r(i ? NULL : line, "\t\r\n", &saveptr);
    if (!fields[i]) return 0;
  }

  if (!parse_u32(fields[0], &row->site_id)) return 0;
  copy_field(row->kind, sizeof(row->kind), fields[1]);
  copy_field(row->function, sizeof(row->function), fields[2]);
  if (!parse_u32(fields[3], &row->inst_no)) return 0;
  copy_field(row->opcode, sizeof(row->opcode), fields[4]);
  copy_field(row->file, sizeof(row->file), fields[5]);
  if (!parse_u32(fields[6], &row->line)) row->line = 0;
  if (!parse_u32(fields[7], &row->column)) row->column = 0;
  return 1;
}

static int load_site_map(const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  char line[1024];
  while (fgets(line, sizeof(line), f)) {
    site_row_t row;
    memset(&row, 0, sizeof(row));
    if (!read_site_row(line, &row)) continue;
    if (site_count == site_capacity) {
      uint32_t new_capacity = site_capacity ? site_capacity * 2u : 65536u;
      site_row_t *new_sites =
          (site_row_t *)realloc(sites, sizeof(*sites) * new_capacity);
      if (!new_sites) {
        perror("realloc site_map");
        fclose(f);
        return 0;
      }
      sites = new_sites;
      site_capacity = new_capacity;
    }
    sites[site_count++] = row;
  }
  fclose(f);
  return 1;
}

static int one_way_path_suffix_match(const char *suffix_text,
                                     const char *path_text) {
  if (!suffix_text || !*suffix_text) return 1;
  if (!path_text || !*path_text) return 0;
  size_t suffix_len = strlen(suffix_text);
  size_t path_len = strlen(path_text);
  if (suffix_len > path_len) return 0;
  const char *suffix = path_text + path_len - suffix_len;
  if (strcmp(suffix, suffix_text) != 0) return 0;
  return suffix == path_text || suffix[-1] == '/';
}

static int path_suffix_match(const char *want, const char *have) {
  return one_way_path_suffix_match(want, have) ||
         one_way_path_suffix_match(have, want);
}

static int line_matches(uint32_t want, uint32_t have, int relax_line) {
  if (want == have) return 1;
  if (!relax_line) return 0;
  uint32_t delta = want > have ? want - have : have - want;
  return delta <= 3u;
}

static int equivalent_site_rows(const site_row_t *a, const site_row_t *b) {
  return a && b && a->site_id == b->site_id && eq(a->kind, b->kind) &&
         eq(a->function, b->function) && a->inst_no == b->inst_no &&
         eq(a->opcode, b->opcode) && eq(a->file, b->file) &&
         a->line == b->line && a->column == b->column;
}

static int site_already_counted(const site_row_t *const *matches,
                                uint32_t match_count,
                                const site_row_t *site) {
  for (uint32_t i = 0; i < match_count; i++) {
    if (matches[i]->site_id == site->site_id &&
        equivalent_site_rows(matches[i], site))
      return 1;
  }
  return 0;
}

static int binding_has_source_selectors(const binding_spec_t *binding) {
  return binding->site_kind[0] || binding->function[0] ||
         binding->opcode[0] || binding->file[0] || binding->have_line ||
         binding->have_inst_no || binding->have_column;
}

static int site_matches_binding_source(const site_row_t *site,
                                       const binding_spec_t *binding,
                                       int relax_inst_no, int relax_line,
                                       int relax_column) {
  if (binding->site_kind[0] && !eq(binding->site_kind, site->kind))
    return 0;
  if (binding->function[0] && !eq(binding->function, site->function))
    return 0;
  if (binding->opcode[0] && !eq(binding->opcode, site->opcode)) return 0;
  if (binding->file[0] && !path_suffix_match(binding->file, site->file))
    return 0;
  if (binding->have_line &&
      !line_matches(binding->line, site->line, relax_line))
    return 0;
  if (!relax_inst_no && binding->have_inst_no &&
      binding->inst_no != site->inst_no)
    return 0;
  if (!relax_column && binding->have_column &&
      binding->column != site->column)
    return 0;
  return 1;
}

static uint32_t collect_source_matches(const binding_spec_t *binding,
                                       int relax_inst_no, int relax_line,
                                       int relax_column,
                                       const site_row_t **found) {
  const site_row_t **matches = NULL;
  uint32_t match_capacity = 0;
  uint32_t match_count = 0;
  if (found) *found = NULL;
  for (uint32_t i = 0; i < site_count; i++) {
    if (!site_matches_binding_source(&sites[i], binding, relax_inst_no,
                                     relax_line, relax_column))
      continue;
    if (site_already_counted(matches, match_count, &sites[i])) continue;
    if (match_count == match_capacity) {
      uint32_t new_capacity = match_capacity ? match_capacity * 2u : 8u;
      const site_row_t **new_matches =
          (const site_row_t **)realloc(matches, sizeof(*matches) * new_capacity);
      if (!new_matches) {
        free(matches);
        return match_count;
      }
      matches = new_matches;
      match_capacity = new_capacity;
    }
    matches[match_count++] = &sites[i];
  }
  if (found && match_count) *found = matches[match_count - 1u];
  free(matches);
  return match_count;
}

static const site_row_t *find_unique_site_id(uint32_t site_id,
                                             uint32_t *matches) {
  const site_row_t *found = NULL;
  uint32_t count = 0;
  if (matches) *matches = 0;
  if (site_id == UINT32_MAX) return NULL;
  for (uint32_t i = 0; i < site_count; i++) {
    if (sites[i].site_id != site_id) continue;
    if (!found) {
      found = &sites[i];
      count = 1u;
    } else if (!equivalent_site_rows(found, &sites[i])) {
      count++;
    }
  }
  if (matches) *matches = count;
  return found;
}

static void bind_to_site(binding_spec_t *binding, const site_row_t *site) {
  binding->site_id = site->site_id;
  binding->have_site_id = 1u;
  if (!binding->have_event_kind) {
    uint32_t event_kind = event_kind_from_text(site->kind);
    if (event_kind != UINT32_MAX) {
      binding->event_kind = event_kind;
      binding->have_event_kind = 1u;
    }
  }
}

static int resolve_site(binding_spec_t *binding) {
  if (!site_count) {
    if (binding->have_site_id) return 1;
    fprintf(stderr, "binding %s has no site_id and no --site-map\n",
            binding->id[0] ? binding->id : "<unnamed>");
    return 0;
  }

  if (binding->have_site_id) {
    uint32_t id_matches = 0;
    const site_row_t *by_id = find_unique_site_id(binding->site_id, &id_matches);
    if (id_matches == 1u &&
        (!binding_has_source_selectors(binding) ||
         site_matches_binding_source(by_id, binding, 0, 0, 0))) {
      bind_to_site(binding, by_id);
      return 1;
    }
  }

  if (binding_has_source_selectors(binding)) {
    const site_row_t *found = NULL;
    uint32_t matches = collect_source_matches(binding, 0, 0, 0, &found);
    const char *mode = "exact";

    if (!matches && binding->have_inst_no) {
      matches = collect_source_matches(binding, 1, 0, 0, &found);
      mode = "relaxed_inst_no";
    }
    if (!matches && binding->have_column) {
      matches = collect_source_matches(binding, 0, 0, 1, &found);
      mode = "relaxed_column";
    }
    if (!matches && binding->have_inst_no && binding->have_column) {
      matches = collect_source_matches(binding, 1, 0, 1, &found);
      mode = "relaxed_inst_no_column";
    }
    if (!matches && binding->have_line) {
      matches = collect_source_matches(binding, 0, 1, 0, &found);
      mode = "relaxed_line";
    }
    if (!matches && binding->have_line && binding->have_column) {
      matches = collect_source_matches(binding, 0, 1, 1, &found);
      mode = "relaxed_line_column";
    }
    if (!matches && binding->have_inst_no && binding->have_line) {
      matches = collect_source_matches(binding, 1, 1, 0, &found);
      mode = "relaxed_inst_no_line";
    }
    if (!matches && binding->have_inst_no && binding->have_line &&
        binding->have_column) {
      matches = collect_source_matches(binding, 1, 1, 1, &found);
      mode = "relaxed_inst_no_line_column";
    }

    if (matches == 1u) {
      bind_to_site(binding, found);
      if (strcmp(mode, "exact") != 0)
        fprintf(stderr, "binding %s source mapping used %s -> site_id=%u\n",
                binding->id[0] ? binding->id : "<unnamed>", mode,
                binding->site_id);
      return 1;
    }

    if (!binding->have_site_id || matches) {
      fprintf(stderr, "binding %s source mapping is %s (%u matches)\n",
              binding->id[0] ? binding->id : "<unnamed>",
              matches ? "ambiguous" : "missing", matches);
      return 0;
    }
  }

  if (binding->have_site_id) return 1;

  fprintf(stderr, "binding %s source mapping is missing (0 matches)\n",
          binding->id[0] ? binding->id : "<unnamed>");
  return 0;
}

static atom_spec_t *new_atom(void) {
  if (atom_count >= MAX_ATOMS) return NULL;
  atom_spec_t *atom = &atoms[atom_count++];
  memset(atom, 0, sizeof(*atom));
  return atom;
}

static binding_spec_t *new_binding(void) {
  if (binding_count >= MAX_BINDINGS) return NULL;
  binding_spec_t *binding = &bindings[binding_count++];
  memset(binding, 0, sizeof(*binding));
  copy_field(binding->value, sizeof(binding->value), "1.0");
  copy_field(binding->confidence, sizeof(binding->confidence), "1.0");
  return binding;
}

static atom_spec_t *find_atom(uint32_t atom_id) {
  for (uint32_t i = 0; i < atom_count; i++)
    if (atoms[i].id == atom_id) return &atoms[i];
  return NULL;
}

static void set_atom_field(atom_spec_t *atom, const char *key,
                           const char *value) {
  if (!atom) return;
  if (eq(key, "id")) {
    if (!parse_u32(value, &atom->id)) error_count++;
  } else if (eq(key, "expr") || eq(key, "expression")) {
    copy_field(atom->expr, sizeof(atom->expr), value);
  } else if (eq(key, "kind") || eq(key, "category")) {
    copy_field(atom->kind, sizeof(atom->kind), value);
  } else if (eq(key, "root")) {
    copy_field(atom->root, sizeof(atom->root), value);
  }
}

static void set_binding_field(binding_spec_t *binding, const char *key,
                              const char *value) {
  if (!binding) return;
  if (eq(key, "id")) {
    copy_field(binding->id, sizeof(binding->id), value);
  } else if (eq(key, "atom") || eq(key, "atom_id")) {
    if (!parse_u32(value, &binding->atom_id)) error_count++;
  } else if (eq(key, "role")) {
    copy_field(binding->role, sizeof(binding->role), value);
  } else if (eq(key, "expr") || eq(key, "expression")) {
    copy_field(binding->expr, sizeof(binding->expr), value);
  } else if (eq(key, "label") || eq(key, "bug") ||
             eq(key, "canary_label")) {
    copy_field(binding->label, sizeof(binding->label), value);
  } else if (eq(key, "event_kind")) {
    binding->event_kind = event_kind_from_text(value);
    binding->have_event_kind = binding->event_kind != UINT32_MAX;
    if (!binding->have_event_kind) error_count++;
  } else if (eq(key, "site_id")) {
    binding->have_site_id = parse_u32(value, &binding->site_id);
    if (!binding->have_site_id) error_count++;
  } else if (eq(key, "kind") || eq(key, "site_kind")) {
    copy_field(binding->site_kind, sizeof(binding->site_kind), value);
    if (!binding->have_event_kind) {
      binding->event_kind = event_kind_from_text(value);
      binding->have_event_kind = binding->event_kind != UINT32_MAX;
    }
  } else if (eq(key, "function")) {
    copy_field(binding->function, sizeof(binding->function), value);
  } else if (eq(key, "opcode")) {
    copy_field(binding->opcode, sizeof(binding->opcode), value);
  } else if (eq(key, "file")) {
    copy_field(binding->file, sizeof(binding->file), value);
  } else if (eq(key, "line")) {
    binding->have_line = parse_u32(value, &binding->line);
    if (!binding->have_line) error_count++;
  } else if (eq(key, "inst_no") || eq(key, "instruction") ||
             eq(key, "instruction_index")) {
    binding->have_inst_no = parse_u32(value, &binding->inst_no);
    if (!binding->have_inst_no) error_count++;
  } else if (eq(key, "column")) {
    binding->have_column = parse_u32(value, &binding->column);
    if (!binding->have_column) error_count++;
  } else if (eq(key, "component") || eq(key, "component_kind")) {
    binding->component_kind = component_kind_from_text(value);
    binding->have_component = binding->component_kind != 0u;
    if (!binding->have_component) error_count++;
  } else if (eq(key, "priority")) {
    binding->have_priority = parse_u32(value, &binding->priority);
    if (!binding->have_priority) error_count++;
  } else if (eq(key, "direction")) {
    copy_field(binding->direction, sizeof(binding->direction), value);
  } else if (eq(key, "value_mode")) {
    copy_field(binding->value_mode, sizeof(binding->value_mode), value);
  } else if (eq(key, "value")) {
    copy_field(binding->value, sizeof(binding->value), value);
  } else if (eq(key, "confidence")) {
    copy_field(binding->confidence, sizeof(binding->confidence), value);
  } else if (eq(key, "phase_index")) {
    copy_field(binding->phase_index, sizeof(binding->phase_index), value);
  } else if (eq(key, "observe_window") || eq(key, "reach_window") ||
             eq(key, "window") || eq(key, "timing")) {
    copy_field(binding->observe_window, sizeof(binding->observe_window), value);
  } else if (eq(key, "range_start") || eq(key, "input_start") ||
             eq(key, "start")) {
    binding->have_range_start = parse_u32(value, &binding->range_start);
    if (!binding->have_range_start) error_count++;
  } else if (eq(key, "range_len") || eq(key, "input_len") ||
             eq(key, "length") || eq(key, "len")) {
    binding->have_range_len = parse_u32(value, &binding->range_len);
    if (!binding->have_range_len) error_count++;
  } else if (eq(key, "mutation_hint") || eq(key, "mutator_hint") ||
             eq(key, "hint")) {
    copy_field(binding->mutation_hint, sizeof(binding->mutation_hint), value);
  } else if (eq(key, "mutation_value") || eq(key, "hint_value") ||
             eq(key, "replacement_value")) {
    copy_field(binding->mutation_value, sizeof(binding->mutation_value), value);
  } else if (eq(key, "mutation_hook") || eq(key, "typed_mutation_hook") ||
             eq(key, "repair_hook_command") || eq(key, "repair_command")) {
    copy_field(binding->mutation_hook, sizeof(binding->mutation_hook), value);
  } else if (eq(key, "relation_from") || eq(key, "from_role") ||
             eq(key, "from")) {
    copy_field(binding->relation_from, sizeof(binding->relation_from), value);
  } else if (eq(key, "relation_to") || eq(key, "to_role") ||
             eq(key, "to")) {
    copy_field(binding->relation_to, sizeof(binding->relation_to), value);
  } else if (eq(key, "object_expr") || eq(key, "object") ||
             eq(key, "same_object_expr")) {
    copy_field(binding->object_expr, sizeof(binding->object_expr), value);
  }
}

static int parse_binding_spec(const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  section_kind_t section = SECTION_NONE;
  atom_spec_t *current_atom = NULL;
  binding_spec_t *current_binding = NULL;
  char line[1024];

  while (fgets(line, sizeof(line), f)) {
    strip_inline_comment(line);
    char *text = trim(line);
    if (!*text) continue;

    int list_item = 0;
    if (text[0] == '-' && isspace((unsigned char)text[1])) {
      list_item = 1;
      text = trim(text + 1);
      if (section == SECTION_ATOMS) {
        current_atom = new_atom();
        current_binding = NULL;
      } else if (section == SECTION_BINDINGS) {
        current_binding = new_binding();
        current_atom = NULL;
      } else {
        error_count++;
        continue;
      }
    }

    char *key = NULL;
    char *value = NULL;
    if (!parse_kv(text, &key, &value)) continue;

    if (!list_item && value[0] == '\0') {
      if (eq(key, "tc")) {
        section = SECTION_TC;
        current_atom = NULL;
        current_binding = NULL;
      } else if (eq(key, "atoms")) {
        section = SECTION_ATOMS;
        current_atom = NULL;
        current_binding = NULL;
      } else if (eq(key, "bindings")) {
        section = SECTION_BINDINGS;
        current_atom = NULL;
        current_binding = NULL;
      } else if (eq(key, "target") || eq(key, "observe_at") ||
                 eq(key, "source_location") || eq(key, "feature")) {
        /* These are structural YAML headings; fields below are parsed by the
           current atom/binding context. */
      }
      continue;
    }

    if (section == SECTION_ATOMS && current_atom) {
      set_atom_field(current_atom, key, value);
    } else if (section == SECTION_BINDINGS && current_binding) {
      set_binding_field(current_binding, key, value);
    } else if (section == SECTION_TC) {
      if (eq(key, "category"))
        copy_field(tc_category, sizeof(tc_category), value);
      else if (eq(key, "expr") || eq(key, "expression"))
        copy_field(tc_expression, sizeof(tc_expression), value);
    } else {
      if (eq(key, "tc_id") || eq(key, "id"))
        copy_field(tc_id, sizeof(tc_id), value);
    }
  }

  fclose(f);
  return 1;
}

static int validate_binding(binding_spec_t *binding) {
  int ok = 1;
  int range_binding = binding->have_range_start || binding->have_range_len;
  int canary_binding = 0;
  if (!binding->id[0]) copy_field(binding->id, sizeof(binding->id), "<unnamed>");
  if (!binding->atom_id || !find_atom(binding->atom_id)) {
    fprintf(stderr, "binding %s references unknown atom %u\n", binding->id,
            binding->atom_id);
    ok = 0;
  }
  if (!binding->role[0]) {
    fprintf(stderr, "binding %s is missing role\n", binding->id);
    ok = 0;
  }
  if (!binding->expr[0]) {
    fprintf(stderr, "binding %s is missing semantic expression\n", binding->id);
    ok = 0;
  }
  if (!binding->have_component) {
    fprintf(stderr, "binding %s is missing component kind\n", binding->id);
    ok = 0;
  }
  if (!binding->have_priority) {
    fprintf(stderr, "binding %s is missing priority\n", binding->id);
    ok = 0;
  }
  if (!binding->direction[0]) {
    fprintf(stderr, "binding %s is missing direction\n", binding->id);
    ok = 0;
  }
  if (!binding->value_mode[0]) {
    fprintf(stderr, "binding %s is missing value_mode\n", binding->id);
    ok = 0;
  }
  if (range_binding &&
      (!binding->have_range_start || !binding->have_range_len ||
       !binding->range_len)) {
    fprintf(stderr, "binding %s has an invalid input range\n", binding->id);
    ok = 0;
  }
  if (range_binding && !eq(binding->role, "input_influence") &&
      !eq(binding->role, "input-influence")) {
    fprintf(stderr, "binding %s uses range fields without input_influence role\n",
            binding->id);
    ok = 0;
  }
  if (!binding->have_event_kind && binding->site_kind[0]) {
    binding->event_kind = event_kind_from_text(binding->site_kind);
    binding->have_event_kind = binding->event_kind != UINT32_MAX;
  }
  canary_binding =
      binding->have_event_kind && binding->event_kind == FORMTRIG_EVENT_CANARY;
  if (canary_binding && !binding->have_site_id && binding->label[0]) {
    binding->site_id = label_site_id(binding->label);
    binding->have_site_id = 1u;
  }
  if (canary_binding) {
    if (!binding->label[0] && !binding->have_site_id) {
      fprintf(stderr, "binding %s canary binding is missing label/site_id\n",
              binding->id);
      ok = 0;
    }
    if (!eq(binding->role, "root_observe") &&
        !eq(binding->role, "root-observe") && !eq(binding->role, "root")) {
      fprintf(stderr, "binding %s canary binding must be root_observe\n",
              binding->id);
      ok = 0;
    }
    if (!eq(binding->value_mode, "hit")) {
      fprintf(stderr,
              "binding %s canary binding may only use value_mode=hit\n",
              binding->id);
      ok = 0;
    }
  }
  if (eq(binding->role, "same_object") || eq(binding->role, "same-object") ||
      eq(binding->role, "object_identity") ||
      eq(binding->role, "object-identity")) {
    if (!binding->relation_from[0] || !binding->relation_to[0] ||
        !binding->object_expr[0]) {
      fprintf(stderr,
              "binding %s same_object binding is missing relation_from, "
              "relation_to, or object_expr\n",
              binding->id);
      ok = 0;
    }
  }
  if (!binding->have_event_kind && !range_binding) {
    fprintf(stderr, "binding %s is missing event_kind/site kind\n",
            binding->id);
    ok = 0;
  }
  if (!canary_binding &&
      (binding->have_event_kind || binding->site_kind[0] ||
       binding->have_site_id || binding->function[0] || binding->file[0] ||
       binding->have_line || binding->have_inst_no || binding->have_column) &&
      !resolve_site(binding))
    ok = 0;
  return ok;
}

static int validate_spec(void) {
  int ok = error_count == 0u;
  if (!tc_id[0]) {
    fprintf(stderr, "BindingSpec is missing tc_id\n");
    ok = 0;
  }
  if (!tc_category[0]) {
    fprintf(stderr, "BindingSpec is missing tc.category\n");
    ok = 0;
  }
  if (!tc_expression[0]) {
    fprintf(stderr, "BindingSpec is missing tc.expression\n");
    ok = 0;
  }
  if (!atom_count) {
    fprintf(stderr, "BindingSpec has no atoms\n");
    ok = 0;
  }
  if (!binding_count) {
    fprintf(stderr, "BindingSpec has no bindings\n");
    ok = 0;
  }

  for (uint32_t i = 0; i < atom_count; i++) {
    if (!atoms[i].id) {
      fprintf(stderr, "atom entry %u is missing id\n", i + 1u);
      ok = 0;
    }
    if (!atoms[i].expr[0]) {
      fprintf(stderr, "atom %u is missing expr\n", atoms[i].id);
      ok = 0;
    }
    if (!atoms[i].kind[0]) {
      fprintf(stderr, "atom %u is missing kind\n", atoms[i].id);
      ok = 0;
    }
    if (!atoms[i].root[0]) {
      fprintf(stderr, "atom %u is missing root\n", atoms[i].id);
      ok = 0;
    }
  }

  for (uint32_t i = 0; i < binding_count; i++)
    if (!validate_binding(&bindings[i])) ok = 0;

  return ok;
}

static int write_lift_spec(FILE *out) {
  fprintf(out, "# compiled_from_binding_spec tc_id=%s category=%s\n", tc_id,
          tc_category);
  fprintf(out, "# tc_expression=%s\n", tc_expression);
  for (uint32_t i = 0; i < atom_count; i++)
    fprintf(out, "atom_category %u %s\n", atoms[i].id, atoms[i].kind);

  for (uint32_t i = 0; i < binding_count; i++) {
    binding_spec_t *b = &bindings[i];
    fprintf(out, "# binding id=%s atom=%u role=%s expr=%s\n", b->id,
            b->atom_id, b->role, b->expr);
    if (b->phase_index[0]) {
      fprintf(out, "phase %u %u %u %u %u %s %s", b->event_kind,
              b->site_id, b->component_kind, b->atom_id, b->priority,
              b->phase_index, b->confidence[0] ? b->confidence : "1.0");
      if (b->observe_window[0]) fprintf(out, " %s", b->observe_window);
      fputc('\n', out);
    } else if (b->have_event_kind && b->have_site_id) {
      fprintf(out, "role_component %u %u %s %u %u %u %s %s %s %s",
              b->event_kind, b->site_id, b->role, b->component_kind,
              b->atom_id, b->priority, b->direction, b->value_mode,
              b->value[0] ? b->value : "1.0",
              b->confidence[0] ? b->confidence : "1.0");
      if (b->observe_window[0]) fprintf(out, " %s", b->observe_window);
      fputc('\n', out);
    }
    if (b->have_range_start && b->have_range_len) {
      if (b->have_event_kind && b->have_site_id)
        fprintf(out, "range %u %u %u %u %s", b->event_kind, b->site_id,
                b->range_start, b->range_len,
                b->confidence[0] ? b->confidence : "1.0");
      else
        fprintf(out, "range * * %u %u %s", b->range_start, b->range_len,
              b->confidence[0] ? b->confidence : "1.0");
      if (b->mutation_hint[0]) {
        fprintf(out, " %s %s", b->mutation_hint,
                b->mutation_value[0] ? b->mutation_value : "0");
      } else if (b->observe_window[0]) {
        fprintf(out, " none 0");
      }
      if (b->observe_window[0]) fprintf(out, " %s", b->observe_window);
      fputc('\n', out);
    }
    if ((eq(b->role, "same_object") || eq(b->role, "same-object") ||
         eq(b->role, "object_identity") || eq(b->role, "object-identity")) &&
        b->relation_from[0] && b->relation_to[0] && b->object_expr[0]) {
      fprintf(out, "same_object_relation %u %s %s %s\n", b->atom_id,
              b->relation_from, b->relation_to, b->object_expr);
    }
    if (b->mutation_hook[0]) fprintf(out, "mutation_hook %s\n", b->mutation_hook);
  }

  return ferror(out) ? 0 : 1;
}

int main(int argc, char **argv) {
  const char *site_map = NULL;
  const char *out_path = NULL;
  const char *spec_path = NULL;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--site-map")) {
      if (++i >= argc) {
        usage(argv[0]);
        return 2;
      }
      site_map = argv[i];
    } else if (!strcmp(argv[i], "--out")) {
      if (++i >= argc) {
        usage(argv[0]);
        return 2;
      }
      out_path = argv[i];
    } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
      usage(argv[0]);
      return 0;
    } else if (!spec_path) {
      spec_path = argv[i];
    } else {
      usage(argv[0]);
      return 2;
    }
  }

  if (!spec_path) {
    usage(argv[0]);
    return 2;
  }

  if (site_map && !load_site_map(site_map)) return 2;
  if (!parse_binding_spec(spec_path)) return 2;
  if (!validate_spec()) return 1;

  FILE *out = stdout;
  if (out_path) {
    out = fopen(out_path, "w");
    if (!out) {
      perror(out_path);
      return 2;
    }
  }

  int ok = write_lift_spec(out);
  if (out_path) fclose(out);
  return ok ? 0 : 2;
}
