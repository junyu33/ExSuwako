#ifndef EXSUWAKO_NAIVE_H
#define EXSUWAKO_NAIVE_H
#include "poly.h"
/* The caller supplies a monic degree-m modulus; unified setup validates it. */
void naive_reduce_into(const poly_t *input, const poly_t *modulus,
                       size_t m, poly_t *output);
poly_t naive_reduce(const poly_t *input, const poly_t *modulus, size_t m);
#endif
