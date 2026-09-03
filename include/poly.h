#ifndef EXSUWAKO_POLY_H
#define EXSUWAKO_POLY_H

#include <gf2x.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned long word_t;
enum { WORD_BITS = sizeof(word_t) * 8 };

typedef struct {
    word_t *v;
    size_t n;
} poly_t;

static inline void die(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(EXIT_FAILURE);
}

static inline size_t poly_words_for_bits(size_t bits) {
    return (bits + WORD_BITS - 1) / WORD_BITS;
}

static inline poly_t poly_new(size_t n) {
    poly_t p = {calloc(n ? n : 1, sizeof(word_t)), n};
    if (!p.v) die("allocation failed");
    return p;
}

static inline void poly_free(poly_t *p) {
    free(p->v);
    p->v = NULL;
    p->n = 0;
}

static inline long poly_degree(const poly_t *p) {
    size_t i = p->n;
    while (i && p->v[i - 1] == 0) --i;
    if (!i) return -1;
    word_t x = p->v[i - 1];
    int top = WORD_BITS - 1;
    while (((x >> top) & 1u) == 0) --top;
    return (long)((i - 1) * WORD_BITS + (size_t)top);
}

static inline void poly_set_bit(poly_t *p, size_t bit) {
    if (bit / WORD_BITS >= p->n) die("polynomial bit capacity exceeded");
    p->v[bit / WORD_BITS] |= (word_t)1 << (bit % WORD_BITS);
}

static inline void poly_xor_left_shift(poly_t *dst, const poly_t *src,
                                       size_t shift) {
    size_t whole = shift / WORD_BITS;
    unsigned bits = (unsigned)(shift % WORD_BITS);
    for (size_t i = 0; i < src->n && i + whole < dst->n; ++i) {
        dst->v[i + whole] ^= src->v[i] << bits;
        if (bits && i + whole + 1 < dst->n)
            dst->v[i + whole + 1] ^= src->v[i] >> (WORD_BITS - bits);
    }
}

static inline void poly_xor_right_shift(poly_t *dst, const poly_t *src,
                                        size_t shift) {
    size_t whole = shift / WORD_BITS;
    unsigned bits = (unsigned)(shift % WORD_BITS);
    for (size_t i = whole; i < src->n; ++i) {
        size_t j = i - whole;
        if (j >= dst->n) break;
        dst->v[j] ^= src->v[i] >> bits;
        if (bits && i + 1 < src->n)
            dst->v[j] ^= src->v[i + 1] << (WORD_BITS - bits);
    }
}

static inline poly_t poly_shift_right(const poly_t *src, size_t shift) {
    poly_t dst = poly_new(src->n);
    poly_xor_right_shift(&dst, src, shift);
    return dst;
}

static inline poly_t poly_from_exponents(size_t bits,
                                         const size_t *exponents,
                                         size_t count) {
    poly_t p = poly_new(poly_words_for_bits(bits));
    for (size_t i = 0; i < count; ++i) poly_set_bit(&p, exponents[i]);
    return p;
}

static inline int poly_mul_gf2x(poly_t *out, const poly_t *a,
                                const poly_t *b) {
    size_t an = a->n, bn = b->n;
    while (an && a->v[an - 1] == 0) --an;
    while (bn && b->v[bn - 1] == 0) --bn;
    memset(out->v, 0, out->n * sizeof(word_t));
    if (!an || !bn) return 0;
    if (out->n < an + bn) return -2;
    return gf2x_mul(out->v, a->v, (unsigned long)an,
                    b->v, (unsigned long)bn);
}

static inline void poly_divmod(const poly_t *numerator,
                               const poly_t *denominator,
                               poly_t *quotient, poly_t *remainder) {
    memcpy(remainder->v, numerator->v, remainder->n * sizeof(word_t));
    memset(quotient->v, 0, quotient->n * sizeof(word_t));
    long den_degree = poly_degree(denominator);
    if (den_degree < 0) die("division by zero polynomial");
    for (;;) {
        long rem_degree = poly_degree(remainder);
        if (rem_degree < den_degree) break;
        size_t shift = (size_t)(rem_degree - den_degree);
        poly_set_bit(quotient, shift);
        poly_xor_left_shift(remainder, denominator, shift);
    }
}

#endif
