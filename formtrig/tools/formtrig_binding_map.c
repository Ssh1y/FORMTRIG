#define _POSIX_C_SOURCE 200809L

#include "formtrig/formtrig_abi.h"

#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_BINDINGS 512u
#define MAX_ATOMS 128u
#define MAX_SITE_ROLES 128u
#define MAX_RANGE_ROWS 128u

enum ft_category {
  FT_CATEGORY_GENERIC = 0,
  FT_CATEGORY_NUMERIC,
  FT_CATEGORY_EQUALITY,
  FT_CATEGORY_BINARY_NULL,
  FT_CATEGORY_LIFECYCLE
};

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

typedef struct binding_row {
  uint32_t binding_id;
  uint32_t event_kind;
  uint32_t site_id;
  uint32_t role;
  uint32_t component_kind;
  uint32_t atom_id;
  uint32_t priority;
  char direction[16];
  char value_mode[32];
  char value[64];
  char confidence[64];
  char phase_index[32];
  char observe_window[32];
  char op[32];
  uint64_t event_id;
  uint32_t collapsed_with;
  const site_row_t *site;
  const char *mapping_status;
  const char *reason;
  uint32_t tier;
  uint32_t lift_allowed;
} binding_row_t;

typedef struct site_role_set {
  uint32_t atom_id;
  uint32_t site_id;
  uint32_t roles;
} site_role_set_t;

typedef struct same_object_relation {
  uint32_t atom_id;
  uint32_t from_role;
  uint32_t to_role;
  char object_expr[128];
} same_object_relation_t;

typedef struct atom_summary {
  uint32_t atom_id;
  enum ft_category category;
  uint32_t roles;
  uint32_t collapsed;
  uint32_t missing;
  uint32_t stateful_root_count;
  uint32_t stateful_use_count;
  uint32_t stateful_same_object_count;
  uint32_t same_object_relation_count;
  uint32_t same_object_relation_roles;
  uint32_t tier;
  const char *reason;
  uint32_t lift_allowed;
} atom_summary_t;

static site_row_t *sites;
static uint32_t site_count;
static uint32_t site_capacity;
static binding_row_t bindings[MAX_BINDINGS];
static uint32_t binding_count;
static atom_summary_t atoms[MAX_ATOMS];
static uint32_t atom_count;
static site_role_set_t site_roles[MAX_SITE_ROLES];
static uint32_t site_role_count;
static same_object_relation_t same_object_relations[MAX_BINDINGS];
static uint32_t same_object_relation_count;
static char range_rows[MAX_RANGE_ROWS][192];
static uint32_t range_row_count;

static atom_summary_t *atom_slot(uint32_t atom_id);

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s --category numeric|equality|binary-null|lifecycle "
          "--site-map site_map.tsv [--normalized-spec OUT] "
          "<FORMTRIG_LIFT_SPEC>\n",
          argv0);
}

static uint64_t fnv_mix_u64(uint64_t sig, uint64_t value) {
  sig ^= value;
  sig *= 1099511628211ULL;
  return sig;
}

static int parse_u32(const char *s, uint32_t *out) {
  if (!s || !out) return 0;
  if (!strcmp(s, "*")) {
    *out = UINT32_MAX;
    return 1;
  }
  char *end = NULL;
  errno = 0;
  unsigned long v = strtoul(s, &end, 0);
  if (errno || end == s || *end != '\0' || v > UINT32_MAX) return 0;
  *out = (uint32_t)v;
  return 1;
}

static char *next_token(char **saveptr) {
  return strtok_r(NULL, " \t\r\n,", saveptr);
}

static void copy_field(char *dst, size_t dst_size, const char *src) {
  if (!dst || !dst_size) return;
  if (!src) src = "";
  snprintf(dst, dst_size, "%s", src);
}

