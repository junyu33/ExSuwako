#ifndef EXSUWAKO_BARRETT_H
#define EXSUWAKO_BARRETT_H
#include "poly.h"
poly_t barrett_setup(const poly_t *modulus, size_t m);
poly_t barrett_reduce(const poly_t *c, const poly_t *modulus,
                      const poly_t *mu, size_t m);
#endif
