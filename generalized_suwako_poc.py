"""Proof-of-concept generalized Suwako reduction over GF(2).

The modulus is

    g(x) = x^m + 1 + sum_{t in taps} x^t,

where every tap satisfies 0 < t < m.  Thus its Hamming weight is
``len(taps) + 2`` and is at least 3.

The input is restricted to deg(x) < 2m, which is the usual range for the
product of two degree-<m polynomials.
"""

import random
import time
from collections.abc import Iterable


def _normalize_taps(m: int, taps: Iterable[int]) -> tuple[int, ...]:
    """Validate and canonicalize the non-leading, non-constant exponents."""
    if m < 2:
        raise ValueError("m must be at least 2")

    normalized = tuple(sorted(taps))
    if not normalized:
        raise ValueError("at least one internal tap is required (weight >= 3)")
    if len(set(normalized)) != len(normalized):
        raise ValueError("tap exponents must be distinct")
    if normalized[0] <= 0 or normalized[-1] >= m:
        raise ValueError("every tap exponent t must satisfy 0 < t < m")

    return normalized


def generalized_suwako(x: int, m: int, taps: Iterable[int]) -> int:
    """Reduce ``x`` modulo ``x^m + 1 + sum(x^t for t in taps)``.

    Let

        x = L + x^m H,
        U(X) = XOR_{t in taps} (X >> (m - t)),
        V(X) = X XOR XOR_{t in taps} ((X << t) mod x^m).

    Recursive high-part folding gives

        red(x) = L XOR V((I + U)^(-1) H).

    On the m-bit truncated space U is nilpotent.  In characteristic two,

        (I + U)^(-1) = product_k (I + U^(2^k)),
        U^(2^k)(X)   = XOR_t (X >> (2^k * (m - t))).

    All shifts in one round must read the same old state.  The ``old`` /
    ``next_state`` assignment below is the scalar PoC equivalent of two
    ping-pong buffers in a SIMD or hardware implementation.
    """
    taps = _normalize_taps(m, taps)

    if x < 0:
        raise ValueError("x must be non-negative")
    if x.bit_length() > 2 * m:
        raise ValueError("this PoC requires deg(x) < 2m")

    mask = (1 << m) - 1
    low = x & mask
    high = x >> m

    deltas = tuple(m - t for t in taps)
    min_delta = min(deltas)

    # state <- product_k (I + U^(2^k)) high
    state = high
    scale = 1  # scale = 2^k

    while scale * min_delta < m:
        old = state
        feedback = 0

        # Crucial: every term reads 'old', not the partially updated state.
        for delta in deltas:
            shift = scale * delta
            if shift < m:
                feedback ^= old >> shift

        state = old ^ feedback
        scale <<= 1

    # Apply V to the fully closed high part.
    folded = state
    for t in taps:
        folded ^= (state << t) & mask

    return low ^ folded


def naive_sparse_reduction(x: int, m: int, taps: Iterable[int]) -> int:
    """Bit-by-bit reference reduction for validation only."""
    taps = _normalize_taps(m, taps)

    if x < 0:
        raise ValueError("x must be non-negative")

    modulus = (1 << m) | 1
    for t in taps:
        modulus ^= 1 << t

    while x.bit_length() - 1 >= m:
        x ^= modulus << (x.bit_length() - 1 - m)

    return x


def _num_rounds(m: int, taps: Iterable[int]) -> int:
    """Return ceil(log2(m / Delta_min)) without floating point."""
    min_delta = min(m - t for t in taps)
    rounds = 0
    scale = 1
    while scale * min_delta < m:
        rounds += 1
        scale <<= 1
    return rounds


def _check_case(x: int, m: int, taps: tuple[int, ...], case_no: int) -> None:
    expected = naive_sparse_reduction(x, m, taps)
    actual = generalized_suwako(x, m, taps)

    if expected == actual:
        return

    print("\n[!] Mismatch detected!")
    print(f"Case #{case_no}")
    print(f"  m                 = {m}")
    print(f"  taps              = {taps}")
    print(f"  Hamming weight    = {len(taps) + 2}")
    print(f"  deltas            = {tuple(m - t for t in taps)}")
    print(f"  generalized rounds= {_num_rounds(m, taps)}")
    print(f"  input x           = {hex(x)}")
    print(f"  expected          = {hex(expected)}")
    print(f"  actual            = {hex(actual)}")
    print(f"  error bits        = {hex(expected ^ actual)}")
    raise AssertionError("generalized Suwako validation failed")


def run_validation(
    num_tests: int = 10_000,
    max_m_random: int = 2_048,
    max_hamming_weight: int = 12,
    seed: int | None = None,
) -> None:
    """Validate random sparse moduli of Hamming weight 3 and above."""
    rng = random.Random(seed)

    print("[*] Starting generalized Suwako validation...")
    print(f"[*] Random tests       : {num_tests}")
    print(f"[*] Maximum m          : {max_m_random}")
    print(f"[*] Maximum weight     : {max_hamming_weight}")
    print(f"[*] RNG seed           : {seed}")

    start_time = time.time()
    pass_count = 0

    # Hand-picked edge cases: trinomial, pentanomial, many taps,
    # Delta_min = 1, and taps near both ends.
    edge_cases = [
        (3, (1,)),
        (8, (1, 3, 4)),
        (16, (1, 2, 15)),
        (31, (1, 3, 7, 15, 30)),
        (64, (1, 7, 19, 37, 63)),
        (127, (1, 2, 4, 8, 16, 32, 64, 126)),
    ]

    case_no = 0
    for m, taps in edge_cases:
        for x in (0, 1, (1 << (2 * m)) - 1, rng.getrandbits(2 * m)):
            case_no += 1
            _check_case(x, m, taps, case_no)
            pass_count += 1

    try:
        for i in range(num_tests):
            m = rng.randint(3, max_m_random)

            max_weight_here = min(max_hamming_weight, m + 1)
            weight = rng.randint(3, max_weight_here)
            num_taps = weight - 2
            taps = tuple(sorted(rng.sample(range(1, m), num_taps)))

            x = rng.getrandbits(2 * m)

            case_no += 1
            _check_case(x, m, taps, case_no)
            pass_count += 1

            if (i + 1) % 1_000 == 0:
                print(f"  Progress: {i + 1}/{num_tests} random cases passed...")

    except KeyboardInterrupt:
        print("\n[!] Test interrupted by user.")

    duration = time.time() - start_time
    print("-" * 60)
    print(f"[+] ALL {pass_count} test cases passed.")
    print(f"[+] Elapsed: {duration:.3f} s")
    print("-" * 60)


if __name__ == "__main__":
    run_validation()
