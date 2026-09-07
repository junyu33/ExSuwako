#!/usr/bin/env python3
"""
Round 2 computational falsification tests for ExSuwako / sparse nilpotent feedback inversion.

This file goes beyond GF(2).

Tests:
1. Randomized + exhaustive tests over dual numbers R=F2[e]/(e^2).
2. Randomized tests over GF(4)=F2[a]/(a^2+a+1).
3. Exhaustive support-geometry checks for all nonempty constant-free supports
   with m<=18.
4. Randomized positive-characteristic radix-p tests over F3.

Important observation:
Over a general commutative characteristic-two algebra, a nonzero coefficient
a_r can satisfy a_r^(2^k)=0. Thus "stage k uses exactly all taps with
2^k d_r < m" is too strong unless one restricts the coefficient ring
(e.g. to a field/reduced setting), or interprets W_fb as scheduled work.
"""

import random
from itertools import product, combinations


# ============================================================
# Generic polynomial helpers for small finite coefficient rings
# ============================================================

def trim(p):
    p = p[:]
    while p and p[-1] == 0:
        p.pop()
    return p


def poly_mul(p, q, add, mul):
    if not p or not q:
        return []

    out = [0] * (len(p) + len(q) - 1)

    for i, a in enumerate(p):
        if a == 0:
            continue
        for j, b in enumerate(q):
            if b != 0:
                out[i + j] = add(out[i + j], mul(a, b))

    return trim(out)


def poly_mod_monic(A, f, add, mul):
    """
    Polynomial remainder by monic f over an arbitrary commutative ring.
    Monicity is enough: no coefficient inverses are needed.
    """
    A = trim(A)
    m = len(f) - 1

    while A and len(A) - 1 >= m:
        c = A[-1]
        sh = len(A) - 1 - m

        for i, fi in enumerate(f):
            if fi != 0:
                A[i + sh] = add(A[i + sh], mul(c, fi))

        A = trim(A)

    return A + [0] * (m - len(A))


# ============================================================
# 1. Dual numbers F2[e]/(e^2)
# ============================================================

DUAL_ELEMS = [0, 1, 2, 3]


def d_add(x, y):
    return x ^ y


def d_mul(x, y):
    # encode a+b*e as a | (b<<1)
    a, b = x & 1, (x >> 1) & 1
    c, d = y & 1, (y >> 1) & 1

    # (a+b e)(c+d e) = ac + (ad+bc)e, since e^2=0
    return (a & c) | (((a & d) ^ (b & c)) << 1)


def d_frob(x, k):
    for _ in range(k):
        x = d_mul(x, x)
    return x


def T_apply_ring(y, q, m, add, mul):
    out = [0] * m

    for e in range(1, m):
        a = q[e]
        if a == 0:
            continue

        d = m - e
        for i in range(m - d):
            out[i] = add(out[i], mul(a, y[i + d]))

    return out


def factor_inverse_ring(H, q, m, add, mul, frob):
    """
    Apply prod_k (I + T^(2^k)) over characteristic two.

    Returns:
      y,
      scheduled_work: counts every formal surviving geometric tap,
      effective_work: ignores taps whose Frobenius coefficient became zero.
    """
    taps = [(m - e, q[e]) for e in range(1, m) if q[e] != 0]

    if not taps:
        return H[:], 0, 0

    delta = min(d for d, _ in taps)

    D = 0
    s = delta
    while s < m:
        s <<= 1
        D += 1

    y = H[:]
    scheduled_work = 0
    effective_work = 0

    for k in range(D):
        old = y[:]
        contrib = [0] * m
        scale = 1 << k

        for d, a in taps:
            sh = scale * d

            if sh >= m:
                continue

            scheduled_work += m - sh
            ak = frob(a, k)

            if ak == 0:
                continue

            effective_work += m - sh

            for i in range(m - sh):
                contrib[i] = add(contrib[i], mul(ak, old[i + sh]))

        y = [add(u, v) for u, v in zip(old, contrib)]

    return y, scheduled_work, effective_work


def support_work_formula(q, m):
    total = 0

    for e in range(1, m):
        if q[e] == 0:
            continue

        d = m - e
        sh = d

        while sh < m:
            total += m - sh
            sh <<= 1

    return total


def reduce_feedback_ring(A, q, m, add, mul, frob):
    L = A[:m]
    H = A[m:2 * m]

    Y, scheduled, effective = factor_inverse_ring(H, q, m, add, mul, frob)

    qY = poly_mul(q, Y, add, mul) + [0] * (2 * m)
    S = qY[:m]
    r = [add(L[i], S[i]) for i in range(m)]

    return r, Y, scheduled, effective


