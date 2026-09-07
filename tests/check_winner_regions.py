#!/usr/bin/env python3
"""Contract checks for deterministic winner-region summaries."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


FIELDS = [
    "sample_id", "m", "word_bits", "h", "Delta_min",
    "log2_m_over_delta", "winner", "winner_reason",
]


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "bench" / "scripts" / "summarize_winner_regions.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-regions-") as directory:
        root = Path(directory)
        source, detail, summary = root / "points.csv", root / "detail.csv", root / "summary.csv"
        rows = []
        for delta, winners in [
            (1, ["GS", "GS", "BarrettGF2X"]),
            (64, ["LopezDahabLoop", "uncertain", "BarrettGF2X"]),
        ]:
            for h, winner in zip((2, 3, 5), winners):
                rows.append({
                    "sample_id": f"d{delta}-h{h}", "m": 128, "word_bits": 64,
                    "h": h, "Delta_min": delta,
                    "log2_m_over_delta": 7 if delta == 1 else 1,
                    "winner": winner,
                    "winner_reason": "timing-unstable" if winner == "uncertain" else "unique-winner",
                })
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)
        completed = subprocess.run([
            sys.executable, str(script), "--input", str(source),
            "--detail", str(detail), "--summary", str(summary),
        ], capture_output=True, text=True)
        if completed.returncode:
            raise AssertionError(completed.stderr)
        with detail.open(newline="", encoding="utf-8") as stream:
            details = {(row["regime"], row["Delta_min"]): row for row in csv.DictReader(stream)}
        if details[("hard-feedback", "1")]["persistent_Barrett_h"] != "5":
            raise AssertionError("hard-feedback crossover changed")
        friendly = details[("ld-applicable", "64")]
        if friendly["persistent_Barrett_h"] != "5" or friendly["uncertain"] != "1":
            raise AssertionError("uncertainty or friendly crossover changed")
        with summary.open(newline="", encoding="utf-8") as stream:
            summaries = list(csv.DictReader(stream))
        if len(summaries) != 2 or any(row["persistent_Barrett_rows"] != "1" for row in summaries):
            raise AssertionError("region aggregation changed")
    print("winner-region summary contract checks passed")


if __name__ == "__main__":
    main()
