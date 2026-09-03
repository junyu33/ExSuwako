#ifndef EXSUWAKO_DENSE_H
#define EXSUWAKO_DENSE_H

#include "poly.h"

typedef struct dense_plan dense_plan;

/* Return zero if the row-major m-by-m matrix size overflows size_t. */
int dense_matrix_bytes(size_t m, size_t *bytes);
dense_plan *dense_plan_create(const poly_t *modulus, size_t m);
void dense_plan_destroy(dense_plan *plan);
size_t dense_plan_storage_bytes(const dense_plan *plan);
void dense_reduce_into(const poly_t *input, dense_plan *plan, poly_t *output);
poly_t dense_reduce(const poly_t *input, const poly_t *modulus, size_t m);

#endif
