#!/usr/bin/env python3
"""
Round 1 computational falsification tests for ExSuwako / sparse nilpotent feedback inversion.

Tests:
1. Randomized tests over GF(2), arbitrary monic binary modulus f=x^m+q.
2. Exhaustive tests for all monic binary moduli and all inputs with deg(A)<2m,
   for 1 <= m <= 6.

Verified properties:
- H = (I+T)Y
- feedback reduction equals ordinary polynomial long division
- scheduled coefficient work equals
      W_fb = sum_r sum_k [m - 2^k d_r]_+
"""

import random


def clmul(a: int, b: int) -> int:
    """Carry-less multiplication in GF(2)[x]."""
    out = 0
    while b:
        if b & 1:
            out ^= a
        a <<= 1
        b >>= 1
    return out


def poly_mod(a: int, f: int) -> int:
    """Polynomial remainder a mod monic f over GF(2)."""
    df = f.bit_length() - 1
    while a and a.bit_length() - 1 >= df:
        a ^= f << ((a.bit_length() - 1) - df)
    return a


def positive_tap_distances(q: int, m: int) -> list[int]:
    """
    q is the lower part of f=x^m+q, deg(q)<m.
    Positive term x^e contributes feedback distance d=m-e.
    Constant term e=0 contributes to S, not to T.
    """
    return [m - e for e in range(1, m) if (q >> e) & 1]


def T_apply(y: int, ds: list[int], m: int) -> int:
    """T(y) = XOR_r (y >> d_r), truncated to m coefficients."""
    out = 0
    for d in ds:
        out ^= y >> d
    return out & ((1 << m) - 1)


def ceil_log2_ratio(m: int, delta: int) -> int:
    """Smallest D with 2^D * delta >= m."""
    D = 0
    s = delta
    while s < m:
        s <<= 1
        D += 1
    return D


def frobenius_inverse_apply(h: int, ds: list[int], m: int):
    """
    Apply (I+T)^(-1) = prod_k (I + T^(2^k)) to h over GF(2).

    Within one stage, all shifted contributions are computed from the same
    snapshot 'old'. In-place tap updates would be incorrect.
    """
    mask = (1 << m) - 1

    if not ds:
        return h & mask, 0, 0

    D = ceil_log2_ratio(m, min(ds))
    y = h & mask
    work = 0

    for k in range(D):
        old = y
        contrib = 0
        scale = 1 << k

        for d in ds:
            sh = scale * d
            if sh < m:
                contrib ^= old >> sh
                work += m - sh

        y = (old ^ contrib) & mask

    return y, D, work


def work_formula(ds: list[int], m: int) -> int:
    """W_fb = sum_r sum_k [m - 2^k d_r]_+."""
    total = 0
    for d in ds:
        sh = d
        while sh < m:
            total += m - sh
            sh <<= 1
    return total


def reduce_via_feedback(a: int, q: int, m: int):
    """
    f = x^m + q.
    A = L + x^m H.
    Solve H=(I+T)Y, then return L + S(Y),
    where qY = S(Y) + x^m T(Y).
    """
    mask = (1 << m) - 1
    L = a & mask
    H = (a >> m) & mask

    ds = positive_tap_distances(q, m)
    Y, D, work = frobenius_inverse_apply(H, ds, m)

    qY = clmul(q, Y)
    S = qY & mask
    r = (L ^ S) & mask

    return r, Y, D, work, ds


def randomized_test(seed=20260808, trials=20_000, max_m=128):
    rng = random.Random(seed)

    for _ in range(trials):
        m = rng.randint(1, max_m)
        q = rng.getrandbits(m)
        f = (1 << m) | q
        a = rng.getrandbits(2 * m)

        r_fb, Y, D, work, ds = reduce_via_feedback(a, q, m)
        H = (a >> m) & ((1 << m) - 1)

        # Property 1: H=(I+T)Y
        assert (Y ^ T_apply(Y, ds, m)) == H

        # Property 2: feedback reduction equals long division
        assert r_fb == poly_mod(a, f)

        # Property 3: scheduled work equals exact geometry formula
        assert work == work_formula(ds, m)

    print(f"PASS: {trials:,} randomized GF(2) trials; 1 <= m <= {max_m}")
    print(f"seed={seed}")


def exhaustive_small(max_m=6):
    total = 0

    for m in range(1, max_m + 1):
        count_m = 0

        for q in range(1 << m):
            f = (1 << m) | q
            ds = positive_tap_distances(q, m)

            for a in range(1 << (2 * m)):
                r_fb, Y, D, work, ds2 = reduce_via_feedback(a, q, m)
                H = (a >> m) & ((1 << m) - 1)

                assert ds2 == ds
                assert (Y ^ T_apply(Y, ds, m)) == H
                assert r_fb == poly_mod(a, f)
                assert work == work_formula(ds, m)

                count_m += 1
                total += 1

        print(f"m={m}: exhaustive PASS ({count_m:,} cases)")

    print(f"EXHAUSTIVE PASS: {total:,} total (modulus,input) pairs")


if __name__ == "__main__":
    randomized_test()
    exhaustive_small()
