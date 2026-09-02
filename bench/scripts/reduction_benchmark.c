#define _POSIX_C_SOURCE 200809L

#include "reduction.h"

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <time.h>

static uint64_t rng_state;
static const char *input_distribution = "uniform-full-range:v1";
static const char *timing_scope = "reduction-steady-state:v1";

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

/*
 * Steady-state reduction timing for one method.
 *
 * The method object owns all reducer-specific plan/scratch state. The timed
 * region contains only repeated calls to method->reduce_into(); setup,
 * allocation, correctness checks, and checksum consumption happen outside.
 */
static double time_reducer(const reduction_method *method,
                           const poly_t *inputs, size_t count, int repeats) {
    double *samples = calloc((size_t)repeats, sizeof(*samples));
    poly_t *outputs = calloc(count, sizeof(*outputs));
    if (!samples || !outputs) die("allocation failed");

    for (size_t i = 0; i < count; ++i)
        outputs[i] = poly_new(method->output_words);

    for (int repeat = 0; repeat < repeats; ++repeat) {
        struct timespec start = monotonic_time();
        for (size_t i = 0; i < count; ++i)
            method->reduce_into(&inputs[i], method->context, &outputs[i]);
        samples[repeat] = elapsed_ns(start, monotonic_time()) / (double)count;

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
    if (!gs_samples || !serial_samples || !naive_samples || !barrett_samples)
        die("allocation failed");
    size_t *delta_values = calloc((size_t)supports, sizeof(*delta_values));
    int *has_delta = calloc((size_t)supports, sizeof(*has_delta));
    char **tap_values = calloc((size_t)supports, sizeof(*tap_values));
    if (!delta_values || !has_delta || !tap_values) die("allocation failed");

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
        reduction_method methods[4];
        size_t method_count = 0;
        methods[method_count++] = reduction_make_gs(taps, s, m);
        methods[method_count++] = reduction_make_serial(taps, s, m);
        if (!skip_naive)
            methods[method_count++] =
                reduction_make_naive(&modulus, m, input_words);
        methods[method_count++] = reduction_make_barrett(&modulus, m);

        poly_t *inputs = calloc((size_t)inputs_count, sizeof(*inputs));
        if (!inputs) die("allocation failed");
        for (int i = 0; i < inputs_count; ++i) {
            inputs[i] = poly_new(input_words);
            uniform_full_range_input(&inputs[i], m);
        }

        check_reducers(methods, method_count, inputs, (size_t)inputs_count);

        gs_samples[trial] = time_reducer(
            &methods[0], inputs, (size_t)inputs_count, repeats);
        serial_samples[trial] = time_reducer(
            &methods[1], inputs, (size_t)inputs_count, repeats);
        if (!skip_naive)
            naive_samples[trial] = time_reducer(
                &methods[2], inputs, (size_t)inputs_count, repeats);
        barrett_samples[trial] = time_reducer(
            &methods[method_count - 1], inputs, (size_t)inputs_count, repeats);

        for (int i = 0; i < inputs_count; ++i) poly_free(&inputs[i]);
        free(inputs);
        for (size_t method = 0; method < method_count; ++method)
            reduction_method_destroy(&methods[method]);
        poly_free(&modulus);
        free(taps);
        free(pool);
    }

    printf("m,s,h,taps,Delta_min,input_distribution,timing_scope,"
           "GS_ns,Serial_ns,Naive_ns,BarrettGF2X_ns,"
           "Serial/GS,Naive/GS,BarrettGF2X/GS,sample,seed\n");
    for (int trial = 0; trial < supports; ++trial) {
        double gs = gs_samples[trial];
        double serial = serial_samples[trial];
        double naive = naive_samples[trial];
        double barrett = barrett_samples[trial];
        printf("%zu,%zu,%zu,%s,", m, s, s + 1, tap_values[trial]);
        if (has_delta[trial]) printf("%zu,", delta_values[trial]);
        else printf("NA,");
        printf("%s,%s,%.1f,%.1f,%.1f,%.1f,%.3f,%.3f,%.3f,%d,%llu\n",
               input_distribution, timing_scope,
               gs, serial, naive, barrett,
               serial / gs, skip_naive ? 0.0 : naive / gs, barrett / gs,
               trial, (unsigned long long)seed);
        free(tap_values[trial]);
    }

    free(gs_samples);
    free(serial_samples);
    free(naive_samples);
    free(barrett_samples);
    free(delta_values);
    free(has_delta);
    free(tap_values);
    free(exact_taps);
    return 0;
}
