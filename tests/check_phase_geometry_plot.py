#!/usr/bin/env python3
"""Contract test for fixed-m phase-geometry SVG panels."""

from __future__ import annotations

import csv
import math
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


FIELDS = [
    "sample_id", "m", "h", "Delta_min", "log2_m_over_delta",
    "measurement_trial",
]


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "bench" / "scripts" / "plot_phase_geometry.py"
    )
    with tempfile.TemporaryDirectory(prefix="exsuwako-phase-geometry-") as directory:
        root = Path(directory)
        source = root / "phase.csv"
        output = root / "phase.svg"
        rows = [
            {
                "sample_id": "m128-near", "m": 128, "h": 3,
                "Delta_min": 1, "log2_m_over_delta": math.log2(128),
                "measurement_trial": trial,
            }
            for trial in range(2)
        ]
        rows.extend([
            {
                "sample_id": "m128-far", "m": 128, "h": 5,
                "Delta_min": 64, "log2_m_over_delta": math.log2(2),
                "measurement_trial": 0,
            },
            {
                "sample_id": "m128-empty", "m": 128, "h": 1,
                "Delta_min": "NA", "log2_m_over_delta": "",
                "measurement_trial": 0,
            },
            {
                "sample_id": "m256-mid", "m": 256, "h": 9,
                "Delta_min": 16, "log2_m_over_delta": math.log2(16),
                "measurement_trial": 0,
            },
        ])
        write_rows(source, rows)
        completed = subprocess.run(
            [sys.executable, str(script), "--input", str(source),
             "--output", str(output)],
            capture_output=True, text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        if "panels=2 points=3 no_feedback=1" not in completed.stdout:
            raise AssertionError(f"unexpected plot summary: {completed.stdout}")
        tree = ET.parse(output)
        text = " ".join(element.text or "" for element in tree.iter())
        for expected in [
            "m = 128", "m = 256", "modulus Hamming weight h",
            "m / Delta_min (log2 scale)",
            "no feedback: 1 (not on log axis)",
        ]:
            if expected not in text:
                raise AssertionError(f"missing SVG label: {expected}")

        invalid = root / "invalid.csv"
        write_rows(invalid, [{
            "sample_id": "bad", "m": 128, "h": 3, "Delta_min": 2,
            "log2_m_over_delta": 99, "measurement_trial": 0,
        }])
        rejected = subprocess.run(
            [sys.executable, str(script), "--input", str(invalid),
             "--output", str(root / "invalid.svg")],
            capture_output=True, text=True,
        )
        if rejected.returncode == 0 or "does not match" not in rejected.stderr:
            raise AssertionError("invalid phase coordinate was not rejected")
    print("phase-geometry plot contract checks passed")


if __name__ == "__main__":
    main()
