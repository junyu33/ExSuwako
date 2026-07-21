#ifndef EXSUWAKO_SPARSE_SHIFT_H
#define EXSUWAKO_SPARSE_SHIFT_H

#include <stddef.h>

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

#endif
