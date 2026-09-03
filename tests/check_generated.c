#include "generated.h"
#include "naive.h"

#include <errno.h>

static uint64_t generated_rng = 0x8cb92baa3f3d8dd7ULL;

static uint64_t next_random(void) {
    generated_rng ^= generated_rng << 7;
    generated_rng ^= generated_rng >> 9;
    return generated_rng;
}

static size_t parse_size(const char *text, int allow_zero) {
    errno = 0;
    char *end = NULL;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno || !end || *end || (!allow_zero && value == 0)
            || value > SIZE_MAX)
        die("invalid generated-check degree");
    return (size_t)value;
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

static void compare_one(const poly_t *input, const poly_t *modulus,
                        generated_plan *plan, size_t m) {
    poly_t expected = naive_reduce(input, modulus, m);
    poly_t actual = poly_new(poly_words_for_bits(m) + 2);
    memset(actual.v, 0xff, actual.n * sizeof(*actual.v));
    generated_reduce_into(input, plan, &actual);
    if (!poly_equal(&actual, &expected))
        die("generated reduction mismatch against long division");
    poly_free(&actual);
    poly_free(&expected);
}

int main(int argc, char **argv) {
    if (argc < 3)
        die("usage: check_generated PLUGIN M [TAP ...]");
    const char *plugin_path = argv[1];
    size_t m = parse_size(argv[2], 0);
    size_t tap_count = (size_t)(argc - 3);
    size_t *taps = tap_count ? malloc(tap_count * sizeof(*taps)) : NULL;
    if (tap_count && !taps) die("allocation failed");
    for (size_t i = 0; i < tap_count; ++i) {
        taps[i] = parse_size(argv[i + 3], 1);
        if (taps[i] >= m || (i && taps[i - 1] >= taps[i]))
            die("generated-check taps must be canonical and below m");
    }

    poly_t modulus = poly_from_exponents(m + 1, taps, tap_count);
    poly_set_bit(&modulus, m);
    generated_plan *plan = generated_plan_load(
        plugin_path, m, taps, tap_count);
    if (generated_plan_storage_bytes(plan) == 0)
        die("generated plan storage must be positive");

    poly_t input = poly_new(poly_words_for_bits(2 * m));
    for (size_t bit = 0; bit < 2 * m; ++bit) {
        memset(input.v, 0, input.n * sizeof(*input.v));
        poly_set_bit(&input, bit);
        compare_one(&input, &modulus, plan, m);
    }
    for (size_t trial = 0; trial < 128; ++trial) {
        for (size_t i = 0; i < input.n; ++i)
            input.v[i] = (word_t)next_random();
        unsigned top_bits = (unsigned)((2 * m) % WORD_BITS);
        if (top_bits != 0)
            input.v[input.n - 1] &= ((word_t)1 << top_bits) - 1;
        compare_one(&input, &modulus, plan, m);
    }

    poly_free(&input);
    generated_plan_destroy(plan);
    poly_free(&modulus);
    free(taps);
    return EXIT_SUCCESS;
}
