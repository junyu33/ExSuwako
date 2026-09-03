#ifndef EXSUWAKO_REDUCTION_H
#define EXSUWAKO_REDUCTION_H

#include "poly.h"

typedef void (*reduction_reduce_into_fn)(
    const poly_t *input, void *context, poly_t *output);

typedef void (*reduction_destroy_fn)(void *context);
typedef size_t (*reduction_plan_storage_fn)(const void *context);

typedef struct {
    const char *name;
    size_t output_words;
    void *context;
    reduction_reduce_into_fn reduce_into;
    reduction_destroy_fn destroy;
    reduction_plan_storage_fn plan_storage;
} reduction_method;

reduction_method reduction_make_gs(const size_t *taps, size_t tap_count,
                                   size_t m);
reduction_method reduction_make_serial(const size_t *taps, size_t tap_count,
                                       size_t m);
reduction_method reduction_make_naive(const poly_t *modulus, size_t m,
                                      size_t input_words);
reduction_method reduction_make_barrett(const poly_t *modulus, size_t m);
reduction_method reduction_make_dense(const poly_t *modulus, size_t m);
size_t reduction_method_plan_storage_bytes(const reduction_method *method);
void reduction_method_destroy(reduction_method *method);

#endif
