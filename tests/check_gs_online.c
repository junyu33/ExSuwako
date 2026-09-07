#include "GS.h"
#include "naive.h"

static uint64_t rng_state = UINT64_C(0x4f4e4c494e454646);

static uint64_t rng_next(void) {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

static int compare_size_t(const void *left, const void *right) {
    size_t a = *(const size_t *)left;
    size_t b = *(const size_t *)right;
    return (a > b) - (a < b);
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

static void check_case(size_t m, const size_t *taps, size_t tap_count,
                       size_t trials) {
    poly_t modulus = poly_from_exponents(m + 1, taps, tap_count);
    poly_set_bit(&modulus, m);
    gs_plan *planned = gs_plan_create(taps, tap_count, m);
    gs_online_context *online =
        gs_online_context_create(taps, tap_count, m);
    size_t input_words = poly_words_for_bits(2 * m);
    size_t output_words = poly_words_for_bits(m);
    poly_t input = poly_new(input_words);
    poly_t expected = poly_new(input_words);
    poly_t planned_output = poly_new(output_words + 2);
    poly_t online_output = poly_new(output_words + 2);

    for (size_t trial = 0; trial < trials; ++trial) {
        for (size_t i = 0; i < input.n; ++i)
            input.v[i] = (word_t)rng_next();
        unsigned input_top_bits = (unsigned)((2 * m) % WORD_BITS);
        if (input_top_bits)
            input.v[input.n - 1] &= ((word_t)1 << input_top_bits) - 1;

        memset(expected.v, 0xa5, expected.n * sizeof(*expected.v));
        memset(planned_output.v, 0xa5,
               planned_output.n * sizeof(*planned_output.v));
        memset(online_output.v, 0xa5,
               online_output.n * sizeof(*online_output.v));
        naive_reduce_into(&input, &modulus, m, &expected);
        gs_reduce_into(&input, planned, &planned_output);
        gs_reduce_online_into(&input, online, &online_output);

        if (!poly_equal(&expected, &planned_output)
                || !poly_equal(&expected, &online_output)) {
            fprintf(stderr,
                    "FFR-online mismatch: m=%zu taps=%zu trial=%zu\n",
                    m, tap_count, trial);
            exit(EXIT_FAILURE);
        }
    }

    poly_free(&online_output);
    poly_free(&planned_output);
    poly_free(&expected);
    poly_free(&input);
    gs_online_context_destroy(online);
    gs_plan_destroy(planned);
    poly_free(&modulus);
}

int main(void) {
    static const size_t constant_only[] = {0};
    static const size_t unit_gap[] = {1, 63, 64, 126};
    static const size_t aligned[] = {64, 128, 192};
    static const size_t mixed[] = {0, 1, 63, 64, 65, 190};
    check_case(1, NULL, 0, 32);
    check_case(1, constant_only, 1, 32);
    check_case(127, unit_gap, 4, 256);
    check_case(257, aligned, 3, 256);
    check_case(257, mixed, 6, 256);

    for (size_t trial = 0; trial < 4000; ++trial) {
        size_t m = 1 + (size_t)(rng_next() % 512);
        size_t tap_count = (size_t)(rng_next() % ((m < 65 ? m : 65) + 1));
        size_t *pool = malloc(m * sizeof(*pool));
        size_t *taps = tap_count
            ? malloc(tap_count * sizeof(*taps)) : NULL;
        if (!pool || (tap_count && !taps)) die("allocation failed");
        for (size_t i = 0; i < m; ++i) pool[i] = i;
        for (size_t i = m; i > 1; --i) {
            size_t j = (size_t)(rng_next() % i);
            size_t temporary = pool[i - 1];
            pool[i - 1] = pool[j];
            pool[j] = temporary;
        }
        if (tap_count) {
            memcpy(taps, pool, tap_count * sizeof(*taps));
            qsort(taps, tap_count, sizeof(*taps), compare_size_t);
        }
        check_case(m, taps, tap_count, 1);
        free(taps);
        free(pool);
    }

    puts("FFR-online correctness: PASS");
    return 0;
}
