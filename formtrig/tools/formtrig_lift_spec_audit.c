#define _POSIX_C_SOURCE 200809L

#include "formtrig/formtrig_abi.h"

#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ATOMS 128u

enum ft_category {
  FT_CATEGORY_GENERIC = 0,
  FT_CATEGORY_NUMERIC,
  FT_CATEGORY_EQUALITY,
  FT_CATEGORY_BINARY_NULL,
  FT_CATEGORY_LIFECYCLE
};

typedef struct atom_binding {
  uint32_t atom_id;
  enum ft_category category;
  uint32_t roles;
  uint32_t event_count;
  uint32_t location_only_count;
  uint32_t influence_count;
  uint32_t collapsed;
  uint32_t site_count;
  uint32_t site_ids[64];
  uint32_t site_roles[64];
} atom_binding_t;

static atom_binding_t atoms[MAX_ATOMS];
static uint32_t atom_count;

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s [--category numeric|equality|binary-null|lifecycle] "
          "<FORMTRIG_LIFT_SPEC>\n",
          argv0);
}

static uint32_t role_bit(uint32_t role) {
  if (role == FORMTRIG_ROLE_UNKNOWN || role > 31u) return 0u;
  return 1u << (role - 1u);
}

static int has_role(const atom_binding_t *atom, uint32_t role) {
  return atom && (atom->roles & role_bit(role)) != 0u;
}

static atom_binding_t *existing_atom(uint32_t atom_id) {
  for (uint32_t i = 0; i < atom_count; i++)
    if (atoms[i].atom_id == atom_id) return &atoms[i];
  return NULL;
}

static atom_binding_t *atom_slot(uint32_t atom_id) {
  if (!atom_id) return NULL;
  atom_binding_t *existing = existing_atom(atom_id);
  if (existing) return existing;
  if (atom_count >= MAX_ATOMS) return NULL;
  atom_binding_t *atom = &atoms[atom_count++];
  memset(atom, 0, sizeof(*atom));
  atom->atom_id = atom_id;
  return atom;
}

