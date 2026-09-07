#ifndef EXSUWAKO_GS_H
#define EXSUWAKO_GS_H
#include "poly.h"

typedef struct gs_plan gs_plan;
typedef struct gs_online_context gs_online_context;

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

/*
 * Schedule-free FFR.  The context borrows the canonical ascending tap list
 * and owns only reusable state/descriptor scratch; doubled shifts are derived
 * anew inside every reduction call and are never reused as a retained plan.
 */
gs_online_context *gs_online_context_create(
    const size_t *taps, size_t s, size_t m);
void gs_online_context_destroy(gs_online_context *context);
size_t gs_online_context_storage_bytes(const gs_online_context *context);
void gs_reduce_online_into(
    const poly_t *input, gs_online_context *context, poly_t *output);
#endif
