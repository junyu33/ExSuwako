#include "naive.h"

void naive_reduce_into(const poly_t *input, const poly_t *modulus,
                       size_t m, poly_t *output) {
    if (output->n < input->n) die("naive output buffer is too small");
    memset(output->v, 0, output->n * sizeof(word_t));
    memcpy(output->v, input->v, input->n * sizeof(word_t));
    while (poly_degree(output) >= (long)m) {
        size_t shift = (size_t)(poly_degree(output) - (long)m);
        poly_xor_left_shift(output, modulus, shift);
    }
}

poly_t naive_reduce(const poly_t *input, const poly_t *modulus, size_t m) {
    poly_t r = poly_new(input->n);
    naive_reduce_into(input, modulus, m, &r);
    return r;
}
