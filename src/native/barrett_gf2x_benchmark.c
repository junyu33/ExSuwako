/* Native reduction-only benchmark using the upstream gf2x multiplication API. */

#define _POSIX_C_SOURCE 200809L

#include <gf2x.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef unsigned long word_t;
enum { WORD_BITS = sizeof(word_t) * 8 };

typedef struct {
    word_t *v;
    size_t n;
} poly_t;

static void die(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(EXIT_FAILURE);
}

static poly_t poly_new(size_t n) {
    poly_t p = {calloc(n ? n : 1, sizeof(word_t)), n};
    if (!p.v) die("allocation failed");
    return p;
}

static void poly_free(poly_t *p) {
    free(p->v);
    p->v = NULL;
    p->n = 0;
}

static size_t poly_words_for_bits(size_t bits) {
    return (bits + WORD_BITS - 1) / WORD_BITS;
}

static long poly_degree(const poly_t *p) {
    size_t i = p->n;
    while (i && p->v[i - 1] == 0) --i;
    if (!i) return -1;
    word_t x = p->v[i - 1];
    int top = WORD_BITS - 1;
    while (((x >> top) & 1u) == 0) --top;
    return (long)((i - 1) * WORD_BITS + (size_t)top);
}

static void poly_set_bit(poly_t *p, size_t bit) {
    if (bit / WORD_BITS >= p->n) die("polynomial bit capacity exceeded");
    p->v[bit / WORD_BITS] |= (word_t)1 << (bit % WORD_BITS);
}

static void poly_xor_shift(poly_t *dst, const poly_t *src, size_t shift) {
    size_t whole = shift / WORD_BITS;
    unsigned bits = (unsigned)(shift % WORD_BITS);
    for (size_t i = 0; i < src->n && i + whole < dst->n; ++i) {
        dst->v[i + whole] ^= src->v[i] << bits;
        if (bits && i + whole + 1 < dst->n)
            dst->v[i + whole + 1] ^= src->v[i] >> (WORD_BITS - bits);
    }
}

static poly_t poly_shift_right(const poly_t *src, size_t shift) {
    poly_t dst = poly_new(src->n);
    size_t whole = shift / WORD_BITS;
    unsigned bits = (unsigned)(shift % WORD_BITS);
    for (size_t i = whole; i < src->n; ++i) {
        size_t j = i - whole;
        dst.v[j] ^= src->v[i] >> bits;
        if (bits && i + 1 < src->n)
            dst.v[j] ^= src->v[i + 1] << (WORD_BITS - bits);
    }
    return dst;
}

static poly_t poly_from_exponents(size_t bits, const size_t *exponents, size_t count) {
    poly_t p = poly_new(poly_words_for_bits(bits));
    for (size_t i = 0; i < count; ++i) poly_set_bit(&p, exponents[i]);
    return p;
}

static int poly_mul_gf2x(poly_t *out, const poly_t *a, const poly_t *b) {
    size_t an = a->n, bn = b->n;
    while (an && a->v[an - 1] == 0) --an;
    while (bn && b->v[bn - 1] == 0) --bn;
    memset(out->v, 0, out->n * sizeof(word_t));
    if (!an || !bn) return 0;
    if (out->n < an + bn) return -2;
    return gf2x_mul(out->v, a->v, (unsigned long)an,
                    b->v, (unsigned long)bn);
}

static void poly_divmod(const poly_t *numerator, const poly_t *denominator,
                        poly_t *quotient, poly_t *remainder) {
    memcpy(remainder->v, numerator->v, remainder->n * sizeof(word_t));
    memset(quotient->v, 0, quotient->n * sizeof(word_t));
    long den_degree = poly_degree(denominator);
    if (den_degree < 0) die("division by zero polynomial");
    for (;;) {
        long rem_degree = poly_degree(remainder);
        if (rem_degree < den_degree) break;
        size_t shift = (size_t)(rem_degree - den_degree);
        poly_set_bit(quotient, shift);
        poly_xor_shift(remainder, denominator, shift);
    }
}

static poly_t barrett_setup(const poly_t *modulus, size_t m) {
    poly_t numerator = poly_new(poly_words_for_bits(2 * m + 1));
    poly_set_bit(&numerator, 2 * m);
    poly_t quotient = poly_new(numerator.n);
    poly_t remainder = poly_new(numerator.n);
    poly_divmod(&numerator, modulus, &quotient, &remainder);
    poly_free(&numerator);
    poly_free(&remainder);
    return quotient;
}