static int parse_u32(const char *s, uint32_t *out) {
  if (!s || !out) return 0;
  if (strcmp(s, "*") == 0) {
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
  return FORMTRIG_ROLE_UNKNOWN;
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

static char *next_token(char **saveptr) {
  return strtok_r(NULL, " \t\r\n,", saveptr);
}

static void mark_role(uint32_t atom_id, uint32_t role, uint32_t site_id) {
  atom_binding_t *atom = atom_slot(atom_id);
  if (!atom) return;

  atom->event_count++;
  if (role == FORMTRIG_ROLE_UNKNOWN) {
    atom->location_only_count++;
    return;
  }

  atom->roles |= role_bit(role);
  if (role == FORMTRIG_ROLE_INPUT_INFLUENCE) atom->influence_count++;

  if (site_id != UINT32_MAX && role < 32u) {
    uint32_t bit = role_bit(role);
    for (uint32_t i = 0; i < atom->site_count; i++) {
      if (atom->site_ids[i] != site_id) continue;
      if ((atom->site_roles[i] & ~bit) != 0u) atom->collapsed = 1u;
      atom->site_roles[i] |= bit;
      return;
    }
    if (atom->site_count < 64u) {
      atom->site_ids[atom->site_count] = site_id;
      atom->site_roles[atom->site_count] = bit;
      atom->site_count++;
    }
  }
}

static void parse_line(char *line) {
  char *comment = strchr(line, '#');
  if (comment) *comment = '\0';
  char *saveptr = NULL;
  char *op = strtok_r(line, " \t\r\n,", &saveptr);
  if (!op) return;

  if (!strcmp(op, "atom_category") || !strcmp(op, "atom-category") ||
      !strcmp(op, "atom_kind") || !strcmp(op, "atom-kind")) {
    char *atom_text = next_token(&saveptr);
    char *category_text = next_token(&saveptr);
    uint32_t atom_id = 0;
    if (!parse_u32(atom_text, &atom_id)) return;
    atom_binding_t *atom = atom_slot(atom_id);
    if (atom) atom->category = parse_category(category_text);
    return;
  }

  if (!strcmp(op, "role_component") || !strcmp(op, "role-event") ||
      !strcmp(op, "role_event")) {
    char *event_kind = next_token(&saveptr);
    char *site = next_token(&saveptr);
    char *role_text = next_token(&saveptr);
    char *component = next_token(&saveptr);
    char *atom_text = next_token(&saveptr);
    (void)event_kind;
    (void)component;

    uint32_t site_id = 0;
    uint32_t atom_id = 0;
    if (!parse_u32(site, &site_id) || !parse_u32(atom_text, &atom_id)) return;
    mark_role(atom_id, parse_role(role_text), site_id);
    return;
  }

  if (!strcmp(op, "phase") || !strcmp(op, "prefix")) {
    char *event_kind = next_token(&saveptr);
    char *site = next_token(&saveptr);
    char *component = next_token(&saveptr);
    char *atom_text = next_token(&saveptr);
    (void)event_kind;
    (void)component;

    uint32_t site_id = 0;
    uint32_t atom_id = 0;
    if (!parse_u32(site, &site_id) || !parse_u32(atom_text, &atom_id)) return;
    mark_role(atom_id, FORMTRIG_ROLE_LIFECYCLE_EVENT, site_id);
    return;
  }

  if (!strcmp(op, "component") || !strcmp(op, "event")) {
    char *event_kind = next_token(&saveptr);
    char *site = next_token(&saveptr);
    char *component = next_token(&saveptr);
    char *atom_text = next_token(&saveptr);
    (void)event_kind;
    (void)component;

    uint32_t site_id = 0;
    uint32_t atom_id = 0;
    if (!parse_u32(site, &site_id) || !parse_u32(atom_text, &atom_id)) return;
    mark_role(atom_id, FORMTRIG_ROLE_UNKNOWN, site_id);
  }
}

static uint32_t binding_tier(const atom_binding_t *atom) {
  int root = has_role(atom, FORMTRIG_ROLE_ROOT_OBSERVE);
  int producer = has_role(atom, FORMTRIG_ROLE_PRODUCER) ||
                 has_role(atom, FORMTRIG_ROLE_DESIRED_PRODUCER) ||
                 has_role(atom, FORMTRIG_ROLE_OPPOSITE_PRODUCER);
  int use = has_role(atom, FORMTRIG_ROLE_USE);
  int lifecycle = has_role(atom, FORMTRIG_ROLE_LIFECYCLE_EVENT);
  int same_object = has_role(atom, FORMTRIG_ROLE_SAME_OBJECT);
  int influence = has_role(atom, FORMTRIG_ROLE_INPUT_INFLUENCE);

  if (root && producer && use && lifecycle && same_object && influence)
    return 4u;
  if (root && lifecycle && use && same_object) return 3u;
  if (root && producer && use) return 2u;
  if (root) return 1u;
  return 0u;
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

static const char *decision_reason(const atom_binding_t *atom,
                                   enum ft_category category, uint32_t tier) {
  if (atom->collapsed) return "semantic_role_collapse";
  if (tier < min_tier(category)) return "insufficient_binding_tier";
  if (category == FT_CATEGORY_BINARY_NULL &&
      (!has_role(atom, FORMTRIG_ROLE_ROOT_OBSERVE) ||
       !has_role(atom, FORMTRIG_ROLE_USE)))
    return "missing_root_or_use";
  if (category == FT_CATEGORY_LIFECYCLE &&
      !has_role(atom, FORMTRIG_ROLE_SAME_OBJECT))
    return "missing_same_object";
  return "ok";
}

static int compare_atoms(const void *a, const void *b) {
  const atom_binding_t *aa = (const atom_binding_t *)a;
  const atom_binding_t *bb = (const atom_binding_t *)b;
  if (aa->atom_id < bb->atom_id) return -1;
  if (aa->atom_id > bb->atom_id) return 1;
  return 0;
}

int main(int argc, char **argv) {
  enum ft_category fallback_category = FT_CATEGORY_GENERIC;
  const char *path = NULL;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--category")) {
      if (++i >= argc) {
        usage(argv[0]);
        return 2;
      }
      fallback_category = parse_category(argv[i]);
      continue;
    }
    if (!path)
      path = argv[i];
    else {
      usage(argv[0]);
      return 2;
    }
  }

  if (!path) {
    usage(argv[0]);
    return 2;
  }

  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 2;
  }

  char line[512];
  while (fgets(line, sizeof(line), f)) parse_line(line);
  fclose(f);

  qsort(atoms, atom_count, sizeof(atoms[0]), compare_atoms);
  printf("atom_id,category,binding_tier,lift_allowed,roles,event_count,"
         "location_only_count,collapsed,reason\n");

  int failures = 0;
  for (uint32_t i = 0; i < atom_count; i++) {
    atom_binding_t *atom = &atoms[i];
    uint32_t tier = binding_tier(atom);
    enum ft_category category =
        atom->category == FT_CATEGORY_GENERIC ? fallback_category
                                              : atom->category;
    const char *reason = decision_reason(atom, category, tier);
    int allowed = !strcmp(reason, "ok");
    if (!allowed) failures++;
    printf("%u,%s,%s,%s,0x%08x,%u,%u,%u,%s\n", atom->atom_id,
           category_name(category), tier_name(tier), allowed ? "true" : "false",
           atom->roles, atom->event_count, atom->location_only_count,
           atom->collapsed, reason);
  }

  if (!atom_count) {
    fprintf(stderr, "no atom bindings found in %s\n", path);
    return 2;
  }

  return failures ? 1 : 0;
}
