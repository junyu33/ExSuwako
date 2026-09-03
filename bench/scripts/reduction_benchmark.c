#define _POSIX_C_SOURCE 200809L

#include "GS.h"
#include "reduction.h"

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <time.h>

static uint64_t rng_state;
static const char *input_distribution = "uniform-full-range:v1";
static const char *timing_scope = "reduction-steady-state:v1";
static const char *setup_scope = "modulus-plan:v1";
static const char *timing_order = "cyclic-method-rotation:v1";
static const char *gs_source_cost_model = "scalar-source-v1";

typedef enum {
    REDUCER_GS,
    REDUCER_SERIAL,
    REDUCER_NAIVE,
    REDUCER_BARRETT
} reducer_kind;

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

static int compare_size_t(const void *left, const void *right) {
    size_t a = *(const size_t *)left;
    size_t b = *(const size_t *)right;
    return (a > b) - (a < b);
}

static size_t parse_size(const char *text, const char *name) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (!isdigit((unsigned char)text[0]) || !end || *end || errno == ERANGE ||
        value > SIZE_MAX) {
        fprintf(stderr, "invalid %s: %s\n", name, text);
        exit(EXIT_FAILURE);
    }
    return (size_t)value;
}

static int parse_positive_int(const char *text, const char *name) {
    size_t value = parse_size(text, name);
    if (value == 0 || value > INT_MAX) {
        fprintf(stderr, "%s must be in [1, %d]\n", name, INT_MAX);
        exit(EXIT_FAILURE);
    }
    return (int)value;
}

static uint64_t parse_seed(const char *text) {
    char *end = NULL;
    errno = 0;
    if (!isdigit((unsigned char)text[0])) die("invalid seed");
    unsigned long long value = strtoull(text, &end, 0);
    if (!end || *end || errno == ERANGE || value > UINT64_MAX)
        die("invalid seed");
    return (uint64_t)value;
}

static size_t *parse_tap_list(const char *text, size_t m, size_t *count) {
    *count = 0;
    if (strcmp(text, "-") == 0) return NULL;
    if (!text[0]) die("tap list must be '-' or a comma-separated list");

    size_t capacity = 1;
    for (const char *p = text; *p; ++p)
        if (*p == ',') ++capacity;
    size_t *taps = malloc(capacity * sizeof(*taps));
    if (!taps) die("allocation failed");

    const char *cursor = text;
    while (*cursor) {
        if (!isdigit((unsigned char)*cursor))
            die("tap list must contain canonical unsigned decimal integers");
        char *end = NULL;
        errno = 0;
        unsigned long long value = strtoull(cursor, &end, 10);
        if (end == cursor || errno == ERANGE || value > SIZE_MAX)
            die("tap exponent is out of range");
        if (value >= m) die("tap exponent must be smaller than m");
        if (*count && value <= taps[*count - 1])
            die("tap list must be strictly increasing and duplicate-free");
        taps[(*count)++] = (size_t)value;
        if (*end == '\0') break;
        if (*end != ',' || end[1] == '\0')
            die("tap list must be comma-separated without empty entries");
        cursor = end + 1;
    }
    return taps;
}

static char *serialize_taps(const size_t *taps, size_t count) {
    if (count == 0) {
        char *empty = malloc(2);
        if (!empty) die("allocation failed");
        strcpy(empty, "-");
        return empty;
    }

    size_t bytes = 1;
    for (size_t i = 0; i < count; ++i)
        bytes += (size_t)snprintf(NULL, 0, "%zu", taps[i]) + (i != 0);
    char *result = malloc(bytes);
    if (!result) die("allocation failed");
    size_t offset = 0;
    for (size_t i = 0; i < count; ++i) {
        if (i) result[offset++] = ';';
        offset += (size_t)snprintf(result + offset, bytes - offset,
                                   "%zu", taps[i]);
    }
    return result;
}

