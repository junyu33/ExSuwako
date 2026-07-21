#include "naive.h"

poly_t naive_reduce(const poly_t *input, const poly_t *modulus, size_t m) {
    poly_t r = poly_new(input->n);
    memcpy(r.v, input->v, input->n * sizeof(word_t));
    while (poly_degree(&r) >= (long)m) {
        size_t shift = (size_t)(poly_degree(&r) - (long)m);
        poly_xor_left_shift(&r, modulus, shift);
    }
    return r;
}
