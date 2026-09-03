#include "dense.h"
#include "sparse_shift.h"

/*
 * Fixed-modulus dense linear reduction over GF(2).
 *
 * For A = L + x^m H, setup materializes the m-by-m binary matrix M_g for
 * H -> x^m H mod g.  The identity map on L is implicit.  Rows are contiguous,
 * so reduction computes every output bit as one constant-trip-count parity.
 */

struct dense_plan {
    size_t m;
    size_t row_words;
    size_t matrix_words;
    word_t *rows;
    poly_t high;
};

int dense_matrix_bytes(size_t m, size_t *bytes) {
    if (!bytes || m == 0) return 0;
    size_t row_words = poly_words_for_bits(m);
    if (row_words != 0 && m > SIZE_MAX / row_words) return 0;
    size_t matrix_words = m * row_words;
    if (matrix_words > SIZE_MAX / sizeof(word_t)) return 0;
    *bytes = matrix_words * sizeof(word_t);
    return 1;
}

static unsigned word_parity(word_t value) {
    for (unsigned shift = WORD_BITS / 2; shift != 0; shift /= 2)
        value ^= value >> shift;
    return (unsigned)(value & 1u);
}

static void mask_top_word(word_t *words, size_t count, size_t m) {
    unsigned top_bits = (unsigned)(m % WORD_BITS);
    if (top_bits != 0)
        words[count - 1] &= ((word_t)1 << top_bits) - 1;
}

static void multiply_by_x_mod_g(word_t *column, const word_t *q,
                                size_t words, size_t m) {
    unsigned top_offset = (unsigned)((m - 1) % WORD_BITS);
    word_t reduce = (column[(m - 1) / WORD_BITS] >> top_offset) & 1u;
    word_t carry = 0;
    for (size_t i = 0; i < words; ++i) {
        word_t next_carry = column[i] >> (WORD_BITS - 1);
        column[i] = (column[i] << 1) ^ carry;
        carry = next_carry;
    }
    mask_top_word(column, words, m);
    word_t mask = (word_t)0 - reduce;
    for (size_t i = 0; i < words; ++i)
        column[i] ^= q[i] & mask;
}

dense_plan *dense_plan_create(const poly_t *modulus, size_t m) {
    if (m == 0) die("dense modulus degree must be positive");
    if (!modulus || poly_degree(modulus) != (long)m)
        die("dense modulus must be monic of degree m");

    size_t matrix_bytes;
    if (!dense_matrix_bytes(m, &matrix_bytes))
        die("dense matrix size overflows size_t");

    dense_plan *plan = calloc(1, sizeof(*plan));
    if (!plan) die("allocation failed");
    plan->m = m;
    plan->row_words = poly_words_for_bits(m);
    plan->matrix_words = matrix_bytes / sizeof(word_t);
    plan->rows = calloc(plan->matrix_words, sizeof(*plan->rows));
    if (!plan->rows) die("allocation failed");
    plan->high = poly_new(plan->row_words);

    poly_t q = poly_new(plan->row_words);
    poly_t column = poly_new(plan->row_words);
    size_t copied = modulus->n < plan->row_words
        ? modulus->n : plan->row_words;
    memcpy(q.v, modulus->v, copied * sizeof(*q.v));
    mask_top_word(q.v, q.n, m);
    memcpy(column.v, q.v, q.n * sizeof(*q.v));

    for (size_t input_bit = 0; input_bit < m; ++input_bit) {
        size_t matrix_word = input_bit / WORD_BITS;
        word_t matrix_bit = (word_t)1 << (input_bit % WORD_BITS);
        for (size_t output_bit = 0; output_bit < m; ++output_bit) {
            if ((column.v[output_bit / WORD_BITS]
                    >> (output_bit % WORD_BITS)) & 1u) {
                plan->rows[output_bit * plan->row_words + matrix_word]
                    |= matrix_bit;
            }
        }
        multiply_by_x_mod_g(column.v, q.v, q.n, m);
    }

    poly_free(&column);
    poly_free(&q);
    return plan;
}

void dense_plan_destroy(dense_plan *plan) {
    if (!plan) return;
    poly_free(&plan->high);
    free(plan->rows);
    free(plan);
}

size_t dense_plan_storage_bytes(const dense_plan *plan) {
    if (!plan) return 0;
    return sizeof(*plan)
         + plan->matrix_words * sizeof(*plan->rows)
         + plan->high.n * sizeof(*plan->high.v);
}

void dense_reduce_into(const poly_t *input, dense_plan *plan,
                       poly_t *output) {
    if (output->n < plan->row_words)
        die("dense output buffer is too small");

    sparse_assign_right_shift(
        plan->high.v, plan->high.n, input, plan->m);
    mask_top_word(plan->high.v, plan->high.n, plan->m);

    for (size_t i = 0; i < plan->row_words; ++i)
        output->v[i] = i < input->n ? input->v[i] : 0;
    if (output->n > plan->row_words)
        memset(output->v + plan->row_words, 0,
               (output->n - plan->row_words) * sizeof(*output->v));

    for (size_t output_bit = 0; output_bit < plan->m; ++output_bit) {
        const word_t *row = plan->rows + output_bit * plan->row_words;
        word_t products = 0;
        for (size_t i = 0; i < plan->row_words; ++i)
            products ^= row[i] & plan->high.v[i];
        output->v[output_bit / WORD_BITS] ^=
            (word_t)word_parity(products) << (output_bit % WORD_BITS);
    }
    mask_top_word(output->v, plan->row_words, plan->m);
}

poly_t dense_reduce(const poly_t *input, const poly_t *modulus, size_t m) {
    dense_plan *plan = dense_plan_create(modulus, m);
    poly_t result = poly_new(plan->row_words);
    dense_reduce_into(input, plan, &result);
    dense_plan_destroy(plan);
    return result;
}