static poly_t barrett_reduce(const poly_t *c, const poly_t *modulus,
                             const poly_t *mu, size_t m) {
    poly_t q1 = poly_shift_right(c, m - 1);
    poly_t q2 = poly_new(q1.n + mu->n);
    poly_t q3;
    if (poly_mul_gf2x(&q2, &q1, mu) != 0) die("gf2x q1*mu failed");
    q3 = poly_shift_right(&q2, m + 1);

    poly_t product = poly_new(q3.n + modulus->n);
    if (poly_mul_gf2x(&product, &q3, modulus) != 0)
        die("gf2x q3*modulus failed");
    poly_t r = poly_new(c->n > product.n ? c->n : product.n);
    for (size_t i = 0; i < r.n; ++i) {
        word_t x = i < c->n ? c->v[i] : 0;
        word_t y = i < product.n ? product.v[i] : 0;
        r.v[i] = x ^ y;
    }
    size_t keep = poly_words_for_bits(m + 1);
    for (size_t i = keep; i < r.n; ++i) r.v[i] = 0;
    unsigned keep_bits = (unsigned)(m % WORD_BITS) + 1;
    r.v[keep - 1] &= keep_bits == WORD_BITS
        ? (word_t)~(word_t)0
        : ((word_t)1 << keep_bits) - 1;
    while (poly_degree(&r) >= (long)m) {
        size_t shift = (size_t)(poly_degree(&r) - (long)m);
        poly_xor_shift(&r, modulus, shift);
    }
    poly_free(&q1); poly_free(&q2); poly_free(&q3);
    poly_free(&product);
    return r;
}

static poly_t naive_reduce(const poly_t *input, const poly_t *modulus, size_t m) {
    poly_t r = poly_new(input->n);
    memcpy(r.v, input->v, input->n * sizeof(word_t));
    while (poly_degree(&r) >= (long)m) {
        size_t shift = (size_t)(poly_degree(&r) - (long)m);
        poly_xor_shift(&r, modulus, shift);
    }
    return r;
}

static poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m) {
    poly_t low = poly_new(poly_words_for_bits(m));
    poly_t state = poly_shift_right(input, m);
    poly_t next = poly_new(state.n);
    size_t dmin = m + 1;
    for (size_t i = 0; i < s; ++i) if (taps[i] > 0 && m - taps[i] < dmin) dmin = m - taps[i];
    size_t rounds = dmin > m ? 0 : 0;
    while (dmin <= m && (((size_t)1 << rounds) * dmin < m)) ++rounds;
    for (size_t k = 0; k < rounds; ++k) {
        memcpy(next.v, state.v, state.n * sizeof(word_t));
        for (size_t i = 0; i < s; ++i) {
            size_t factor = (size_t)1 << k;
            size_t delta = m - taps[i];
            if (!taps[i] || factor * delta >= m) continue;
            poly_xor_shift(&next, &state, factor * delta);
        }
        poly_t swap = state;
        state = next;
        next = swap;
    }
    for (size_t i = 0; i < low.n && i < input->n; ++i) low.v[i] = input->v[i];
    for (size_t i = 0; i < s; ++i) poly_xor_shift(&low, &state, taps[i]);
    poly_t result = low;
    poly_free(&state);
    poly_free(&next);
    return result;
}

static uint64_t rng_state = 0;
static uint64_t rng_next(void) {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

static int random_bit(void) { return (int)(rng_next() & 1); }

static struct timespec monotonic_time(void) {
    struct timespec x;
    if (clock_gettime(CLOCK_MONOTONIC, &x) != 0) die("clock_gettime failed");
    return x;
}

static double elapsed_ns(struct timespec a, struct timespec b) {
    time_t seconds = b.tv_sec - a.tv_sec;
    long nanoseconds = b.tv_nsec - a.tv_nsec;
    return (double)seconds * 1e9 + (double)nanoseconds;
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

static void random_input(poly_t *p, size_t m) {
    memset(p->v, 0, p->n * sizeof(word_t));
    poly_set_bit(p, m + (size_t)(rng_next() % m));
    for (size_t i = 0; i < m; ++i) if (random_bit()) poly_set_bit(p, i);
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

static double time_method(int method, const poly_t *inputs, size_t count,
                          const size_t *taps, size_t s, size_t m,
                          const poly_t *modulus, const poly_t *mu,
                          int repeats) {
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
                    poly_t b = gs_reduce(&inputs[i], taps, s, m);
                    poly_t c = barrett_reduce(&inputs[i], &modulus, &mu, m);
                    poly_t a = {NULL, 0};
                    int correct = poly_equal(&b, &c);
                    if (!skip_naive) {
                        a = naive_reduce(&inputs[i], &modulus, m);
                        correct = correct && poly_equal(&a, &b);
                    }
                    if (!correct) {
                        fprintf(stderr, "correctness mismatch m=%zu s=%zu trial=%d input=%d gs=%d barrett=%d\n",
                                m, s, trial, i, poly_equal(&a, &b), poly_equal(&b, &c));
                        fprintf(stderr, "degrees input=%ld modulus=%ld a=%ld b=%ld c=%ld\n",
                                poly_degree(&inputs[i]), poly_degree(&modulus),
                                skip_naive ? -1 : poly_degree(&a), poly_degree(&b), poly_degree(&c));
                        die("correctness mismatch");
                    }
                    if (!skip_naive) poly_free(&a);
                    poly_free(&b); poly_free(&c);
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
            printf("%zu,%zu,%zu,%.1f,%.1f,%.1f,%.3f,%.3f\n", m, s, s + 1, gs,
                   naive, barrett, skip_naive ? 0.0 : naive / gs, barrett / gs);
        }
    }
    return 0;
}
