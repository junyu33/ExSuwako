#!/usr/bin/env python3
"""Verify the committed Rabin pilot modulus and deterministic search record."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from sage.all import GF, PolynomialRing  # type: ignore[import-not-found]


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "bench/manifests/e2e/rabin-pilot-m512.jsonl"
GENERATOR = ROOT / "bench/scripts/generate_rabin_irreducible_manifest.py"


def main() -> None:
    original = MANIFEST.read_text(encoding="utf-8")
    row = json.loads(original)
    ring = PolynomialRing(GF(2), "x")
    x = ring.gen()
    modulus = x ** row["m"] + sum(x ** tap for tap in row["taps"])
    if not modulus.is_irreducible():
        raise AssertionError("committed Rabin pilot modulus is reducible")

    with tempfile.TemporaryDirectory() as directory:
        regenerated = Path(directory) / "pilot.jsonl"
        subprocess.run(
            [
                "python3", str(GENERATOR),
                "--m", str(row["m"]),
                "--h", str(row["h"]),
                "--delta-min", str(row["delta_min"]),
                "--seed", str(row["search_seed"]),
                "--count", "1",
                "--output", str(regenerated),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if regenerated.read_text(encoding="utf-8") != original:
            raise AssertionError("Rabin pilot manifest is not reproducible")
    print("Rabin pilot manifest checks passed")


if __name__ == "__main__":
    main()
