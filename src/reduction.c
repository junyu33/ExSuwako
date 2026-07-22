#include "reduction.h"

#include "barrett.h"
#include "GS.h"
#include "naive.h"
#include "serial.h"

typedef struct {
    const poly_t *modulus;
    size_t m;
} naive_context;

typedef struct {
    poly_t mu;
    barrett_plan *plan;
} barrett_context;

static void gs_reduce_adapter(const poly_t *input, void *context,
                              poly_t *output) {
    gs_reduce_into(input, context, output);
}

static void serial_reduce_adapter(const poly_t *input, void *context,
                                  poly_t *output) {
    serial_reduce_into(input, context, output);
}

static void naive_reduce_adapter(const poly_t *input, void *context,
                                 poly_t *output) {
    naive_context *naive = context;
    naive_reduce_into(input, naive->modulus, naive->m, output);
}

static void barrett_reduce_adapter(const poly_t *input, void *context,
                                   poly_t *output) {
    barrett_context *barrett = context;
    barrett_reduce_into(input, barrett->plan, output);
}

static void gs_destroy_adapter(void *context) {
    gs_plan_destroy(context);
}

static void serial_destroy_adapter(void *context) {
    serial_plan_destroy(context);
}

static void naive_destroy_adapter(void *context) {
    free(context);
}

static void barrett_destroy_adapter(void *context) {
    barrett_context *barrett = context;
    if (!barrett) return;
    barrett_plan_destroy(barrett->plan);
    poly_free(&barrett->mu);
    free(barrett);
}

reduction_method reduction_make_gs(const size_t *taps, size_t tap_count,
                                   size_t m) {
    return (reduction_method){
        "GS",
        poly_words_for_bits(m),
        gs_plan_create(taps, tap_count, m),
        gs_reduce_adapter,
        gs_destroy_adapter
    };
}

reduction_method reduction_make_serial(const size_t *taps, size_t tap_count,
                                       size_t m) {
    return (reduction_method){
        "Serial",
        poly_words_for_bits(m),
        serial_plan_create(taps, tap_count, m),
        serial_reduce_adapter,
        serial_destroy_adapter
    };
}

reduction_method reduction_make_naive(const poly_t *modulus, size_t m,
                                      size_t input_words) {
    naive_context *context = malloc(sizeof(*context));
    if (!context) die("allocation failed");
    context->modulus = modulus;
    context->m = m;
    return (reduction_method){
        "Naive",
        input_words,
        context,
        naive_reduce_adapter,
        naive_destroy_adapter
    };
}

reduction_method reduction_make_barrett(const poly_t *modulus, size_t m) {
    barrett_context *context = malloc(sizeof(*context));
    if (!context) die("allocation failed");
    context->mu = barrett_setup(modulus, m);
    context->plan = barrett_plan_create(modulus, &context->mu, m);
    return (reduction_method){
        "BarrettGF2X",
        poly_words_for_bits(m),
        context,
        barrett_reduce_adapter,
        barrett_destroy_adapter
    };
}

void reduction_method_destroy(reduction_method *method) {
    if (!method || !method->destroy) return;
    method->destroy(method->context);
    method->context = NULL;
    method->reduce_into = NULL;
    method->destroy = NULL;
    method->output_words = 0;
}
