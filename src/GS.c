#include "GS.h"
#include "sparse_shift.h"

typedef struct {
    size_t offset;
    size_t count;
    size_t aligned_count;
} round_desc;

struct gs_plan {
    size_t m;
    size_t state_words;
    size_t round_count;
    size_t assembly_count;
    size_t assembly_aligned_count;
    round_desc *rounds;
    shift_desc *feedback_shifts;
    shift_desc *assembly_shifts;
    poly_t state;
};

static size_t aligned_shift_count(const shift_desc *shifts, size_t count) {
    size_t aligned = 0;
    for (size_t i = 0; i < count; ++i)
        aligned += shifts[i].bit_offset == 0;
    return aligned;
}

static void extract_high_part(word_t *state, size_t state_words,
                              const poly_t *input, size_t m) {
    size_t word_offset = m / WORD_BITS;
    unsigned bit_offset = (unsigned)(m % WORD_BITS);

    for (size_t dst = 0; dst < state_words; ++dst) {
        size_t src = dst + word_offset;
        word_t value = src < input->n ? input->v[src] >> bit_offset : 0;
        if (bit_offset != 0 && src + 1 < input->n)
            value ^= input->v[src + 1] << (WORD_BITS - bit_offset);
        state[dst] = value;
    }
    state[state_words] = 0;
}

static inline word_t feedback_aligned_accumulate(
    const word_t *state,
    size_t state_words,
    size_t dst,
    const shift_desc *shifts,
    size_t shift_count,
    word_t acc)
{
    for (size_t j = 0; j < shift_count; ++j) {
        size_t word_offset = shifts[j].word_offset;
        if (word_offset >= state_words - dst) break;
        acc ^= state[dst + word_offset];
    }
    return acc;
}

static inline word_t feedback_unaligned_accumulate(
    const word_t *state,
    size_t state_words,
    size_t dst,
    const shift_desc *shifts,
    size_t shift_count,
    word_t acc)
{
    size_t j = 0;
    while (j < shift_count) {
        size_t word_offset = shifts[j].word_offset;
        if (word_offset >= state_words - dst) break;

        size_t src = dst + word_offset;
        word_t lower = state[src];
        word_t upper = state[src + 1];
        do {
            unsigned bit_offset = shifts[j].bit_offset;
            acc ^= sparse_right_shift_word(lower, upper, bit_offset);
            ++j;
        } while (j < shift_count
              && shifts[j].word_offset == word_offset);
    }
    return acc;
}

static void feedback_stage_in_place(
    word_t *state,
    size_t state_words,
    const shift_desc *shifts,
    size_t shift_count,
    size_t aligned_count)
{
    if (aligned_count == 0) {
        for (size_t dst = 0; dst < state_words; ++dst)
            state[dst] = feedback_unaligned_accumulate(
                state, state_words, dst, shifts, shift_count, state[dst]);
        return;
    }

    if (aligned_count == shift_count) {
        for (size_t dst = 0; dst < state_words; ++dst)
            state[dst] = feedback_aligned_accumulate(
                state, state_words, dst, shifts, shift_count, state[dst]);
        return;
    }

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
                acc ^= sparse_right_shift_word(lower, upper, bit_offset);
                ++j;
            } while (j < shift_count
                  && shifts[j].word_offset == word_offset);
        }
        state[dst] = acc;
    }
}

static inline word_t assembly_aligned_accumulate(
    const word_t *state,
    size_t state_words,
    size_t dst,
    const shift_desc *shifts,
    size_t shift_count,
    word_t acc)
{
    for (size_t j = 0; j < shift_count; ++j) {
        size_t word_offset = shifts[j].word_offset;
        if (word_offset > dst) break;
        size_t src = dst - word_offset;
        if (src < state_words) acc ^= state[src];
    }
    return acc;
}

static inline word_t assembly_unaligned_accumulate(
    const word_t *state,
    size_t state_words,
    size_t dst,
    const shift_desc *shifts,
    size_t shift_count,
    word_t acc)
{
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
            acc ^= (upper << bit_offset)
                ^ (lower >> (WORD_BITS - bit_offset));
            ++j;
        } while (j < shift_count
              && shifts[j].word_offset == word_offset);
    }
    return acc;
}

