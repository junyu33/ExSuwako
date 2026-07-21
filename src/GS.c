#include "GS.h"

typedef struct {
    size_t word_offset;
    unsigned bit_offset;
} shift_desc;

static int compare_shift_desc(const void *left, const void *right) {
    const shift_desc *a = left;
    const shift_desc *b = right;
    if (a->word_offset < b->word_offset) return -1;
    if (a->word_offset > b->word_offset) return 1;
    return (a->bit_offset > b->bit_offset)
         - (a->bit_offset < b->bit_offset);
}

static void feedback_stage_in_place(
    word_t *state,
    size_t state_words,
    const shift_desc *shifts,
    size_t shift_count)
{
    for (size_t dst = 0; dst < state_words; ++dst) {
        word_t acc = state[dst];
        size_t j = 0;

        while (j < shift_count) {
            size_t word_offset = shifts[j].word_offset;
            if (word_offset >= state_words - dst) break;

            size_t src = dst + word_offset;
            word_t lower = state[src];
            word_t upper = state[src + 1];
            do {
                unsigned bit_offset = shifts[j].bit_offset;
                acc ^= bit_offset == 0
                    ? lower
                    : (lower >> bit_offset)
                    ^ (upper << (WORD_BITS - bit_offset));
                ++j;
            } while (j < shift_count
                  && shifts[j].word_offset == word_offset);
        }

        state[dst] = acc;
    }
}

static void assemble_low_part(
    poly_t *output,
    const poly_t *input,
    const word_t *state,
    size_t state_words,
    const shift_desc *shifts,
    size_t shift_count,
    size_t m)
{
    for (size_t dst = 0; dst < output->n; ++dst) {
        word_t acc = dst < input->n ? input->v[dst] : 0;
        size_t j = 0;

        while (j < shift_count) {
            size_t word_offset = shifts[j].word_offset;
            if (word_offset > dst) break;

            size_t src = dst - word_offset;
            if (src >= state_words) {
                ++j;
                continue;
            }

            word_t upper = state[src];
            word_t lower = src > 0 ? state[src - 1] : 0;
            do {
                unsigned bit_offset = shifts[j].bit_offset;
                acc ^= bit_offset == 0
                    ? upper
                    : (upper << bit_offset)
                    ^ (lower >> (WORD_BITS - bit_offset));
                ++j;
            } while (j < shift_count
                  && shifts[j].word_offset == word_offset);
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

    shift_desc *shifts = s ? malloc(s * sizeof(*shifts)) : NULL;
    if (s && !shifts) die("allocation failed");

    for (size_t factor = 1;; factor <<= 1) {
        size_t shift_count = 0;
        for (size_t i = 0; i < s; ++i) {
            if (taps[i] == 0) continue;
            size_t delta = m - taps[i];
            if (factor > (m - 1) / delta) continue;
            size_t shift = factor * delta;
            shifts[shift_count++] = (shift_desc){
                shift / WORD_BITS,
                (unsigned)(shift % WORD_BITS)
            };
        }
        if (shift_count == 0) break;
        qsort(shifts, shift_count, sizeof(*shifts), compare_shift_desc);
        feedback_stage_in_place(
            state.v, state_words, shifts, shift_count);
        if (factor > SIZE_MAX / 2) break;
    }

    for (size_t i = 0; i < s; ++i)
        shifts[i] = (shift_desc){
            taps[i] / WORD_BITS,
            (unsigned)(taps[i] % WORD_BITS)
        };
    if (s) qsort(shifts, s, sizeof(*shifts), compare_shift_desc);

    poly_t low = poly_new(state_words);
    assemble_low_part(&low, input, state.v, state_words, shifts, s, m);
    free(shifts);
    poly_free(&state);
    return low;
}
