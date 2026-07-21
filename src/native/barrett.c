#include "barrett.h"

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

poly_t barrett_reduce(const poly_t *c, const poly_t *modulus,
                      const poly_t *mu, size_t m) {
    poly_t q1 = poly_shift_right(c, m - 1);
    poly_t q2 = poly_new(q1.n + mu->n);
    if (poly_mul_gf2x(&q2, &q1, mu) != 0) die("gf2x q1*mu failed");
    poly_t q3 = poly_shift_right(&q2, m + 1);
    poly_t product = poly_new(q3.n + modulus->n);
    if (poly_mul_gf2x(&product, &q3, modulus) != 0)
        die("gf2x q3*modulus failed");

    poly_t r = poly_new(c->n > product.n ? c->n : product.n);
    for (size_t i = 0; i < r.n; ++i) {
        word_t x = i < c->n ? c->v[i] : 0;
        word_t y = i < product.n ? product.v[i] : 0;
        r.v[i] = x ^ y;
    }
    size_t keep = poly_words_for_bits(m + 1);
    for (size_t i = keep; i < r.n; ++i) r.v[i] = 0;
    unsigned keep_bits = (unsigned)(m % WORD_BITS) + 1;
    r.v[keep - 1] &= keep_bits == WORD_BITS
        ? (word_t)~(word_t)0
        : ((word_t)1 << keep_bits) - 1;
    while (poly_degree(&r) >= (long)m) {
        size_t shift = (size_t)(poly_degree(&r) - (long)m);
        poly_xor_left_shift(&r, modulus, shift);
    }
    poly_free(&q1); poly_free(&q2); poly_free(&q3); poly_free(&product);
    return r;
}
