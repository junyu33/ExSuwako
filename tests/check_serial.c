#include "GS.h"
#include "naive.h"
#include "serial.h"

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

            gs_plan *gs = gs_plan_create(taps, tap_count, m);
            serial_plan *serial = serial_plan_create(taps, tap_count, m);
            poly_t gs_result = gs_reduce_planned(&input, gs);
            poly_t serial_result = serial_reduce_planned(&input, serial);
            poly_t naive_result = naive_reduce(&input, &modulus, m);

            if (!poly_equal(&serial_result, &gs_result)
                    || !poly_equal(&serial_result, &naive_result)) {
                fprintf(stderr, "serial mismatch: m=%zu trial=%zu taps=%zu\n",
                        m, trial, tap_count);
                return EXIT_FAILURE;
            }

            poly_free(&naive_result);
            poly_free(&serial_result);
            poly_free(&gs_result);
            serial_plan_destroy(serial);
            gs_plan_destroy(gs);
            poly_free(&input);
            poly_free(&modulus);
            free(taps);
        }
    }

    puts("serial sparse folding correctness: ok");
    return EXIT_SUCCESS;
}
