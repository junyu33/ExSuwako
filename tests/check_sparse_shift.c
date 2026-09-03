#include "sparse_shift.h"

static uint64_t shift_rng = 0x8ebc6af09c88c6e3ULL;

static uint64_t next_shift_random(void) {
    shift_rng ^= shift_rng << 7;
    shift_rng ^= shift_rng >> 9;
    return shift_rng;
}

static int source_bit(const poly_t *source, size_t bit) {
    if (bit / WORD_BITS >= source->n) return 0;
    return (int)((source->v[bit / WORD_BITS] >> (bit % WORD_BITS)) & 1u);
}

static int destination_bit(const word_t *destination, size_t bit) {
    return (int)((destination[bit / WORD_BITS] >> (bit % WORD_BITS)) & 1u);
}

static void check_assign_shift(size_t source_words, size_t destination_words,
                               size_t shift) {
    poly_t source = poly_new(source_words);
    word_t *destination = malloc(destination_words * sizeof(*destination));
    if (!destination) die("allocation failed");
    for (size_t i = 0; i < source.n; ++i)
        source.v[i] = (word_t)next_shift_random();
    memset(destination, 0xa5, destination_words * sizeof(*destination));

    sparse_assign_right_shift(
        destination, destination_words, &source, shift);
    for (size_t bit = 0; bit < destination_words * WORD_BITS; ++bit) {
        size_t source_index = bit + shift;
        int expected = source_index >= bit
            ? source_bit(&source, source_index) : 0;
        if (destination_bit(destination, bit) != expected) {
            fprintf(stderr,
                    "sparse right-shift mismatch: src_words=%zu "
                    "dst_words=%zu shift=%zu bit=%zu\n",
                    source_words, destination_words, shift, bit);
            exit(EXIT_FAILURE);
        }
    }
    free(destination);
    poly_free(&source);
}

static void check_word_gather(void) {
    for (unsigned offset = 0; offset < WORD_BITS; ++offset) {
        for (size_t trial = 0; trial < 1000; ++trial) {
            word_t lower = (word_t)next_shift_random();
            word_t upper = (word_t)next_shift_random();
            word_t expected = lower >> offset;
            if (offset != 0)
                expected ^= upper << (WORD_BITS - offset);
            word_t actual = sparse_right_shift_word(lower, upper, offset);
            if (actual != expected)
                die("shared sparse word-gather primitive mismatch");
        }
    }
}

int main(void) {
    for (size_t source_words = 0; source_words <= 4; ++source_words) {
        for (size_t destination_words = 1; destination_words <= 5;
             ++destination_words) {
            size_t limit = (source_words + 2) * WORD_BITS;
            for (size_t shift = 0; shift <= limit; ++shift)
                check_assign_shift(source_words, destination_words, shift);
        }
    }
    check_word_gather();
    printf("shared sparse right-shift boundaries: ok\n");
    return EXIT_SUCCESS;
}
