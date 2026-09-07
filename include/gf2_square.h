#ifndef EXSUWAKO_GF2_SQUARE_H
#define EXSUWAKO_GF2_SQUARE_H

#include "poly.h"

/* Expand an m-bit polynomial to its ordinary degree-below-2m square. */
void gf2_square_to_2m(const poly_t *input, size_t m, poly_t *output);

#endif
