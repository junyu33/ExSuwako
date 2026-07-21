#define _POSIX_C_SOURCE 200809L

#include "barrett.h"
#include "GS.h"
#include "naive.h"
#include <time.h>

static uint64_t rng_state;
static uint64_t rng_next(void) {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

static void random_input(poly_t *p, size_t m) {
    memset(p->v, 0, p->n * sizeof(word_t));
    poly_set_bit(p, m + (size_t)(rng_next() % m));
    for (size_t i = 0; i < m; ++i)
        if (rng_next() & 1) poly_set_bit(p, i);
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
    struct timespec x;
    if (clock_gettime(CLOCK_MONOTONIC, &x) != 0) die("clock_gettime failed");
    return x;
}

static double elapsed_ns(struct timespec a, struct timespec b) {
    return (double)(b.tv_sec - a.tv_sec) * 1e9 + (double)(b.tv_nsec - a.tv_nsec);
}

static int compare_double(const void *left, const void *right) {
    double a = *(const double *)left, b = *(const double *)right;
    return (a > b) - (a < b);
}

static double median(double *values, size_t count) {
    qsort(values, count, sizeof(double), compare_double);
    if (count & 1) return values[count / 2];
    return (values[count / 2 - 1] + values[count / 2]) / 2.0;
}

static double time_method(int method, const poly_t *inputs, size_t count,
                          const size_t *taps, size_t s, size_t m,
                          const poly_t *modulus, const poly_t *mu, int repeats) {
    double *samples = calloc((size_t)repeats, sizeof(double));
    if (!samples) die("allocation failed");
    for (int rep = 0; rep < repeats; ++rep) {
        struct timespec start = monotonic_time();
        for (size_t i = 0; i < count; ++i) {
            poly_t out;
            if (method == 0) out = gs_reduce(&inputs[i], taps, s, m);
            else if (method == 1) out = naive_reduce(&inputs[i], modulus, m);
            else out = barrett_reduce(&inputs[i], modulus, mu, m);
            poly_free(&out);
        }
        samples[rep] = elapsed_ns(start, monotonic_time()) / (double)count;
    }
    double result = median(samples, (size_t)repeats);
    free(samples);
    return result;
}

static void shuffle(size_t *a, size_t n) {
    for (size_t i = n; i > 1; --i) {
        size_t j = (size_t)(rng_next() % i), t = a[i - 1];
        a[i - 1] = a[j]; a[j] = t;
    }
}

int main(int argc, char **argv) {
    size_t m_values[] = {64, 128, 256, 512, 1024};
    size_t s_values[] = {1, 2, 4, 8, 16, 32, 64, 128};
    int supports = argc > 1 ? atoi(argv[1]) : 12;
    int inputs_count = argc > 2 ? atoi(argv[2]) : 64;
    int repeats = argc > 3 ? atoi(argv[3]) : 5;
    int custom_m = argc > 4;
    int skip_naive = argc > 5 && strcmp(argv[5], "no-naive") == 0;
    if (custom_m) m_values[0] = (size_t)strtoull(argv[4], NULL, 10);
    rng_state = 0x9e3779b97f4a7c15ULL;
    printf("m,s,h,GS_ns,naive_ns,BarrettGF2X_ns,naive/GS,BarrettGF2X/GS\n");

    size_t m_count = custom_m ? 1 : sizeof(m_values) / sizeof(m_values[0]);
    for (size_t mi = 0; mi < m_count; ++mi) {
        size_t m = m_values[mi];
        for (size_t si = 0; si < sizeof(s_values) / sizeof(s_values[0]); ++si) {
            size_t s = s_values[si];
            if (s >= m) continue;
            double *gs_samples = calloc((size_t)supports, sizeof(double));
            double *naive_samples = calloc((size_t)supports, sizeof(double));
            double *barrett_samples = calloc((size_t)supports, sizeof(double));
            if (!gs_samples || !naive_samples || !barrett_samples) die("allocation failed");
            for (int trial = 0; trial < supports; ++trial) {
                size_t *pool = malloc(m * sizeof(size_t));
                size_t *taps = malloc(s * sizeof(size_t));
                if (!pool || !taps) die("allocation failed");
                for (size_t i = 0; i < m; ++i) pool[i] = i;
                shuffle(pool, m);
                memcpy(taps, pool, s * sizeof(size_t));
                poly_t modulus = poly_from_exponents(m + 1, taps, s);
                poly_set_bit(&modulus, m);
                poly_t mu = barrett_setup(&modulus, m);
                poly_t *inputs = calloc((size_t)inputs_count, sizeof(poly_t));
                if (!inputs) die("allocation failed");
                for (int i = 0; i < inputs_count; ++i) {
                    inputs[i] = poly_new(poly_words_for_bits(2 * m));
                    random_input(&inputs[i], m);
                    poly_t gs = gs_reduce(&inputs[i], taps, s, m);
                    poly_t barrett = barrett_reduce(&inputs[i], &modulus, &mu, m);
                    int correct = poly_equal(&gs, &barrett);
                    poly_t naive = {NULL, 0};
                    if (!skip_naive) {
                        naive = naive_reduce(&inputs[i], &modulus, m);
                        correct = correct && poly_equal(&naive, &gs);
                    }
                    if (!correct) die("correctness mismatch");
                    if (!skip_naive) poly_free(&naive);
                    poly_free(&gs); poly_free(&barrett);
                }
                gs_samples[trial] = time_method(0, inputs, (size_t)inputs_count, taps, s, m, &modulus, &mu, repeats);
                naive_samples[trial] = skip_naive ? 0.0 : time_method(1, inputs, (size_t)inputs_count, taps, s, m, &modulus, &mu, repeats);
                barrett_samples[trial] = time_method(2, inputs, (size_t)inputs_count, taps, s, m, &modulus, &mu, repeats);
                for (int i = 0; i < inputs_count; ++i) poly_free(&inputs[i]);
                free(inputs); poly_free(&modulus); poly_free(&mu); free(pool); free(taps);
            }
            double gs = median(gs_samples, (size_t)supports);
            double naive = skip_naive ? 0.0 : median(naive_samples, (size_t)supports);
            double barrett = median(barrett_samples, (size_t)supports);
            free(gs_samples); free(naive_samples); free(barrett_samples);
            printf("%zu,%zu,%zu,%.1f,%.1f,%.1f,%.3f,%.3f\n", m, s, s + 1,
                   gs, naive, barrett, skip_naive ? 0.0 : naive / gs, barrett / gs);
        }
    }
    return 0;
}
