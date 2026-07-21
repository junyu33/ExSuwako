"""Benchmark GS and strong serial folding on random sparse moduli."""

from __future__ import annotations

import argparse
import csv
import random
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
        command = [
            str(args.binary), str(args.supports), str(args.inputs),
            str(args.repeats), str(m), str(s),
        ]
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        benchmark_rows = list(csv.DictReader(completed.stdout.splitlines()))
        if len(benchmark_rows) != 1:
            raise RuntimeError(f"expected one row for m={m}, h={h}")
        row = dict(benchmark_rows[0])
        row["power"] = power
        row["seed"] = args.seed
        rows.append(row)
        print(
            f"m=2^{power} h={h} "
            f"GS={row['GS_ns']}ns serial={row['Serial_ns']}ns "
            f"serial/GS={row['Serial/GS']}",
            flush=True,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["power", "m", "s", "h", "GS_ns", "Serial_ns", "Serial/GS", "seed"]
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
