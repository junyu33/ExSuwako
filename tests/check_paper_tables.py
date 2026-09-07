#!/usr/bin/env python3
"""Contract checks for compact paper-table summaries."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


POINT_FIELDS = [
    "sample_id", "m", "h", "Delta_min", "winner", "winner_reason",
    "GS_median_ns", "BarrettGF2X_median_ns", "timing_scope",
    "implementation", "multiplication_backend",
]
RAW_FIELDS = [
    "sample_id", "m", "h", "Delta_min", "measurement_trials",
    "measurement_trial", "timing_scope", "setup_scope", "plan_storage_model",
    "metadata_status", "implementation", "multiplication_backend",
    "GS_setup_ns", "GS_plan_bytes", "GS_ns",
    "Serial_setup_ns", "Serial_plan_bytes", "Serial_ns",
    "BarrettGF2X_setup_ns", "BarrettGF2X_plan_bytes", "BarrettGF2X_ns",
]


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "bench" / "scripts" / "summarize_paper_tables.py"
    degrees = (128, 512, 2048, 8192, 32768, 131072)
    with tempfile.TemporaryDirectory(prefix="exsuwako-paper-tables-") as directory:
        root = Path(directory)
        points = root / "points.csv"
        raw = root / "raw.csv"
        with points.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=POINT_FIELDS)
            writer.writeheader()
            for m in degrees:
                for h, winner in ((9, "GS"), (33, "BarrettGF2X")):
                    writer.writerow({
                        "sample_id": f"m{m}-h{h}", "m": m, "h": h,
                        "Delta_min": 1, "winner": winner,
                        "winner_reason": "unique-winner", "GS_median_ns": h,
                        "BarrettGF2X_median_ns": 20,
                        "timing_scope": "reduction-steady-state:v1",
                        "implementation": "portable-scalar-c:v1",
                        "multiplication_backend": "gf2x:v1",
                    })
        with raw.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=RAW_FIELDS)
            writer.writeheader()
            for m in degrees:
                for trial in range(3):
                    row = {
                        "sample_id": f"m{m}-anchor", "m": m, "h": 9,
                        "Delta_min": 1, "measurement_trials": 3,
                        "measurement_trial": trial,
                        "timing_scope": "reduction-steady-state:v1",
                        "setup_scope": "modulus-plan:v1",
                        "plan_storage_model": "requested-owned-bytes:v1",
                        "metadata_status": "paper-grade",
                        "implementation": "portable-scalar-c:v1",
                        "multiplication_backend": "gf2x:v1",
                    }
                    for index, method in enumerate(("GS", "Serial", "BarrettGF2X"), 1):
                        row[f"{method}_setup_ns"] = 10 * index + trial
                        row[f"{method}_plan_bytes"] = 100 * index
                        row[f"{method}_ns"] = 5 * index
                    writer.writerow(row)
        portable = root / "portable.csv"
        setup = root / "setup.csv"
        completed = subprocess.run([
            sys.executable, str(script), "--points", str(points), "--raw", str(raw),
            "--portable-output", str(portable), "--setup-storage-output", str(setup),
            "--min-trials", "3", "--paper-grade",
        ], capture_output=True, text=True)
        if completed.returncode:
            raise AssertionError(completed.stderr)
        with portable.open(newline="", encoding="utf-8") as stream:
            portable_rows = list(csv.DictReader(stream))
        with setup.open(newline="", encoding="utf-8") as stream:
            setup_rows = list(csv.DictReader(stream))
        if len(portable_rows) != 6 or {row["persistent_Barrett_h"] for row in portable_rows} != {"33"}:
            raise AssertionError("portable crossover rows are incomplete")
        if len(setup_rows) != 6 or {row["GS_setup_median_ns"] for row in setup_rows} != {"11.0"}:
            raise AssertionError("setup/storage medians are incorrect")
    print("paper-table summary contract checks passed")


if __name__ == "__main__":
    main()
