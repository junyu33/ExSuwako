#include "reduction.h"

#include "barrett.h"
#include "dense.h"
#include "generated.h"
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

static void dense_reduce_adapter(const poly_t *input, void *context,
                                 poly_t *output) {
    dense_reduce_into(input, context, output);
}

static void generated_reduce_adapter(const poly_t *input, void *context,
                                     poly_t *output) {
    generated_reduce_into(input, context, output);
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

static void dense_destroy_adapter(void *context) {
    dense_plan_destroy(context);
}

static void generated_destroy_adapter(void *context) {
    generated_plan_destroy(context);
}

static size_t gs_storage_adapter(const void *context) {
    return gs_plan_storage_bytes(context);
}

static size_t serial_storage_adapter(const void *context) {
    return serial_plan_storage_bytes(context);
}

static size_t naive_storage_adapter(const void *context) {
    return context ? sizeof(naive_context) : 0;
}

static size_t barrett_storage_adapter(const void *context) {
    const barrett_context *barrett = context;
    if (!barrett) return 0;
    return sizeof(*barrett)
         + barrett->mu.n * sizeof(*barrett->mu.v)
         + barrett_plan_storage_bytes(barrett->plan);
}

static size_t dense_storage_adapter(const void *context) {
    return dense_plan_storage_bytes(context);
}

static size_t generated_storage_adapter(const void *context) {
    return generated_plan_storage_bytes(context);
}

reduction_method reduction_make_gs(const size_t *taps, size_t tap_count,
                                   size_t m) {
    gs_plan *plan = gs_plan_create(taps, tap_count, m);
    return (reduction_method){
        .name = "GS",
        .output_words = poly_words_for_bits(m),
        .context = plan,
        .reduce_into = gs_reduce_adapter,
        .destroy = gs_destroy_adapter,
        .plan_storage = gs_storage_adapter,
    };
}

reduction_method reduction_make_serial(const size_t *taps, size_t tap_count,
                                       size_t m) {
    serial_plan *plan = serial_plan_create(taps, tap_count, m);
    return (reduction_method){
        .name = "Serial",
        .output_words = poly_words_for_bits(m),
        .context = plan,
        .reduce_into = serial_reduce_adapter,
        .destroy = serial_destroy_adapter,
        .plan_storage = serial_storage_adapter,
    };
}

reduction_method reduction_make_naive(const poly_t *modulus, size_t m,
                                      size_t input_words) {
    if (m == 0) die("naive modulus degree must be positive");
    if (!modulus || poly_degree(modulus) != (long)m)
        die("naive modulus must be monic of degree m");
    naive_context *context = malloc(sizeof(*context));
    if (!context) die("allocation failed");
    context->modulus = modulus;
    context->m = m;
    return (reduction_method){
        .name = "Naive",
        .output_words = input_words,
        .context = context,
        .reduce_into = naive_reduce_adapter,
        .destroy = naive_destroy_adapter,
        .plan_storage = naive_storage_adapter,
    };
}

reduction_method reduction_make_barrett(const poly_t *modulus, size_t m) {
    barrett_context *context = malloc(sizeof(*context));
    if (!context) die("allocation failed");
    context->mu = barrett_setup(modulus, m);
    context->plan = barrett_plan_create(modulus, &context->mu, m);
    return (reduction_method){
        .name = "BarrettGF2X",
        .output_words = poly_words_for_bits(m),
        .context = context,
        .reduce_into = barrett_reduce_adapter,
        .destroy = barrett_destroy_adapter,
        .plan_storage = barrett_storage_adapter,
    };
}

reduction_method reduction_make_dense(const poly_t *modulus, size_t m) {
    dense_plan *plan = dense_plan_create(modulus, m);
    return (reduction_method){
        .name = "Dense",
        .output_words = poly_words_for_bits(m),
        .context = plan,
        .reduce_into = dense_reduce_adapter,
        .destroy = dense_destroy_adapter,
        .plan_storage = dense_storage_adapter,
    };
}

reduction_method reduction_make_generated(const char *shared_object,
                                           const size_t *taps,
                                           size_t tap_count, size_t m) {
    generated_plan *plan = generated_plan_load(
        shared_object, m, taps, tap_count);
    return (reduction_method){
        .name = "Generated",
        .output_words = poly_words_for_bits(m),
        .context = plan,
        .reduce_into = generated_reduce_adapter,
        .destroy = generated_destroy_adapter,
        .plan_storage = generated_storage_adapter,
    };
}

size_t reduction_method_plan_storage_bytes(const reduction_method *method) {
    return method && method->plan_storage
        ? method->plan_storage(method->context)
        : 0;
}

void reduction_method_destroy(reduction_method *method) {
    if (!method || !method->destroy) return;
    method->destroy(method->context);
    method->context = NULL;
    method->reduce_into = NULL;
    method->destroy = NULL;
    method->plan_storage = NULL;
    method->output_words = 0;
}
