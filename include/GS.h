#ifndef EXSUWAKO_GS_H
#define EXSUWAKO_GS_H
#include "poly.h"

typedef struct gs_plan gs_plan;

gs_plan *gs_plan_create(const size_t *taps, size_t s, size_t m);
void gs_plan_destroy(gs_plan *plan);
void gs_reduce_into(const poly_t *input, gs_plan *plan, poly_t *output);
poly_t gs_reduce_planned(const poly_t *input, gs_plan *plan);
poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m);
#endif
