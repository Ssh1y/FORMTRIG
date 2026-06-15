#define _POSIX_C_SOURCE 200809L

#include "formtrig/formtrig_abi.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ROWS 65536u

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

typedef struct query {
  const char *file_substr;
  const char *function_substr;
  const char *kind;
  uint32_t line;
  uint32_t line_window;
  uint32_t inst_no;
  uint32_t have_inst_no;
  const char *emit;
  const char *tc_id;
  const char *tc_category;
  const char *tc_expression;
  const char *atom_kind;
  const char *atom_expression;
  const char *atom_root;
  uint32_t atom_id;
  const char *role;
  const char *component_text;
  uint32_t component_kind;
  uint32_t priority;
  const char *direction;
  const char *value_mode;
  const char *observe_window;
  double value;
  double confidence;
} query_t;

static void usage(const char *argv0) {
  fprintf(stderr,
          "usage: %s [filters] "
          "[--emit csv|ids|env|lift-spec|binding-spec|binding-context] "
          "<site-map.tsv>\n"
          "\n"
          "filters:\n"
          "  --file SUBSTR       match source file substring\n"
          "  --function SUBSTR   match function substring\n"
          "  --kind KIND         match pass kind, e.g. cmp, branch, binary\n"
          "  --line N            match source line\n"
          "  --inst-no N         match LLVM instruction ordinal in function\n"
          "  --line-window N     allow +/- N around --line\n"
          "\n"
          "lift-spec output options:\n"
          "  --atom ID           atom id for generated role_component rows\n"
          "  --role ROLE         root_observe|guard|producer|use|repair_hook|...\n"
          "  --component KIND    FORMTRIG component kind number\n"
          "  --priority N        component priority\n"
          "  --direction DIR     lower|higher\n"
          "  --value-mode MODE   distance|hit|outcome|not_outcome|a|b|c|distance_to_c|absent\n"
          "  --value X           optional constant value\n"
          "  --observe-window W  post_reach|pre_reach|any\n"
          "  --confidence X      optional confidence, default 1.0\n",
          argv0);
  fprintf(stderr,
          "\n"
          "binding-spec output options:\n"
          "  --tc-id ID          target/TC id for generated BindingSpec\n"
          "  --tc-category CAT   TC category, defaults to --atom-kind\n"
          "  --tc-expr EXPR      full TC expression/description\n"
          "  --atom-kind CAT     per-atom category\n"
          "  --atom-expr EXPR    atom expression, defaults to --tc-expr\n"
          "  --atom-root ROOT    root variable/event expression, defaults to "
          "--atom-expr\n");
  fprintf(stderr,
          "\n"
          "binding-context output uses the BindingSpec metadata above and emits "
          "a JSON candidate context for offline human/LLM BindingSpec "
          "generation.\n");
}

static int parse_u32(const char *s, uint32_t *out) {
  if (!s || !out) return 0;
  char *end = NULL;
  errno = 0;
  unsigned long v = strtoul(s, &end, 0);
  if (errno || end == s || *end != '\0' || v > UINT32_MAX) return 0;
  *out = (uint32_t)v;
  return 1;
}

static int parse_double(const char *s, double *out) {
  if (!s || !out) return 0;
  char *end = NULL;
  errno = 0;
  double v = strtod(s, &end);
  if (errno || end == s || *end != '\0') return 0;
  *out = v;
  return 1;
}

