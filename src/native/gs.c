#include "gs.h"

poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m) {
    poly_t low = poly_new(poly_words_for_bits(m));
    poly_t state = poly_shift_right(input, m);
    poly_t old = poly_new(state.n);
    size_t dmin = m + 1;
    for (size_t i = 0; i < s; ++i)
        if (taps[i] > 0 && m - taps[i] < dmin) dmin = m - taps[i];
    size_t rounds = 0;
    while (dmin <= m && (((size_t)1 << rounds) * dmin < m)) ++rounds;
    for (size_t k = 0; k < rounds; ++k) {
        memcpy(old.v, state.v, state.n * sizeof(word_t));
        size_t factor = (size_t)1 << k;
        for (size_t i = 0; i < s; ++i) {
            size_t delta = m - taps[i];
            if (!taps[i] || factor * delta >= m) continue;
            poly_xor_right_shift(&state, &old, factor * delta);
        }
    }
    for (size_t i = 0; i < low.n && i < input->n; ++i) low.v[i] = input->v[i];
    for (size_t i = 0; i < s; ++i) poly_xor_left_shift(&low, &state, taps[i]);
    poly_free(&state);
    poly_free(&old);
    return low;
}
