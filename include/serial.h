#ifndef EXSUWAKO_SERIAL_H
#define EXSUWAKO_SERIAL_H

#include "poly.h"

typedef struct serial_plan serial_plan;

serial_plan *serial_plan_create(const size_t *taps, size_t s, size_t m);
void serial_plan_destroy(serial_plan *plan);
void serial_reduce_into(const poly_t *input, serial_plan *plan, poly_t *output);
poly_t serial_reduce_planned(const poly_t *input, serial_plan *plan);
poly_t serial_reduce(const poly_t *input, const size_t *taps, size_t s,
                     size_t m);

#endif
