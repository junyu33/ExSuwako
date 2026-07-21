"""Compare Generalized Suwako with Barrett reduction using Karatsuba.

The reciprocal-like auxiliary polynomial is precomputed outside the timed
reduction path. This remains a Python microbenchmark, not a native result.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import time
from pathlib import Path

from random_support_naive_benchmark import (
    exsuwako_reduce,
    naive_reduce,
    naive_steps,
    schedule_metrics,
)


def karatsuba(a: int, b: int, cutoff: int = 32) -> int:
    """Multiply binary polynomials with recursive Karatsuba splitting."""
    if not a or not b:
        return 0
    if min(a.bit_length(), b.bit_length()) <= cutoff:
        if a.bit_length() > b.bit_length():
            a, b = b, a
        result = 0
        while a:
            if a & 1:
                result ^= b
            a >>= 1
            b <<= 1
        return result

    split = max(a.bit_length(), b.bit_length()) // 2
    mask = (1 << split) - 1
    a0, a1 = a & mask, a >> split
    b0, b1 = b & mask, b >> split
    z0 = karatsuba(a0, b0, cutoff)
    z2 = karatsuba(a1, b1, cutoff)
    z1 = karatsuba(a0 ^ a1, b0 ^ b1, cutoff) ^ z0 ^ z2
    return z0 ^ (z1 << split) ^ (z2 << (2 * split))


def polynomial_divmod(numerator: int, denominator: int) -> tuple[int, int]:
    quotient = 0
    remainder = numerator
    denominator_degree = denominator.bit_length() - 1
    while remainder and remainder.bit_length() - 1 >= denominator_degree:
        shift = remainder.bit_length() - 1 - denominator_degree
        quotient |= 1 << shift
        remainder ^= denominator << shift
    return quotient, remainder


def barrett_setup(m: int, exponents: list[int]) -> tuple[int, int]:
    modulus = sum(1 << exponent for exponent in exponents)
    mu, remainder = polynomial_divmod(1 << (2 * m), modulus)
    if remainder >= modulus:
        raise AssertionError("invalid reciprocal setup")
    return modulus, mu


def barrett_reduce(c: int, m: int, modulus: int, mu: int) -> int:
    """Barrett reduction for deg(c) < 2m over GF(2)[x]."""
    low_mask = (1 << (m + 1)) - 1
    q1 = c >> (m - 1)
    q2 = karatsuba(q1, mu)
    q3 = q2 >> (m + 1)
    r = (c ^ karatsuba(q3, modulus)) & low_mask

    while r and r.bit_length() - 1 >= m:
        r ^= modulus << (r.bit_length() - 1 - m)
    return r


def median_time(fn, inputs, args) -> float:
    samples = []
    for _ in range(args.repeats):
        start = time.perf_counter_ns()
        for x in inputs:
            fn(x)
        samples.append((time.perf_counter_ns() - start) / len(inputs))
    return statistics.median(samples)


def benchmark(args: argparse.Namespace) -> list[dict[str, object]]:
    rng = random.Random(args.seed)
    rows = []
    for m in args.m_values:
        for s in [value for value in args.s_values if 0 <= value < m]:
            gs_times, naive_times, barrett_times = [], [], []
            metrics = []
            for _ in range(args.supports):
                support = sorted(rng.sample(range(m), s), reverse=True)
                exponents = [m, *support]
                modulus, mu = barrett_setup(m, exponents)
                inputs = [
                    (1 << (degree := rng.randint(m, 2 * m - 1)))
                    | rng.getrandbits(degree)
                    for _ in range(args.inputs)
                ]

                for x in inputs:
                    expected = naive_reduce(x, m, exponents)
                    actual_gs = exsuwako_reduce(x, m, exponents)
                    actual_barrett = barrett_reduce(x, m, modulus, mu)
                    if expected != actual_gs or expected != actual_barrett:
                        raise AssertionError(
                            f"correctness mismatch: m={m}, s={s}, "
                            f"exponents={exponents}, x={x:#x}"
                        )

                rounds, active_sum, low_taps = schedule_metrics(m, exponents)
                metrics.append(
                    {
                        "rounds": rounds,
                        "active_sum": active_sum,
                        "low_taps": low_taps,
                        "naive_steps": statistics.mean(
                            naive_steps(x, m, exponents) for x in inputs
                        ),
                    }
                )

                gs = lambda x: exsuwako_reduce(x, m, exponents)
                naive = lambda x: naive_reduce(x, m, exponents)
                barrett = lambda x: barrett_reduce(x, m, modulus, mu)
                gs(inputs[0])
                naive(inputs[0])
                barrett(inputs[0])
                gs_times.append(median_time(gs, inputs, args))
                naive_times.append(median_time(naive, inputs, args))
                barrett_times.append(median_time(barrett, inputs, args))

            gs_ns = statistics.median(gs_times)
            naive_ns = statistics.median(naive_times)
            barrett_ns = statistics.median(barrett_times)
            rows.append(
                {
                    "m": m,
                    "s": s,
                    "hamming_weight": s + 1,
                    "gs_ns": round(gs_ns, 1),
                    "naive_ns": round(naive_ns, 1),
                    "barrett_karatsuba_ns": round(barrett_ns, 1),
                    "naive_over_gs": round(naive_ns / gs_ns, 3),
                    "barrett_over_gs": round(barrett_ns / gs_ns, 3),
                    "median_rounds": round(
                        statistics.median(x["rounds"] for x in metrics), 2
                    ),
                    "median_active_sum": round(
                        statistics.median(x["active_sum"] for x in metrics), 2
                    ),
                    "median_naive_steps": round(
                        statistics.median(x["naive_steps"] for x in metrics), 2
                    ),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-values", default="64,128,256,512,1024")
    parser.add_argument("--s-values", default="1,2,4,8,16,32,64,128")
    parser.add_argument("--supports", type=int, default=12)
    parser.add_argument("--inputs", type=int, default=64)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    args.m_values = [int(x) for x in args.m_values.split(",")]
    args.s_values = [int(x) for x in args.s_values.split(",")]

    rows = benchmark(args)
    fields = list(rows[0]) if rows else []
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    print("m,s,h,GS_ns,naive_ns,BarrettK_ns,naive/GS,BarrettK/GS,rounds,sum_hk,naive_steps")
    for row in rows:
        print(
            f"{row['m']},{row['s']},{row['hamming_weight']},"
            f"{row['gs_ns']},{row['naive_ns']},{row['barrett_karatsuba_ns']},"
            f"{row['naive_over_gs']},{row['barrett_over_gs']},"
            f"{row['median_rounds']},{row['median_active_sum']},"
            f"{row['median_naive_steps']}"
        )


if __name__ == "__main__":
    main()
