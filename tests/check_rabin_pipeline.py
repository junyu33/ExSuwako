#!/usr/bin/env python3
"""Exercise metadata collection and paired analysis for the Rabin workload."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "bench/scripts/collect_rabin_benchmark.py"
ANALYZER = ROOT / "bench/scripts/analyze_rabin_benchmark.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    cpu = min(os.sched_getaffinity(0))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest = root / "manifest.jsonl"
        raw = root / "raw.csv"
        summary = root / "summary.csv"
        manifest.write_text(
            json.dumps(
                {
                    "schema": "exsuwako-rabin-modulus:v1",
                    "sample_id": "aes-polynomial",
                    "provenance": "pipeline-regression:v1",
                    "m": 8,
                    "h": 5,
                    "delta_min": 4,
                    "taps": [0, 1, 3, 4],
                    "search_seed": 0,
                    "accepted_attempt": 1,
                    "irreducible": True,
                    "certificate": "known-aes-polynomial:v1",
                    "sage_version": "not-used",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "python3", str(COLLECTOR),
                "--binary", str(args.binary),
                "--manifest", str(manifest),
                "--output", str(raw),
                "--trials", "3",
                "--warmups", "1",
                "--cpu", str(cpu),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "python3", str(ANALYZER),
                "--input", str(raw),
                "--output", str(summary),
                "--bootstrap", "100",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with raw.open(newline="", encoding="utf-8") as stream:
            raw_rows = list(csv.DictReader(stream))
        with summary.open(newline="", encoding="utf-8") as stream:
            summary_rows = list(csv.DictReader(stream))
        if len(raw_rows) != 12 or len(summary_rows) != 4:
            raise AssertionError("unexpected Rabin pipeline output size")
        if any(row["metadata_status"] != "exploratory" for row in raw_rows):
            raise AssertionError("pipeline lost exploratory metadata status")
        if {row["method"] for row in summary_rows} != {
            "FFR", "BarrettGF2X", "Serial", "NTL-IterIrredTest"
        }:
            raise AssertionError("pipeline summary has the wrong methods")
    print("Rabin collection and analysis checks passed")


if __name__ == "__main__":
    main()
