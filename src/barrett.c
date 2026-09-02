#include "barrett.h"
#include "sparse_shift.h"

/*
 * Barrett is the multiplication-based baseline. Its two products call
 * gf2x_mul() through poly_mul_gf2x() in poly.h.
 *
 * The library path is selected by the Makefile link line:
 *
 *     -L$(GF2X_PREFIX)/lib -lgf2x
 *
 * With the current default GF2X_PREFIX=/usr/local, this machine has no
 * /usr/local/lib/libgf2x.a; the linker trace resolves -lgf2x to
 * /usr/lib/libgf2x.so. To force a static libgf2x.a baseline, point
 * GF2X_PREFIX at an installation containing $(GF2X_PREFIX)/lib/libgf2x.a
 * and adjust the link flags accordingly.
 */

struct barrett_plan {
    const poly_t *modulus;
    const poly_t *mu;
    size_t m;
    size_t output_words;

    /*
     * Lifetime-reused workspaces:
     *
     *   small: q1 -> q3 -> corrected remainder
     *   large: q1 * mu -> q3 * modulus
     *
     * The two gf2x calls still have disjoint input and output buffers.
     */
    poly_t small;
    poly_t large;
};

static size_t used_words(const poly_t *p) {
    size_t n = p->n;
    while (n && p->v[n - 1] == 0) --n;
    return n;
}

poly_t barrett_setup(const poly_t *modulus, size_t m) {
    poly_t numerator = poly_new(poly_words_for_bits(2 * m + 1));
    poly_set_bit(&numerator, 2 * m);
    /* deg(floor(x^(2m) / modulus)) = m, so m + 1 bits suffice. */
    poly_t quotient = poly_new(poly_words_for_bits(m + 1));
    poly_t remainder = poly_new(numerator.n);
    poly_divmod(&numerator, modulus, &quotient, &remainder);
    poly_free(&numerator);
    poly_free(&remainder);
    return quotient;
}

barrett_plan *barrett_plan_create(const poly_t *modulus,
                                  const poly_t *mu, size_t m) {
    barrett_plan *plan = calloc(1, sizeof(*plan));
    if (!plan) die("allocation failed");

    plan->modulus = modulus;
    plan->mu = mu;
    plan->m = m;
    plan->output_words = poly_words_for_bits(m);
    size_t small_words = poly_words_for_bits(m + 1);
    size_t mu_words = used_words(mu);
    size_t modulus_words = used_words(modulus);
    size_t rhs_words = mu_words > modulus_words ? mu_words : modulus_words;
    plan->small = poly_new(small_words);
    plan->large = poly_new(small_words + rhs_words);
    return plan;
}

void barrett_plan_destroy(barrett_plan *plan) {
    if (!plan) return;
    poly_free(&plan->small);
    poly_free(&plan->large);
    free(plan);
}

void barrett_reduce_into(const poly_t *c, barrett_plan *plan, poly_t *output) {
    if (output->n < plan->output_words)
        die("Barrett output buffer is too small");

    /* small = q1, large = q1 * mu. */
    sparse_assign_right_shift(
        plan->small.v, plan->small.n, c, plan->m - 1);
    if (poly_mul_gf2x(&plan->large, &plan->small, plan->mu) != 0)
        die("gf2x q1*mu failed");

    /* Reuse small for q3, then overwrite large with q3 * modulus. */
    sparse_assign_right_shift(
        plan->small.v, plan->small.n, &plan->large, plan->m + 1);
    if (poly_mul_gf2x(&plan->large, &plan->small, plan->modulus) != 0)
        die("gf2x q3*modulus failed");

    /* q3 is dead; reuse small for the corrected remainder. */
    for (size_t i = 0; i < plan->small.n; ++i) {
        word_t x = i < c->n ? c->v[i] : 0;
        word_t y = i < plan->large.n ? plan->large.v[i] : 0;
        plan->small.v[i] = x ^ y;
    }
    unsigned keep_bits = (unsigned)(plan->m % WORD_BITS) + 1;
    plan->small.v[plan->small.n - 1] &= keep_bits == WORD_BITS
        ? (word_t)~(word_t)0
        : ((word_t)1 << keep_bits) - 1;
    size_t top_word = plan->m / WORD_BITS;
    unsigned top_bit = (unsigned)(plan->m % WORD_BITS);
    if ((plan->small.v[top_word] >> top_bit) & 1u)
        poly_xor_left_shift(&plan->small, plan->modulus, 0);

    memcpy(output->v, plan->small.v,
           plan->output_words * sizeof(word_t));
    unsigned top_bits = (unsigned)(plan->m % WORD_BITS);
    if (top_bits != 0)
        output->v[plan->output_words - 1] &= ((word_t)1 << top_bits) - 1;
}

poly_t barrett_reduce(const poly_t *c, const poly_t *modulus,
                      const poly_t *mu, size_t m) {
    barrett_plan *plan = barrett_plan_create(modulus, mu, m);
    poly_t result = poly_new(plan->output_words);
    barrett_reduce_into(c, plan, &result);
    barrett_plan_destroy(plan);
    return result;
}
