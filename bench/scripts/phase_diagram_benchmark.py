"""Collect exact or random per-support reduction points for a phase diagram."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
from pathlib import Path
from typing import Any


def validate_manifest_entry(value: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"manifest line {line_number}: expected a JSON object")
    sample_id = value.get("sample_id")
    m = value.get("m")
    taps = value.get("taps")
    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError(f"manifest line {line_number}: invalid sample_id")
    if isinstance(m, bool) or not isinstance(m, int) or m <= 0:
        raise ValueError(f"manifest line {line_number}: m must be positive")
    if not isinstance(taps, list):
        raise ValueError(f"manifest line {line_number}: taps must be a list")
    previous = -1
    for tap in taps:
        if isinstance(tap, bool) or not isinstance(tap, int):
            raise ValueError(
                f"manifest line {line_number}: tap exponents must be integers"
            )
        if tap < 0 or tap >= m:
            raise ValueError(
                f"manifest line {line_number}: tap {tap} is outside [0, {m})"
            )
        if tap <= previous:
            raise ValueError(
                f"manifest line {line_number}: taps must be strictly increasing"
            )
        previous = tap
    return value


def load_manifest(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"manifest line {line_number}: invalid JSON: {error.msg}"
                ) from error
            entry = validate_manifest_entry(value, line_number)
            sample_id = entry["sample_id"]
            if sample_id in sample_ids:
                raise ValueError(
                    f"manifest line {line_number}: duplicate sample_id {sample_id!r}"
                )
            sample_ids.add(sample_id)
            entries.append(entry)
    if not entries:
        raise ValueError("manifest contains no entries")
    return entries


def exact_tap_argument(taps: list[int]) -> str:
    return ",".join(str(tap) for tap in taps) if taps else "-"


def add_derived_fields(row: dict[str, object], sample_id: str) -> None:
    row["sample_id"] = sample_id
    delta = str(row["Delta_min"])
    row["log2_m_over_delta"] = (
        "" if delta == "NA" else math.log2(int(str(row["m"])) / int(delta))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--m", type=int, default=1 << 20)
    parser.add_argument(
        "--s",
        type=int,
        nargs="+",
        default=[8, 16, 32, 64, 96, 128, 160, 192, 256, 320, 384, 448, 512],
    )
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--inputs", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-naive", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows: list[dict[str, object]] = []
    fields = [
        "sample_id",
        "m",
        "s",
        "h",
        "taps",
        "Delta_min",
        "log2_m_over_delta",
        "GS_ns",
        "Serial_ns",
        "Naive_ns",
        "BarrettGF2X_ns",
        "Serial/GS",
        "Naive/GS",
        "BarrettGF2X/GS",
        "sample",
        "seed",
    ]

    def save_rows() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def run(command: list[str]) -> list[dict[str, str]]:
        if args.no_naive:
            command.append("no-naive")
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        return list(csv.DictReader(completed.stdout.splitlines()))

    if args.manifest is not None:
        for entry in load_manifest(args.manifest):
            c_seed = rng.getrandbits(64) or 1
            taps = entry["taps"]
            command = [
                str(args.binary),
                "--taps",
                exact_tap_argument(taps),
                str(args.inputs),
                str(args.repeats),
                str(entry["m"]),
                hex(c_seed),
            ]
            parsed = run(command)
            if len(parsed) != 1:
                raise RuntimeError(
                    f"expected one row for sample {entry['sample_id']!r}"
                )
            row: dict[str, object] = dict(parsed[0])
            expected_taps = ";".join(str(tap) for tap in taps) if taps else "-"
            if row["taps"] != expected_taps:
                raise RuntimeError(
                    f"benchmark changed taps for sample {entry['sample_id']!r}"
                )
            row["seed"] = c_seed
            add_derived_fields(row, entry["sample_id"])
            rows.append(row)
            print(
                f"sample={entry['sample_id']} m={row['m']} taps={row['taps']} "
                f"serial/GS={row['Serial/GS']} barrett/GS={row['BarrettGF2X/GS']}",
                flush=True,
            )
            save_rows()
    else:
        for s in args.s:
            if not 0 <= s <= args.m:
                raise ValueError(f"invalid support size {s} for m={args.m}")
            c_seed = rng.getrandbits(64) or 1
            command = [
                str(args.binary),
                str(args.samples),
                str(args.inputs),
                str(args.repeats),
                str(args.m),
                str(s),
                hex(c_seed),
            ]
            parsed = run(command)
            if len(parsed) != args.samples:
                raise RuntimeError(f"expected {args.samples} rows for s={s}")
            for parsed_row in parsed:
                row = dict(parsed_row)
                row["seed"] = c_seed
                sample_id = f"random-m{args.m}-s{s}-{row['sample']}"
                add_derived_fields(row, sample_id)
                rows.append(row)
                print(
                    f"sample={sample_id} delta={row['Delta_min']} "
                    f"serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
                    flush=True,
                )
            save_rows()


if __name__ == "__main__":
    main()
