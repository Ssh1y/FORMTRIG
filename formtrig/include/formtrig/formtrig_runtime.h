#ifndef FORMTRIG_RUNTIME_H
#define FORMTRIG_RUNTIME_H

#include <stddef.h>
#include <stdint.h>
#include "formtrig/formtrig_abi.h"

#ifdef __cplusplus
extern "C" {
#endif

extern uint8_t __formtrig_active;
extern uint8_t __formtrig_pre_reach_enabled;
extern uint8_t __formtrig_suppress;

void formtrig_reset(void);
void formtrig_target_hit(const char *label);
int formtrig_target_selected(const char *label);
int formtrig_target_from_canary(void);
void formtrig_crash_predicate(int satisfied, const char *label);
void formtrig_record_direct_binary(int satisfied);
void formtrig_record_direct_margin(double distance, const char *kind);
void formtrig_record_lifted_distance(double distance, const char *kind);
void formtrig_record_progress_component(uint32_t kind, uint32_t atom_id,
                                        uint32_t priority, uint32_t flags,
                                        uint64_t source_id,
                                        uint64_t context_hash, double value,
                                        double confidence);
void formtrig_record_oob_margin(int64_t index, int64_t length, int64_t access_size);
void formtrig_record_divisor(int64_t divisor);
void formtrig_record_modular_add(uint64_t lhs, uint64_t rhs, unsigned bit_width);
void formtrig_record_null_sink(int is_null);
void formtrig_record_hot_range(uint32_t start, uint32_t len, double influence);
void formtrig_register_input(const void *data, size_t len);
void formtrig_finalize(void);
int formtrig_suppress_canary_events(void);
void formtrig_suppress_begin(void);
void formtrig_suppress_end(void);

void *__formtrig_malloc(size_t size, uint32_t site_id);
void __formtrig_free(void *ptr, uint32_t site_id);

void __formtrig_log_cmp(uint32_t site_id, uint32_t predicate, uint64_t lhs,
                        uint64_t rhs, uint8_t outcome);
void __formtrig_log_cmp_ex(uint32_t site_id, uint32_t predicate, uint64_t lhs,
                           uint64_t rhs, uint8_t outcome,
                           uint32_t site_class);
void __formtrig_log_branch(uint32_t site_id, uint8_t outcome);
void __formtrig_log_mem_access(uint32_t site_id, const void *ptr, size_t size,
                               uint8_t is_write, uint64_t value);
void __formtrig_log_mem_transfer(uint32_t site_id, const void *dst,
                                 const void *src, size_t size);
void __formtrig_log_div(uint32_t site_id, int64_t divisor);
void __formtrig_log_mod(uint32_t site_id, int64_t divisor);
void __formtrig_log_arith(uint32_t site_id, uint32_t opcode, uint64_t lhs,
                          uint64_t rhs, uint64_t result, uint32_t bit_width);

#ifdef __cplusplus
}
#endif

#endif
