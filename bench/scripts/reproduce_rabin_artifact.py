#!/usr/bin/env python3
"""Verify raw Rabin data and reproduce its summary and paper figure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "bench/artifact/rabin-v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    dataset = args.data_root / contract["dataset"]["filename"]
    if sha256(dataset) != contract["dataset"]["sha256"]:
        raise ValueError("Rabin raw dataset hash mismatch")
    with dataset.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != contract["dataset"]["rows"]:
        raise ValueError("Rabin raw dataset row-count mismatch")
    if {row["git_commit"] for row in rows} != {contract["dataset"]["git_commit"]}:
        raise ValueError("Rabin collection commit mismatch")
    if {row["binary_sha256"] for row in rows} != {
        contract["dataset"]["binary_sha256"]
    }:
        raise ValueError("Rabin binary digest mismatch")
    if {row["metadata_status"] for row in rows} != {"paper-grade"}:
        raise ValueError("Rabin dataset is not paper-grade")
    manifest = ROOT / contract["manifest"]["path"]
    if sha256(manifest) != contract["manifest"]["sha256"]:
        raise ValueError("Rabin modulus manifest hash mismatch")

    args.output.mkdir(parents=True, exist_ok=True)
    summary = args.output / "rabin-summary.csv"
    figure = args.output / "rabin-e2e.svg"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "bench/scripts/analyze_rabin_benchmark.py"),
            "--input", str(dataset),
            "--output", str(summary),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "bench/scripts/plot_rabin_e2e.py"),
            "--input", str(summary),
            "--output", str(figure),
        ],
        check=True,
    )
    for name, expected in contract["outputs"].items():
        actual = sha256(args.output / name)
        if actual != expected:
            raise ValueError(f"Rabin artifact mismatch for {name}: {actual}")
    print(f"Rabin artifact reproduced ({len(rows)} rows, 2 outputs)")


if __name__ == "__main__":
    main()