static int is_observe_window(const char *s) {
  return s && (!strcmp(s, "post_reach") || !strcmp(s, "post-reach") ||
               !strcmp(s, "after_reach") || !strcmp(s, "after-reach") ||
               !strcmp(s, "pre_reach") || !strcmp(s, "pre-reach") ||
               !strcmp(s, "before_reach") || !strcmp(s, "before-reach") ||
               !strcmp(s, "any") || !strcmp(s, "both"));
}

static void parse_optional_tail(char **saveptr, binding_row_t *b) {
  char *token = NULL;
  while ((token = next_token(saveptr)) != NULL) {
    if (is_observe_window(token)) {
      copy_field(b->observe_window, sizeof(b->observe_window), token);
      return;
    }
  }
}

static uint32_t role_bit(uint32_t role) {
  if (role == FORMTRIG_ROLE_UNKNOWN || role > 31u) return 0u;
  return 1u << (role - 1u);
}

static int role_participates_in_semantic_collapse(uint32_t role) {
  return role != FORMTRIG_ROLE_UNKNOWN &&
         role != FORMTRIG_ROLE_INPUT_INFLUENCE &&
         role != FORMTRIG_ROLE_REPAIR_HOOK;
}

static int token_eq(const char *s, const char *a, const char *b,
                    const char *c) {
  if (!s) return 0;
  return (a && !strcmp(s, a)) || (b && !strcmp(s, b)) ||
         (c && !strcmp(s, c));
}

static int value_mode_observes_state(const char *mode) {
  if (!mode) return 0;
  if (token_eq(mode, "distance", "dist", "1")) return 1;
  if (token_eq(mode, "outcome", "3", NULL)) return 1;
  if (token_eq(mode, "not_outcome", "not-outcome", "4")) return 1;
  if (token_eq(mode, "a", "5", NULL)) return 1;
  if (token_eq(mode, "b", "6", NULL)) return 1;
  if (token_eq(mode, "c", "7", NULL)) return 1;
  if (token_eq(mode, "distance_to_a", "distance-to-a", "8")) return 1;
  if (token_eq(mode, "target_distance_a", "target-distance-a", NULL))
    return 1;
  if (token_eq(mode, "abs_to_a", "abs-to-a", NULL)) return 1;
  if (token_eq(mode, "distance_to_b", "distance-to-b", "9")) return 1;
  if (token_eq(mode, "target_distance_b", "target-distance-b", NULL))
    return 1;
  if (token_eq(mode, "abs_to_b", "abs-to-b", NULL)) return 1;
  if (token_eq(mode, "distance_to_c", "distance-to-c", "10")) return 1;
  if (token_eq(mode, "target_distance_c", "target-distance-c", NULL))
    return 1;
  if (token_eq(mode, "abs_to_c", "abs-to-c", NULL)) return 1;
  return 0;
}

static int same_object_relation_complete(const atom_summary_t *atom) {
  if (!atom || !atom->same_object_relation_count) return 0;
  return (atom->same_object_relation_roles & ~atom->roles) == 0u;
}

