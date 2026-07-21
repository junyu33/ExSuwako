#include "GS.h"

typedef struct {
    size_t word_offset;
    unsigned bit_offset;
} shift_desc;

typedef struct {
    size_t offset;
    size_t count;
} round_desc;

struct gs_plan {
    size_t m;
    size_t state_words;
    size_t round_count;
    size_t assembly_count;
    round_desc *rounds;
    shift_desc *feedback_shifts;
    shift_desc *assembly_shifts;
    poly_t state;
};

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
        qsort(round_shifts, shift_count, sizeof(*round_shifts), compare_shift_desc);

        round_desc *rounds = realloc(
            plan->rounds, (plan->round_count + 1) * sizeof(*rounds));
        shift_desc *feedback = realloc(
            plan->feedback_shifts,
            (feedback_count + shift_count) * sizeof(*feedback));
        if (!rounds || !feedback) die("allocation failed");
        plan->rounds = rounds;
        plan->feedback_shifts = feedback;
        plan->rounds[plan->round_count++] = (round_desc){
            feedback_count, shift_count
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
              sizeof(*plan->assembly_shifts), compare_shift_desc);
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

poly_t gs_reduce_planned(const poly_t *input, gs_plan *plan) {
    memset(plan->state.v, 0, plan->state.n * sizeof(word_t));
    poly_xor_right_shift(&plan->state, input, plan->m);
    plan->state.v[plan->state_words] = 0;

    for (size_t i = 0; i < plan->round_count; ++i) {
        const round_desc *round = &plan->rounds[i];
        feedback_stage_in_place(
            plan->state.v,
            plan->state_words,
            plan->feedback_shifts + round->offset,
            round->count);
    }

    poly_t low = poly_new(plan->state_words);
    assemble_low_part(
        &low, input, plan->state.v, plan->state_words,
        plan->assembly_shifts, plan->assembly_count, plan->m);
    return low;
}

poly_t gs_reduce(const poly_t *input, const size_t *taps, size_t s, size_t m) {
    gs_plan *plan = gs_plan_create(taps, s, m);
    poly_t result = gs_reduce_planned(input, plan);
    gs_plan_destroy(plan);
    return result;
}
