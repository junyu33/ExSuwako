#!/usr/bin/env python3
"""Build compact portable-C and setup/storage paper-table summaries."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


DEGREES = (128, 512, 2048, 8192, 32768, 131072)
METHODS = ("GS", "Serial", "BarrettGF2X")


def positive(row: dict[str, str], field: str, where: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise ValueError(f"{where}: invalid {field}") from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{where}: {field} must be finite and positive")
    return value


def load_points(path: Path) -> dict[int, list[dict[str, str]]]:
    required = {
        "sample_id", "m", "h", "Delta_min", "winner", "winner_reason",
        "GS_median_ns", "BarrettGF2X_median_ns",
        "implementation", "multiplication_backend",
    }
    by_m: dict[int, list[dict[str, str]]] = defaultdict(list)
    coordinates: set[tuple[int, int, int]] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing fields: {sorted(missing)}")
        for line_number, row in enumerate(reader, 2):
            where = f"{path}:{line_number}"
            if row["implementation"] != "portable-scalar-c:v1":
                raise ValueError(f"{where}: incompatible implementation")
            if row["multiplication_backend"] != "gf2x:v1":
                raise ValueError(f"{where}: incompatible multiplication backend")
            m, h, delta = int(row["m"]), int(row["h"]), int(row["Delta_min"])
            coordinate = (m, h, delta)
            if coordinate in coordinates:
                raise ValueError(f"{where}: duplicate coordinate {coordinate}")
            coordinates.add(coordinate)
            positive(row, "GS_median_ns", where)
            positive(row, "BarrettGF2X_median_ns", where)
            by_m[m].append(row)
    if tuple(sorted(by_m)) != DEGREES:
        raise ValueError("winner points do not contain the six paper degrees")
    return by_m


def portable_rows(by_m: dict[int, list[dict[str, str]]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for m in DEGREES:
        delta_one = sorted(
            (row for row in by_m[m] if int(row["Delta_min"]) == 1),
            key=lambda row: int(row["h"]),
        )
        anchors = [row for row in delta_one if int(row["h"]) == 9]
        if len(anchors) != 1:
            raise ValueError(f"m={m}: expected one (h,Delta_min)=(9,1) anchor")
        anchor = anchors[0]
        stable = [row for row in delta_one if row["winner_reason"] == "unique-winner"]
        crossover = next((
            row for index, row in enumerate(stable)
            if row["winner"] == "BarrettGF2X"
            and all(later["winner"] == "BarrettGF2X" for later in stable[index:])
        ), None)
        if crossover is None:
            raise ValueError(f"m={m}: no persistent Delta_min=1 Barrett crossover")
        anchor_gs = float(anchor["GS_median_ns"])
        anchor_barrett = float(anchor["BarrettGF2X_median_ns"])
        cross_gs = float(crossover["GS_median_ns"])
        cross_barrett = float(crossover["BarrettGF2X_median_ns"])
        output.append({
            "m": m, "anchor_h": 9, "anchor_Delta_min": 1,
            "anchor_winner": anchor["winner"],
            "anchor_GS_median_ns": f"{anchor_gs:.9g}",
            "anchor_Barrett_median_ns": f"{anchor_barrett:.9g}",
            "anchor_Barrett_over_GS": f"{anchor_barrett / anchor_gs:.6g}",
            "persistent_Barrett_h": int(crossover["h"]),
            "crossover_GS_median_ns": f"{cross_gs:.9g}",
            "crossover_Barrett_median_ns": f"{cross_barrett:.9g}",
            "crossover_Barrett_over_GS": f"{cross_barrett / cross_gs:.6g}",
            "crossover_rule": "first-stable-Barrett-after-which-all-later-stable-are-Barrett",
            "timing_scope": "reduction-steady-state:v1",
            "implementation": "portable-scalar-c:v1",
            "multiplication_backend": "gf2x:v1",
        })
    return output


def load_setup(
    paths: list[Path], min_trials: int, paper_grade: bool,
) -> list[dict[str, object]]:
    required = {
        "sample_id", "m", "h", "Delta_min", "measurement_trials",
        "measurement_trial", "timing_scope", "setup_scope",
        "plan_storage_model", "metadata_status", "implementation",
        "multiplication_backend",
    }
    for method in METHODS:
        required.update((f"{method}_setup_ns", f"{method}_plan_bytes", f"{method}_ns"))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            missing = required.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path}: missing fields: {sorted(missing)}")
            for line_number, row in enumerate(reader, 2):
                if row["timing_scope"] != "reduction-steady-state:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible timing scope")
                if row["setup_scope"] != "modulus-plan:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible setup scope")
                if row["plan_storage_model"] != "requested-owned-bytes:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible storage model")
                if row["implementation"] != "portable-scalar-c:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible implementation")
                if row["multiplication_backend"] != "gf2x:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible multiplication backend")
                if paper_grade and row["metadata_status"] != "paper-grade":
                    raise ValueError(f"{path}:{line_number}: non-paper-grade row")
                trial = int(row["measurement_trial"])
                key = (row["sample_id"], trial)
                if key in seen:
                    raise ValueError(f"{path}:{line_number}: duplicate sample/trial {key}")
                seen.add(key)
                if int(row["h"]) == 9 and int(row["Delta_min"]) == 1:
                    grouped[row["sample_id"]].append(row)
    output: list[dict[str, object]] = []
    by_degree: dict[int, str] = {}
    for sample_id, rows in grouped.items():
        first = rows[0]
        declared = int(first["measurement_trials"])
        trials = sorted(int(row["measurement_trial"]) for row in rows)
        if trials != list(range(declared)) or declared < min_trials:
            raise ValueError(f"{sample_id}: incomplete anchor trials")
        invariants = (
            "m", "h", "Delta_min", "measurement_trials", "timing_scope",
            "setup_scope", "plan_storage_model", "metadata_status",
            "implementation", "multiplication_backend",
            *(f"{method}_plan_bytes" for method in METHODS),
        )
        if any(row[field] != first[field] for row in rows[1:] for field in invariants):
            raise ValueError(f"{sample_id}: setup/storage invariants changed")
        m = int(first["m"])
        if m in by_degree:
            raise ValueError(f"m={m}: duplicate setup anchor")
        by_degree[m] = sample_id
        row_out: dict[str, object] = {
            "m": m, "h": 9, "Delta_min": 1, "trial_count": declared,
            "setup_scope": first["setup_scope"],
            "plan_storage_model": first["plan_storage_model"],
        }
        for method in METHODS:
            if any(float(row[f"{method}_ns"]) <= 0 for row in rows):
                raise ValueError(f"{sample_id}: {method} is not enabled")
            setups = [positive(row, f"{method}_setup_ns", sample_id) for row in rows]
            row_out[f"{method}_setup_median_ns"] = statistics.median(setups)
            row_out[f"{method}_plan_bytes"] = int(first[f"{method}_plan_bytes"])
        output.append(row_out)
    if tuple(sorted(by_degree)) != DEGREES:
        raise ValueError("setup anchors do not contain the six paper degrees")
    return sorted(output, key=lambda row: int(row["m"]))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--raw", type=Path, nargs="+", required=True)
    parser.add_argument("--portable-output", type=Path, required=True)
    parser.add_argument("--setup-storage-output", type=Path, required=True)
    parser.add_argument("--min-trials", type=int, default=31)
    parser.add_argument("--paper-grade", action="store_true")
    args = parser.parse_args()
    if args.min_trials <= 0:
        raise ValueError("min-trials must be positive")
    portable = portable_rows(load_points(args.points))
    setup = load_setup(args.raw, args.min_trials, args.paper_grade)
    write_csv(args.portable_output, portable)
    write_csv(args.setup_storage_output, setup)
    print(f"portable_rows={len(portable)} setup_storage_rows={len(setup)}")


if __name__ == "__main__":
    main()
