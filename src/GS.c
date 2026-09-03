#include "GS.h"
#include "sparse_shift.h"

/*
 * Generalized Suwako sparse reduction over GF(2).
 *
 * For a modulus f = x^m + q(x), split the product input as
 *
 *     C = L + x^m H.
 *
 * A conventional sparse fold repeatedly applies the high-part feedback
 *
 *     U(Y) = sum_{t != 0} Y >> (m - t)
 *
 * and accumulates low-part contributions
 *
 *     V(Y) = sum_t (Y << t) mod x^m.
 *
 * This implementation computes the closed feedback state
 *
 *     X = H + U(H) + U^2(H) + ...
 *
 * by the doubling identity over GF(2):
 *
 *     I + U + U^2 + ... = (I + U)(I + U^2)(I + U^4)...
 *
 * Since every U is a sum of right shifts, U^(2^k) is obtained by doubling
 * the shift distances. The plan stores those per-stage shifts; reduce_into()
 * reuses one state buffer and then returns L + V(X).
 */

typedef struct {
    size_t offset;
    size_t count;
    size_t aligned_count;
    size_t affected_words;
} round_desc;

struct gs_plan {
    size_t m;
    size_t state_words;

    /*
     * feedback_shifts is a flat array. Each round_desc selects one contiguous
     * slice containing the shifts for one doubling stage U^(2^k).
     */
    size_t round_count;
    round_desc *rounds;
    shift_desc *feedback_shifts;

    /*
     * assembly_shifts contains the original taps t for V(X). Unlike feedback
     * shifts, these are applied once after the closure state has been computed.
     */
    size_t assembly_count;
    size_t assembly_aligned_count;
    shift_desc *assembly_shifts;

    /*
     * One reusable m-bit state plus one sentinel word. The sentinel lets the
     * right-shift gather path read state[src + 1] without a boundary branch.
     */
    poly_t state;
};

static size_t aligned_shift_count(const shift_desc *shifts, size_t count) {
    size_t aligned = 0;
    for (size_t i = 0; i < count; ++i)
        aligned += shifts[i].bit_offset == 0;
    return aligned;
}

/*
 * Initialize state <- H = input >> m, truncated to m bits.
 *
 * This is assignment, not XOR accumulation. It avoids clearing the whole state
 * before calling the generic poly_xor_right_shift helper.
 */
static void extract_high_part(word_t *state, size_t state_words,
                              const poly_t *input, size_t m) {
    sparse_assign_right_shift(state, state_words, input, m);
    state[state_words] = 0;
}

/* Accumulate a set of word-aligned right shifts into one destination word. */
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

/*
 * Accumulate non-word-aligned right shifts into one destination word.
 *
 * Shifts are sorted by word_offset, so all shifts reading the same adjacent
 * source pair reuse the same lower/upper loads.
 */
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

/*
 * Apply one doubling stage in place:
 *
 *     state <- state + U^(2^k)(state).
 *
 * The loop writes destination words from low to high. Each right shift reads
 * the same or a higher source word, so source words needed by later
 * destinations have not been overwritten yet. This is why the stage can be
 * in-place without a second full state buffer.
 */
static void feedback_stage_in_place(
    word_t *state,
    size_t state_words,
    const shift_desc *shifts,
    size_t shift_count,
    size_t aligned_count,
    size_t affected_words)
{
    if (aligned_count == 0) {
        for (size_t dst = 0; dst < affected_words; ++dst)
            state[dst] = feedback_unaligned_accumulate(
                state, state_words, dst, shifts, shift_count, state[dst]);
        return;
    }

    if (aligned_count == shift_count) {
        for (size_t dst = 0; dst < affected_words; ++dst)
            state[dst] = feedback_aligned_accumulate(
                state, state_words, dst, shifts, shift_count, state[dst]);
        return;
    }

    for (size_t dst = 0; dst < affected_words; ++dst) {
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

/* Accumulate word-aligned low-part assembly shifts into one output word. */
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

/*
 * Accumulate non-word-aligned low-part assembly shifts into one output word.
 *
 * Assembly is a left shift of the closed state, truncated mod x^m. From a
 * destination-word view this gathers from state[src] and state[src - 1].
 */
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

/*
 * Compute output <- L + V(state), where state is the closed feedback X.
 *
 * The input low words provide L directly; the assembly shifts add q(x) * X
 * modulo x^m. The final mask clears padding bits above degree m - 1.
 */
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

    /*
     * Build the feedback schedule. At stage factor = 2^k, tap t contributes
     * a right shift by factor * (m - t), as long as that shift can still affect
     * the m-bit state.
     */
    for (size_t factor = 1;; factor <<= 1) {
        size_t shift_count = 0;
        size_t min_shift = m;
        for (size_t i = 0; i < s; ++i) {
            if (taps[i] == 0) continue;
            size_t delta = m - taps[i];
            if (factor > (m - 1) / delta) continue;
            size_t shift = factor * delta;
            if (shift < min_shift) min_shift = shift;
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
            feedback_count, shift_count, aligned_count,
            poly_words_for_bits(m - min_shift)
        };
        memcpy(plan->feedback_shifts + feedback_count,
               round_shifts, shift_count * sizeof(*round_shifts));
        feedback_count += shift_count;
        if (factor > SIZE_MAX / 2) break;
    }
    free(round_shifts);

    /*
     * Build the final assembly schedule from the original tap positions t.
     * Taps include t = 0 when the modulus has a constant term, and that shift
     * is valid for assembly even though it has no high-part feedback.
     */
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

size_t gs_plan_feedback_stage_count(const gs_plan *plan) {
    return plan ? plan->round_count : 0;
}

size_t gs_plan_feedback_active_taps(const gs_plan *plan, size_t stage) {
    if (!plan || stage >= plan->round_count)
        die("GS feedback stage index is out of range");
    return plan->rounds[stage].count;
}

size_t gs_plan_feedback_active_tap_sum(const gs_plan *plan) {
    if (!plan) return 0;
    size_t total = 0;
    for (size_t stage = 0; stage < plan->round_count; ++stage)
        total += plan->rounds[stage].count;
    return total;
}

/* Sum the nonzero coefficient destinations scheduled for every shift. */
size_t gs_plan_feedback_scheduled_coefficient_work(const gs_plan *plan) {
    if (!plan) return 0;
    size_t total = 0;
    for (size_t stage = 0; stage < plan->round_count; ++stage) {
        const round_desc *round = &plan->rounds[stage];
        for (size_t j = 0; j < round->count; ++j) {
            const shift_desc *desc =
                &plan->feedback_shifts[round->offset + j];
            size_t shift = desc->word_offset * WORD_BITS + desc->bit_offset;
            total += plan->m - shift;
        }
    }
    return total;
}

void gs_reduce_into(const poly_t *input, gs_plan *plan, poly_t *output) {
    if (output->n < plan->state_words)
        die("GS output buffer is too small");

    extract_high_part(
        plan->state.v, plan->state_words, input, plan->m);

    /* Compute X = product_k (I + U^(2^k)) H. */
    for (size_t i = 0; i < plan->round_count; ++i) {
        const round_desc *round = &plan->rounds[i];
        feedback_stage_in_place(
            plan->state.v,
            plan->state_words,
            plan->feedback_shifts + round->offset,
            round->count,
            round->aligned_count,
            round->affected_words);
    }

    /* Return L + V(X). */
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
