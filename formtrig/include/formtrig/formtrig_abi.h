#ifndef FORMTRIG_ABI_H
#define FORMTRIG_ABI_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef FORMTRIG_AFL_MAP_SIZE
#define FORMTRIG_AFL_MAP_SIZE 65536u
#endif

#define FORMTRIG_SHM_MAGIC 0x46545249u
#define FORMTRIG_SHM_VERSION 8u
#define FORMTRIG_SHM_OFFSET (FORMTRIG_AFL_MAP_SIZE + 16u)
#define FORMTRIG_SHM_SIZE 4096u
#define FORMTRIG_MAX_HOT_RANGES 8u
#define FORMTRIG_MAX_PROGRESS_COMPONENTS 16u
#define FORMTRIG_MAX_ATOM_SIGNALS 16u
#define FORMTRIG_FRONTIER_MAX 128u
#define FORMTRIG_SHM_ENV_VAR "__FORMTRIG_SHM_FILE"

typedef struct formtrig_hot_range {
  uint32_t start;
  uint32_t len;
  double influence;
  uint32_t hint_kind;
  uint32_t hint_value;
} formtrig_hot_range_t;

typedef struct formtrig_source_record {
  uint32_t kind;
  uint32_t site_id;
  uint32_t predicate;
  uint32_t outcome;
  uint32_t after_reach;
  uint32_t mode;
  uint32_t linked_count;
  uint32_t reserved;
  uint64_t a;
  uint64_t b;
  double distance;
} formtrig_source_record_t;

typedef struct formtrig_progress_component {
  uint32_t kind;
  uint32_t atom_id;
  uint32_t role;
  uint32_t priority;
  uint32_t flags;
  uint32_t reserved;
  uint64_t source_id;
  uint64_t context_hash;
  double value;
  double confidence;
} formtrig_progress_component_t;

typedef struct formtrig_atom_signal {
  uint32_t atom_id;
  uint32_t role_bits;
  uint32_t event_bits;
  uint32_t lifecycle_prefix;
  uint32_t root_value_bucket;
  uint32_t object_id_bucket;
  uint16_t guard_bits;
  uint16_t producer_bits;
  uint16_t use_bits;
  uint16_t flags;
} formtrig_atom_signal_t;

typedef struct formtrig_shm_record {
  uint32_t magic;
  uint32_t version;
  uint32_t flags;
  uint32_t target_hit_count;
  uint64_t trace_signature;
  double d_t;
  double d_f;
  double d_f_lifted;
  double d_f_spec_lifted;
  double d_f_heuristic_lifted;
  double d_f_manual_lifted;
  uint32_t hot_range_count;
  uint32_t component_count;
  uint32_t atom_signal_count;
  uint32_t source_flags;
  uint32_t observed_source_flags;
  formtrig_source_record_t source;
  formtrig_hot_range_t hot_ranges[FORMTRIG_MAX_HOT_RANGES];
  formtrig_progress_component_t components[FORMTRIG_MAX_PROGRESS_COMPONENTS];
  formtrig_atom_signal_t atom_signals[FORMTRIG_MAX_ATOM_SIGNALS];
} formtrig_shm_record_t;

enum {
  FORMTRIG_EVENT_TARGET_HIT = 1u,
  FORMTRIG_EVENT_CRASH_PREDICATE = 2u,
  FORMTRIG_EVENT_DIRECT_BINARY = 3u,
  FORMTRIG_EVENT_DIRECT_MARGIN = 4u,
  FORMTRIG_EVENT_MALLOC = 5u,
  FORMTRIG_EVENT_FREE = 6u,
  FORMTRIG_EVENT_CMP = 7u,
  FORMTRIG_EVENT_BRANCH = 8u,
  FORMTRIG_EVENT_MEMORY = 9u,
  FORMTRIG_EVENT_DIV_MOD = 10u,
  FORMTRIG_EVENT_ARITH = 11u,
  FORMTRIG_EVENT_MANUAL_LIFT = 12u,
  FORMTRIG_EVENT_CANARY = 13u,
  FORMTRIG_EVENT_MEM_TRANSFER = 15u
};

