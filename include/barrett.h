#ifndef EXSUWAKO_BARRETT_H
#define EXSUWAKO_BARRETT_H
#include "poly.h"

typedef struct barrett_plan barrett_plan;

poly_t barrett_setup(const poly_t *modulus, size_t m);
barrett_plan *barrett_plan_create(const poly_t *modulus,
                                  const poly_t *mu, size_t m);
void barrett_plan_destroy(barrett_plan *plan);
size_t barrett_plan_storage_bytes(const barrett_plan *plan);
void barrett_reduce_into(const poly_t *c, barrett_plan *plan, poly_t *output);
poly_t barrett_reduce(const poly_t *c, const poly_t *modulus,
                      const poly_t *mu, size_t m);
#endif
