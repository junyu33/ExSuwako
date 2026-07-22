#include "reduction.h"

static uint64_t check_rng = 0xd1b54a32d192ed03ULL;

static uint64_t next_random(void) {
    check_rng ^= check_rng << 7;
    check_rng ^= check_rng >> 9;
    return check_rng;
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
}

static void random_input(poly_t *input, size_t m) {
    memset(input->v, 0, input->n * sizeof(word_t));
    size_t bits = 2 * m;
    for (size_t i = 0; i < bits; ++i)
        if (next_random() & 1) poly_set_bit(input, i);
}

static void check_methods(const reduction_method *methods,
                          size_t method_count, const poly_t *input,
                          size_t m, size_t trial, size_t tap_count) {
    poly_t *outputs = calloc(method_count, sizeof(*outputs));
    if (!outputs) die("allocation failed");

    for (size_t i = 0; i < method_count; ++i) {
        outputs[i] = poly_new(methods[i].output_words);
        methods[i].reduce_into(input, methods[i].context, &outputs[i]);
    }

    for (size_t i = 1; i < method_count; ++i) {
        if (!poly_equal(&outputs[0], &outputs[i])) {
            fprintf(stderr,
                    "reduction mismatch: m=%zu trial=%zu taps=%zu "
                    "left=%s right=%s\n",
                    m, trial, tap_count, methods[0].name, methods[i].name);
            exit(EXIT_FAILURE);
        }
    }

    for (size_t i = 0; i < method_count; ++i)
        poly_free(&outputs[i]);
    free(outputs);
}

int main(void) {
    const size_t degrees[] = {8, 31, 64, 65, 127, 128, 257};

    for (size_t mi = 0; mi < sizeof(degrees) / sizeof(degrees[0]); ++mi) {
        size_t m = degrees[mi];
        for (size_t trial = 0; trial < 100; ++trial) {
            size_t tap_count = 2 + (size_t)(next_random() % 7);
            if (tap_count > m) tap_count = m;
            size_t *taps = malloc(tap_count * sizeof(*taps));
            if (!taps) die("allocation failed");
            choose_taps(taps, tap_count, m, (trial & 1) == 0);

            poly_t modulus = poly_from_exponents(m + 1, taps, tap_count);
            poly_set_bit(&modulus, m);
            poly_t input = poly_new(poly_words_for_bits(2 * m));
            random_input(&input, m);

            reduction_method methods[] = {
                reduction_make_gs(taps, tap_count, m),
                reduction_make_serial(taps, tap_count, m),
                reduction_make_naive(&modulus, m, input.n),
                reduction_make_barrett(&modulus, m),
            };
            size_t method_count = sizeof(methods) / sizeof(methods[0]);
            check_methods(methods, method_count, &input, m, trial, tap_count);

            for (size_t i = 0; i < method_count; ++i)
                reduction_method_destroy(&methods[i]);
            poly_free(&input);
            poly_free(&modulus);
            free(taps);
        }
    }

    puts("reduction correctness: ok");
    return EXIT_SUCCESS;
}
