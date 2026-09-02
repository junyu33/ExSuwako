#include "naive.h"

void naive_reduce_into(const poly_t *input, const poly_t *modulus,
                       size_t m, poly_t *output) {
    if (output->n < input->n) die("naive output buffer is too small");
    memcpy(output->v, input->v, input->n * sizeof(word_t));
    if (output->n > input->n)
        memset(output->v + input->n, 0,
               (output->n - input->n) * sizeof(word_t));
    for (;;) {
        long degree = poly_degree(output);
        if (degree < (long)m) break;
        size_t shift = (size_t)(degree - (long)m);
        poly_xor_left_shift(output, modulus, shift);
    }
}

poly_t naive_reduce(const poly_t *input, const poly_t *modulus, size_t m) {
    poly_t r = poly_new(input->n);
    naive_reduce_into(input, modulus, m, &r);
    return r;
}
