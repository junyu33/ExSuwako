"""Collect per-support GS/serial/Barrett points for a phase diagram."""

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
    parser.add_argument("--m", type=int, default=1 << 20)
    parser.add_argument("--s", type=int, nargs="+",
                        default=[8, 16, 32, 64, 96, 128, 160, 192, 256,
                                 320, 384, 448, 512])
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--inputs", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows: list[dict[str, object]] = []
    for s in args.s:
        if not 1 <= s < args.m:
            raise ValueError(f"invalid support size {s} for m={args.m}")
        for sample in range(args.samples):
            # The C driver receives a distinct seed, so all three reducers use
            # exactly the same support and input batch for this row.
            c_seed = rng.getrandbits(64) or 1
            command = [
                str(args.binary), "1", str(args.inputs), str(args.repeats),
                str(args.m), str(s), hex(c_seed),
            ]
            completed = subprocess.run(
                command, check=True, capture_output=True, text=True,
            )
            parsed = list(csv.DictReader(completed.stdout.splitlines()))
            if len(parsed) != 1:
                raise RuntimeError(f"expected one row for s={s}")
            row = dict(parsed[0])
            row["sample"] = sample
            row["seed"] = c_seed
            row["log2_m_over_delta"] = __import__("math").log2(
                args.m / float(row["Delta_min"])
            )
            rows.append(row)
            print(
                f"m={args.m} s={s} sample={sample} "
                f"delta={row['Delta_min']} "
                f"serial/GS={row['Serial/GS']} "
                f"barrett/GS={row['BarrettGF2X/GS']}",
                flush=True,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "m", "s", "h", "Delta_min", "log2_m_over_delta", "GS_ns",
        "Serial_ns", "BarrettGF2X_ns", "Serial/GS", "BarrettGF2X/GS",
        "sample", "seed",
    ]
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
