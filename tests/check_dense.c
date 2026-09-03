#include "dense.h"
#include "naive.h"

static uint64_t dense_rng = 0x589965cc75374cc3ULL;

static uint64_t next_dense_random(void) {
    dense_rng ^= dense_rng << 7;
    dense_rng ^= dense_rng >> 9;
    return dense_rng;
}

static int equal_polynomial(const poly_t *left, const poly_t *right) {
    size_t words = left->n > right->n ? left->n : right->n;
    for (size_t i = 0; i < words; ++i) {
        word_t a = i < left->n ? left->v[i] : 0;
        word_t b = i < right->n ? right->v[i] : 0;
        if (a != b) return 0;
    }
    return 1;
}

static void compare_one(const poly_t *input, const poly_t *modulus,
                        size_t m, dense_plan *plan) {
    poly_t expected = naive_reduce(input, modulus, m);
    poly_t actual = poly_new(poly_words_for_bits(m) + 2);
    memset(actual.v, 0xff, actual.n * sizeof(*actual.v));
    dense_reduce_into(input, plan, &actual);
    if (!equal_polynomial(&actual, &expected))
        die("dense reduction mismatch against long division");
    unsigned top_bits = (unsigned)(m % WORD_BITS);
    size_t output_words = poly_words_for_bits(m);
    if (top_bits != 0 && actual.v[output_words - 1] >> top_bits)
        die("dense reducer left nonzero top padding");
    for (size_t i = output_words; i < actual.n; ++i)
        if (actual.v[i] != 0) die("dense reducer left nonzero output tail");
    poly_free(&actual);
    poly_free(&expected);
}

static void check_modulus(size_t m, const size_t *taps, size_t tap_count) {
    poly_t modulus = poly_from_exponents(m + 1, taps, tap_count);
    poly_set_bit(&modulus, m);
    dense_plan *plan = dense_plan_create(&modulus, m);

    size_t matrix_bytes;
    if (!dense_matrix_bytes(m, &matrix_bytes))
        die("small dense matrix size unexpectedly overflowed");
    if (dense_plan_storage_bytes(plan) <= matrix_bytes)
        die("dense plan storage omitted its context or scratch");

    size_t input_words = poly_words_for_bits(2 * m);
    poly_t input = poly_new(input_words);
    for (size_t high_bit = 0; high_bit < m; ++high_bit) {
        memset(input.v, 0, input.n * sizeof(*input.v));
        poly_set_bit(&input, m + high_bit);
        if ((high_bit & 3u) == 0) poly_set_bit(&input, high_bit);
        compare_one(&input, &modulus, m, plan);
    }
    for (size_t trial = 0; trial < 64; ++trial) {
        for (size_t i = 0; i < input.n; ++i)
            input.v[i] = (word_t)next_dense_random();
        unsigned top_bits = (unsigned)((2 * m) % WORD_BITS);
        if (top_bits != 0)
            input.v[input.n - 1] &= ((word_t)1 << top_bits) - 1;
        compare_one(&input, &modulus, m, plan);
    }

    poly_free(&input);
    dense_plan_destroy(plan);
    poly_free(&modulus);
}

int main(void) {
    const size_t degrees[] = {
        1, 2, 7, WORD_BITS - 1, WORD_BITS, WORD_BITS + 1,
        2 * WORD_BITS - 1, 2 * WORD_BITS + 1, 257
    };
    for (size_t index = 0; index < sizeof(degrees) / sizeof(degrees[0]);
         ++index) {
        size_t m = degrees[index];
        check_modulus(m, NULL, 0);

        const size_t constant[] = {0};
        check_modulus(m, constant, 1);

        size_t endpoint[] = {m - 1};
        check_modulus(m, endpoint, 1);

        size_t *dense = malloc(m * sizeof(*dense));
        if (!dense) die("allocation failed");
        for (size_t tap = 0; tap < m; ++tap) dense[tap] = tap;
        check_modulus(m, dense, m);
        free(dense);
    }
    printf("dense linear-map reduction: ok\n");
    return EXIT_SUCCESS;
}
