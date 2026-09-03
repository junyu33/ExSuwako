#ifndef EXSUWAKO_GS_H
#define EXSUWAKO_GS_H
#include "poly.h"

typedef struct gs_plan gs_plan;

typedef struct {
    size_t aligned_word_contributions;
    size_t cross_word_contributions;
    size_t word_shifts;
    size_t word_xors;
    size_t logical_word_reads;
    size_t logical_word_writes;
    size_t scratch_words;
} gs_source_cost;

gs_plan *gs_plan_create(const size_t *taps, size_t s, size_t m);
void gs_plan_destroy(gs_plan *plan);
/* Read-only schedule metadata; these accessors do not instrument reduction. */
size_t gs_plan_feedback_stage_count(const gs_plan *plan);
size_t gs_plan_feedback_active_taps(const gs_plan *plan, size_t stage);
size_t gs_plan_feedback_active_tap_sum(const gs_plan *plan);
size_t gs_plan_feedback_scheduled_coefficient_work(const gs_plan *plan);
size_t gs_plan_storage_bytes(const gs_plan *plan);
gs_source_cost gs_plan_source_cost(const gs_plan *plan);
void gs_reduce_into(const poly_t *input, gs_plan *plan, poly_t *output);
poly_t gs_reduce_planned(const poly_t *input, gs_plan *plan);
poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m);
#endif
