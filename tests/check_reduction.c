#include "reduction.h"

static const uint64_t check_seed = 0xd1b54a32d192ed03ULL;
static uint64_t check_rng = 0xd1b54a32d192ed03ULL;

enum {
    FIXED_DEGREE_TRIALS = 100,
    RANDOM_STRESS_TRIALS = 10000,
    RANDOM_MAX_DEGREE = 512,
};

typedef struct {
    const char *id;
    size_t m;
    const size_t *taps;
    size_t tap_count;
    const size_t *input_bits;
    size_t input_bit_count;
} reduction_regression_case;

#include "reduction_regressions.h"

static uint64_t next_random(void) {
    check_rng ^= check_rng << 7;
    check_rng ^= check_rng >> 9;
    return check_rng;
}

static int compare_size_t(const void *left, const void *right) {
    size_t a = *(const size_t *)left;
    size_t b = *(const size_t *)right;
    return (a > b) - (a < b);
}

static void shuffle(size_t *values, size_t count) {
    for (size_t i = count; i > 1; --i) {
        size_t j = (size_t)(next_random() % i);
        size_t temporary = values[i - 1];
        values[i - 1] = values[j];
        values[j] = temporary;
    }
}

static int poly_equal(const poly_t *a, const poly_t *b) {
    size_t count = a->n > b->n ? a->n : b->n;
    for (size_t i = 0; i < count; ++i) {
        word_t x = i < a->n ? a->v[i] : 0;
        word_t y = i < b->n ? b->v[i] : 0;
        if (x != y) return 0;
    }
    return 1;
}

static void check_canonical_output(const poly_t *output, size_t m,
                                   const char *method) {
    size_t words = poly_words_for_bits(m);
    if (output->n < words) die("reducer returned an undersized output");
    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (top_bits != 0
            && (output->v[words - 1] >> top_bits) != 0) {
        fprintf(stderr, "%s left nonzero top-word padding for m=%zu\n",
                method, m);
        exit(EXIT_FAILURE);
    }
    for (size_t i = words; i < output->n; ++i) {
        if (output->v[i] != 0) {
            fprintf(stderr, "%s left nonzero output tail for m=%zu\n",
                    method, m);
            exit(EXIT_FAILURE);
        }
    }
}

static void choose_taps(size_t *taps, size_t count, size_t m,
                        int force_unit_gap) {
    taps[0] = 0;
    size_t first_random = 1;
    if (force_unit_gap && count > 1) {
        taps[1] = m - 1;
        first_random = 2;
    }
    for (size_t i = first_random; i < count; ++i) {
        size_t candidate;
        int duplicate;
        do {
            candidate = 1 + (size_t)(next_random() % (m - 1));
            duplicate = 0;
            for (size_t j = 1; j < i; ++j)
                duplicate |= taps[j] == candidate;
        } while (duplicate);
        taps[i] = candidate;
    }
    qsort(taps, count, sizeof(*taps), compare_size_t);
}

/*
 * Cycle through deliberately different support geometries.  The resulting
 * list is already in the canonical ascending order required by the native
 * API.  Profiles include empty, dense, sparse, constant-free, unit-gap,
 * mixed word-aligned/unaligned distances, and unrestricted supports; no
 * irreducibility assumption is made.
 */
static size_t *choose_stress_taps(size_t m, size_t trial, size_t *count) {
    size_t profile = trial % 8;
    size_t start = 0;
    size_t available = m;

    if (profile == 0) {
        *count = 0;
    } else if (profile == 1) {
        *count = m;
    } else if (profile == 2) {
        if (m > WORD_BITS + 1) {
            *count = 3;
            size_t *alignment = malloc(*count * sizeof(*alignment));
            if (!alignment) die("allocation failed");
            alignment[0] = m - (WORD_BITS + 1);
            alignment[1] = m - WORD_BITS;
            alignment[2] = m - 1;
            return alignment;
        }
        *count = 1;
    } else if (profile == 3) {
        /* Constant-free, including the empty boundary when m == 1. */
        start = 1;
        available = m - 1;
        *count = available ? 1 + (size_t)(next_random() % available) : 0;
    } else if (profile == 4) {
        *count = m == 1 ? 1 : 2;
        size_t *endpoints = malloc(*count * sizeof(*endpoints));
        if (!endpoints) die("allocation failed");
        endpoints[0] = 0;
        if (*count == 2) endpoints[1] = m - 1;
        return endpoints;
    } else if (profile == 5) {
        size_t limit = m < 8 ? m : 8;
        *count = (size_t)(next_random() % (limit + 1));
    } else if (profile == 6) {
        size_t limit = m < 8 ? m : 8;
        *count = m - (size_t)(next_random() % (limit + 1));
    } else {
        *count = (size_t)(next_random() % (m + 1));
    }

    if (*count == 0) return NULL;
    size_t *pool = malloc(available * sizeof(*pool));
    size_t *taps = malloc(*count * sizeof(*taps));
    if (!pool || !taps) die("allocation failed");
    for (size_t i = 0; i < available; ++i) pool[i] = start + i;
    shuffle(pool, available);
    memcpy(taps, pool, *count * sizeof(*taps));
    qsort(taps, *count, sizeof(*taps), compare_size_t);
    free(pool);
    return taps;
}

static void random_input(poly_t *input, size_t m) {
    memset(input->v, 0, input->n * sizeof(word_t));
    size_t bits = 2 * m;
    for (size_t i = 0; i < bits; ++i)
        if (next_random() & 1) poly_set_bit(input, i);
}

