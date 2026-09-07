#include "gf2_square.h"

#include <limits.h>

static uint64_t spread32(uint32_t x) {
    uint64_t y = x;
    y = (y | (y << 16)) & UINT64_C(0x0000ffff0000ffff);
    y = (y | (y << 8)) & UINT64_C(0x00ff00ff00ff00ff);
    y = (y | (y << 4)) & UINT64_C(0x0f0f0f0f0f0f0f0f);
    y = (y | (y << 2)) & UINT64_C(0x3333333333333333);
    y = (y | (y << 1)) & UINT64_C(0x5555555555555555);
    return y;
}

static uint32_t input_chunk32(const poly_t *input, size_t chunk) {
    size_t bit = chunk * 32;
    size_t word = bit / WORD_BITS;
    unsigned offset = (unsigned)(bit % WORD_BITS);
    uint64_t value = word < input->n ? input->v[word] >> offset : 0;
    if (offset && offset + 32 > WORD_BITS && word + 1 < input->n)
        value |= (uint64_t)input->v[word + 1] << (WORD_BITS - offset);
    return (uint32_t)value;
}

static void output_chunk64(poly_t *output, size_t chunk, uint64_t value) {
    size_t bit = chunk * 64;
    size_t word = bit / WORD_BITS;
    unsigned offset = (unsigned)(bit % WORD_BITS);
    if (word < output->n) output->v[word] |= (word_t)(value << offset);
    if (offset && word + 1 < output->n)
        output->v[word + 1] |= (word_t)(value >> (WORD_BITS - offset));
#if ULONG_MAX == UINT32_MAX
    if (!offset && word + 1 < output->n)
        output->v[word + 1] |= (word_t)(value >> 32);
#endif
}

void gf2_square_to_2m(const poly_t *input, size_t m, poly_t *output) {
    if (!input || !output) die("square input and output are required");
    if (input->n < poly_words_for_bits(m)
            || output->n < poly_words_for_bits(2 * m))
        die("square buffer is too small");
    memset(output->v, 0, output->n * sizeof(*output->v));
    size_t chunks = (m + 31) / 32;
    for (size_t chunk = 0; chunk < chunks; ++chunk) {
        uint32_t value = input_chunk32(input, chunk);
        if (chunk + 1 == chunks && m % 32)
            value &= (UINT32_C(1) << (m % 32)) - 1;
        output_chunk64(output, chunk, spread32(value));
    }
}
