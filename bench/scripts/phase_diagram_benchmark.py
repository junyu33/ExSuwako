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


CURRENT_INPUT_DISTRIBUTION = "uniform-full-range:v1"
CURRENT_TIMING_SCOPE = "reduction-steady-state:v1"
CURRENT_SETUP_SCOPE = "modulus-plan:v1"
CURRENT_TIMING_ORDER = "cyclic-method-rotation:v1"
CURRENT_AGGREGATION = "median-of-trial-medians:no-outlier-removal:v1"


def validate_manifest_entry(value: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"manifest line {line_number}: expected a JSON object")
    sample_id = value.get("sample_id")
    provenance = value.get("provenance")
    m = value.get("m")
    taps = value.get("taps")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError(f"manifest line {line_number}: invalid sample_id")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError(f"manifest line {line_number}: invalid provenance")
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


def serialized_taps(taps: list[int]) -> str:
    return ";".join(str(tap) for tap in taps) if taps else "-"


def parse_serialized_taps(value: str, m: int) -> list[int]:
    if value == "-":
        return []
    try:
        taps = [int(tap) for tap in value.split(";")]
    except ValueError as error:
        raise RuntimeError(f"benchmark emitted invalid taps: {value!r}") from error
    previous = -1
    for tap in taps:
        if tap < 0 or tap >= m or tap <= previous:
            raise RuntimeError(
                f"benchmark emitted noncanonical taps for m={m}: {value!r}"
            )
        previous = tap
    return taps


def derive_geometry(m: int, taps: list[int]) -> dict[str, object]:
    if not taps:
        delta_min: int | None = None
    else:
        delta_min = min(m - tap for tap in taps)

    active_counts: list[int] = []
    scheduled_work = 0
    scale = 1
    while True:
        active = [m - tap for tap in taps if scale * (m - tap) < m]
        if not active:
            break
        active_counts.append(len(active))
        scheduled_work += sum(m - scale * distance for distance in active)
        scale *= 2

    return {
        "s": len(taps),
        "h": len(taps) + 1,
        "Delta_min": "NA" if delta_min is None else delta_min,
        "log2_m_over_delta": (
            "" if delta_min is None else math.log2(m / delta_min)
        ),
        "feedback_stages": len(active_counts),
        "active_tap_counts": (
            ";".join(str(count) for count in active_counts)
            if active_counts
            else "-"
        ),
        "W_fb": scheduled_work,
    }


def validate_benchmark_geometry(
    row: dict[str, object], m: int, taps: list[int]
) -> None:
    geometry = derive_geometry(m, taps)
    expected = {
        "m": str(m),
        "s": str(geometry["s"]),
        "h": str(geometry["h"]),
        "taps": serialized_taps(taps),
        "Delta_min": str(geometry["Delta_min"]),
        "feedback_stages": str(geometry["feedback_stages"]),
        "active_tap_counts": str(geometry["active_tap_counts"]),
    }
    for field, value in expected.items():
        if str(row.get(field)) != value:
            raise RuntimeError(
                f"benchmark geometry mismatch for {field}: "
                f"expected {value!r}, got {row.get(field)!r}"
            )
    if row.get("input_distribution") != CURRENT_INPUT_DISTRIBUTION:
        raise RuntimeError(
            "benchmark emitted an unexpected input distribution: "
            f"{row.get('input_distribution')!r}"
        )
    if row.get("timing_scope") != CURRENT_TIMING_SCOPE:
        raise RuntimeError(
            "benchmark emitted an unexpected timing scope: "
            f"{row.get('timing_scope')!r}"
        )
    if row.get("setup_scope") != CURRENT_SETUP_SCOPE:
        raise RuntimeError(
            "benchmark emitted an unexpected setup scope: "
            f"{row.get('setup_scope')!r}"
        )
    if row.get("timing_order") != CURRENT_TIMING_ORDER:
        raise RuntimeError(
            "benchmark emitted an unexpected timing order: "
            f"{row.get('timing_order')!r}"
        )
    for field in [
        "GS_setup_ns", "Serial_setup_ns", "Naive_setup_ns",
        "BarrettGF2X_setup_ns",
    ]:
        try:
            value = float(str(row.get(field)))
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"benchmark emitted invalid setup timing for {field}: "
                f"{row.get(field)!r}"
            ) from error
        if value < 0:
            raise RuntimeError(
                f"benchmark emitted negative setup timing for {field}: {value}"
            )