def randomized_dual_test(seed=20260808, trials=20_000, max_m=24):
    rng = random.Random(seed)
    vanish_cases = 0

    for _ in range(trials):
        m = rng.randint(1, max_m)

        q = [rng.choice(DUAL_ELEMS) for _ in range(m)]
        f = q + [1]
        A = [rng.choice(DUAL_ELEMS) for _ in range(2 * m)]

        r, Y, scheduled, effective = reduce_feedback_ring(
            A, q, m, d_add, d_mul, d_frob
        )

        H = A[m:2 * m]
        TY = T_apply_ring(Y, q, m, d_add, d_mul)

        assert [d_add(Y[i], TY[i]) for i in range(m)] == H
        assert r == poly_mod_monic(A, f, d_add, d_mul)
        assert scheduled == support_work_formula(q, m)

        if effective < scheduled:
            vanish_cases += 1

    print(
        f"PASS: {trials:,} randomized tests over F2[e]/(e^2), m<={max_m}"
    )
    print(
        f"Frobenius killed at least one scheduled nonzero tap in "
        f"{vanish_cases:,} cases."
    )


def exhaustive_dual(max_m=3):
    total = 0

    for m in range(1, max_m + 1):
        count_m = 0

        for q_tuple in product(DUAL_ELEMS, repeat=m):
            q = list(q_tuple)
            f = q + [1]

            for A_tuple in product(DUAL_ELEMS, repeat=2 * m):
                A = list(A_tuple)

                r, Y, scheduled, effective = reduce_feedback_ring(
                    A, q, m, d_add, d_mul, d_frob
                )

                H = A[m:2 * m]
                TY = T_apply_ring(Y, q, m, d_add, d_mul)

                assert [d_add(Y[i], TY[i]) for i in range(m)] == H
                assert r == poly_mod_monic(A, f, d_add, d_mul)
                assert scheduled == support_work_formula(q, m)

                count_m += 1
                total += 1

        print(f"dual numbers: m={m}, exhaustive PASS ({count_m:,} cases)")

    print(f"DUAL EXHAUSTIVE PASS: {total:,} total cases")


# ============================================================
# 2. GF(4) = F2[a]/(a^2+a+1)
# ============================================================

def f4_add(x, y):
    return x ^ y


def f4_mul(x, y):
    p = 0

    for i in range(2):
        if (y >> i) & 1:
            p ^= x << i

    # reduce by a^2+a+1 = binary 111
    if p & 0b1000:
        p ^= 0b111 << 1
    if p & 0b0100:
        p ^= 0b111

    return p & 0b11


def f4_frob(x, k):
    for _ in range(k):
        x = f4_mul(x, x)
    return x


def serial_inverse_char2(H, q, m, add, mul):
    """
    Independent finite geometric-series inverse:
      (I+T)^-1 H = H + TH + T^2H + ...
    Since T^m=0, m terms suffice.
    """
    out = H[:]
    term = H[:]

    for _ in range(1, m):
        term = T_apply_ring(term, q, m, add, mul)
        out = [add(u, v) for u, v in zip(out, term)]

    return out


def randomized_gf4_test(seed=20260808 ^ 0xF4, trials=20_000, max_m=32):
    rng = random.Random(seed)

    for _ in range(trials):
        m = rng.randint(1, max_m)

        q = [rng.randrange(4) for _ in range(m)]
        f = q + [1]
        A = [rng.randrange(4) for _ in range(2 * m)]

        r, Y, scheduled, effective = reduce_feedback_ring(
            A, q, m, f4_add, f4_mul, f4_frob
        )

        H = A[m:2 * m]

        # Independent inverse construction
        Y_serial = serial_inverse_char2(H, q, m, f4_add, f4_mul)
        assert Y == Y_serial

        # Direct equation
        TY = T_apply_ring(Y, q, m, f4_add, f4_mul)
        assert [f4_add(Y[i], TY[i]) for i in range(m)] == H

        # Independent polynomial division
        assert r == poly_mod_monic(A, f, f4_add, f4_mul)

        # In a field, Frobenius never kills a nonzero coefficient.
        assert scheduled == effective
        assert scheduled == support_work_formula(q, m)

    print(f"PASS: {trials:,} randomized GF(4) tests, m<={max_m}")
    print(
        "Factorized inverse = serial geometric inverse = direct monic reduction."
    )


# ============================================================
# 3. Exhaustive support-geometry checks
# ============================================================

def W_from_distances(m, ds):
    total = 0

    for d in ds:
        sh = d
        while sh < m:
            total += m - sh
            sh <<= 1

    return total


def coarse_stage_bound(m, ds):
    total = 0

    for d in ds:
        stages = 0
        sh = d

        while sh < m:
            sh <<= 1
            stages += 1

        total += m * stages

    return total


