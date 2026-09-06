#include "lopez_dahab.h"
#include "sparse_shift.h"

typedef struct {
    shift_desc full_word;
    shift_desc partial_word;
} lopez_dahab_tap;

struct lopez_dahab_plan {
    size_t m;
    size_t state_words;
    size_t input_words;
    size_t tap_count;
    unsigned top_bits;
    word_t top_mask;
    lopez_dahab_tap *taps;
    word_t *work;
};

lopez_dahab_plan *lopez_dahab_plan_create(
    const size_t *taps, size_t tap_count, size_t m)
{
    if (m <= WORD_BITS)
        die("Lopez-Dahab requires m greater than one word");
    if (tap_count && !taps) die("Lopez-Dahab taps are missing");

    size_t limit = m - WORD_BITS;
    for (size_t i = 0; i < tap_count; ++i) {
        if (taps[i] > limit)
            die("Lopez-Dahab extension requires deg(q) <= m-W");
    }

    lopez_dahab_plan *plan = calloc(1, sizeof(*plan));
    if (!plan) die("allocation failed");
    plan->m = m;
    plan->state_words = poly_words_for_bits(m);
    plan->input_words = poly_words_for_bits(2 * m);
    plan->tap_count = tap_count;
    plan->top_bits = (unsigned)(m % WORD_BITS);
    plan->top_mask = plan->top_bits
        ? ((word_t)1 << plan->top_bits) - 1
        : ~(word_t)0;
    plan->taps = tap_count ? malloc(tap_count * sizeof(*plan->taps)) : NULL;
    plan->work = calloc(plan->input_words, sizeof(*plan->work));
    if ((tap_count && !plan->taps) || !plan->work)
        die("allocation failed");

    size_t padding = plan->state_words * WORD_BITS - m;
    for (size_t i = 0; i < tap_count; ++i) {
        size_t full_shift = padding + taps[i];
        plan->taps[i] = (lopez_dahab_tap){
            .full_word = {
                .word_offset = full_shift / WORD_BITS,
                .bit_offset = (unsigned)(full_shift % WORD_BITS),
            },
            .partial_word = {
                .word_offset = taps[i] / WORD_BITS,
                .bit_offset = (unsigned)(taps[i] % WORD_BITS),
            },
        };
    }
    return plan;
}

void lopez_dahab_plan_destroy(lopez_dahab_plan *plan) {
    if (!plan) return;
    free(plan->work);
    free(plan->taps);
    free(plan);
}

size_t lopez_dahab_plan_storage_bytes(const lopez_dahab_plan *plan) {
    if (!plan) return 0;
    return sizeof(*plan)
         + plan->tap_count * sizeof(*plan->taps)
         + plan->input_words * sizeof(*plan->work);
}

static inline void scatter_word(word_t *work, size_t target,
                                word_t value, shift_desc shift) {
    work[target] ^= value << shift.bit_offset;
    if (shift.bit_offset)
        work[target + 1] ^=
            value >> (WORD_BITS - shift.bit_offset);
}

void lopez_dahab_reduce_into(const poly_t *input, lopez_dahab_plan *plan,
                             poly_t *output) {
    if (output->n < plan->state_words)
        die("Lopez-Dahab output buffer is too small");

    size_t copied = input->n < plan->input_words
        ? input->n : plan->input_words;
    memcpy(plan->work, input->v, copied * sizeof(*plan->work));
    if (copied < plan->input_words)
        memset(plan->work + copied, 0,
               (plan->input_words - copied) * sizeof(*plan->work));

    for (size_t source = plan->input_words;
         source-- > plan->state_words;) {
        word_t top = plan->work[source];
        plan->work[source] = 0;
        size_t base = source - plan->state_words;
        for (size_t i = 0; i < plan->tap_count; ++i) {
            shift_desc shift = plan->taps[i].full_word;
            scatter_word(plan->work, base + shift.word_offset, top, shift);
        }
    }

    if (plan->top_bits) {
        size_t source = plan->state_words - 1;
        word_t top = plan->work[source] >> plan->top_bits;
        plan->work[source] &= plan->top_mask;
        for (size_t i = 0; i < plan->tap_count; ++i) {
            shift_desc shift = plan->taps[i].partial_word;
            scatter_word(plan->work, shift.word_offset, top, shift);
        }
    }

    memcpy(output->v, plan->work,
           plan->state_words * sizeof(*output->v));
    if (output->n > plan->state_words)
        memset(output->v + plan->state_words, 0,
               (output->n - plan->state_words) * sizeof(*output->v));
    output->v[plan->state_words - 1] &= plan->top_mask;
}