static void assemble_low_part(
    poly_t *output,
    const poly_t *input,
    const word_t *state,
    size_t state_words,
    const shift_desc *shifts,
    size_t shift_count,
    size_t aligned_count,
    size_t m)
{
    if (aligned_count == 0) {
        for (size_t dst = 0; dst < output->n; ++dst) {
            word_t acc = dst < input->n ? input->v[dst] : 0;
            output->v[dst] = assembly_unaligned_accumulate(
                state, state_words, dst, shifts, shift_count, acc);
        }
    } else if (aligned_count == shift_count) {
        for (size_t dst = 0; dst < output->n; ++dst) {
            word_t acc = dst < input->n ? input->v[dst] : 0;
            output->v[dst] = assembly_aligned_accumulate(
                state, state_words, dst, shifts, shift_count, acc);
        }
    } else {
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
    }

    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (top_bits != 0)
        output->v[output->n - 1] &= ((word_t)1 << top_bits) - 1;
}

gs_plan *gs_plan_create(const size_t *taps, size_t s, size_t m) {
    gs_plan *plan = calloc(1, sizeof(*plan));
    shift_desc *round_shifts = s ? malloc(s * sizeof(*round_shifts)) : NULL;
    size_t feedback_count = 0;
    if (!plan || (s && !round_shifts)) die("allocation failed");

    plan->m = m;
    plan->state_words = poly_words_for_bits(m);
    plan->assembly_count = s;
    plan->state = poly_new(plan->state_words + 1);

    for (size_t factor = 1;; factor <<= 1) {
        size_t shift_count = 0;
        for (size_t i = 0; i < s; ++i) {
            if (taps[i] == 0) continue;
            size_t delta = m - taps[i];
            if (factor > (m - 1) / delta) continue;
            size_t shift = factor * delta;
            round_shifts[shift_count++] = (shift_desc){
                shift / WORD_BITS,
                (unsigned)(shift % WORD_BITS)
            };
        }
        if (shift_count == 0) break;
        qsort(round_shifts, shift_count, sizeof(*round_shifts),
              shift_desc_compare);
        size_t aligned_count = aligned_shift_count(round_shifts, shift_count);

        round_desc *rounds = realloc(
            plan->rounds, (plan->round_count + 1) * sizeof(*rounds));
        shift_desc *feedback = realloc(
            plan->feedback_shifts,
            (feedback_count + shift_count) * sizeof(*feedback));
        if (!rounds || !feedback) die("allocation failed");
        plan->rounds = rounds;
        plan->feedback_shifts = feedback;
        plan->rounds[plan->round_count++] = (round_desc){
            feedback_count, shift_count, aligned_count
        };
        memcpy(plan->feedback_shifts + feedback_count,
               round_shifts, shift_count * sizeof(*round_shifts));
        feedback_count += shift_count;
        if (factor > SIZE_MAX / 2) break;
    }
    free(round_shifts);

    plan->assembly_shifts = s ? malloc(s * sizeof(*plan->assembly_shifts)) : NULL;
    if (s && !plan->assembly_shifts) die("allocation failed");
    for (size_t i = 0; i < s; ++i)
        plan->assembly_shifts[i] = (shift_desc){
            taps[i] / WORD_BITS,
            (unsigned)(taps[i] % WORD_BITS)
        };
    if (s)
        qsort(plan->assembly_shifts, s,
              sizeof(*plan->assembly_shifts), shift_desc_compare);
    plan->assembly_aligned_count = aligned_shift_count(
        plan->assembly_shifts, s);
    return plan;
}

void gs_plan_destroy(gs_plan *plan) {
    if (!plan) return;
    poly_free(&plan->state);
    free(plan->assembly_shifts);
    free(plan->feedback_shifts);
    free(plan->rounds);
    free(plan);
}

void gs_reduce_into(const poly_t *input, gs_plan *plan, poly_t *output) {
    if (output->n < plan->state_words)
        die("GS output buffer is too small");

    extract_high_part(
        plan->state.v, plan->state_words, input, plan->m);

    for (size_t i = 0; i < plan->round_count; ++i) {
        const round_desc *round = &plan->rounds[i];
        feedback_stage_in_place(
            plan->state.v,
            plan->state_words,
            plan->feedback_shifts + round->offset,
            round->count,
            round->aligned_count);
    }

    assemble_low_part(
        output, input, plan->state.v, plan->state_words,
        plan->assembly_shifts, plan->assembly_count,
        plan->assembly_aligned_count, plan->m);
}

poly_t gs_reduce_planned(const poly_t *input, gs_plan *plan) {
    poly_t low = poly_new(plan->state_words);
    gs_reduce_into(input, plan, &low);
    return low;
}

poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m) {
    gs_plan *plan = gs_plan_create(taps, s, m);
    poly_t result = gs_reduce_planned(input, plan);
    gs_plan_destroy(plan);
    return result;
}