def exhaustive_support_geometry(max_m=18):
    checked = 0

    for m in range(2, max_m + 1):
        distances = list(range(1, m))

        for h in range(1, m):
            best_W = -1
            best_ds = None

            for ds in combinations(distances, h):
                w = W_from_distances(m, ds)
                coarse = coarse_stage_bound(m, ds)

                assert w < coarse

                if w > best_W:
                    best_W = w
                    best_ds = ds

                checked += 1

            # For fixed (m,h), closest distinct taps maximize W.
            expected = tuple(range(1, h + 1))
            assert best_ds == expected

    print(
        "PASS: exhausted all nonempty constant-free supports "
        f"for 2 <= m <= {max_m}"
    )
    print(f"Checked {checked:,} (m,support) cases.")
    print(
        "For every fixed (m,h), maximum W occurred at distances {1,...,h}."
    )
    print(
        "Exact W was always strictly below "
        "m * sum_r ceil(log2(m/d_r))."
    )


# ============================================================
# 4. Positive characteristic: F3 radix-p identity
# ============================================================

P = 3


def f3_add(x, y):
    return (x + y) % P


def f3_mul(x, y):
    return (x * y) % P


def T3(y, q, m):
    out = [0] * m

    for e in range(1, m):
        a = q[e] % P
        if a == 0:
            continue

        d = m - e

        for i in range(m - d):
            out[i] = (out[i] + a * y[i + d]) % P

    return out


def T3_power(y, q, m, n):
    z = y[:]

    for _ in range(n):
        z = T3(z, q, m)

    return z


def serial_geom3(H, q, m):
    """
    (I+T)^-1 = I - T + T^2 - T^3 + ...
    """
    out = [0] * m
    term = H[:]
    sign = 1

    for _ in range(m):
        for i in range(m):
            out[i] = (out[i] + sign * term[i]) % P

        term = T3(term, q, m)
        sign *= -1

    return [x % P for x in out]


def radix3_inverse(H, q, m):
    """
    Product factors:
      (I+T)^-1
        = prod_k (I - T^(3^k) + T^(2*3^k))
    until nilpotence kills the remaining powers.
    """
    taps = [(m - e, q[e] % P) for e in range(1, m) if q[e] % P]

    if not taps:
        return H[:]

    delta = min(d for d, _ in taps)
    y = H[:]
    scale = 1

    while scale * delta < m:
        old = y[:]

        t1 = T3_power(old, q, m, scale)
        t2 = T3_power(old, q, m, 2 * scale)

        y = [
            (old[i] - t1[i] + t2[i]) % P
            for i in range(m)
        ]

        scale *= 3

    return y


def poly_mul_f3(p, q):
    if not p or not q:
        return []

    out = [0] * (len(p) + len(q) - 1)

    for i, a in enumerate(p):
        for j, b in enumerate(q):
            out[i + j] = (out[i + j] + a * b) % P

    return trim(out)


def poly_mod_f3(A, f):
    A = trim(A)
    m = len(f) - 1

    while A and len(A) - 1 >= m:
        c = A[-1] % P
        sh = len(A) - 1 - m

        for i, fi in enumerate(f):
            A[i + sh] = (A[i + sh] - c * fi) % P

        A = trim(A)

    return A + [0] * (m - len(A))


def randomized_f3_test(seed=20260811, trials=10_000, max_m=12):
    rng = random.Random(seed)

    for _ in range(trials):
        m = rng.randint(1, max_m)

        q = [rng.randrange(P) for _ in range(m)]
        f = q + [1]
        A = [rng.randrange(P) for _ in range(2 * m)]

        L = A[:m]
        H = A[m:2 * m]

        Y = radix3_inverse(H, q, m)

        # Product/radix factorization = finite geometric inverse
        assert Y == serial_geom3(H, q, m)

        # H=(I+T)Y
        TY = T3(Y, q, m)
        assert [(Y[i] + TY[i]) % P for i in range(m)] == H

        # Over odd characteristic, remainder is L - S(Y)
        qY = poly_mul_f3(q, Y) + [0] * (2 * m)
        r = [(L[i] - qY[i]) % P for i in range(m)]

        assert r == poly_mod_f3(A, f)

    print(f"PASS: {trials:,} randomized tests over F3, m<={max_m}")
    print(
        "Positive-characteristic radix-p inverse identity and reduction signs "
        "are consistent."
    )


if __name__ == "__main__":
    print("=== Dual numbers: randomized ===")
    randomized_dual_test()
    print()

    print("=== Dual numbers: exhaustive ===")
    exhaustive_dual()
    print()

    print("=== GF(4): randomized ===")
    randomized_gf4_test()
    print()

    print("=== Support geometry: exhaustive ===")
    exhaustive_support_geometry()
    print()

    print("=== F3: positive-characteristic radix-p test ===")
    randomized_f3_test()
