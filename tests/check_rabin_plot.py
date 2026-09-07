#!/usr/bin/env python3
"""Smoke-test the Rabin E2E plot contract."""

from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLOTTER = ROOT / "bench/scripts/plot_rabin_e2e.py"


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "summary.csv"
        figure = root / "figure.svg"
        fields = [
            "sample_id", "m", "h", "delta_min", "taps", "method", "trials",
            "median_e2e_ns", "median_ci_low_ns", "median_ci_high_ns",
            "method_over_FFR", "ratio_ci_low", "ratio_ci_high",
        ]
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for m in (128, 512):
                for method, ratio in (("FFR", 1.0), ("BarrettGF2X", 2.0)):
                    writer.writerow(
                        {
                            "sample_id": f"m{m}", "m": m, "h": 9,
                            "delta_min": 1, "taps": "0;1", "method": method,
                            "trials": 31, "median_e2e_ns": m * ratio,
                            "median_ci_low_ns": m * ratio * 0.99,
                            "median_ci_high_ns": m * ratio * 1.01,
                            "method_over_FFR": ratio,
                            "ratio_ci_low": ratio * 0.99,
                            "ratio_ci_high": ratio * 1.01,
                        }
                    )
        subprocess.run(
            ["python3", str(PLOTTER), "--input", str(source), "--output", str(figure)],
            check=True,
        )
        text = figure.read_text(encoding="utf-8")
        if "FFR" not in text or "BarrettGF2X" not in text:
            raise AssertionError("Rabin figure lost method labels")
    print("Rabin E2E plot checks passed")


if __name__ == "__main__":
    main()