enum {
  FORMTRIG_FLAG_REACHED = 1u << 0,
  FORMTRIG_FLAG_CRASH_PREDICATE = 1u << 1,
  FORMTRIG_FLAG_LIFTED = 1u << 2,
  FORMTRIG_FLAG_SPEC_LIFTED = 1u << 3,
  FORMTRIG_FLAG_HEURISTIC_LIFTED = 1u << 4,
  FORMTRIG_FLAG_MANUAL_LIFTED = 1u << 5
};

enum {
  FORMTRIG_SOURCE_NATIVE = 1u << 0,
  FORMTRIG_SOURCE_SPEC_LIFTED = 1u << 1,
  FORMTRIG_SOURCE_HEURISTIC_LIFTED = 1u << 2,
  FORMTRIG_SOURCE_MANUAL_TARGET = 1u << 3
};

enum {
  FORMTRIG_MUTATION_HINT_NONE = 0u,
  FORMTRIG_MUTATION_HINT_SET_BYTE = 1u,
  FORMTRIG_MUTATION_HINT_CLEAR = 2u,
  FORMTRIG_MUTATION_HINT_FILL = 3u,
  FORMTRIG_MUTATION_HINT_DELETE = 4u,
  FORMTRIG_MUTATION_HINT_INSERT_BYTE = 5u,
  FORMTRIG_MUTATION_HINT_WRITE_U16_LE = 6u,
  FORMTRIG_MUTATION_HINT_WRITE_U32_LE = 7u,
  FORMTRIG_MUTATION_HINT_XOR_BYTE = 8u
};

enum {
  FORMTRIG_COMPONENT_NATIVE_DISTANCE = 1u,
  FORMTRIG_COMPONENT_LIFTED_DISTANCE = 2u,
  FORMTRIG_COMPONENT_BOUNDARY_MARGIN = 3u,
  FORMTRIG_COMPONENT_OPERAND_INFLUENCE = 4u,
  FORMTRIG_COMPONENT_GUARD_PROGRESS = 5u,
  FORMTRIG_COMPONENT_PRODUCER_USE = 6u,
  FORMTRIG_COMPONENT_LIFECYCLE_PREFIX = 7u,
  FORMTRIG_COMPONENT_OBJECT_IDENTITY = 8u,
  FORMTRIG_COMPONENT_EVENT_PHASE = 9u
};

enum {
  FORMTRIG_ROLE_UNKNOWN = 0u,
  FORMTRIG_ROLE_ROOT_OBSERVE = 1u,
  FORMTRIG_ROLE_GUARD = 2u,
  FORMTRIG_ROLE_PRODUCER = 3u,
  FORMTRIG_ROLE_DESIRED_PRODUCER = 4u,
  FORMTRIG_ROLE_OPPOSITE_PRODUCER = 5u,
  FORMTRIG_ROLE_USE = 6u,
  FORMTRIG_ROLE_LIFECYCLE_EVENT = 7u,
  FORMTRIG_ROLE_SAME_OBJECT = 8u,
  FORMTRIG_ROLE_INPUT_INFLUENCE = 9u,
  FORMTRIG_ROLE_REPAIR_HOOK = 10u
};

enum {
  FORMTRIG_ATOM_SIGNAL_OBSERVED = 1u << 0,
  FORMTRIG_ATOM_SIGNAL_HAS_ROOT_VALUE = 1u << 1,
  FORMTRIG_ATOM_SIGNAL_HAS_OBJECT_ID = 1u << 2
};

enum {
  FORMTRIG_COMPONENT_LOWER_IS_BETTER = 1u << 0,
  FORMTRIG_COMPONENT_HIGHER_IS_BETTER = 1u << 1,
  FORMTRIG_COMPONENT_TC_ROOTED = 1u << 2,
  FORMTRIG_COMPONENT_NATIVE = 1u << 3,
  FORMTRIG_COMPONENT_LIFTED = 1u << 4,
  FORMTRIG_COMPONENT_INPUT_INFLUENCE = 1u << 5,
  FORMTRIG_COMPONENT_SPEC_LIFTED = 1u << 6,
  FORMTRIG_COMPONENT_HEURISTIC_LIFTED = 1u << 7,
  FORMTRIG_COMPONENT_MANUAL_TARGET = 1u << 8
};

#ifdef __cplusplus
}
#endif

#endif
