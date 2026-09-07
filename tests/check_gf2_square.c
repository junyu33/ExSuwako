#include "gf2_square.h"

static uint64_t state = UINT64_C(0x5351554152455445);

static uint64_t next_word(void) {
    state ^= state << 7;
    state ^= state >> 9;
    return state;
}

static int bit(const poly_t *p, size_t i) {
    return (int)((p->v[i / WORD_BITS] >> (i % WORD_BITS)) & 1u);
}

int main(void) {
    for (size_t m = 1; m <= 513; ++m) {
        poly_t input = poly_new(poly_words_for_bits(m));
        poly_t output = poly_new(poly_words_for_bits(2 * m));
        for (size_t trial = 0; trial < 20; ++trial) {
            for (size_t i = 0; i < input.n; ++i) input.v[i] = next_word();
            gf2_square_to_2m(&input, m, &output);
            for (size_t i = 0; i < m; ++i) {
                if (bit(&output, 2 * i) != bit(&input, i))
                    die("square coefficient mismatch");
                if (2 * i + 1 < 2 * m && bit(&output, 2 * i + 1))
                    die("square has a nonzero odd coefficient");
            }
        }
        poly_free(&input);
        poly_free(&output);
    }
    puts("GF(2) square checks passed");
    return 0;
}