static uint32_t parse_role(const char *s) {
  if (!s) return FORMTRIG_ROLE_UNKNOWN;
  if (!strcmp(s, "root") || !strcmp(s, "root_observe") ||
      !strcmp(s, "root-observe") || !strcmp(s, "1"))
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
  if (!strcmp(s, "lifecycle") || !strcmp(s, "lifecycle_event") ||
      !strcmp(s, "lifecycle-event") || !strcmp(s, "7"))
    return FORMTRIG_ROLE_LIFECYCLE_EVENT;
  if (!strcmp(s, "same_object") || !strcmp(s, "same-object") ||
      !strcmp(s, "object_identity") || !strcmp(s, "object-identity") ||
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

static const char *tier_name(uint32_t tier) {
  switch (tier) {
    case 4:
      return "B4";
    case 3:
      return "B3";
    case 2:
      return "B2";
    case 1:
      return "B1";
    default:
      return "B0";
  }
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

static int equivalent_site_rows(const site_row_t *a, const site_row_t *b) {
  return a && b && a->site_id == b->site_id && !strcmp(a->kind, b->kind) &&
         !strcmp(a->function, b->function) && a->inst_no == b->inst_no &&
         !strcmp(a->opcode, b->opcode) && !strcmp(a->file, b->file) &&
         a->line == b->line && a->column == b->column;
}

static const site_row_t *find_site(uint32_t site_id, uint32_t *matches) {
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

static binding_row_t *new_binding(const char *op) {
  if (binding_count >= MAX_BINDINGS) return NULL;
  binding_row_t *b = &bindings[binding_count++];
  memset(b, 0, sizeof(*b));
  b->binding_id = binding_count;
  b->role = FORMTRIG_ROLE_UNKNOWN;
  b->site_id = UINT32_MAX;
  b->event_kind = UINT32_MAX;
  copy_field(b->value, sizeof(b->value), "1.0");
  copy_field(b->confidence, sizeof(b->confidence), "1.0");
  copy_field(b->op, sizeof(b->op), op);
  return b;
}

static void parse_spec_line(char *line) {
  char *comment = strchr(line, '#');
  if (comment) *comment = '\0';

  char *saveptr = NULL;
  char *op = strtok_r(line, " \t\r\n,", &saveptr);
  if (!op || !*op) return;

  if (!strcmp(op, "atom_category") || !strcmp(op, "atom-category") ||
      !strcmp(op, "atom_kind") || !strcmp(op, "atom-kind")) {
    char *atom_text = next_token(&saveptr);
    char *category_text = next_token(&saveptr);
    uint32_t atom_id = 0;
    if (!parse_u32(atom_text, &atom_id)) return;
    atom_summary_t *atom = atom_slot(atom_id);
    if (atom) atom->category = parse_category(category_text);
    return;
  }

  if (!strcmp(op, "same_object_relation") ||
      !strcmp(op, "same-object-relation") ||
      !strcmp(op, "object_identity_relation") ||
      !strcmp(op, "object-identity-relation")) {
    char *atom_text = next_token(&saveptr);
    char *from_role = next_token(&saveptr);
    char *to_role = next_token(&saveptr);
    char *object_expr = next_token(&saveptr);
    uint32_t atom_id = 0;
    if (!parse_u32(atom_text, &atom_id) || !object_expr || !*object_expr)
      return;
    if (same_object_relation_count >= MAX_BINDINGS) return;
    same_object_relation_t *rel =
        &same_object_relations[same_object_relation_count++];
    memset(rel, 0, sizeof(*rel));
    rel->atom_id = atom_id;
    rel->from_role = parse_role(from_role);
    rel->to_role = parse_role(to_role);
    copy_field(rel->object_expr, sizeof(rel->object_expr), object_expr);
    return;
  }

  if (!strcmp(op, "role_component") || !strcmp(op, "role-event") ||
      !strcmp(op, "role_event")) {
    binding_row_t *b = new_binding(op);
    if (!b) return;
    char *event_kind = next_token(&saveptr);
    char *site_id = next_token(&saveptr);
    char *role = next_token(&saveptr);
    char *component = next_token(&saveptr);
    char *atom = next_token(&saveptr);
    char *priority = next_token(&saveptr);
    char *direction = next_token(&saveptr);
    char *value_mode = next_token(&saveptr);
    char *value = next_token(&saveptr);
    char *confidence = next_token(&saveptr);

    if (!parse_u32(event_kind, &b->event_kind) ||
        !parse_u32(site_id, &b->site_id) ||
        !parse_u32(component, &b->component_kind) ||
        !parse_u32(atom, &b->atom_id) ||
        !parse_u32(priority, &b->priority)) {
      b->reason = "malformed_binding";
      return;
    }
    b->role = parse_role(role);
    copy_field(b->direction, sizeof(b->direction), direction);
    copy_field(b->value_mode, sizeof(b->value_mode), value_mode);
    copy_field(b->value, sizeof(b->value), value);
    copy_field(b->confidence, sizeof(b->confidence), confidence);
    parse_optional_tail(&saveptr, b);
    return;
  }

  if (!strcmp(op, "range") || !strcmp(op, "hot_range") ||
      !strcmp(op, "hot-range")) {
    char *event_kind = next_token(&saveptr);
    char *site_id = next_token(&saveptr);
    char *start = next_token(&saveptr);
    char *len = next_token(&saveptr);
    char *influence = next_token(&saveptr);
    char *mutation_hint = next_token(&saveptr);
    char *mutation_value = next_token(&saveptr);
    char *observe_window = next_token(&saveptr);
    uint32_t ignored = 0;
    if (!event_kind || !site_id || !start || !len) return;
    if (!parse_u32(event_kind, &ignored) || !parse_u32(site_id, &ignored) ||
        !parse_u32(start, &ignored) || !parse_u32(len, &ignored))
      return;
    if (!influence) influence = "1.0";
    if (range_row_count < MAX_RANGE_ROWS) {
      if (mutation_hint) {
        snprintf(range_rows[range_row_count++], sizeof(range_rows[0]),
                 "range %s %s %s %s %s %s %s%s%s", event_kind, site_id, start,
                 len, influence, mutation_hint,
                 mutation_value ? mutation_value : "0",
                 observe_window ? " " : "",
                 observe_window ? observe_window : "");
      } else {
        snprintf(range_rows[range_row_count++], sizeof(range_rows[0]),
                 "range %s %s %s %s %s", event_kind, site_id, start, len,
                 influence);
      }
    }
    return;
  }

  if (!strcmp(op, "component") || !strcmp(op, "event")) {
    binding_row_t *b = new_binding(op);
    if (!b) return;
    char *event_kind = next_token(&saveptr);
    char *site_id = next_token(&saveptr);
    char *component = next_token(&saveptr);
    char *atom = next_token(&saveptr);
    char *priority = next_token(&saveptr);
    char *direction = next_token(&saveptr);
    char *value_mode = next_token(&saveptr);
    char *value = next_token(&saveptr);
    char *confidence = next_token(&saveptr);

    if (!parse_u32(event_kind, &b->event_kind) ||
        !parse_u32(site_id, &b->site_id) ||
        !parse_u32(component, &b->component_kind) ||
        !parse_u32(atom, &b->atom_id) ||
        !parse_u32(priority, &b->priority)) {
      b->reason = "malformed_binding";
      return;
    }
    copy_field(b->direction, sizeof(b->direction), direction);
    copy_field(b->value_mode, sizeof(b->value_mode), value_mode);
    copy_field(b->value, sizeof(b->value), value);
    copy_field(b->confidence, sizeof(b->confidence), confidence);
    parse_optional_tail(&saveptr, b);
    return;
  }

  if (!strcmp(op, "phase") || !strcmp(op, "prefix")) {
    binding_row_t *b = new_binding(op);
    if (!b) return;
    char *event_kind = next_token(&saveptr);
    char *site_id = next_token(&saveptr);
    char *component = next_token(&saveptr);
    char *atom = next_token(&saveptr);
    char *priority = next_token(&saveptr);
    char *phase_index = next_token(&saveptr);
    char *confidence = next_token(&saveptr);
    if (!parse_u32(event_kind, &b->event_kind) ||
        !parse_u32(site_id, &b->site_id) ||
        !parse_u32(component, &b->component_kind) ||
        !parse_u32(atom, &b->atom_id) ||
        !parse_u32(priority, &b->priority)) {
      b->reason = "malformed_binding";
      return;
    }
    b->role = FORMTRIG_ROLE_LIFECYCLE_EVENT;
    copy_field(b->direction, sizeof(b->direction), "higher");
    copy_field(b->value_mode, sizeof(b->value_mode), "hit");
    copy_field(b->phase_index, sizeof(b->phase_index), phase_index);
    copy_field(b->confidence, sizeof(b->confidence), confidence);
    parse_optional_tail(&saveptr, b);
  }
}

static int load_lift_spec(const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 0;
  }

  char line[512];
  while (fgets(line, sizeof(line), f)) parse_spec_line(line);
  fclose(f);
  return 1;
}

static atom_summary_t *atom_slot(uint32_t atom_id) {
  if (!atom_id) return NULL;
  for (uint32_t i = 0; i < atom_count; i++)
    if (atoms[i].atom_id == atom_id) return &atoms[i];
  if (atom_count >= MAX_ATOMS) return NULL;
  atom_summary_t *atom = &atoms[atom_count++];
  memset(atom, 0, sizeof(*atom));
  atom->atom_id = atom_id;
  return atom;
}

static site_role_set_t *site_role_slot(uint32_t atom_id, uint32_t site_id) {
  for (uint32_t i = 0; i < site_role_count; i++) {
    if (site_roles[i].atom_id == atom_id && site_roles[i].site_id == site_id)
      return &site_roles[i];
  }
  if (site_role_count >= MAX_SITE_ROLES) return NULL;
  site_role_set_t *slot = &site_roles[site_role_count++];
  memset(slot, 0, sizeof(*slot));
  slot->atom_id = atom_id;
  slot->site_id = site_id;
  return slot;
}

static uint32_t binding_tier(const atom_summary_t *atom) {
  int root = atom && atom->stateful_root_count > 0u;
  int producer = (atom->roles & role_bit(FORMTRIG_ROLE_PRODUCER)) != 0 ||
                 (atom->roles & role_bit(FORMTRIG_ROLE_DESIRED_PRODUCER)) != 0 ||
                 (atom->roles & role_bit(FORMTRIG_ROLE_OPPOSITE_PRODUCER)) != 0;
  int use = (atom->roles & role_bit(FORMTRIG_ROLE_USE)) != 0;
  int lifecycle = (atom->roles & role_bit(FORMTRIG_ROLE_LIFECYCLE_EVENT)) != 0;
  int same_object = atom->stateful_same_object_count > 0u &&
                    same_object_relation_complete(atom);
  int influence = (atom->roles & role_bit(FORMTRIG_ROLE_INPUT_INFLUENCE)) != 0;
  int repair = (atom->roles & role_bit(FORMTRIG_ROLE_REPAIR_HOOK)) != 0;

  uint32_t tier = 0u;
  if (root) tier = 1u;
  if (root && producer && use) tier = 2u;
  if (root && lifecycle && use && same_object && tier < 3u) tier = 3u;
  if (root && (influence || repair)) tier = 4u;
  return tier;
}

static uint32_t min_tier(enum ft_category category) {
  switch (category) {
    case FT_CATEGORY_NUMERIC:
    case FT_CATEGORY_EQUALITY:
      return 1u;
    case FT_CATEGORY_BINARY_NULL:
      return 2u;
    case FT_CATEGORY_LIFECYCLE:
      return 3u;
    default:
      return 1u;
  }
}

static const char *atom_reason(const atom_summary_t *atom,
                               enum ft_category category) {
  if (atom->missing) return "missing_runtime_event";
  if (atom->collapsed) return "semantic_role_collapse";
  if (category == FT_CATEGORY_BINARY_NULL) {
    if ((atom->roles & role_bit(FORMTRIG_ROLE_ROOT_OBSERVE)) == 0 ||
        (atom->roles & role_bit(FORMTRIG_ROLE_USE)) == 0)
      return "missing_root_or_use";
    if (!atom->stateful_root_count) return "missing_stateful_root_observe";
    if ((atom->roles & role_bit(FORMTRIG_ROLE_PRODUCER)) == 0 &&
        (atom->roles & role_bit(FORMTRIG_ROLE_DESIRED_PRODUCER)) == 0 &&
        (atom->roles & role_bit(FORMTRIG_ROLE_OPPOSITE_PRODUCER)) == 0)
      return "missing_producer";
  }
  if (min_tier(category) >= 1u &&
      (atom->roles & role_bit(FORMTRIG_ROLE_ROOT_OBSERVE)) != 0 &&
      !atom->stateful_root_count)
    return "missing_stateful_root_observe";
  if (category == FT_CATEGORY_LIFECYCLE) {
    if ((atom->roles & role_bit(FORMTRIG_ROLE_ROOT_OBSERVE)) == 0 ||
        (atom->roles & role_bit(FORMTRIG_ROLE_LIFECYCLE_EVENT)) == 0 ||
        (atom->roles & role_bit(FORMTRIG_ROLE_USE)) == 0)
      return "missing_lifecycle_role";
    if ((atom->roles & role_bit(FORMTRIG_ROLE_SAME_OBJECT)) == 0)
      return "missing_same_object";
    if (!atom->stateful_same_object_count)
      return "missing_stateful_same_object";
    if (!atom->same_object_relation_count)
      return "missing_same_object_relation";
    if (!same_object_relation_complete(atom))
      return "missing_same_object_endpoint";
  }
  if (atom->tier < min_tier(category)) return "insufficient_binding_tier";
  return "ok";
}

static enum ft_category effective_atom_category(const atom_summary_t *atom,
                                                enum ft_category fallback) {
  if (atom && atom->category != FT_CATEGORY_GENERIC) return atom->category;
  return fallback;
}

static void resolve_bindings(enum ft_category fallback_category) {
  for (uint32_t i = 0; i < binding_count; i++) {
    binding_row_t *b = &bindings[i];
    uint32_t matches = 0;
    if (b->event_kind == FORMTRIG_EVENT_CANARY && b->site_id != UINT32_MAX) {
      b->site = NULL;
      b->mapping_status = "exact";
    } else {
      b->site = find_site(b->site_id, &matches);
    }
    if (b->mapping_status) {
      /* Pseudo-events such as canaries are runtime ABI events, not LLVM rows. */
    } else if (b->site_id == UINT32_MAX) {
      b->mapping_status = "ambiguous";
    } else if (!matches) {
      b->mapping_status = "missing";
    } else if (matches == 1u) {
      b->mapping_status = "exact";
    } else {
      b->mapping_status = "ambiguous";
    }

    uint64_t event_id = 1469598103934665603ULL;
    event_id = fnv_mix_u64(event_id, b->atom_id);
    event_id = fnv_mix_u64(event_id, b->binding_id);
    event_id = fnv_mix_u64(event_id, b->role);
    event_id = fnv_mix_u64(event_id, b->event_kind);
    event_id = fnv_mix_u64(event_id, b->site_id);
    event_id = fnv_mix_u64(event_id, b->component_kind);
    b->event_id = event_id;

    atom_summary_t *atom = atom_slot(b->atom_id);
    if (!atom) continue;
    atom->roles |= role_bit(b->role);
    if (!strcmp(b->mapping_status, "missing")) atom->missing = 1u;
    if (b->role == FORMTRIG_ROLE_ROOT_OBSERVE &&
        value_mode_observes_state(b->value_mode))
      atom->stateful_root_count++;
    if (b->role == FORMTRIG_ROLE_USE &&
        value_mode_observes_state(b->value_mode))
      atom->stateful_use_count++;
    if (b->role == FORMTRIG_ROLE_SAME_OBJECT &&
        value_mode_observes_state(b->value_mode))
      atom->stateful_same_object_count++;

    if (b->site_id != UINT32_MAX &&
        role_participates_in_semantic_collapse(b->role)) {
      site_role_set_t *site_role = site_role_slot(b->atom_id, b->site_id);
      if (site_role) {
        uint32_t bit = role_bit(b->role);
        if ((site_role->roles & ~bit) != 0u) {
          atom->collapsed = 1u;
          b->collapsed_with = site_role->roles;
        }
        site_role->roles |= bit;
      }
    }
  }

  for (uint32_t i = 0; i < same_object_relation_count; i++) {
    const same_object_relation_t *rel = &same_object_relations[i];
    if (rel->from_role == FORMTRIG_ROLE_UNKNOWN ||
        rel->to_role == FORMTRIG_ROLE_UNKNOWN)
      continue;
    atom_summary_t *atom = atom_slot(rel->atom_id);
    if (!atom) continue;
    atom->same_object_relation_count++;
    atom->same_object_relation_roles |=
        role_bit(rel->from_role) | role_bit(rel->to_role);
  }

  for (uint32_t i = 0; i < atom_count; i++) {
    atoms[i].tier = binding_tier(&atoms[i]);
    atoms[i].reason = atom_reason(
        &atoms[i], effective_atom_category(&atoms[i], fallback_category));
    atoms[i].lift_allowed = !strcmp(atoms[i].reason, "ok");
  }

  for (uint32_t i = 0; i < binding_count; i++) {
    binding_row_t *b = &bindings[i];
    atom_summary_t *atom = atom_slot(b->atom_id);
    if (!atom) continue;
    b->tier = atom->tier;
    b->reason = b->reason ? b->reason : atom->reason;
    b->lift_allowed = atom->lift_allowed;
    if (atom->collapsed && !b->collapsed_with && b->site_id != UINT32_MAX &&
        role_participates_in_semantic_collapse(b->role)) {
      site_role_set_t *site_role = site_role_slot(b->atom_id, b->site_id);
      if (site_role) b->collapsed_with = site_role->roles & ~role_bit(b->role);
    }
  }
}

static void print_header(void) {
  printf("binding_id,atom_id,category,role,event_kind,site_id,event_id,"
         "mapping_status,collapsed_with,binding_tier,lift_allowed,reason,"
         "component_kind,priority,direction,value_mode,function,file,line,"
         "column,opcode,observe_window\n");
}

static void print_binding(const binding_row_t *b,
                          enum ft_category fallback_category) {
  atom_summary_t *atom = atom_slot(b->atom_id);
  enum ft_category category = effective_atom_category(atom, fallback_category);
  printf("%u,%u,%s,%s,%u,", b->binding_id, b->atom_id,
         category_name(category), role_name(b->role), b->event_kind);
  if (b->site_id == UINT32_MAX)
    printf("*,");
  else
    printf("%u,", b->site_id);
  printf("%016llx,%s,0x%08x,%s,%s,%s,%u,%u,%s,%s,",
         (unsigned long long)b->event_id, b->mapping_status,
         b->collapsed_with, tier_name(b->tier),
         b->lift_allowed ? "true" : "false", b->reason ? b->reason : "ok",
         b->component_kind, b->priority, b->direction, b->value_mode);
  if (b->site) {
    printf("%s,%s,%u,%u,%s", b->site->function, b->site->file, b->site->line,
           b->site->column, b->site->opcode);
  } else {
    printf(",,0,0,");
  }
  printf(",%s", b->observe_window[0] ? b->observe_window : "post_reach");
  putchar('\n');
}

static int write_normalized_spec(const char *path) {
  FILE *f = fopen(path, "w");
  if (!f) {
    perror(path);
    return 0;
  }

  for (uint32_t i = 0; i < binding_count; i++) {
    const binding_row_t *b = &bindings[i];
    if (!b->lift_allowed) {
      fclose(f);
      return 0;
    }
    if (!strcmp(b->op, "phase") || !strcmp(b->op, "prefix")) {
      fprintf(f, "phase %u %u %u %u %u %s %s %llu", b->event_kind,
              b->site_id, b->component_kind, b->atom_id, b->priority,
              b->phase_index[0] ? b->phase_index : "1",
              b->confidence[0] ? b->confidence : "1.0",
              (unsigned long long)b->event_id);
      if (b->observe_window[0]) fprintf(f, " %s", b->observe_window);
      fputc('\n', f);
      continue;
    }
    if (b->role == FORMTRIG_ROLE_UNKNOWN) {
      fprintf(f, "component %u %u %u %u %u %s %s %s %s %llu %llu",
              b->event_kind, b->site_id, b->component_kind, b->atom_id,
              b->priority, b->direction, b->value_mode,
              b->value[0] ? b->value : "1.0",
              b->confidence[0] ? b->confidence : "1.0",
              (unsigned long long)b->event_id,
              (unsigned long long)b->event_id);
      if (b->observe_window[0]) fprintf(f, " %s", b->observe_window);
      fputc('\n', f);
    } else {
      fprintf(f, "role_component %u %u %s %u %u %u %s %s %s %s %llu %llu",
              b->event_kind, b->site_id, role_name(b->role),
              b->component_kind, b->atom_id, b->priority, b->direction,
              b->value_mode, b->value[0] ? b->value : "1.0",
              b->confidence[0] ? b->confidence : "1.0",
              (unsigned long long)b->event_id,
              (unsigned long long)b->event_id);
      if (b->observe_window[0]) fprintf(f, " %s", b->observe_window);
      fputc('\n', f);
    }
  }
  for (uint32_t i = 0; i < same_object_relation_count; i++) {
    const same_object_relation_t *rel = &same_object_relations[i];
    atom_summary_t *atom = atom_slot(rel->atom_id);
    if (!atom || !atom->lift_allowed) {
      fclose(f);
      return 0;
    }
    if (rel->from_role == FORMTRIG_ROLE_UNKNOWN ||
        rel->to_role == FORMTRIG_ROLE_UNKNOWN)
      continue;
    fprintf(f, "same_object_relation %u %s %s", rel->atom_id,
            role_name(rel->from_role), role_name(rel->to_role));
    if (rel->object_expr[0]) fprintf(f, " %s", rel->object_expr);
    fputc('\n', f);
  }
  for (uint32_t i = 0; i < range_row_count; i++)
    fprintf(f, "%s\n", range_rows[i]);

  fclose(f);
  return 1;
}

int main(int argc, char **argv) {
  enum ft_category category = FT_CATEGORY_GENERIC;
  const char *site_map = NULL;
  const char *normalized_spec = NULL;
  const char *spec = NULL;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--category")) {
      if (++i >= argc) {
        usage(argv[0]);
        return 2;
      }
      category = parse_category(argv[i]);
    } else if (!strcmp(argv[i], "--site-map")) {
      if (++i >= argc) {
        usage(argv[0]);
        return 2;
      }
      site_map = argv[i];
    } else if (!strcmp(argv[i], "--normalized-spec")) {
      if (++i >= argc) {
        usage(argv[0]);
        return 2;
      }
      normalized_spec = argv[i];
    } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
      usage(argv[0]);
      return 0;
    } else if (!spec) {
      spec = argv[i];
    } else {
      usage(argv[0]);
      return 2;
    }
  }

  if (!site_map || !spec) {
    usage(argv[0]);
    return 2;
  }

  if (!load_site_map(site_map) || !load_lift_spec(spec)) return 2;
  if (!binding_count) {
    fprintf(stderr, "no bindings found in %s\n", spec);
    return 2;
  }

  resolve_bindings(category);
  print_header();
  uint32_t failures = 0;
  for (uint32_t i = 0; i < binding_count; i++) {
    print_binding(&bindings[i], category);
    if (!bindings[i].lift_allowed) failures++;
  }
  if (!failures && normalized_spec && !write_normalized_spec(normalized_spec))
    return 2;
  return failures ? 1 : 0;
}
