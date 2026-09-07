#!/usr/bin/env python3
"""Contract smoke test for the isolated FFR-online experiment family."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = root / "manifest.jsonl"
        raw = root / "raw.csv"
        summary = root / "summary.csv"
        subprocess.run(
            [
                "python3", "bench/scripts/generate_ffr_online_manifest.py",
                "--output", str(manifest),
            ],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        entries = [json.loads(line) for line in manifest.read_text().splitlines()]
        if len(entries) != 45 or len({row["sample_id"] for row in entries}) != 45:
            raise AssertionError("FFR-online manifest must contain 45 unique points")
        if entries[0]["taps"] != [63, 127]:
            raise AssertionError("unexpected first controlled support")

        subprocess.run(
            [
                "python3", "bench/scripts/collect_ffr_online_benchmark.py",
                "--binary", str(args.binary), "--manifest", str(manifest),
                "--output", str(raw), "--inputs", "2", "--repeats", "2",
                "--trials", "3", "--limit", "1",
            ],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "python3", "bench/scripts/analyze_ffr_online_benchmark.py",
                "--input", str(raw), "--output", str(summary),
                "--min-trials", "3",
            ],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        with summary.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1 or float(rows[0]["Online_over_Planned"]) <= 0:
            raise AssertionError("invalid FFR-online summary")
        if rows[0]["PlannedFFR_plan_bytes"] == rows[0]["OnlineFFR_workspace_bytes"]:
            raise AssertionError("planned schedule and online workspace were conflated")
    print("FFR-online experiment pipeline: PASS")


if __name__ == "__main__":
    main()
