#!/usr/bin/env python3
"""Verify the committed Rabin pilot modulus and deterministic search record."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from sage.all import GF, PolynomialRing  # type: ignore[import-not-found]


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = [
    ROOT / "bench/manifests/e2e/rabin-pilot-m512.jsonl",
    ROOT / "bench/manifests/e2e/rabin-main-delta1-h9.jsonl",
]
GENERATOR = ROOT / "bench/scripts/generate_rabin_irreducible_manifest.py"


def main() -> None:
    ring = PolynomialRing(GF(2), "x")
    x = ring.gen()
    checked = 0
    for manifest in MANIFESTS:
        for original in manifest.read_text(encoding="utf-8").splitlines():
            row = json.loads(original)
            modulus = x ** row["m"] + sum(x ** tap for tap in row["taps"])
            if not modulus.is_irreducible():
                raise AssertionError(f"{row['sample_id']} is reducible")
            with tempfile.TemporaryDirectory() as directory:
                regenerated = Path(directory) / "modulus.jsonl"
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
                if regenerated.read_text(encoding="utf-8").strip() != original:
                    raise AssertionError(f"{row['sample_id']} is not reproducible")
            checked += 1
    print(f"Rabin manifest checks passed ({checked} records)")


if __name__ == "__main__":
    main()