static void check_methods(const reduction_method *methods,
                          size_t method_count, const poly_t *input,
                          size_t m, size_t trial, const size_t *taps,
                          size_t tap_count, const char *suite) {
    poly_t *outputs = calloc(method_count, sizeof(*outputs));
    if (!outputs) die("allocation failed");

    for (size_t i = 0; i < method_count; ++i) {
        outputs[i] = poly_new(methods[i].output_words + 2);
        memset(outputs[i].v, 0xff, outputs[i].n * sizeof(*outputs[i].v));
        methods[i].reduce_into(input, methods[i].context, &outputs[i]);
        check_canonical_output(&outputs[i], m, methods[i].name);
    }

    for (size_t i = 1; i < method_count; ++i) {
        if (!poly_equal(&outputs[0], &outputs[i])) {
            fprintf(stderr,
                    "reduction mismatch: suite=%s seed=0x%016llx m=%zu "
                    "trial=%zu taps=",
                    suite, (unsigned long long)check_seed, m, trial);
            if (tap_count == 0) {
                fputc('-', stderr);
            } else {
                for (size_t tap = 0; tap < tap_count; ++tap)
                    fprintf(stderr, "%s%zu", tap ? "," : "", taps[tap]);
            }
            fprintf(stderr, " left=%s right=%s input_words=",
                    methods[0].name, methods[i].name);
            for (size_t word = 0; word < input->n; ++word)
                fprintf(stderr, "%s%0*lx", word ? ":" : "",
                        (int)(2 * sizeof(word_t)), input->v[word]);
            fputc('\n', stderr);
            exit(EXIT_FAILURE);
        }
    }

    for (size_t i = 0; i < method_count; ++i)
        poly_free(&outputs[i]);
    free(outputs);
}

static void check_exact_input(size_t m, size_t trial, const size_t *taps,
                              size_t tap_count, poly_t *input,
                              const char *suite) {
    poly_t modulus = poly_from_exponents(m + 1, taps, tap_count);
    poly_set_bit(&modulus, m);

    reduction_method methods[] = {
        reduction_make_gs(taps, tap_count, m),
        reduction_make_serial(taps, tap_count, m),
        reduction_make_naive(&modulus, m, input->n),
        reduction_make_barrett(&modulus, m),
    };
    size_t method_count = sizeof(methods) / sizeof(methods[0]);
    check_methods(methods, method_count, input, m, trial, taps, tap_count,
                  suite);

    for (size_t i = 0; i < method_count; ++i)
        reduction_method_destroy(&methods[i]);
    poly_free(&modulus);
}

static void check_random_case(size_t m, size_t trial, size_t *taps,
                              size_t tap_count, const char *suite) {
    poly_t input = poly_new(poly_words_for_bits(2 * m));
    random_input(&input, m);
    check_exact_input(m, trial, taps, tap_count, &input, suite);
    poly_free(&input);
}

static void check_regression_cases(void) {
    size_t count = sizeof(reduction_regressions)
                 / sizeof(reduction_regressions[0]);
    for (size_t i = 0; i < count; ++i) {
        const reduction_regression_case *test = &reduction_regressions[i];
        poly_t input = poly_new(poly_words_for_bits(2 * test->m));
        for (size_t bit = 0; bit < test->input_bit_count; ++bit) {
            if (test->input_bits[bit] >= 2 * test->m)
                die("regression input bit is outside the reduction domain");
            poly_set_bit(&input, test->input_bits[bit]);
        }
        check_exact_input(test->m, i, test->taps, test->tap_count,
                          &input, test->id);
        poly_free(&input);
    }
}

int main(void) {
    const size_t degrees[] = {
        1, 2, 8, 31, WORD_BITS - 1, WORD_BITS, WORD_BITS + 1,
        2 * WORD_BITS - 1, 2 * WORD_BITS, 2 * WORD_BITS + 1,
        3 * WORD_BITS - 1, 3 * WORD_BITS, 3 * WORD_BITS + 1, 257
    };

    check_regression_cases();

    for (size_t mi = 0; mi < sizeof(degrees) / sizeof(degrees[0]); ++mi) {
        size_t m = degrees[mi];
        for (size_t trial = 0; trial < FIXED_DEGREE_TRIALS; ++trial) {
            size_t tap_count = 2 + (size_t)(next_random() % 7);
            if (tap_count > m) tap_count = m;
            size_t *taps = malloc(tap_count * sizeof(*taps));
            if (!taps) die("allocation failed");
            choose_taps(taps, tap_count, m, (trial & 1) == 0);

            check_random_case(m, trial, taps, tap_count, "fixed-degrees");
            free(taps);
        }
    }

    for (size_t trial = 0; trial < RANDOM_STRESS_TRIALS; ++trial) {
        size_t m = 1 + (size_t)(next_random() % RANDOM_MAX_DEGREE);
        size_t tap_count;
        size_t *taps = choose_stress_taps(m, trial, &tap_count);
        check_random_case(m, trial, taps, tap_count, "random-polynomials");
        free(taps);
    }

    printf("reduction correctness: ok (%zu regression, %zu fixed-degree and "
           "%d random full-input cases, seed=0x%016llx)\n",
           sizeof(reduction_regressions) / sizeof(reduction_regressions[0]),
           sizeof(degrees) / sizeof(degrees[0]) * FIXED_DEGREE_TRIALS,
           RANDOM_STRESS_TRIALS, (unsigned long long)check_seed);
    return EXIT_SUCCESS;
}
