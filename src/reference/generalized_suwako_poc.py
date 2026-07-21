"""Minimal proof of concept for generalized Suwako reduction over GF(2)[x].

Input:
    M H
    e_0 e_1 ... e_{H-1}

The exponents must satisfy:
    e_0 = M > e_1 > ... > e_{H-1} >= 0.

The script tests 10^4 random inputs whose degrees are uniformly chosen from
[M, 2M - 1].  It prints PASS if generalized Suwako always agrees with naive
polynomial long division, and FAIL otherwise.
"""

import random


def exsuwako_reduce(x, m, exponents):
    """Reduce x modulo sum(x^e for e in exponents) by generalized Suwako."""
    mask = (1 << m) - 1
    low = x & mask
    high = x >> m
    lower_exponents = exponents[1:]

    # U uses only positive lower exponents.
    positive_exponents = [t for t in lower_exponents if t > 0]
    state = high

    if positive_exponents:
        deltas = [m - t for t in positive_exponents]
        min_delta = min(deltas)
        scale = 1

        while scale * min_delta < m:
            old = state
            feedback = 0

            # Every shift in one round reads the same old state.
            for delta in deltas:
                shift = scale * delta
                if shift < m:
                    feedback ^= old >> shift

            state = old ^ feedback
            scale <<= 1

    # V(state) = (q(x) * state) mod x^m.
    folded = 0
    for t in lower_exponents:
        folded ^= (state << t) & mask

    return low ^ folded


def naive_reduce(x, m, exponents):
    """Reduce x by ordinary polynomial long division over GF(2)."""
    modulus = 0
    for e in exponents:
        modulus |= 1 << e

    while x.bit_length() - 1 >= m:
        x ^= modulus << (x.bit_length() - 1 - m)

    return x


def main():
    try:
        print("Enter M and the Hamming weight H:")
        print("  M H")
        m, h = map(int, input("> ").split())

        print(f"Enter the {h} nonzero exponents in strictly descending order:")
        print(f"  The first exponent must be M = {m}.")
        print("  Example: 128 8 4 3 0 represents x^128 + x^8 + x^4 + x^3 + 1.")
        exponents = list(map(int, input("> ").split()))

        if m < 1 or h < 1:
            raise ValueError
        if len(exponents) != h:
            raise ValueError
        if exponents[0] != m:
            raise ValueError
        if any(exponents[i] <= exponents[i + 1] for i in range(h - 1)):
            raise ValueError
        if exponents[-1] < 0:
            raise ValueError

    except (ValueError, IndexError):
        print("INVALID INPUT")
        return

    # Reproducibility seed: the date the ExSuwako PoC was first shared
    # with Paul Zimmermann and Richard Brent.
    rng = random.Random(20260719)

    print(
        f"Testing 10,000 random inputs with degrees in [{m}, {2 * m - 1}]..."
    )

    for _ in range(10_000):
        degree = rng.randint(m, 2 * m - 1)
        x = (1 << degree) | rng.getrandbits(degree)

        if exsuwako_reduce(x, m, exponents) != naive_reduce(
            x, m, exponents
        ):
            print("FAIL")
            return

    print("PASS")


if __name__ == "__main__":
    main()
