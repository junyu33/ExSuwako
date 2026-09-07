#!/usr/bin/env python3
"""Summarize Rabin E2E trials and paired method ratios."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_median(values: list[float], rng: random.Random, count: int) -> tuple[float, float]:
    estimates = [
        statistics.median(rng.choices(values, k=len(values))) for _ in range(count)
    ]
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument("--seed", type=lambda text: int(text, 0), default=0x524142494E)
    args = parser.parse_args()
    if args.bootstrap < 1:
        raise ValueError("bootstrap count must be positive")

    with args.input.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    grouped: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    sample_info: dict[str, dict[str, str]] = {}
    for row in rows:
        grouped[row["sample_id"]][row["method"]][int(row["trial"])] = float(row["e2e_ns"])
        info = {name: row[name] for name in ("m", "h", "delta_min", "taps")}
        if row["sample_id"] in sample_info and sample_info[row["sample_id"]] != info:
            raise ValueError(f"{row['sample_id']} has inconsistent modulus metadata")
        sample_info[row["sample_id"]] = info

    output_rows: list[dict[str, object]] = []
    rng = random.Random(args.seed)
    for sample_id, methods in sorted(grouped.items()):
        if "FFR" not in methods:
            raise ValueError(f"{sample_id} has no FFR rows")
        trials = sorted(methods["FFR"])
        for method, observations in sorted(methods.items()):
            if sorted(observations) != trials:
                raise ValueError(f"{sample_id}/{method} has incomplete paired trials")
            values = [observations[trial] for trial in trials]
            median = statistics.median(values)
            low, high = bootstrap_median(values, rng, args.bootstrap)
            if method == "FFR":
                ratio = ratio_low = ratio_high = 1.0
            else:
                ratios = [observations[trial] / methods["FFR"][trial] for trial in trials]
                ratio = statistics.median(ratios)
                ratio_low, ratio_high = bootstrap_median(ratios, rng, args.bootstrap)
            output_rows.append(
                {
                    "sample_id": sample_id,
                    **sample_info[sample_id],
                    "method": method,
                    "trials": len(values),
                    "median_e2e_ns": f"{median:.9g}",
                    "median_ci_low_ns": f"{low:.9g}",
                    "median_ci_high_ns": f"{high:.9g}",
                    "method_over_FFR": f"{ratio:.9g}",
                    "ratio_ci_low": f"{ratio_low:.9g}",
                    "ratio_ci_high": f"{ratio_high:.9g}",
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"samples={len(grouped)} methods={len(output_rows)} output={args.output}")


if __name__ == "__main__":
    main()
