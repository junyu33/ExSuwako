#!/usr/bin/env python3
"""Contract checks for fixed-weight support quantile summaries."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


FIELDS = [
    "sample_id", "provenance", "m", "word_bits", "s", "h", "taps",
    "Delta_min", "feedback_stages", "feedback_active_tap_sum", "W_fb",
    "input_distribution", "timing_scope", "setup_scope", "timing_order",
    "aggregation", "inputs", "batch_repeats", "warmup_runs",
    "measurement_trials", "measurement_trial", "seed", "Dense_enabled",
    "LopezDahabLoop_enabled", "GS_ns", "Serial_ns", "BarrettGF2X_ns",
    "Serial/GS", "BarrettGF2X/GS", "Naive_ns", "Dense_ns", "Dense/GS",
    "LopezDahabLoop_ns", "LopezDahabLoop/GS",
]


def run(command: list[str], succeeds: bool = True) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)
    if (completed.returncode == 0) != succeeds:
        raise AssertionError(
            f"unexpected command status {completed.returncode}:\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def write_input(path: Path, duplicate: bool = False) -> None:
    rows: list[dict[str, object]] = []
    for support in range(5):
        taps = "1;" + str(10 + support)
        if duplicate and support == 4:
            taps = "1;10"
        for trial in range(3):
            gs = 10.0 * (support + 1) + (trial - 1)
            rows.append({
                "sample_id": f"random-{support}",
                "provenance": "synthetic-fixed-weight-uniform:v1",
                "m": 32,
                "word_bits": 64,
                "s": 2,
                "h": 3,
                "taps": taps,
                "Delta_min": 22 - support,
                "feedback_stages": support + 1,
                "feedback_active_tap_sum": 2 * (support + 1),
                "W_fb": 100 * (support + 1),
                "input_distribution": "uniform-full-range:v1",
                "timing_scope": "reduction-steady-state:v1",
                "setup_scope": "modulus-plan:v1",
                "timing_order": "cyclic-method-rotation:v1",
                "aggregation": "median-of-trial-medians:no-outlier-removal:v1",
                "inputs": 2,
                "batch_repeats": 2,
                "warmup_runs": 1,
                "measurement_trials": 3,
                "measurement_trial": trial,
                "seed": 17,
                "Dense_enabled": 0,
                "LopezDahabLoop_enabled": 0,
                "GS_ns": gs,
                "Serial_ns": 2 * gs,
                "BarrettGF2X_ns": 3 * gs,
                "Serial/GS": 2,
                "BarrettGF2X/GS": 3,
                "Naive_ns": 0,
                "Dense_ns": 0,
                "Dense/GS": 0,
                "LopezDahabLoop_ns": 0,
                "LopezDahabLoop/GS": 0,
            })
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "bench" / "scripts" / "summarize_fixed_weight.py"
    )
    with tempfile.TemporaryDirectory(prefix="exsuwako-fixed-weight-") as directory:
        root = Path(directory)
        source = root / "raw.csv"
        supports = root / "supports.csv"
        summary = root / "summary.csv"
        write_input(source)
        command = [
            sys.executable, str(script), "--input", str(source),
            "--supports", str(supports), "--summary", str(summary),
            "--min-supports", "5", "--min-trials", "3",
            "--min-batch-repeats", "2",
        ]
        run(command)
        with supports.open(newline="", encoding="utf-8") as stream:
            support_rows = list(csv.DictReader(stream))
        if [float(row["GS_ns"]) for row in support_rows] != [10, 20, 30, 40, 50]:
            raise AssertionError("trial medians were not computed per support")
        with summary.open(newline="", encoding="utf-8") as stream:
            summary_rows = list(csv.DictReader(stream))
        gs = next(row for row in summary_rows if row["metric"] == "GS_ns")
        if (
            gs["unique_supports"] != "5"
            or float(gs["median"]) != 30
            or float(gs["p90"]) != 50
            or float(gs["p99"]) != 50
        ):
            raise AssertionError("support quantiles do not use the frozen rule")
        if any(row["metric"] == "Naive_ns" for row in summary_rows):
            raise AssertionError("disabled method was included in summary")

        duplicate = root / "duplicate.csv"
        write_input(duplicate, duplicate=True)
        rejected = list(command)
        rejected[rejected.index(str(source))] = str(duplicate)
        run(rejected, succeeds=False)

        too_few = list(command)
        too_few[too_few.index("5")] = "6"
        run(too_few, succeeds=False)
    print("fixed-weight support summary contract checks passed")


if __name__ == "__main__":
    main()
