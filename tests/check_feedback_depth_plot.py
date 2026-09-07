#!/usr/bin/env python3
"""Contract checks for exact feedback-depth plots."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    plotter = repository / "bench" / "scripts" / "plot_feedback_depth.py"
    fields = ["sample_id", "m", "Delta_min", "feedback_stages"]
    rows = [
        {"sample_id": "m8-d1", "m": 8, "Delta_min": 1, "feedback_stages": 3},
        {"sample_id": "m8-d2", "m": 8, "Delta_min": 2, "feedback_stages": 2},
        {"sample_id": "m16-d1", "m": 16, "Delta_min": 1, "feedback_stages": 4},
        {"sample_id": "m16-d4", "m": 16, "Delta_min": 4, "feedback_stages": 2},
    ]
    with tempfile.TemporaryDirectory(prefix="exsuwako-depth-") as directory:
        root = Path(directory)
        source, figure = root / "depth.csv", root / "depth.svg"
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        command = [
            sys.executable, str(plotter), "--input", str(source),
            "--output", str(figure),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode:
            raise AssertionError(completed.stderr)
        text = " ".join(node.text or "" for node in ET.parse(figure).iter())
        for label in ["Fixed-m gap sweep", "Gap-one scaling", "log2(Delta_min)"]:
            if label not in text:
                raise AssertionError(f"depth figure is missing {label!r}")
        invalid = root / "invalid.csv"
        rows[0]["feedback_stages"] = 2
        with invalid.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        command[command.index(str(source))] = str(invalid)
        rejected = subprocess.run(command, capture_output=True, text=True)
        if rejected.returncode == 0:
            raise AssertionError("incorrect feedback depth was accepted")
    print("feedback-depth plot contract checks passed")


if __name__ == "__main__":
    main()
