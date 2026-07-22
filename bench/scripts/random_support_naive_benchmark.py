"""Microbenchmark random fixed-weight binary moduli.

This compares the current Python PoC against its bit-level long-division
baseline. It is evidence for Python microbenchmark behavior only, not a
native implementation result.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "reference"))

from generalized_suwako_poc import exsuwako_reduce, naive_reduce


def schedule_metrics(m: int, exponents: list[int]) -> tuple[int, int, int]:
    taps = exponents[1:]
    positive = [t for t in taps if t > 0]
    if not positive:
        return 0, 0, len(taps)

    deltas = [m - t for t in positive]
    min_delta = min(deltas)
    rounds = 0
    active_sum = 0
    scale = 1
    while scale * min_delta < m:
        rounds += 1
        active_sum += sum(1 for delta in deltas if scale * delta < m)
        scale <<= 1
    return rounds, active_sum, len(taps)


def naive_steps(x: int, m: int, exponents: list[int]) -> int:
    modulus = 0
    for exponent in exponents:
        modulus |= 1 << exponent

    steps = 0
    while x.bit_length() - 1 >= m:
        x ^= modulus << (x.bit_length() - 1 - m)
        steps += 1
    return steps


def median_time(fn, inputs: list[int], m: int, exponents: list[int], repeats: int) -> float:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        for x in inputs:
            fn(x, m, exponents)
        samples.append((time.perf_counter_ns() - start) / len(inputs))
    return statistics.median(samples)


def benchmark(args: argparse.Namespace) -> list[dict[str, object]]:
    rng = random.Random(args.seed)
    rows = []

    for m in args.m_values:
        s_values = [s for s in args.s_values if 0 <= s < m]
        for s in s_values:
            support_metrics = []
            gs_times = []
            naive_times = []

            for _ in range(args.supports):
                support = sorted(rng.sample(range(m), s), reverse=True)
                exponents = [m, *support]
                inputs = []
                for _ in range(args.inputs):
                    degree = rng.randint(m, 2 * m - 1)
                    inputs.append((1 << degree) | rng.getrandbits(degree))

                for x in inputs:
                    expected = naive_reduce(x, m, exponents)
                    actual = exsuwako_reduce(x, m, exponents)
                    if expected != actual:
                        raise AssertionError(
                            f"correctness mismatch: m={m}, s={s}, "
                            f"exponents={exponents}, x={x:#x}"
                        )

                rounds, active_sum, low_taps = schedule_metrics(m, exponents)
                support_metrics.append(
                    {
                        "rounds": rounds,
                        "active_sum": active_sum,
                        "low_taps": low_taps,
                        "naive_steps": statistics.mean(
                            naive_steps(x, m, exponents) for x in inputs
                        ),
                    }
                )

                # Warm up both call paths before timing.
                exsuwako_reduce(inputs[0], m, exponents)
                naive_reduce(inputs[0], m, exponents)
                gs_times.append(
                    median_time(
                        exsuwako_reduce, inputs, m, exponents, args.repeats
                    )
                )
                naive_times.append(
                    median_time(naive_reduce, inputs, m, exponents, args.repeats)
                )

            gs_ns = statistics.median(gs_times)
            naive_ns = statistics.median(naive_times)
            ratio = naive_ns / gs_ns if gs_ns else float("inf")
            rows.append(
                {
                    "m": m,
                    "s": s,
                    "hamming_weight": s + 1,
                    "gs_ns": round(gs_ns, 1),
                    "naive_ns": round(naive_ns, 1),
                    "speedup_naive_over_gs": round(ratio, 3),
                    "median_rounds": round(
                        statistics.median(x["rounds"] for x in support_metrics), 2
                    ),
                    "median_active_sum": round(
                        statistics.median(x["active_sum"] for x in support_metrics),
                        2,
                    ),
                    "median_naive_steps": round(
                        statistics.median(x["naive_steps"] for x in support_metrics),
                        2,
                    ),
                    "model_gs": round(
                        statistics.median(
                            x["rounds"] + x["active_sum"] + x["low_taps"]
                            for x in support_metrics
                        ),
                        2,
                    ),
                }
            )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-values", default="64,128,256,512,1024")
    parser.add_argument("--s-values", default="0,1,2,4,8,16,32,64,128,256")
    parser.add_argument("--supports", type=int, default=6)
    parser.add_argument("--inputs", type=int, default=24)
    parser.add_argument("--repeats", type=int, default=3)
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

    print("m,s,h,GS_ns,naive_ns,naive/GS,rounds,sum_hk,naive_steps,model")
    for row in rows:
        print(
            f"{row['m']},{row['s']},{row['hamming_weight']},"
            f"{row['gs_ns']},{row['naive_ns']},"
            f"{row['speedup_naive_over_gs']},"
            f"{row['median_rounds']},{row['median_active_sum']},"
            f"{row['median_naive_steps']},{row['model_gs']}"
        )

    print("\nLargest tested s with median naive/GS >= 1:")
    for m in sorted(set(row["m"] for row in rows)):
        wins = [row for row in rows if row["m"] == m and row["speedup_naive_over_gs"] >= 1]
        if wins:
            best = max(wins, key=lambda row: row["s"])
            print(
                f"m={m}: s={best['s']} (h={best['hamming_weight']}), "
                f"ratio={best['speedup_naive_over_gs']}"
            )
        else:
            print(f"m={m}: none")


if __name__ == "__main__":
    main()
