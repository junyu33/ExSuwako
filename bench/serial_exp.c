#define _POSIX_C_SOURCE 200809L

#include "barrett.h"
#include "GS.h"
#include "serial.h"
#include <time.h>

static uint64_t rng_state;

static uint64_t rng_next(void) {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

static void shuffle(size_t *a, size_t n) {
    for (size_t i = n; i > 1; --i) {
        size_t j = (size_t)(rng_next() % i);
        size_t t = a[i - 1];
        a[i - 1] = a[j];
        a[j] = t;
    }
}

static void random_input(poly_t *input, size_t m) {
    memset(input->v, 0, input->n * sizeof(word_t));
    poly_set_bit(input, m + (size_t)(rng_next() % m));
    for (size_t i = 0; i < m; ++i)
        if (rng_next() & 1) poly_set_bit(input, i);
}

static int poly_equal(const poly_t *a, const poly_t *b) {
    size_t n = a->n > b->n ? a->n : b->n;
    for (size_t i = 0; i < n; ++i) {
        word_t x = i < a->n ? a->v[i] : 0;
        word_t y = i < b->n ? b->v[i] : 0;
        if (x != y) return 0;
    }
    return 1;
}

static struct timespec monotonic_time(void) {
    struct timespec result;
    if (clock_gettime(CLOCK_MONOTONIC, &result) != 0)
        die("clock_gettime failed");
    return result;
}

static double elapsed_ns(struct timespec start, struct timespec stop) {
    return (double)(stop.tv_sec - start.tv_sec) * 1e9
         + (double)(stop.tv_nsec - start.tv_nsec);
}

static int compare_double(const void *left, const void *right) {
    double a = *(const double *)left;
    double b = *(const double *)right;
    return (a > b) - (a < b);
}

static double median(double *values, size_t count) {
    qsort(values, count, sizeof(*values), compare_double);
    if (count & 1) return values[count / 2];
    return (values[count / 2 - 1] + values[count / 2]) / 2.0;
}

static volatile word_t benchmark_sink;

/*
 * This benchmark intentionally compares only the two sparse reducers. Plans,
 * input batches, and output buffers are prepared before the timestamp. The
 * timed region contains repeated calls to one reducer, so it measures the
 * steady-state distinction between serial U-propagation and GS doubling.
 * Correctness and checksum consumption are outside the timed region.
 */
static double time_reducer(int method, const poly_t *inputs, size_t count,
                           gs_plan *gs, serial_plan *serial_plan_value,
                           barrett_plan *barrett, int repeats) {
    double *samples = calloc((size_t)repeats, sizeof(*samples));
    poly_t *outputs = calloc(count, sizeof(*outputs));
    if (!samples || !outputs) die("allocation failed");

    size_t output_words = poly_words_for_bits(m);
    for (size_t i = 0; i < count; ++i)
        outputs[i] = poly_new(output_words);

    for (int repeat = 0; repeat < repeats; ++repeat) {
        struct timespec start = monotonic_time();
        for (size_t i = 0; i < count; ++i) {
            if (method == 1)
                serial_reduce_into(&inputs[i], serial_plan_value, &outputs[i]);
            else if (method == 2)
                barrett_reduce_into(&inputs[i], barrett, &outputs[i]);
            else
                gs_reduce_into(&inputs[i], gs, &outputs[i]);
        }
        samples[repeat] = elapsed_ns(start, monotonic_time()) / (double)count;

        /* Keep output observably live without charging checksum work. */
        word_t checksum = 0;
        for (size_t i = 0; i < count; ++i) {
            checksum ^= outputs[i].v[0];
            checksum ^= outputs[i].v[outputs[i].n - 1];
        }
        benchmark_sink ^= checksum;
    }

    double result = median(samples, (size_t)repeats);
    for (size_t i = 0; i < count; ++i) poly_free(&outputs[i]);
    free(outputs);
    free(samples);
    return result;
}

int main(int argc, char **argv) {
    int supports = argc > 1 ? atoi(argv[1]) : 1;
    int inputs_count = argc > 2 ? atoi(argv[2]) : 1;
    int repeats = argc > 3 ? atoi(argv[3]) : 1;
    size_t m = argc > 4 ? (size_t)strtoull(argv[4], NULL, 10) : 1024;
    size_t s = argc > 5 ? (size_t)strtoull(argv[5], NULL, 10) : 8;
    uint64_t seed = argc > 6
        ? (uint64_t)strtoull(argv[6], NULL, 0)
        : 0x9e3779b97f4a7c15ULL;
    if (m == 0 || s == 0 || s > m) die("invalid m or support size");

    rng_state = seed;
    double *gs_samples = calloc((size_t)supports, sizeof(*gs_samples));
    double *serial_samples = calloc((size_t)supports, sizeof(*serial_samples));
    double *barrett_samples = calloc((size_t)supports, sizeof(*barrett_samples));
    if (!gs_samples || !serial_samples || !barrett_samples) die("allocation failed");
    size_t *delta_values = calloc((size_t)supports, sizeof(*delta_values));
    if (!delta_values) die("allocation failed");

    for (int trial = 0; trial < supports; ++trial) {
        size_t *pool = malloc(m * sizeof(*pool));
        size_t *taps = malloc(s * sizeof(*taps));
        if (!pool || !taps) die("allocation failed");
        for (size_t i = 0; i < m; ++i) pool[i] = i;
        shuffle(pool, m);
        memcpy(taps, pool, s * sizeof(*taps));

        size_t delta_min = m;
        for (size_t i = 0; i < s; ++i) {
            size_t delta = m - taps[i];
            if (delta < delta_min) delta_min = delta;
        }
        delta_values[trial] = delta_min;

        poly_t modulus = poly_from_exponents(m + 1, taps, s);
        poly_set_bit(&modulus, m);
        poly_t mu = barrett_setup(&modulus, m);
        gs_plan *gs = gs_plan_create(taps, s, m);
        serial_plan *serial = serial_plan_create(taps, s, m);
        barrett_plan *barrett = barrett_plan_create(&modulus, &mu, m);
        poly_t *inputs = calloc((size_t)inputs_count, sizeof(*inputs));
        if (!inputs) die("allocation failed");
        for (int i = 0; i < inputs_count; ++i) {
            inputs[i] = poly_new(poly_words_for_bits(2 * m));
            random_input(&inputs[i], m);
        }

        for (int i = 0; i < inputs_count; ++i) {
            poly_t gs_result = poly_new(poly_words_for_bits(m));
            poly_t serial_result = poly_new(poly_words_for_bits(m));
            poly_t barrett_result = poly_new(poly_words_for_bits(m));
            gs_reduce_into(&inputs[i], gs, &gs_result);
            serial_reduce_into(&inputs[i], serial, &serial_result);
            barrett_reduce_into(&inputs[i], barrett, &barrett_result);
            if (!poly_equal(&gs_result, &serial_result)
                || !poly_equal(&gs_result, &barrett_result))
                die("GS/serial correctness mismatch");
            poly_free(&gs_result);
            poly_free(&serial_result);
            poly_free(&barrett_result);
        }

        gs_samples[trial] = time_reducer(
            0, inputs, (size_t)inputs_count, gs, serial, barrett, repeats);
        serial_samples[trial] = time_reducer(
            1, inputs, (size_t)inputs_count, gs, serial, barrett, repeats);
        barrett_samples[trial] = time_reducer(
            2, inputs, (size_t)inputs_count, gs, serial, barrett, repeats);

        for (int i = 0; i < inputs_count; ++i) poly_free(&inputs[i]);
        free(inputs);
        serial_plan_destroy(serial);
        gs_plan_destroy(gs);
        barrett_plan_destroy(barrett);
        poly_free(&modulus);
        poly_free(&mu);
        free(taps);
        free(pool);
    }

    double gs = median(gs_samples, (size_t)supports);
    double serial = median(serial_samples, (size_t)supports);
    double barrett = median(barrett_samples, (size_t)supports);
    size_t delta_min = delta_values[0];
    for (int trial = 1; trial < supports; ++trial)
        if (delta_values[trial] < delta_min) delta_min = delta_values[trial];
    printf("m,s,h,Delta_min,GS_ns,Serial_ns,BarrettGF2X_ns,Serial/GS,BarrettGF2X/GS\n");
    printf("%zu,%zu,%zu,%.0f,%.1f,%.1f,%.1f,%.3f,%.3f\n",
           m, s, s + 1, delta_min, gs, serial, barrett,
           serial / gs, barrett / gs);
    free(gs_samples);
    free(serial_samples);
    free(barrett_samples);
    free(delta_values);
    return 0;
}
