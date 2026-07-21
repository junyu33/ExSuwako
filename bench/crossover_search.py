"""Coarse-scan and binary-search the GS/Barrett crossover.

The C benchmark reports Barrett/GS. Values above one mean GS is faster;
values below one mean Barrett is faster. The binary search assumes the
coarse interval has the expected decreasing trend. It is only a locator:
all raw coarse and binary measurements are written to the output CSV so
non-monotonic or noisy boundaries remain visible.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
from pathlib import Path


DEFAULT_M = [2**power for power in range(16, 25)]
DEFAULT_COARSE = [32, 48, 64, 96, 128, 160, 192, 256]


def run_point(binary: Path, gf2x_lib: Path | None, m: int, s: int,
              supports: int, inputs: int, repeats: int) -> dict[str, object]:
    command = [
        str(binary), str(supports), str(inputs), str(repeats), str(m),
        "no-naive", str(s), str(s),
    ]
    environment = os.environ.copy()
    if gf2x_lib is not None:
        old_path = environment.get("LD_LIBRARY_PATH", "")
        environment["LD_LIBRARY_PATH"] = (
            str(gf2x_lib) if not old_path else f"{gf2x_lib}:{old_path}"
        )
    completed = subprocess.run(
        command, check=True, capture_output=True, text=True, env=environment
    )
    rows = list(csv.DictReader(completed.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one benchmark row for m={m}, s={s}")
    row = rows[0]
    return {
        "m": m,
        "s": s,
        "GS_ns": float(row["GS_ns"]),
        "BarrettGF2X_ns": float(row["BarrettGF2X_ns"]),
        "BarrettGF2X/GS": float(row["BarrettGF2X/GS"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--gf2x-lib", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--supports", type=int, default=2)
    parser.add_argument("--inputs", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--m", type=int, nargs="+", default=DEFAULT_M)
    parser.add_argument("--coarse", type=int, nargs="+", default=DEFAULT_COARSE)
    args = parser.parse_args()

    cache: dict[tuple[int, int], dict[str, object]] = {}

    def measure(m: int, s: int, phase: str) -> dict[str, object]:
        key = (m, s)
        if key not in cache:
            cache[key] = run_point(
                args.binary, args.gf2x_lib, m, s,
                args.supports, args.inputs, args.repeats,
            )
        row = dict(cache[key])
        row["phase"] = phase
        print(f"m={m} s={s} ratio={row['BarrettGF2X/GS']:.3f} ({phase})")
        return row

    output_rows: list[dict[str, object]] = []
    for m in args.m:
        coarse_rows = [measure(m, s, "coarse") for s in args.coarse]
        output_rows.extend(coarse_rows)
        crossing = next(
            (index for index, row in enumerate(coarse_rows)
             if float(row["BarrettGF2X/GS"]) < 1.0),
            None,
        )
        if crossing is None:
            print(f"m={m}: no crossover in coarse range")
            continue
        high = int(coarse_rows[crossing]["s"])
        low = 1 if crossing == 0 else int(coarse_rows[crossing - 1]["s"])
        while high - low > 1:
            middle = (low + high) // 2
            row = measure(m, middle, "binary")
            output_rows.append(row)
            if float(row["BarrettGF2X/GS"]) < 1.0:
                high = middle
            else:
                low = middle
        print(f"m={m}: candidate boundary between s={low} and s={high}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["m", "s", "phase", "GS_ns", "BarrettGF2X_ns", "BarrettGF2X/GS"]
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    main()
