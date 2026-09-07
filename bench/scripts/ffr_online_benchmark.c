#define _POSIX_C_SOURCE 200809L

#include "GS.h"
#include "naive.h"

#include <ctype.h>
#include <errno.h>
#include <time.h>

static volatile word_t benchmark_sink;
static uint64_t rng_state;

typedef struct {
    const char *name;
    void *context;
    void (*reduce_into)(const poly_t *, void *, poly_t *);
} timed_method;

static void planned_adapter(const poly_t *input, void *context,
                            poly_t *output) {
    gs_reduce_into(input, context, output);
}

static void online_adapter(const poly_t *input, void *context,
                           poly_t *output) {
    gs_reduce_online_into(input, context, output);
}

static uint64_t rng_next(void) {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

static size_t parse_size(const char *text, const char *name) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 0);
    if (!isdigit((unsigned char)text[0]) || !end || *end
            || errno == ERANGE || value > SIZE_MAX) {
        fprintf(stderr, "invalid %s: %s\n", name, text);
        exit(EXIT_FAILURE);
    }
    return (size_t)value;
}

static size_t *parse_taps(const char *text, size_t m, size_t *count) {
    *count = 0;
    if (strcmp(text, "-") == 0) return NULL;
    size_t capacity = 1;
    for (const char *p = text; *p; ++p) capacity += *p == ',';
    size_t *taps = malloc(capacity * sizeof(*taps));
    if (!taps) die("allocation failed");

    const char *cursor = text;
    while (*cursor) {
        if (!isdigit((unsigned char)*cursor)) die("invalid tap list");
        char *end = NULL;
        errno = 0;
        unsigned long long value = strtoull(cursor, &end, 10);
        if (end == cursor || errno == ERANGE || value >= m)
            die("tap is outside [0,m)");
        if (*count && value <= taps[*count - 1])
            die("taps must be canonical and strictly increasing");
        taps[(*count)++] = (size_t)value;
        if (!*end) break;
        if (*end != ',' || !end[1]) die("invalid tap list separator");
        cursor = end + 1;
    }
    return taps;
}

static struct timespec now(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0)
        die("clock_gettime failed");
    return value;
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

static void fill_input(poly_t *input, size_t m) {
    for (size_t i = 0; i < input->n; ++i)
        input->v[i] = (word_t)rng_next();
    unsigned top_bits = (unsigned)((2 * m) % WORD_BITS);
    if (top_bits)
        input->v[input->n - 1] &= ((word_t)1 << top_bits) - 1;
}

static int poly_equal(const poly_t *left, const poly_t *right) {
    size_t words = left->n > right->n ? left->n : right->n;
    for (size_t i = 0; i < words; ++i) {
        word_t a = i < left->n ? left->v[i] : 0;
        word_t b = i < right->n ? right->v[i] : 0;
        if (a != b) return 0;
    }
    return 1;
}

static void check_outputs(const timed_method methods[2], const poly_t *inputs,
                          size_t input_count, const poly_t *modulus,
                          size_t m) {
    size_t output_words = poly_words_for_bits(m);
    poly_t planned = poly_new(output_words);
    poly_t online = poly_new(output_words);
    poly_t reference = poly_new(poly_words_for_bits(2 * m));
    for (size_t i = 0; i < input_count; ++i) {
        methods[0].reduce_into(&inputs[i], methods[0].context, &planned);
        methods[1].reduce_into(&inputs[i], methods[1].context, &online);
        naive_reduce_into(&inputs[i], modulus, m, &reference);
        if (!poly_equal(&planned, &online)
                || !poly_equal(&planned, &reference))
            die("planned, online, and long-division outputs disagree");
    }
    poly_free(&reference);
    poly_free(&online);
    poly_free(&planned);
}

static void run_reduction_batches(const timed_method methods[2],
                                  const poly_t *inputs, size_t input_count,
                                  size_t output_words, size_t repeats,
                                  size_t trial, double result[2]) {
    double *samples = calloc(2 * repeats, sizeof(*samples));
    poly_t *outputs[2] = {calloc(input_count, sizeof(poly_t)),
                          calloc(input_count, sizeof(poly_t))};
    if (!samples || !outputs[0] || !outputs[1]) die("allocation failed");
    for (size_t method = 0; method < 2; ++method)
        for (size_t i = 0; i < input_count; ++i)
            outputs[method][i] = poly_new(output_words);

    for (size_t repeat = 0; repeat < repeats; ++repeat) {
        for (size_t position = 0; position < 2; ++position) {
            size_t method = (position + repeat + trial) % 2;
            struct timespec start = now();
            for (size_t i = 0; i < input_count; ++i)
                methods[method].reduce_into(
                    &inputs[i], methods[method].context, &outputs[method][i]);
            samples[method * repeats + repeat] =
                elapsed_ns(start, now()) / (double)input_count;
            for (size_t i = 0; i < input_count; ++i)
                benchmark_sink ^= outputs[method][i].v[0];
        }
    }
    for (size_t method = 0; method < 2; ++method) {
        result[method] = median(samples + method * repeats, repeats);
        for (size_t i = 0; i < input_count; ++i)
            poly_free(&outputs[method][i]);
        free(outputs[method]);
    }
    free(samples);
}

