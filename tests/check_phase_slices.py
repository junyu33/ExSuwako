#!/usr/bin/env python3
"""Contract checks for fixed-gap and fixed-weight phase slices."""

from __future__ import annotations

import csv
import math
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


FIELDS = [
    "m", "h", "Delta_min", "log2_m_over_delta", "winner_reason",
    "GS_median_ns", "BarrettGF2X_median_ns", "LopezDahabLoop_median_ns",
]


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    plotter = repository / "bench" / "scripts" / "plot_phase_slices.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-slices-") as directory:
        root = Path(directory)
        source = root / "points.csv"
        rows = []
        for m in (128, 512, 2048, 8192, 32768, 131072):
            for h in (9, 65):
                for delta in (1, 64):
                    rows.append({
                        "m": m, "h": h, "Delta_min": delta,
                        "log2_m_over_delta": math.log2(m / delta),
                        "winner_reason": "timing-unstable" if h == 65 and delta == 64 else "unique-winner",
                        "GS_median_ns": 10 + h,
                        "BarrettGF2X_median_ns": 20 + m / 128,
                        "LopezDahabLoop_median_ns": "" if delta < 64 else 8 + h,
                    })
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)
        for kind, selections in (("weight", (1, 64)), ("gap", (9, 65))):
            figure = root / f"{kind}.svg"
            completed = subprocess.run([
                sys.executable, str(plotter), "--input", str(source),
                "--output", str(figure), "--kind", kind,
                "--selections", *(str(value) for value in selections),
            ], capture_output=True, text=True)
            if completed.returncode:
                raise AssertionError(completed.stderr)
            tree = ET.parse(figure)
            text = " ".join(node.text or "" for node in tree.iter())
            if "m = 128" not in text or "m = 131072" not in text:
                raise AssertionError("phase-slice figure does not contain six panels")
            uncertain = [
                node for node in tree.iter()
                if node.attrib.get("class") == "uncertain"
            ]
            if not uncertain:
                raise AssertionError("uncertain slice points were not retained")
    print("phase-slice plot contract checks passed")


if __name__ == "__main__":
    main()
