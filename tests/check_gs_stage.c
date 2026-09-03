#include "../src/GS.c"

#include <stdint.h>

enum { RANDOM_STAGE_CASES = 20000 };

static const uint64_t stage_seed = UINT64_C(0xa0761d6478bd642f);
static uint64_t stage_rng = UINT64_C(0xa0761d6478bd642f);

static uint64_t next_random(void) {
    stage_rng ^= stage_rng << 7;
    stage_rng ^= stage_rng >> 9;
    return stage_rng;
}

static int word_bit(const word_t *words, size_t bit) {
    return (int)((words[bit / WORD_BITS] >> (bit % WORD_BITS)) & 1u);
}

static void reference_immutable_stage(word_t *result, const word_t *old,
                                      size_t m, const size_t *distances,
                                      size_t count) {
    for (size_t shift = 0; shift < count; ++shift) {
        size_t distance = distances[shift];
        for (size_t dst = 0; dst + distance < m; ++dst)
            if (word_bit(old, dst + distance))
                result[dst / WORD_BITS] ^= (word_t)1 << (dst % WORD_BITS);
    }
}

static void check_stage(size_t m, const size_t *distances, size_t count,
                        size_t trial, const char *suite) {
    size_t state_words = poly_words_for_bits(m);
    word_t *old = calloc(state_words + 1, sizeof(*old));
    word_t *actual = calloc(state_words + 1, sizeof(*actual));
    word_t *expected = calloc(state_words + 1, sizeof(*expected));
    shift_desc *shifts = malloc(count * sizeof(*shifts));
    if (!old || !actual || !expected || !shifts) die("allocation failed");

    for (size_t i = 0; i < state_words; ++i) old[i] = (word_t)next_random();
    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (top_bits != 0)
        old[state_words - 1] &= ((word_t)1 << top_bits) - 1;
    memcpy(actual, old, (state_words + 1) * sizeof(*actual));
    memcpy(expected, old, (state_words + 1) * sizeof(*expected));

    size_t min_shift = m;
    for (size_t i = 0; i < count; ++i) {
        if (distances[i] == 0 || distances[i] >= m)
            die("invalid stage-test shift");
        if (distances[i] < min_shift) min_shift = distances[i];
        shifts[i] = (shift_desc){
            distances[i] / WORD_BITS,
            (unsigned)(distances[i] % WORD_BITS)
        };
    }
    qsort(shifts, count, sizeof(*shifts), shift_desc_compare);

    reference_immutable_stage(expected, old, m, distances, count);
    feedback_stage_in_place(
        actual, state_words, shifts, count,
        aligned_shift_count(shifts, count),
        poly_words_for_bits(m - min_shift));

    if (memcmp(actual, expected, (state_words + 1) * sizeof(*actual)) != 0) {
        fprintf(stderr,
                "GS immutable-stage mismatch: suite=%s seed=0x%016llx "
                "trial=%zu m=%zu shifts=",
                suite, (unsigned long long)stage_seed, trial, m);
        for (size_t i = 0; i < count; ++i)
            fprintf(stderr, "%s%zu", i ? ";" : "", distances[i]);
        fputc('\n', stderr);
        exit(EXIT_FAILURE);
    }

    free(shifts);
    free(expected);
    free(actual);
    free(old);
}

static void check_explicit_classes(void) {
    static const size_t aligned[] = {64, 128, 192, 256};
    static const size_t unaligned[] = {1, 65, 129, 193};
    static const size_t mixed[] = {1, 63, 64, 65, 127, 128, 256};
    check_stage(319, aligned, sizeof(aligned) / sizeof(aligned[0]),
                0, "all-aligned");
    check_stage(319, unaligned, sizeof(unaligned) / sizeof(unaligned[0]),
                0, "all-unaligned");
    check_stage(319, mixed, sizeof(mixed) / sizeof(mixed[0]),
                0, "mixed");
}

int main(void) {
    check_explicit_classes();

    for (size_t trial = 0; trial < RANDOM_STAGE_CASES; ++trial) {
        size_t m = 2 + (size_t)(next_random() % 511);
        size_t max_count = m - 1 < 16 ? m - 1 : 16;
        size_t count = 1 + (size_t)(next_random() % max_count);
        size_t distances[16];
        for (size_t i = 0; i < count; ++i) {
            size_t candidate;
            int duplicate;
            do {
                candidate = 1 + (size_t)(next_random() % (m - 1));
                duplicate = 0;
                for (size_t j = 0; j < i; ++j)
                    duplicate |= distances[j] == candidate;
            } while (duplicate);
            distances[i] = candidate;
        }
        check_stage(m, distances, count, trial, "random");
    }

    printf("GS immutable-stage semantics: ok "
           "(3 explicit classes, %d random cases, seed=0x%016llx)\n",
           RANDOM_STAGE_CASES, (unsigned long long)stage_seed);
    return EXIT_SUCCESS;
}
