#include "../src/GS.c"

#include <stdint.h>

enum { RANDOM_COMPONENT_CASES = 20000 };

static const uint64_t component_seed = UINT64_C(0xe7037ed1a0b428db);
static uint64_t component_rng = UINT64_C(0xe7037ed1a0b428db);

static uint64_t component_random(void) {
    component_rng ^= component_rng << 7;
    component_rng ^= component_rng >> 9;
    return component_rng;
}

static int component_bit(const word_t *words, size_t bit) {
    return (int)((words[bit / WORD_BITS] >> (bit % WORD_BITS)) & 1u);
}

static void toggle_component_bit(word_t *words, size_t bit) {
    words[bit / WORD_BITS] ^= (word_t)1 << (bit % WORD_BITS);
}

static void random_m_bit_state(word_t *state, size_t m) {
    size_t words = poly_words_for_bits(m);
    for (size_t i = 0; i < words; ++i) state[i] = (word_t)component_random();
    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (top_bits != 0)
        state[words - 1] &= ((word_t)1 << top_bits) - 1;
}

static void reference_right_shift_xor(word_t *result, const word_t *old,
                                      size_t m, size_t distance) {
    for (size_t dst = 0; dst + distance < m; ++dst)
        if (component_bit(old, dst + distance))
            toggle_component_bit(result, dst);
}

static size_t reference_feedback_closure(word_t *state, size_t m,
                                         const size_t *taps,
                                         size_t tap_count) {
    size_t words = poly_words_for_bits(m);
    word_t *old = calloc(words + 1, sizeof(*old));
    if (!old) die("allocation failed");

    size_t rounds = 0;
    for (size_t factor = 1;; factor <<= 1) {
        int active = 0;
        memcpy(old, state, (words + 1) * sizeof(*old));
        for (size_t i = 0; i < tap_count; ++i) {
            if (taps[i] == 0) continue;
            size_t delta = m - taps[i];
            if (factor > (m - 1) / delta) continue;
            active = 1;
            reference_right_shift_xor(state, old, m, factor * delta);
        }
        if (!active) break;
        ++rounds;
        if (factor > SIZE_MAX / 2) break;
    }

    free(old);
    return rounds;
}

static void reference_low_assembly(word_t *result, const word_t *state,
                                   size_t m, const size_t *taps,
                                   size_t tap_count) {
    for (size_t i = 0; i < tap_count; ++i) {
        size_t tap = taps[i];
        for (size_t src = 0; src + tap < m; ++src)
            if (component_bit(state, src))
                toggle_component_bit(result, src + tap);
    }
}

static void print_taps(const size_t *taps, size_t tap_count) {
    if (tap_count == 0) {
        fputc('-', stderr);
        return;
    }
    for (size_t i = 0; i < tap_count; ++i)
        fprintf(stderr, "%s%zu", i ? ";" : "", taps[i]);
}

static void component_failure(const char *component, const char *suite,
                              size_t trial, size_t m, const size_t *taps,
                              size_t tap_count) {
    fprintf(stderr,
            "GS component mismatch: component=%s suite=%s seed=0x%016llx "
            "trial=%zu m=%zu taps=",
            component, suite, (unsigned long long)component_seed, trial, m);
    print_taps(taps, tap_count);
    fputc('\n', stderr);
    exit(EXIT_FAILURE);
}

static void check_components(size_t m, const size_t *taps, size_t tap_count,
                             size_t trial, const char *suite) {
    gs_plan *plan = gs_plan_create(taps, tap_count, m);
    size_t words = poly_words_for_bits(m);

    word_t *high = calloc(words + 1, sizeof(*high));
    word_t *expected_closure = calloc(words + 1, sizeof(*expected_closure));
    if (!high || !expected_closure) die("allocation failed");
    random_m_bit_state(high, m);
    memcpy(expected_closure, high, (words + 1) * sizeof(*expected_closure));
    memcpy(plan->state.v, high, (words + 1) * sizeof(*high));

    size_t expected_rounds = reference_feedback_closure(
        expected_closure, m, taps, tap_count);
    for (size_t round_index = 0; round_index < plan->round_count;
         ++round_index) {
        const round_desc *round = &plan->rounds[round_index];
        feedback_stage_in_place(
            plan->state.v, plan->state_words,
            plan->feedback_shifts + round->offset, round->count,
            round->aligned_count, round->affected_words);
    }
    if (plan->round_count != expected_rounds ||
        memcmp(plan->state.v, expected_closure,
               (words + 1) * sizeof(*expected_closure)) != 0)
        component_failure(
            "feedback-closure", suite, trial, m, taps, tap_count);

    poly_t input = poly_new(poly_words_for_bits(2 * m));
    poly_t output = poly_new(words);
    word_t *assembly_state = calloc(words + 1, sizeof(*assembly_state));
    word_t *expected_output = calloc(words, sizeof(*expected_output));
    if (!assembly_state || !expected_output) die("allocation failed");
    random_m_bit_state(assembly_state, m);
    for (size_t bit = 0; bit < m; ++bit)
        if (component_random() & 1) poly_set_bit(&input, bit);
    memcpy(expected_output, input.v, words * sizeof(*expected_output));
    reference_low_assembly(expected_output, assembly_state, m,
                           taps, tap_count);

    assemble_low_part(
        &output, &input, assembly_state, words, plan->assembly_shifts,
        plan->assembly_count, plan->assembly_aligned_count, m);
    if (memcmp(output.v, expected_output, words * sizeof(*expected_output)) != 0)
        component_failure(
            "low-part-assembly", suite, trial, m, taps, tap_count);

    free(expected_output);
    free(assembly_state);
    poly_free(&output);
    poly_free(&input);
    free(expected_closure);
    free(high);
    gs_plan_destroy(plan);
}

static int compare_taps(const void *left, const void *right) {
    size_t a = *(const size_t *)left;
    size_t b = *(const size_t *)right;
    return (a > b) - (a < b);
}

static void check_explicit_components(void) {
    static const size_t constant_only[] = {0};
    static const size_t constant_free[] = {1, 64, 128};
    static const size_t mixed[] = {0, 1, 63, 64, 65, 127, 128, 257, 318};
    static const size_t dense[] = {
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
    };

    check_components(1, NULL, 0, 0, "empty");
    check_components(65, constant_only, 1, 0, "constant-only");
    check_components(129, constant_free, 3, 0, "constant-free");
    check_components(319, mixed, 9, 0, "mixed-boundaries");
    check_components(17, dense, 17, 0, "dense");
}

int main(void) {
    check_explicit_components();

    for (size_t trial = 0; trial < RANDOM_COMPONENT_CASES; ++trial) {
        size_t m = 1 + (size_t)(component_random() % 512);
        size_t max_taps = m < 16 ? m : 16;
        size_t tap_count = (size_t)(component_random() % (max_taps + 1));
        size_t taps[16];
        for (size_t i = 0; i < tap_count; ++i) {
            size_t candidate;
            int duplicate;
            do {
                candidate = (size_t)(component_random() % m);
                duplicate = 0;
                for (size_t j = 0; j < i; ++j)
                    duplicate |= taps[j] == candidate;
            } while (duplicate);
            taps[i] = candidate;
        }
        qsort(taps, tap_count, sizeof(*taps), compare_taps);
        check_components(m, taps, tap_count, trial, "random");
    }

    printf("GS feedback closure and low-part assembly: ok "
           "(5 explicit classes, %d random cases, seed=0x%016llx)\n",
           RANDOM_COMPONENT_CASES, (unsigned long long)component_seed);
    return EXIT_SUCCESS;
}
