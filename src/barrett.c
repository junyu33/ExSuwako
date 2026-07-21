#include "barrett.h"

struct barrett_plan {
    const poly_t *modulus;
    const poly_t *mu;
    size_t m;
    size_t output_words;
    poly_t q1;
    poly_t q2;
    poly_t q3;
    poly_t product;
    poly_t remainder;
};

static size_t used_words(const poly_t *p) {
    size_t n = p->n;
    while (n && p->v[n - 1] == 0) --n;
    return n;
}

poly_t barrett_setup(const poly_t *modulus, size_t m) {
    poly_t numerator = poly_new(poly_words_for_bits(2 * m + 1));
    poly_set_bit(&numerator, 2 * m);
    poly_t quotient = poly_new(numerator.n);
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
    plan->q1 = poly_new(poly_words_for_bits(m + 1));
    plan->q2 = poly_new(plan->q1.n + used_words(mu));
    plan->q3 = poly_new(poly_words_for_bits(m + 1));
    plan->product = poly_new(plan->q3.n + used_words(modulus));
    plan->remainder = poly_new(poly_words_for_bits(m + 1));
    return plan;
}

void barrett_plan_destroy(barrett_plan *plan) {
    if (!plan) return;
    poly_free(&plan->q1);
    poly_free(&plan->q2);
    poly_free(&plan->q3);
    poly_free(&plan->product);
    poly_free(&plan->remainder);
    free(plan);
}

void barrett_reduce_into(const poly_t *c, barrett_plan *plan, poly_t *output) {
    if (output->n < plan->output_words)
        die("Barrett output buffer is too small");

    memset(plan->q1.v, 0, plan->q1.n * sizeof(word_t));
    poly_xor_right_shift(&plan->q1, c, plan->m - 1);
    if (poly_mul_gf2x(&plan->q2, &plan->q1, plan->mu) != 0)
        die("gf2x q1*mu failed");

    memset(plan->q3.v, 0, plan->q3.n * sizeof(word_t));
    poly_xor_right_shift(&plan->q3, &plan->q2, plan->m + 1);
    if (poly_mul_gf2x(&plan->product, &plan->q3, plan->modulus) != 0)
        die("gf2x q3*modulus failed");

    memset(plan->remainder.v, 0, plan->remainder.n * sizeof(word_t));
    for (size_t i = 0; i < plan->remainder.n; ++i) {
        word_t x = i < c->n ? c->v[i] : 0;
        word_t y = i < plan->product.n ? plan->product.v[i] : 0;
        plan->remainder.v[i] = x ^ y;
    }
    unsigned keep_bits = (unsigned)(plan->m % WORD_BITS) + 1;
    plan->remainder.v[plan->remainder.n - 1] &= keep_bits == WORD_BITS
        ? (word_t)~(word_t)0
        : ((word_t)1 << keep_bits) - 1;
    while (poly_degree(&plan->remainder) >= (long)plan->m) {
        size_t shift = (size_t)(poly_degree(&plan->remainder) - (long)plan->m);
        poly_xor_left_shift(&plan->remainder, plan->modulus, shift);
    }

    memcpy(output->v, plan->remainder.v,
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