static void run_setup_batches(const size_t *taps, size_t tap_count, size_t m,
                              size_t repeats, size_t trial, double result[2]) {
    double *samples = calloc(2 * repeats, sizeof(*samples));
    if (!samples) die("allocation failed");
    for (size_t repeat = 0; repeat < repeats; ++repeat) {
        for (size_t position = 0; position < 2; ++position) {
            size_t method = (position + repeat + trial) % 2;
            struct timespec start = now();
            if (method == 0) {
                gs_plan *plan = gs_plan_create(taps, tap_count, m);
                samples[repeat] = elapsed_ns(start, now());
                gs_plan_destroy(plan);
            } else {
                gs_online_context *context =
                    gs_online_context_create(taps, tap_count, m);
                samples[repeats + repeat] = elapsed_ns(start, now());
                gs_online_context_destroy(context);
            }
        }
    }
    result[0] = median(samples, repeats);
    result[1] = median(samples + repeats, repeats);
    free(samples);
}

int main(int argc, char **argv) {
    if (argc != 7)
        die("usage: ffr_online_benchmark TAPS INPUTS REPEATS TRIALS M SEED");
    size_t inputs_count = parse_size(argv[2], "input count");
    size_t repeats = parse_size(argv[3], "repeat count");
    size_t trials = parse_size(argv[4], "trial count");
    size_t m = parse_size(argv[5], "modulus degree");
    uint64_t seed = (uint64_t)parse_size(argv[6], "seed");
    if (!inputs_count || !repeats || !trials || !m || !seed)
        die("counts, degree, and seed must be positive");

    size_t tap_count = 0;
    size_t *taps = parse_taps(argv[1], m, &tap_count);
    size_t delta_min = m;
    for (size_t i = 0; i < tap_count; ++i) {
        size_t delta = m - taps[i];
        if (delta < delta_min) delta_min = delta;
    }

    poly_t modulus = poly_from_exponents(m + 1, taps, tap_count);
    poly_set_bit(&modulus, m);
    gs_plan *planned = gs_plan_create(taps, tap_count, m);
    gs_online_context *online =
        gs_online_context_create(taps, tap_count, m);
    timed_method methods[2] = {
        {"PlannedFFR", planned, planned_adapter},
        {"OnlineFFR", online, online_adapter},
    };

    rng_state = seed;
    poly_t *inputs = calloc(inputs_count, sizeof(*inputs));
    if (!inputs) die("allocation failed");
    for (size_t i = 0; i < inputs_count; ++i) {
        inputs[i] = poly_new(poly_words_for_bits(2 * m));
        fill_input(&inputs[i], m);
    }
    check_outputs(methods, inputs, inputs_count, &modulus, m);

    double discarded[2];
    run_reduction_batches(methods, inputs, inputs_count,
                          poly_words_for_bits(m), repeats, 0, discarded);

    printf("m,word_bits,s,h,Delta_min,input_distribution,timing_scope,"
           "setup_scope,timing_order,PlannedFFR_plan_bytes,"
           "OnlineFFR_workspace_bytes,PlannedFFR_setup_ns,"
           "OnlineFFR_setup_ns,PlannedFFR_ns,OnlineFFR_ns,"
           "Online/Planned,trial,seed\n");
    for (size_t trial = 0; trial < trials; ++trial) {
        double setup[2];
        double timing[2];
        run_setup_batches(taps, tap_count, m, repeats, trial, setup);
        run_reduction_batches(methods, inputs, inputs_count,
                              poly_words_for_bits(m), repeats, trial, timing);
        printf("%zu,%d,%zu,%zu,", m, WORD_BITS, tap_count, tap_count + 1);
        if (tap_count) printf("%zu,", delta_min);
        else printf("NA,");
        printf("uniform-full-range:v1,ffr-online-steady-state:v1,"
               "ffr-online-workspace:v1,cyclic-two-method-rotation:v1,"
               "%zu,%zu,%.1f,%.1f,%.1f,%.1f,%.6f,%zu,%llu\n",
               gs_plan_storage_bytes(planned),
               gs_online_context_storage_bytes(online),
               setup[0], setup[1], timing[0], timing[1],
               timing[1] / timing[0], trial,
               (unsigned long long)seed);
    }

    for (size_t i = 0; i < inputs_count; ++i) poly_free(&inputs[i]);
    free(inputs);
    gs_online_context_destroy(online);
    gs_plan_destroy(planned);
    poly_free(&modulus);
    free(taps);
    return 0;
}