static char *serialize_active_tap_counts(const gs_plan *plan) {
    size_t stages = gs_plan_feedback_stage_count(plan);
    if (stages == 0) {
        char *empty = malloc(2);
        if (!empty) die("allocation failed");
        strcpy(empty, "-");
        return empty;
    }

    size_t bytes = 1;
    for (size_t stage = 0; stage < stages; ++stage)
        bytes += (size_t)snprintf(
            NULL, 0, "%zu", gs_plan_feedback_active_taps(plan, stage))
            + (stage != 0);
    char *result = malloc(bytes);
    if (!result) die("allocation failed");
    size_t offset = 0;
    for (size_t stage = 0; stage < stages; ++stage) {
        if (stage) result[offset++] = ';';
        offset += (size_t)snprintf(
            result + offset, bytes - offset, "%zu",
            gs_plan_feedback_active_taps(plan, stage));
    }
    return result;
}

/* Uniform A in the full 2m-bit reduction domain, equivalently A=L+x^m H. */
static void uniform_full_range_input(poly_t *input, size_t m) {
    memset(input->v, 0, input->n * sizeof(word_t));
    for (size_t i = 0; i < 2 * m; ++i)
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

static reduction_method make_reducer(reducer_kind kind, const size_t *taps,
                                     size_t tap_count, const poly_t *modulus,
                                     size_t m, size_t input_words) {
    switch (kind) {
    case REDUCER_GS:
        return reduction_make_gs(taps, tap_count, m);
    case REDUCER_SERIAL:
        return reduction_make_serial(taps, tap_count, m);
    case REDUCER_NAIVE:
        return reduction_make_naive(modulus, m, input_words);
    case REDUCER_BARRETT:
        return reduction_make_barrett(modulus, m);
    }
    die("unknown reducer kind");
    return (reduction_method){0};
}

/*
 * Modulus-dependent plan setup timing.
 *
 * m, taps, and modulus are already materialized. Each sample constructs a
 * fresh method, stops the clock, and then destroys it. Thus schedule or
 * reciprocal generation and plan-owned scratch allocation are included,
 * while parsing, modulus materialization, teardown, and benchmark buffers are
 * excluded.
 */
static void time_setups_rotating(const reducer_kind *kinds,
                                 size_t method_count, const size_t *taps,
                                 size_t tap_count, const poly_t *modulus,
                                 size_t m, size_t input_words, int repeats,
                                 double *results) {
    double *samples = calloc(
        method_count * (size_t)repeats, sizeof(*samples));
    if (!samples) die("allocation failed");

    for (int repeat = 0; repeat < repeats; ++repeat) {
        for (size_t position = 0; position < method_count; ++position) {
            size_t method = (position + (size_t)repeat) % method_count;
            struct timespec start = monotonic_time();
            reduction_method plan = make_reducer(
                kinds[method], taps, tap_count, modulus, m, input_words);
            samples[method * (size_t)repeats + (size_t)repeat] =
                elapsed_ns(start, monotonic_time());
            reduction_method_destroy(&plan);
        }
    }

    for (size_t method = 0; method < method_count; ++method)
        results[method] = median(
            &samples[method * (size_t)repeats], (size_t)repeats);
    free(samples);
}

/*
 * Steady-state reduction timing with cyclic method-order rotation.
 *
 * On batch repeat r, timing starts with method r mod method_count and then
 * wraps around. If repeats is divisible by method_count, every method occupies
 * every timing position equally often. The timed region contains only calls
 * to reduce_into(); setup, allocation, checks, and checksums remain outside.
 */
static void time_reducers_rotating(const reduction_method *methods,
                                   size_t method_count, const poly_t *inputs,
                                   size_t count, int repeats, double *results) {
    double *samples = calloc(
        method_count * (size_t)repeats, sizeof(*samples));
    poly_t **outputs = calloc(method_count, sizeof(*outputs));
    if (!samples || !outputs) die("allocation failed");
    for (size_t method = 0; method < method_count; ++method) {
        outputs[method] = calloc(count, sizeof(*outputs[method]));
        if (!outputs[method]) die("allocation failed");
        for (size_t i = 0; i < count; ++i)
            outputs[method][i] = poly_new(methods[method].output_words);
    }

    for (int repeat = 0; repeat < repeats; ++repeat) {
        for (size_t position = 0; position < method_count; ++position) {
            size_t method = (position + (size_t)repeat) % method_count;
            struct timespec start = monotonic_time();
            for (size_t i = 0; i < count; ++i)
                methods[method].reduce_into(
                    &inputs[i], methods[method].context, &outputs[method][i]);
            samples[method * (size_t)repeats + (size_t)repeat] =
                elapsed_ns(start, monotonic_time()) / (double)count;

            word_t checksum = 0;
            for (size_t i = 0; i < count; ++i) {
                checksum ^= outputs[method][i].v[0];
                checksum ^= outputs[method][i].v[outputs[method][i].n - 1];
            }
            benchmark_sink ^= checksum;
        }
    }

    for (size_t method = 0; method < method_count; ++method) {
        results[method] = median(
            &samples[method * (size_t)repeats], (size_t)repeats);
        for (size_t i = 0; i < count; ++i)
            poly_free(&outputs[method][i]);
        free(outputs[method]);
    }
    free(outputs);
    free(samples);
}

static void check_reducers(const reduction_method *methods, size_t method_count,
                           const poly_t *inputs, size_t input_count) {
    poly_t *outputs = calloc(method_count, sizeof(*outputs));
    if (!outputs) die("allocation failed");
    for (size_t method = 0; method < method_count; ++method)
        outputs[method] = poly_new(methods[method].output_words);

    for (size_t i = 0; i < input_count; ++i) {
        for (size_t method = 0; method < method_count; ++method)
            methods[method].reduce_into(
                &inputs[i], methods[method].context, &outputs[method]);

        for (size_t method = 1; method < method_count; ++method)
            if (!poly_equal(&outputs[0], &outputs[method]))
                die("reduction correctness mismatch");
    }

    for (size_t method = 0; method < method_count; ++method)
        poly_free(&outputs[method]);
    free(outputs);
}

int main(int argc, char **argv) {
    int exact_mode = argc > 1 && strcmp(argv[1], "--taps") == 0;
    int supports;
    int inputs_count;
    int repeats;
    size_t m;
    size_t s;
    uint64_t seed;
    int skip_naive;
    size_t *exact_taps = NULL;

    if (exact_mode) {
        if (argc < 7 || argc > 8)
            die("usage: reduction_benchmark --taps LIST inputs repeats m seed [no-naive]");
        supports = 1;
        inputs_count = parse_positive_int(argv[3], "input count");
        repeats = parse_positive_int(argv[4], "repeat count");
        m = parse_size(argv[5], "modulus degree");
        seed = parse_seed(argv[6]);
        skip_naive = argc == 8 && strcmp(argv[7], "no-naive") == 0;
        if (argc == 8 && !skip_naive) die("unknown exact-mode option");
        if (m == 0) die("modulus degree must be positive");
        exact_taps = parse_tap_list(argv[2], m, &s);
    } else {
        supports = argc > 1 ? atoi(argv[1]) : 1;
        inputs_count = argc > 2 ? atoi(argv[2]) : 1;
        repeats = argc > 3 ? atoi(argv[3]) : 1;
        m = argc > 4 ? (size_t)strtoull(argv[4], NULL, 10) : 1024;
        s = argc > 5 ? (size_t)strtoull(argv[5], NULL, 10) : 8;
        seed = argc > 6
            ? (uint64_t)strtoull(argv[6], NULL, 0)
            : 0x9e3779b97f4a7c15ULL;
        skip_naive = argc > 7 && strcmp(argv[7], "no-naive") == 0;
        if (argc > 8 || (argc == 8 && !skip_naive))
            die("unknown random-mode option");
        if (m == 0 || s > m) die("invalid m or support size");
    }
    if (supports <= 0 || inputs_count <= 0 || repeats <= 0)
        die("supports, inputs, and repeats must be positive");
    if (seed == 0) die("seed must be nonzero for the xorshift generator");

    rng_state = seed;
    double *gs_samples = calloc((size_t)supports, sizeof(*gs_samples));
    double *serial_samples = calloc((size_t)supports, sizeof(*serial_samples));
    double *naive_samples = calloc((size_t)supports, sizeof(*naive_samples));
    double *barrett_samples = calloc((size_t)supports, sizeof(*barrett_samples));
    double *gs_setup_samples =
        calloc((size_t)supports, sizeof(*gs_setup_samples));
    double *serial_setup_samples =
        calloc((size_t)supports, sizeof(*serial_setup_samples));
    double *naive_setup_samples =
        calloc((size_t)supports, sizeof(*naive_setup_samples));
    double *barrett_setup_samples =
        calloc((size_t)supports, sizeof(*barrett_setup_samples));
    if (!gs_samples || !serial_samples || !naive_samples || !barrett_samples ||
        !gs_setup_samples || !serial_setup_samples || !naive_setup_samples ||
        !barrett_setup_samples)
        die("allocation failed");
    size_t *delta_values = calloc((size_t)supports, sizeof(*delta_values));
    int *has_delta = calloc((size_t)supports, sizeof(*has_delta));
    char **tap_values = calloc((size_t)supports, sizeof(*tap_values));
    size_t *feedback_stage_values =
        calloc((size_t)supports, sizeof(*feedback_stage_values));
    char **active_tap_values =
        calloc((size_t)supports, sizeof(*active_tap_values));
    size_t *active_tap_sum_values =
        calloc((size_t)supports, sizeof(*active_tap_sum_values));
    size_t *scheduled_work_values =
        calloc((size_t)supports, sizeof(*scheduled_work_values));
    gs_source_cost *source_cost_values =
        calloc((size_t)supports, sizeof(*source_cost_values));
    if (!delta_values || !has_delta || !tap_values || !feedback_stage_values ||
        !active_tap_values || !active_tap_sum_values || !scheduled_work_values ||
        !source_cost_values)
        die("allocation failed");

    for (int trial = 0; trial < supports; ++trial) {
        size_t *pool = NULL;
        size_t *taps = s ? malloc(s * sizeof(*taps)) : NULL;
        if (s && !taps) die("allocation failed");
        if (exact_mode) {
            if (s) memcpy(taps, exact_taps, s * sizeof(*taps));
        } else {
            pool = malloc(m * sizeof(*pool));
            if (!pool) die("allocation failed");
            for (size_t i = 0; i < m; ++i) pool[i] = i;
            shuffle(pool, m);
            if (s) memcpy(taps, pool, s * sizeof(*taps));
            if (s) qsort(taps, s, sizeof(*taps), compare_size_t);
        }
        tap_values[trial] = serialize_taps(taps, s);

        if (s) {
            size_t delta_min = m;
            for (size_t i = 0; i < s; ++i) {
                size_t delta = m - taps[i];
                if (delta < delta_min) delta_min = delta;
            }
            delta_values[trial] = delta_min;
            has_delta[trial] = 1;
        }

        poly_t modulus = poly_from_exponents(m + 1, taps, s);
        poly_set_bit(&modulus, m);

        size_t input_words = poly_words_for_bits(2 * m);
        reducer_kind kinds[4];
        size_t method_count = 0;
        kinds[method_count++] = REDUCER_GS;
        kinds[method_count++] = REDUCER_SERIAL;
        if (!skip_naive) kinds[method_count++] = REDUCER_NAIVE;
        kinds[method_count++] = REDUCER_BARRETT;

        double setup_timings[4] = {0};
        time_setups_rotating(kinds, method_count, taps, s, &modulus, m,
                             input_words, repeats, setup_timings);
        gs_setup_samples[trial] = setup_timings[0];
        serial_setup_samples[trial] = setup_timings[1];
        if (!skip_naive) naive_setup_samples[trial] = setup_timings[2];
        barrett_setup_samples[trial] = setup_timings[method_count - 1];

        reduction_method methods[4];
        for (size_t method = 0; method < method_count; ++method)
            methods[method] = make_reducer(
                kinds[method], taps, s, &modulus, m, input_words);
        gs_plan *gs = methods[0].context;
        feedback_stage_values[trial] = gs_plan_feedback_stage_count(gs);
        active_tap_values[trial] = serialize_active_tap_counts(gs);
        active_tap_sum_values[trial] =
            gs_plan_feedback_active_tap_sum(gs);
        scheduled_work_values[trial] =
            gs_plan_feedback_scheduled_coefficient_work(gs);
        source_cost_values[trial] = gs_plan_source_cost(gs);

        poly_t *inputs = calloc((size_t)inputs_count, sizeof(*inputs));
        if (!inputs) die("allocation failed");
        for (int i = 0; i < inputs_count; ++i) {
            inputs[i] = poly_new(input_words);
            uniform_full_range_input(&inputs[i], m);
        }

        check_reducers(methods, method_count, inputs, (size_t)inputs_count);

        double timings[4] = {0};
        time_reducers_rotating(methods, method_count, inputs,
                               (size_t)inputs_count, repeats, timings);
        gs_samples[trial] = timings[0];
        serial_samples[trial] = timings[1];
        if (!skip_naive) naive_samples[trial] = timings[2];
        barrett_samples[trial] = timings[method_count - 1];

        for (int i = 0; i < inputs_count; ++i) poly_free(&inputs[i]);
        free(inputs);
        for (size_t method = 0; method < method_count; ++method)
            reduction_method_destroy(&methods[method]);
        poly_free(&modulus);
        free(taps);
        free(pool);
    }

    printf("m,word_bits,s,h,taps,Delta_min,feedback_stages,active_tap_counts,"
           "feedback_active_tap_sum,W_fb,"
           "GS_source_cost_model,GS_source_aligned_word_contributions,"
           "GS_source_cross_word_contributions,GS_source_word_shifts,"
           "GS_source_word_xors,GS_source_logical_word_reads,"
           "GS_source_logical_word_writes,GS_source_scratch_words,"
           "input_distribution,timing_scope,setup_scope,timing_order,"
           "GS_setup_ns,Serial_setup_ns,Naive_setup_ns,BarrettGF2X_setup_ns,"
           "GS_ns,Serial_ns,Naive_ns,BarrettGF2X_ns,"
           "Serial/GS,Naive/GS,BarrettGF2X/GS,sample,seed\n");
    for (int trial = 0; trial < supports; ++trial) {
        double gs = gs_samples[trial];
        double serial = serial_samples[trial];
        double naive = naive_samples[trial];
        double barrett = barrett_samples[trial];
        printf("%zu,%d,%zu,%zu,%s,", m, (int)(sizeof(word_t) * CHAR_BIT),
               s, s + 1, tap_values[trial]);
        if (has_delta[trial]) printf("%zu,", delta_values[trial]);
        else printf("NA,");
        const gs_source_cost *source_cost = &source_cost_values[trial];
        printf("%zu,%s,%zu,%zu,%s,%zu,%zu,%zu,%zu,%zu,%zu,%zu,"
               "%s,%s,%s,%s,%.1f,%.1f,%.1f,%.1f,"
               "%.1f,%.1f,%.1f,%.1f,%.3f,%.3f,%.3f,%d,%llu\n",
               feedback_stage_values[trial], active_tap_values[trial],
               active_tap_sum_values[trial], scheduled_work_values[trial],
               gs_source_cost_model,
               source_cost->aligned_word_contributions,
               source_cost->cross_word_contributions,
               source_cost->word_shifts, source_cost->word_xors,
               source_cost->logical_word_reads,
               source_cost->logical_word_writes,
               source_cost->scratch_words,
               input_distribution, timing_scope, setup_scope, timing_order,
               gs_setup_samples[trial], serial_setup_samples[trial],
               naive_setup_samples[trial], barrett_setup_samples[trial],
               gs, serial, naive, barrett,
               serial / gs, skip_naive ? 0.0 : naive / gs, barrett / gs,
               trial, (unsigned long long)seed);
        free(tap_values[trial]);
        free(active_tap_values[trial]);
    }

    free(gs_samples);
    free(serial_samples);
    free(naive_samples);
    free(barrett_samples);
    free(gs_setup_samples);
    free(serial_setup_samples);
    free(naive_setup_samples);
    free(barrett_setup_samples);
    free(delta_values);
    free(has_delta);
    free(tap_values);
    free(feedback_stage_values);
    free(active_tap_values);
    free(active_tap_sum_values);
    free(scheduled_work_values);
    free(source_cost_values);
    free(exact_taps);
    return 0;
}
