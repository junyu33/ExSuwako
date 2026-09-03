"""Benchmark GS and strong serial folding on random sparse moduli."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-h", type=int, default=1000)
    parser.add_argument("--supports", type=int, default=1)
    parser.add_argument("--inputs", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--min-power", type=int, default=3)
    parser.add_argument("--max-power", type=int, default=20)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows: list[dict[str, object]] = []
    for power in range(args.min_power, args.max_power + 1):
        m = 1 << power
        max_h = min(args.max_h, m + 1)
        h = rng.randint(3, max_h)
        s = h - 1
        c_seed = rng.getrandbits(64) or 1
        command = [
            str(args.binary), str(args.supports), str(args.inputs),
            str(args.repeats), str(m), str(s), hex(c_seed),
        ]
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        benchmark_rows = list(csv.DictReader(completed.stdout.splitlines()))
        if len(benchmark_rows) != args.supports:
            raise RuntimeError(f"expected {args.supports} rows for m={m}, h={h}")
        row = dict(benchmark_rows[0])
        for field in [
            "GS_source_aligned_word_contributions",
            "GS_source_cross_word_contributions",
            "GS_source_word_shifts", "GS_source_word_xors",
            "GS_source_logical_word_reads", "GS_source_logical_word_writes",
            "GS_source_scratch_words",
            "GS_setup_ns", "Serial_setup_ns", "Naive_setup_ns",
            "BarrettGF2X_setup_ns",
            "GS_ns", "Serial_ns", "Naive_ns", "BarrettGF2X_ns",
            "Serial/GS", "Naive/GS", "BarrettGF2X/GS",
        ]:
            row[field] = statistics.median(
                float(sample[field]) for sample in benchmark_rows
            )
        row["Delta_min"] = statistics.median(
            int(sample["Delta_min"]) for sample in benchmark_rows
        )
        row["feedback_stages"] = statistics.median(
            int(sample["feedback_stages"]) for sample in benchmark_rows
        )
        row["feedback_active_tap_sum"] = statistics.median(
            int(sample["feedback_active_tap_sum"])
            for sample in benchmark_rows
        )
        row["W_fb"] = statistics.median(
            int(sample["W_fb"]) for sample in benchmark_rows
        )
        # This driver aggregates several random supports into one row, so no
        # single exact tap list represents the resulting median.
        row.pop("taps", None)
        row.pop("active_tap_counts", None)
        row.pop("sample", None)
        row["power"] = power
        row["driver_seed"] = args.seed
        row["seed"] = c_seed
        rows.append(row)
        print(
            f"m=2^{power} h={h} "
            f"GS={row['GS_ns']}ns serial={row['Serial_ns']}ns "
            f"serial/GS={row['Serial/GS']}",
            flush=True,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "power", "m", "word_bits", "s", "h", "Delta_min",
        "feedback_stages", "feedback_active_tap_sum", "W_fb",
        "GS_source_cost_model", "GS_source_aligned_word_contributions",
        "GS_source_cross_word_contributions", "GS_source_word_shifts",
        "GS_source_word_xors", "GS_source_logical_word_reads",
        "GS_source_logical_word_writes", "GS_source_scratch_words",
        "input_distribution",
        "timing_scope", "setup_scope", "timing_order", "GS_setup_ns", "Serial_setup_ns",
        "Naive_setup_ns", "BarrettGF2X_setup_ns",
        "GS_ns", "Serial_ns", "Naive_ns",
        "BarrettGF2X_ns", "Serial/GS", "Naive/GS", "BarrettGF2X/GS",
        "driver_seed", "seed",
    ]
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