def add_derived_fields(
    row: dict[str, object], sample_id: str, provenance: str,
    m: int, taps: list[int]
) -> None:
    validate_benchmark_geometry(row, m, taps)
    row["sample_id"] = sample_id
    row["provenance"] = provenance
    row.update(derive_geometry(m, taps))


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
    parser.add_argument("--warmup-runs", type=int, default=0)
    parser.add_argument("--measurement-trials", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-naive", action="store_true")
    args = parser.parse_args()

    if args.inputs <= 0 or args.repeats <= 0:
        raise ValueError("inputs and repeats must be positive")
    if args.warmup_runs < 0 or args.measurement_trials <= 0:
        raise ValueError(
            "warmup-runs must be nonnegative and measurement-trials positive"
        )

    rng = random.Random(args.seed)
    rows: list[dict[str, object]] = []
    fields = [
        "sample_id",
        "provenance",
        "m",
        "word_bits",
        "s",
        "h",
        "taps",
        "Delta_min",
        "log2_m_over_delta",
        "feedback_stages",
        "active_tap_counts",
        "W_fb",
        "input_distribution",
        "timing_scope",
        "setup_scope",
        "timing_order",
        "aggregation",
        "inputs",
        "batch_repeats",
        "warmup_runs",
        "measurement_trials",
        "measurement_trial",
        "GS_setup_ns",
        "Serial_setup_ns",
        "Naive_setup_ns",
        "BarrettGF2X_setup_ns",
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

    def measured_runs(command: list[str]) -> list[tuple[int, dict[str, str]]]:
        for _ in range(args.warmup_runs):
            run(list(command))
        result: list[tuple[int, dict[str, str]]] = []
        for trial in range(args.measurement_trials):
            for row in run(list(command)):
                result.append((trial, row))
        return result

    def add_measurement_fields(row: dict[str, object], trial: int) -> None:
        row["aggregation"] = CURRENT_AGGREGATION
        row["inputs"] = args.inputs
        row["batch_repeats"] = args.repeats
        row["warmup_runs"] = args.warmup_runs
        row["measurement_trials"] = args.measurement_trials
        row["measurement_trial"] = trial

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
            measured = measured_runs(command)
            if len(measured) != args.measurement_trials:
                raise RuntimeError(
                    f"expected {args.measurement_trials} rows for sample "
                    f"{entry['sample_id']!r}"
                )
            for trial, parsed_row in measured:
                row: dict[str, object] = dict(parsed_row)
                row["seed"] = c_seed
                add_derived_fields(
                    row, entry["sample_id"], entry["provenance"],
                    entry["m"], taps
                )
                add_measurement_fields(row, trial)
                rows.append(row)
                print(
                    f"sample={entry['sample_id']} trial={trial} m={row['m']} "
                    f"taps={row['taps']} serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
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
            measured = measured_runs(command)
            if len(measured) != args.samples * args.measurement_trials:
                raise RuntimeError(
                    f"expected {args.samples * args.measurement_trials} "
                    f"rows for s={s}"
                )
            for trial, parsed_row in measured:
                row = dict(parsed_row)
                row["seed"] = c_seed
                taps = parse_serialized_taps(str(row["taps"]), args.m)
                sample_id = (
                    f"random-m{args.m}-s{s}-seed{c_seed:016x}-"
                    f"sample{row['sample']}"
                )
                add_derived_fields(
                    row, sample_id, "synthetic-fixed-weight-uniform:v1",
                    args.m, taps
                )
                add_measurement_fields(row, trial)
                rows.append(row)
                print(
                    f"sample={sample_id} trial={trial} "
                    f"delta={row['Delta_min']} "
                    f"serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
                    flush=True,
                )
            save_rows()


if __name__ == "__main__":
    main()
