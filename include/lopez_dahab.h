#ifndef EXSUWAKO_LOPEZ_DAHAB_H
#define EXSUWAKO_LOPEZ_DAHAB_H

#include "poly.h"

typedef struct lopez_dahab_plan lopez_dahab_plan;

/* Algorithm 2 requires m > W and deg(q) < m-W for f=x^m+q. */
lopez_dahab_plan *lopez_dahab_plan_create(
    const size_t *taps, size_t tap_count, size_t m);
void lopez_dahab_plan_destroy(lopez_dahab_plan *plan);
size_t lopez_dahab_plan_storage_bytes(const lopez_dahab_plan *plan);
void lopez_dahab_reduce_into(const poly_t *input, lopez_dahab_plan *plan,
                             poly_t *output);

#endif
