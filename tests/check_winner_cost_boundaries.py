#!/usr/bin/env python3
"""Contract checks for the fitted winner-boundary analysis."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


FIELDS = [
    "sample_id", "m", "word_bits", "s", "h", "taps", "Delta_min",
    "log2_m_over_delta", "method_set", "winner", "winner_reason",
    "GS_median_ns", "BarrettGF2X_median_ns", "LopezDahabLoop_median_ns",
]


def run(command: list[str], succeeds: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    if (completed.returncode == 0) != succeeds:
        raise AssertionError(
            f"unexpected status {completed.returncode}: {command}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def fixture_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for h in range(2, 8):
        taps = [*range(max(0, h - 2)), 64]
        taps = sorted(set(taps))
        if len(taps) != h - 1:
            raise AssertionError("test fixture has duplicate taps")
        gs_work = sum((128 - tap + 63) // 64 for tap in taps)
        for tap in taps:
            shift = 128 - tap
            while shift < 128:
                gs_work += (128 - shift + 63) // 64
                shift *= 2
        ld_work = 2 * len(taps)
        rows.append({
            "sample_id": f"m128-h{h}", "m": "128", "word_bits": "64",
            "s": str(h - 1), "h": str(h),
            "taps": ";".join(str(tap) for tap in taps),
            "Delta_min": "64", "log2_m_over_delta": "1",
            "method_set": "GS;BarrettGF2X;LopezDahabLoop",
            "winner": "GS", "winner_reason": "unique-winner",
            "GS_median_ns": str(10 + 2 * gs_work),
            "BarrettGF2X_median_ns": "100",
            "LopezDahabLoop_median_ns": str(20 + 3 * ld_work),
        })
    return rows


def write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "bench" / "scripts" / "fit_winner_cost_boundaries.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-cost-boundaries-") as directory:
        root = Path(directory)
        source = root / "points.csv"
        output = root / "predictions.csv"
        repeat = root / "predictions-repeat.csv"
        diagnostics = root / "diagnostics.csv"
        repeat_diagnostics = root / "diagnostics-repeat.csv"
        write(source, fixture_rows())
        command = [
            sys.executable, str(script), "--input", str(source),
            "--output", str(output), "--diagnostics", str(diagnostics),
        ]
        run(command)
        run([
            sys.executable, str(script), "--input", str(source),
            "--output", str(repeat), "--diagnostics", str(repeat_diagnostics),
        ])
        if output.read_bytes() != repeat.read_bytes():
            raise AssertionError("winner predictions are not deterministic")
        if diagnostics.read_bytes() != repeat_diagnostics.read_bytes():
            raise AssertionError("fit diagnostics are not deterministic")

        with output.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if [row["cost_model_split"] for row in rows] != [
            "calibration", "holdout", "calibration", "holdout",
            "calibration", "holdout",
        ]:
            raise AssertionError("deterministic calibration split changed")
        if any(row["measured_winner"] != "GS" for row in rows):
            raise AssertionError("measured winner was not preserved")
        if any(row["winner_reason"] != "cost-model-prediction" for row in rows):
            raise AssertionError("predicted winner was not labelled")
        if any(float(row["GS_predicted_ns"]) != float(row["GS_median_ns"])
               for row in rows):
            raise AssertionError("exact affine GS fixture was not recovered")
        if any(float(row["LopezDahabLoop_predicted_ns"])
               != float(row["LopezDahabLoop_median_ns"]) for row in rows):
            raise AssertionError("exact affine Lopez-Dahab fixture was not recovered")

        with diagnostics.open(newline="", encoding="utf-8") as stream:
            methods = {row["method"] for row in csv.DictReader(stream)}
        if methods != {"GS", "BarrettGF2X", "LopezDahabLoop"}:
            raise AssertionError("fit diagnostics omit a model method")

        duplicate = root / "duplicate.csv"
        write(duplicate, fixture_rows() + fixture_rows()[:1])
        rejected = list(command)
        rejected[rejected.index(str(source))] = str(duplicate)
        run(rejected, succeeds=False)

    print("winner cost-boundary checks passed")


if __name__ == "__main__":
    main()