static int eq(const char *a, const char *b) {
  return a && b && strcmp(a, b) == 0;
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

static void copy_field(char *dst, size_t dst_size, const char *src) {
  if (!dst || !dst_size) return;
  if (!src) src = "";
  snprintf(dst, dst_size, "%s", src);
}

static int read_row(char *line, site_row_t *row) {
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

static int row_matches(const site_row_t *row, const query_t *q) {
  if (q->file_substr && !strstr(row->file, q->file_substr)) return 0;
  if (q->function_substr && !strstr(row->function, q->function_substr))
    return 0;
  if (q->kind && strcmp(row->kind, q->kind)) return 0;
  if (q->have_inst_no && row->inst_no != q->inst_no) return 0;
  if (q->line) {
    uint32_t lo = q->line > q->line_window ? q->line - q->line_window : 0;
    uint32_t hi = q->line + q->line_window;
    if (row->line < lo || row->line > hi) return 0;
  }
  return 1;
}

static const char *mapping_status(uint32_t matches) {
  if (!matches) return "missing";
  if (matches == 1u) return "exact";
  return "ambiguous";
}

static void print_csv_header(void) {
  printf("site_id,kind,function,inst_no,opcode,file,line,column,"
         "mapping_status\n");
}

static void print_csv_row(const site_row_t *row, uint32_t matches) {
  printf("%u,%s,%s,%u,%s,%s,%u,%u,%s\n", row->site_id, row->kind,
         row->function, row->inst_no, row->opcode, row->file, row->line,
         row->column, mapping_status(matches));
}

static int validate_lift_spec_query(const query_t *q) {
  return q->atom_id && q->role && q->component_kind && q->priority &&
         q->direction && q->value_mode;
}

static void print_lift_spec_row(const site_row_t *row, const query_t *q) {
  printf("role_component * %u %s %u %u %u %s %s %.17g %.17g %u %u",
         row->site_id, q->role, q->component_kind, q->atom_id, q->priority,
         q->direction, q->value_mode, q->value, q->confidence, row->site_id,
         row->site_id);
  if (q->observe_window) printf(" %s", q->observe_window);
  putchar('\n');
}

static void print_yaml_quoted(const char *s) {
  putchar('\'');
  if (!s) s = "";
  for (; *s; s++) {
    if (*s == '\'') putchar('\'');
    putchar(*s);
  }
  putchar('\'');
}

static const char *query_tc_category(const query_t *q) {
  return q->tc_category ? q->tc_category : q->atom_kind;
}

static const char *query_atom_expression(const query_t *q) {
  return q->atom_expression ? q->atom_expression : q->tc_expression;
}

static const char *query_atom_root(const query_t *q) {
  return q->atom_root ? q->atom_root : query_atom_expression(q);
}

static int validate_binding_spec_query(const query_t *q) {
  return validate_lift_spec_query(q) && q->tc_id && q->tc_expression &&
         query_tc_category(q) && q->atom_kind && query_atom_expression(q) &&
         query_atom_root(q);
}

static int validate_binding_context_query(const query_t *q) {
  return q->tc_id && q->tc_expression && query_tc_category(q) &&
         q->atom_id && q->atom_kind && query_atom_expression(q) &&
         query_atom_root(q);
}

static void print_binding_spec_header(const query_t *q) {
  printf("tc_id: ");
  print_yaml_quoted(q->tc_id);
  printf("\n");
  printf("tc:\n");
  printf("  category: ");
  print_yaml_quoted(query_tc_category(q));
  printf("\n");
  printf("  expression: ");
  print_yaml_quoted(q->tc_expression);
  printf("\n");
  printf("atoms:\n");
  printf("  - id: %u\n", q->atom_id);
  printf("    expr: ");
  print_yaml_quoted(query_atom_expression(q));
  printf("\n");
  printf("    kind: ");
  print_yaml_quoted(q->atom_kind);
  printf("\n");
  printf("    root: ");
  print_yaml_quoted(query_atom_root(q));
  printf("\n");
  printf("bindings:\n");
}

static void print_binding_spec_row(const site_row_t *row, const query_t *q) {
  printf("  - id: ");
  char id[128];
  snprintf(id, sizeof(id), "%s_%u", q->role ? q->role : "binding",
           row->site_id);
  print_yaml_quoted(id);
  printf("\n");
  printf("    atom: %u\n", q->atom_id);
  printf("    role: ");
  print_yaml_quoted(q->role);
  printf("\n");
  printf("    expr: ");
  print_yaml_quoted(query_atom_expression(q));
  printf("\n");
  printf("    observe_at:\n");
  printf("      kind: ");
  print_yaml_quoted(row->kind);
  printf("\n");
  printf("      function: ");
  print_yaml_quoted(row->function);
  printf("\n");
  printf("      file: ");
  print_yaml_quoted(row->file);
  printf("\n");
  printf("      line: %u\n", row->line);
  printf("      inst_no: %u\n", row->inst_no);
  printf("      opcode: ");
  print_yaml_quoted(row->opcode);
  printf("\n");
  printf("      column: %u\n", row->column);
  printf("    component: ");
  uint32_t numeric_component = 0;
  if (q->component_text && !parse_u32(q->component_text, &numeric_component)) {
    print_yaml_quoted(q->component_text);
    printf("\n");
  } else {
    printf("%u\n", q->component_kind);
  }
  printf("    priority: %u\n", q->priority);
  printf("    direction: ");
  print_yaml_quoted(q->direction);
  printf("\n");
  printf("    value_mode: ");
  print_yaml_quoted(q->value_mode);
  printf("\n");
  printf("    value: %.17g\n", q->value);
  printf("    confidence: %.17g\n", q->confidence);
  if (q->observe_window) {
    printf("    observe_window: ");
    print_yaml_quoted(q->observe_window);
    printf("\n");
  }
}

static void print_json_quoted(const char *s) {
  putchar('"');
  if (!s) s = "";
  for (; *s; s++) {
    unsigned char c = (unsigned char)*s;
    if (*s == '"' || *s == '\\') {
      putchar('\\');
      putchar(*s);
    } else if (*s == '\b') {
      fputs("\\b", stdout);
    } else if (*s == '\f') {
      fputs("\\f", stdout);
    } else if (*s == '\n') {
      fputs("\\n", stdout);
    } else if (*s == '\r') {
      fputs("\\r", stdout);
    } else if (*s == '\t') {
      fputs("\\t", stdout);
    } else if (c < 0x20u) {
      printf("\\u%04x", c);
    } else {
      putchar(*s);
    }
  }
  putchar('"');
}

static void print_json_string_field(const char *key, const char *value,
                                    int comma) {
  print_json_quoted(key);
  printf(": ");
  print_json_quoted(value);
  if (comma) putchar(',');
  putchar('\n');
}

static int category_has(const query_t *q, const char *needle) {
  const char *cat = query_tc_category(q);
  return cat && strstr(cat, needle);
}

static const char *minimum_tier_for_category(const query_t *q) {
  if (category_has(q, "numeric")) return "B1";
  if (category_has(q, "equality") || category_has(q, "magic"))
    return "B1";
  if (category_has(q, "binary") || category_has(q, "null")) return "B2";
  if (category_has(q, "lifecycle") || category_has(q, "sequence") ||
      category_has(q, "compound"))
    return "B3";
  return "B1";
}

static void print_role_requirement(const char *role, const char *component,
                                   const char *value_mode, const char *why,
                                   int required, int comma) {
  printf("    {");
  printf("\"role\": ");
  print_json_quoted(role);
  printf(", \"required\": %s, \"component\": ", required ? "true" : "false");
  print_json_quoted(component);
  printf(", \"value_mode_hint\": ");
  print_json_quoted(value_mode);
  printf(", \"why\": ");
  print_json_quoted(why);
  printf("}");
  if (comma) putchar(',');
  putchar('\n');
}

static void print_role_requirements(const query_t *q) {
  printf("  \"role_requirements\": [\n");
  if (category_has(q, "numeric")) {
    print_role_requirement("root_observe", "boundary_margin", "distance",
                           "observe the TC operand or normalized boundary "
                           "margin",
                           1, 1);
    print_role_requirement("input_influence", "operand_influence", "hit",
                           "optional field/range evidence for steerable "
                           "mutations",
                           0, 0);
  } else if (category_has(q, "equality") || category_has(q, "magic")) {
    print_role_requirement("root_observe", "root_state", "distance",
                           "observe the compared operand or exact-match "
                           "progress",
                           1, 1);
    print_role_requirement("input_influence", "operand_influence", "hit",
                           "optional bytes/tokens controlling the operand", 0,
                           1);
    print_role_requirement("repair_hook", "operand_influence", "hit",
                           "optional deterministic repair for transformed "
                           "equality",
                           0, 0);
  } else if (category_has(q, "binary") || category_has(q, "null")) {
    print_role_requirement("root_observe", "root_state", "hit",
                           "observe the binary/null root state", 1, 1);
    print_role_requirement("producer", "producer_use", "hit",
                           "observe a writer/initializer/resetter for the "
                           "root",
                           1, 1);
    print_role_requirement("opposite_producer", "producer_use",
                           "not_outcome",
                           "distinguish bypass of the opposite state producer",
                           1, 1);
    print_role_requirement("use", "producer_use", "hit",
                           "observe the use context with the root still "
                           "aligned",
                           1, 1);
    print_role_requirement("guard", "guard_progress", "outcome",
                           "recommended guard or branch controlling the "
                           "producer/use path",
                           0, 0);
  } else if (category_has(q, "lifecycle") || category_has(q, "sequence") ||
             category_has(q, "compound")) {
    print_role_requirement("lifecycle_event", "lifecycle_prefix", "hit",
                           "observe ordered lifecycle events for prefix "
                           "progress",
                           1, 1);
    print_role_requirement("use", "producer_use", "hit",
                           "observe the terminal use or target phase", 1, 1);
    print_role_requirement("same_object", "object_identity", "hit",
                           "bind lifecycle events to the same object", 1, 1);
    print_role_requirement("guard", "guard_progress", "outcome",
                           "recommended phase/guard context for transitions",
                           0, 0);
  } else {
    print_role_requirement("root_observe", "root_state", "hit",
                           "generic minimum observation for TC-rooted lift", 1,
                           0);
  }
  printf("  ],\n");
}

static void print_candidate_site_json(const site_row_t *row, uint32_t matches,
                                      int comma) {
  printf("    {\n");
  printf("      \"site_id\": %u,\n", row->site_id);
  printf("      \"kind\": ");
  print_json_quoted(row->kind);
  printf(",\n");
  printf("      \"function\": ");
  print_json_quoted(row->function);
  printf(",\n");
  printf("      \"inst_no\": %u,\n", row->inst_no);
  printf("      \"opcode\": ");
  print_json_quoted(row->opcode);
  printf(",\n");
  printf("      \"file\": ");
  print_json_quoted(row->file);
  printf(",\n");
  printf("      \"line\": %u,\n", row->line);
  printf("      \"column\": %u,\n", row->column);
  printf("      \"mapping_status\": ");
  print_json_quoted(mapping_status(matches));
  printf("\n");
  printf("    }");
  if (comma) putchar(',');
  putchar('\n');
}

static void print_binding_context(const query_t *q, const site_row_t *rows,
                                  uint32_t row_count, uint32_t match_count) {
  printf("{\n");
  printf("  \"schema\": \"formtrig_binding_context_v1\",\n");
  printf("  \"intent\": ");
  print_json_quoted("offline BindingSpec candidate generation only; "
                    "admission is deterministic and runtime-gated");
  printf(",\n");
  printf("  \"tc_id\": ");
  print_json_quoted(q->tc_id);
  printf(",\n");
  printf("  \"tc\": {\n");
  printf("    ");
  print_json_string_field("category", query_tc_category(q), 1);
  printf("    ");
  print_json_string_field("expression", q->tc_expression, 0);
  printf("  },\n");
  printf("  \"atoms\": [\n");
  printf("    {\n");
  printf("      \"id\": %u,\n", q->atom_id);
  printf("      \"kind\": ");
  print_json_quoted(q->atom_kind);
  printf(",\n");
  printf("      \"minimum_binding_tier\": ");
  print_json_quoted(minimum_tier_for_category(q));
  printf(",\n");
  printf("      \"expr\": ");
  print_json_quoted(query_atom_expression(q));
  printf(",\n");
  printf("      \"root\": ");
  print_json_quoted(query_atom_root(q));
  printf("\n");
  printf("    }\n");
  printf("  ],\n");
  printf("  \"query\": {\n");
  printf("    \"file_substr\": ");
  print_json_quoted(q->file_substr);
  printf(",\n");
  printf("    \"function_substr\": ");
  print_json_quoted(q->function_substr);
  printf(",\n");
  printf("    \"kind\": ");
  print_json_quoted(q->kind);
  printf(",\n");
  printf("    \"line\": %u,\n", q->line);
  printf("    \"line_window\": %u,\n", q->line_window);
  printf("    \"inst_no\": ");
  if (q->have_inst_no)
    printf("%u,\n", q->inst_no);
  else
    printf("null,\n");
  printf("    \"matched_sites\": %u,\n", match_count);
  printf("    \"mapping_status\": ");
  print_json_quoted(mapping_status(match_count));
  printf("\n");
  printf("  },\n");
  print_role_requirements(q);
  printf("  \"candidate_sites\": [\n");
  uint32_t candidate_count = 0;
  for (uint32_t i = 0; i < row_count; i++) {
    if (row_matches(&rows[i], q)) candidate_count++;
  }
  uint32_t emitted = 0;
  for (uint32_t i = 0; i < row_count; i++) {
    if (!row_matches(&rows[i], q)) continue;
    emitted++;
    print_candidate_site_json(&rows[i], match_count,
                              emitted < candidate_count);
  }
  printf("  ],\n");
  printf("  \"binding_rules\": [\n");
  printf("    \"Use candidate sites only as evidence for semantic roles; do not "
         "encode target-id-specific workarounds in FORMTRIG core.\",\n");
  printf("    \"D_F must be computed from spec-generated/runtime raw events on "
         "the FORMTRIG side, not supplied by the target as an oracle.\",\n");
  printf("    \"For non-trigger progress, T/trigger counters are terminal-only "
         "and must not influence D_F or root_state.\",\n");
  printf("    \"Binary/null and lifecycle lifts require producer/use or event/"
         "object bindings that vary under calibration mutations.\"\n");
  printf("  ],\n");
  printf("  \"deterministic_gates\": [\n");
  printf("    \"formtrig_binding_spec_compile\",\n");
  printf("    \"formtrig_binding_map exact/ambiguous/missing and role-collapse "
         "audit\",\n");
  printf("    \"per-atom binding tier minimum audit\",\n");
  printf("    \"run_formtrig_seed_readiness\",\n");
  printf("    \"formtrig_lift_feature_audit provenance/oracle-leakage check\",\n");
  printf("    \"formtrig_binding_signal_diagnose D_F entropy and semantic-role "
         "delta check\",\n");
  printf("    \"run_formtrig_binding_candidate_sweep before long fuzzing\"\n");
  printf("  ]\n");
  printf("}\n");
}

int main(int argc, char **argv) {
  query_t q;
  memset(&q, 0, sizeof(q));
  q.emit = "csv";
  q.confidence = 1.0;
  q.value = 1.0;

  const char *path = NULL;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--file") && i + 1 < argc) {
      q.file_substr = argv[++i];
    } else if (!strcmp(argv[i], "--function") && i + 1 < argc) {
      q.function_substr = argv[++i];
    } else if (!strcmp(argv[i], "--kind") && i + 1 < argc) {
      q.kind = argv[++i];
    } else if (!strcmp(argv[i], "--line") && i + 1 < argc) {
      if (!parse_u32(argv[++i], &q.line)) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--line-window") && i + 1 < argc) {
      if (!parse_u32(argv[++i], &q.line_window)) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--inst-no") && i + 1 < argc) {
      if (!parse_u32(argv[++i], &q.inst_no)) {
        usage(argv[0]);
        return 2;
      }
      q.have_inst_no = 1u;
    } else if (!strcmp(argv[i], "--emit") && i + 1 < argc) {
      q.emit = argv[++i];
    } else if (!strcmp(argv[i], "--tc-id") && i + 1 < argc) {
      q.tc_id = argv[++i];
    } else if (!strcmp(argv[i], "--tc-category") && i + 1 < argc) {
      q.tc_category = argv[++i];
    } else if (!strcmp(argv[i], "--tc-expr") && i + 1 < argc) {
      q.tc_expression = argv[++i];
    } else if (!strcmp(argv[i], "--atom-kind") && i + 1 < argc) {
      q.atom_kind = argv[++i];
    } else if (!strcmp(argv[i], "--atom-expr") && i + 1 < argc) {
      q.atom_expression = argv[++i];
    } else if (!strcmp(argv[i], "--atom-root") && i + 1 < argc) {
      q.atom_root = argv[++i];
    } else if (!strcmp(argv[i], "--atom") && i + 1 < argc) {
      if (!parse_u32(argv[++i], &q.atom_id)) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--role") && i + 1 < argc) {
      q.role = argv[++i];
    } else if (!strcmp(argv[i], "--component") && i + 1 < argc) {
      q.component_text = argv[++i];
      q.component_kind = component_kind_from_text(q.component_text);
      if (!q.component_kind) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--priority") && i + 1 < argc) {
      if (!parse_u32(argv[++i], &q.priority)) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--direction") && i + 1 < argc) {
      q.direction = argv[++i];
    } else if (!strcmp(argv[i], "--value-mode") && i + 1 < argc) {
      q.value_mode = argv[++i];
    } else if ((!strcmp(argv[i], "--observe-window") ||
                !strcmp(argv[i], "--window")) &&
               i + 1 < argc) {
      q.observe_window = argv[++i];
    } else if (!strcmp(argv[i], "--value") && i + 1 < argc) {
      if (!parse_double(argv[++i], &q.value)) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--confidence") && i + 1 < argc) {
      if (!parse_double(argv[++i], &q.confidence)) {
        usage(argv[0]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
      usage(argv[0]);
      return 0;
    } else if (!path) {
      path = argv[i];
    } else {
      usage(argv[0]);
      return 2;
    }
  }

  if (!path) {
    usage(argv[0]);
    return 2;
  }

  if (strcmp(q.emit, "csv") && strcmp(q.emit, "ids") &&
      strcmp(q.emit, "env") && strcmp(q.emit, "lift-spec") &&
      strcmp(q.emit, "binding-spec") && strcmp(q.emit, "binding-context")) {
    usage(argv[0]);
    return 2;
  }

  if (!strcmp(q.emit, "lift-spec") && !validate_lift_spec_query(&q)) {
    usage(argv[0]);
    return 2;
  }

  if (!strcmp(q.emit, "binding-spec") && !validate_binding_spec_query(&q)) {
    usage(argv[0]);
    return 2;
  }

  if (!strcmp(q.emit, "binding-context") &&
      !validate_binding_context_query(&q)) {
    usage(argv[0]);
    return 2;
  }

  FILE *f = fopen(path, "r");
  if (!f) {
    perror(path);
    return 2;
  }

  static site_row_t rows[MAX_ROWS];
  uint32_t row_count = 0;
  uint32_t match_count = 0;
  char line[1024];
  while (fgets(line, sizeof(line), f)) {
    site_row_t row;
    memset(&row, 0, sizeof(row));
    if (!read_row(line, &row)) continue;
    if (row_matches(&row, &q)) {
      match_count++;
      if (row_count < MAX_ROWS) rows[row_count++] = row;
    }
  }
  fclose(f);

  if (!strcmp(q.emit, "csv")) print_csv_header();
  if (!strcmp(q.emit, "env")) printf("FORMTRIG_TARGET_SITE_IDS=");
  if (!strcmp(q.emit, "binding-spec") && match_count)
    print_binding_spec_header(&q);
  if (!strcmp(q.emit, "binding-context") && match_count) {
    print_binding_context(&q, rows, row_count, match_count);
    return 0;
  }

  uint32_t emitted = 0;
  for (uint32_t i = 0; i < row_count; i++) {
    if (!row_matches(&rows[i], &q)) continue;
    if (!strcmp(q.emit, "csv")) {
      print_csv_row(&rows[i], match_count);
    } else if (!strcmp(q.emit, "ids") || !strcmp(q.emit, "env")) {
      if (emitted) putchar(',');
      printf("%u", rows[i].site_id);
    } else if (!strcmp(q.emit, "lift-spec")) {
      print_lift_spec_row(&rows[i], &q);
    } else if (!strcmp(q.emit, "binding-spec")) {
      print_binding_spec_row(&rows[i], &q);
    }
    emitted++;
  }

  if (!strcmp(q.emit, "ids") || !strcmp(q.emit, "env")) putchar('\n');
  return emitted ? 0 : 1;
}
