#ifndef EXSUWAKO_SPARSE_SHIFT_H
#define EXSUWAKO_SPARSE_SHIFT_H

#include "poly.h"

/* Word/bit decomposition shared by the GS and serial sparse plans. */
typedef struct {
    size_t word_offset;
    unsigned bit_offset;
} shift_desc;

static inline int shift_desc_compare(const void *left, const void *right) {
    const shift_desc *a = left;
    const shift_desc *b = right;
    if (a->word_offset < b->word_offset) return -1;
    if (a->word_offset > b->word_offset) return 1;
    return (a->bit_offset > b->bit_offset)
         - (a->bit_offset < b->bit_offset);
}

/*
 * Shared scalar right-shift primitive.
 *
 * A source word contributes its low part to the destination at the same word
 * offset and, for a non-word-aligned shift, its carry to the preceding
 * destination word. GS gathers those two contributions from adjacent source
 * words; serial sparse folding scatters them from one loaded source word.
 */
static inline word_t sparse_right_shift_low(word_t source,
                                            unsigned bit_offset) {
    return source >> bit_offset;
}

static inline word_t sparse_right_shift_carry(word_t source,
                                              unsigned bit_offset) {
    return bit_offset == 0
        ? 0
        : source << (WORD_BITS - bit_offset);
}

static inline word_t sparse_right_shift_word(word_t lower, word_t upper,
                                             unsigned bit_offset) {
    return sparse_right_shift_low(lower, bit_offset)
         ^ sparse_right_shift_carry(upper, bit_offset);
}

#endif
