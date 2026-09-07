#!/usr/bin/env python3
"""Contract check for the explanatory operator construction figure."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "bench" / "scripts" / "draw_operator_schematic.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-operator-") as directory:
        output = Path(directory) / "operator.svg"
        completed = subprocess.run(
            [sys.executable, str(script), "--output", str(output)],
            capture_output=True, text=True,
        )
        if completed.returncode:
            raise AssertionError(completed.stderr)
        tree = ET.parse(output)
        root = tree.getroot()
        labels = " ".join(item.text or "" for item in tree.iter())
        required = (
            "CONSTRUCTION DIAGRAM", "not measured timing or circuit depth",
            "same immutable old", "active shifts {1,5,13}",
            "active shifts {2,10}", "active shift {4}", "active shift {8}",
            "No pairwise tap-sum schedule is materialized", "U¹⁶ = 0",
        )
        missing = [label for label in required if label not in labels]
        if missing:
            raise AssertionError(f"operator schematic is missing labels: {missing}")
        if any(item.tag.endswith("image") for item in root.iter()):
            raise AssertionError("operator schematic unexpectedly embeds a raster image")
    print("operator construction schematic contract checks passed")


if __name__ == "__main__":
    main()
