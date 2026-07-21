#include "GS.h"

static void feedback_stage_in_place(
    word_t *state,
    size_t state_words,
    const size_t *taps,
    size_t tap_count,
    size_t m,
    size_t factor)
{
    for (size_t dst = 0; dst < state_words; ++dst) {
        word_t acc = state[dst];

        for (size_t j = 0; j < tap_count; ++j) {
            if (taps[j] == 0) continue;

            size_t delta = m - taps[j];
            if (factor > (m - 1) / delta) continue;

            size_t shift = factor * delta;
            size_t word_offset = shift / WORD_BITS;
            unsigned bit_offset = (unsigned)(shift % WORD_BITS);
            size_t src = dst + word_offset;
            if (src >= state_words) continue;

            word_t contribution = state[src] >> bit_offset;
            if (bit_offset != 0)
                contribution ^= state[src + 1] << (WORD_BITS - bit_offset);
            acc ^= contribution;
        }

        state[dst] = acc;
    }
}

static void assemble_low_part(
    poly_t *output,
    const poly_t *input,
    const word_t *state,
    size_t state_words,
    const size_t *taps,
    size_t tap_count,
    size_t m)
{
    for (size_t dst = 0; dst < output->n; ++dst) {
        word_t acc = dst < input->n ? input->v[dst] : 0;

        for (size_t j = 0; j < tap_count; ++j) {
            size_t word_offset = taps[j] / WORD_BITS;
            unsigned bit_offset = (unsigned)(taps[j] % WORD_BITS);
            if (dst < word_offset) continue;

            size_t src = dst - word_offset;
            if (src >= state_words) continue;

            word_t contribution = state[src] << bit_offset;
            if (bit_offset != 0 && src > 0)
                contribution ^= state[src - 1] >> (WORD_BITS - bit_offset);
            acc ^= contribution;
        }

        output->v[dst] = acc;
    }

    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (top_bits != 0)
        output->v[output->n - 1] &= ((word_t)1 << top_bits) - 1;
}

poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m) {
    size_t state_words = poly_words_for_bits(m);
    poly_t state = poly_new(state_words + 1);
    poly_xor_right_shift(&state, input, m);
    state.v[state_words] = 0;

    size_t dmin = m + 1;
    for (size_t i = 0; i < s; ++i)
        if (taps[i] > 0 && m - taps[i] < dmin) dmin = m - taps[i];

    size_t rounds = 0;
    while (dmin <= m && (((size_t)1 << rounds) * dmin < m)) ++rounds;
    for (size_t k = 0; k < rounds; ++k)
        feedback_stage_in_place(
            state.v, state_words, taps, s, m, (size_t)1 << k);

    poly_t low = poly_new(state_words);
    assemble_low_part(&low, input, state.v, state_words, taps, s, m);
    poly_free(&state);
    return low;
}
