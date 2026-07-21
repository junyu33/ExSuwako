#include "serial.h"
#include "sparse_shift.h"

typedef struct {
    shift_desc assembly;
    shift_desc feedback;
    int has_feedback;
} serial_tap_desc;

struct serial_plan {
    size_t m;
    size_t state_words;
    size_t tap_count;
    serial_tap_desc *taps;
    poly_t current;
    poly_t next;
};

static int compare_serial_tap(const void *left, const void *right) {
    const serial_tap_desc *a = left;
    const serial_tap_desc *b = right;
    return shift_desc_compare(&a->assembly, &b->assembly);
}

static size_t trim_high_zero_words(const word_t *words, size_t count) {
    while (count && words[count - 1] == 0) --count;
    return count;
}

static void mask_top_word(word_t *words, size_t count, size_t m) {
    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (count && top_bits)
        words[count - 1] &= ((word_t)1 << top_bits) - 1;
}

serial_plan *serial_plan_create(const size_t *taps, size_t s, size_t m) {
    if (m == 0) die("serial modulus degree must be positive");

    serial_plan *plan = calloc(1, sizeof(*plan));
    if (!plan) die("allocation failed");
    plan->m = m;
    plan->state_words = poly_words_for_bits(m);
    plan->tap_count = s;
    plan->taps = s ? malloc(s * sizeof(*plan->taps)) : NULL;
    if (s && !plan->taps) die("allocation failed");
    plan->current = poly_new(plan->state_words);
    plan->next = poly_new(plan->state_words);

    for (size_t i = 0; i < s; ++i) {
        if (taps[i] >= m) die("serial tap must be smaller than m");
        size_t delta = m - taps[i];
        plan->taps[i] = (serial_tap_desc){
            .assembly = {
                taps[i] / WORD_BITS,
                (unsigned)(taps[i] % WORD_BITS)
            },
            .feedback = {
                delta / WORD_BITS,
                (unsigned)(delta % WORD_BITS)
            },
            /* A shift by m is zero on the truncated m-bit state. */
            .has_feedback = taps[i] != 0
        };
    }
    if (s)
        qsort(plan->taps, s, sizeof(*plan->taps), compare_serial_tap);
    return plan;
}

void serial_plan_destroy(serial_plan *plan) {
    if (!plan) return;
    poly_free(&plan->next);
    poly_free(&plan->current);
    free(plan->taps);
    free(plan);
}

/*
 * Compute one conventional sparse feedback step.
 *
 * Each nonzero source limb is loaded once. For every sparse tap, the same
 * loaded word contributes both to V(current), accumulated directly into the
 * final output, and to U(current), accumulated into the preallocated next
 * buffer. No shifted polynomial or per-tap temporary array is materialized.
 */
static void serial_fold_step(poly_t *output, const word_t *current,
                             word_t *next, size_t active_words,
                             const serial_plan *plan) {
    memset(next, 0, active_words * sizeof(*next));

    for (size_t src = 0; src < active_words; ++src) {
        word_t value = current[src];
        if (value == 0) continue;

        for (size_t i = 0; i < plan->tap_count; ++i) {
            const serial_tap_desc *tap = &plan->taps[i];

            /* Accumulate (current << tap) mod x^m into R. */
            size_t left_dst = src + tap->assembly.word_offset;
            unsigned left_bits = tap->assembly.bit_offset;
            if (left_dst < plan->state_words) {
                output->v[left_dst] ^= value << left_bits;
                if (left_bits && left_dst + 1 < plan->state_words)
                    output->v[left_dst + 1] ^=
                        value >> (WORD_BITS - left_bits);
            }

            if (!tap->has_feedback) continue;

            /* Accumulate current >> (m - tap) into the next Y. */
            size_t right_words = tap->feedback.word_offset;
            unsigned right_bits = tap->feedback.bit_offset;
            if (src >= right_words) {
                size_t right_dst = src - right_words;
                next[right_dst] ^= value >> right_bits;
                if (right_bits && right_dst > 0)
                    next[right_dst - 1] ^=
                        value << (WORD_BITS - right_bits);
            }
        }
    }
}

void serial_reduce_into(const poly_t *input, serial_plan *plan,
                        poly_t *output) {
    if (output->n < plan->state_words)
        die("serial output buffer is too small");

    /* R <- L. Clear extra output capacity so callers may safely reuse it. */
    memset(output->v, 0, output->n * sizeof(word_t));
    size_t low_words = input->n < plan->state_words
        ? input->n : plan->state_words;
    memcpy(output->v, input->v, low_words * sizeof(word_t));
    mask_top_word(output->v, plan->state_words, plan->m);

    /* Y <- H. Both state buffers are retained by the plan across calls. */
    memset(plan->current.v, 0, plan->current.n * sizeof(word_t));
    poly_xor_right_shift(&plan->current, input, plan->m);
    mask_top_word(plan->current.v, plan->state_words, plan->m);

    size_t active_words = trim_high_zero_words(
        plan->current.v, plan->state_words);
    while (active_words) {
        serial_fold_step(output, plan->current.v, plan->next.v,
                         active_words, plan);
        mask_top_word(output->v, plan->state_words, plan->m);

        word_t *swap = plan->current.v;
        plan->current.v = plan->next.v;
        plan->next.v = swap;
        active_words = trim_high_zero_words(
            plan->current.v, active_words);
    }
}

poly_t serial_reduce_planned(const poly_t *input, serial_plan *plan) {
    poly_t result = poly_new(plan->state_words);
    serial_reduce_into(input, plan, &result);
    return result;
}

poly_t serial_reduce(const poly_t *input, const size_t *taps, size_t s,
                     size_t m) {
    serial_plan *plan = serial_plan_create(taps, s, m);
    poly_t result = serial_reduce_planned(input, plan);
    serial_plan_destroy(plan);
    return result;
}
