#!/usr/bin/env python3
"""Contract checks for winner classification and 2x3 block SVG rendering."""

from __future__ import annotations

import csv
import math
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


FIELDS = [
    "sample_id", "provenance", "m", "word_bits", "s", "h", "taps",
    "Delta_min", "log2_m_over_delta", "input_distribution", "timing_scope",
    "setup_scope", "timing_order", "aggregation", "inputs", "batch_repeats",
    "warmup_runs", "measurement_trials", "measurement_trial", "seed",
    "Serial_enabled", "Dense_enabled", "Generated_enabled", "LopezDahabLoop_enabled",
    "GS_ns", "Serial_ns", "BarrettGF2X_ns", "Dense_ns",
    "LopezDahabLoop_ns",
]


def run(command: list[str], succeeds: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    if (completed.returncode == 0) != succeeds:
        raise AssertionError(
            f"unexpected command status {completed.returncode}:\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def measurements(kind: str, trial: int) -> tuple[float, float, float, float, float]:
    if kind == "gs":
        return 10, 15, 20, 0, 0
    if kind == "serial":
        return 20, 10, 30, 0, 0
    if kind == "barrett":
        return 20, 30, 10, 0, 0
    if kind == "operational":
        return 10, 10.05, 30, 0, 0
    if kind == "statistical":
        serial = 10 / (0.989 if trial < 16 else 1.001)
        return 10, serial, 30, 0, 0
    if kind == "unstable":
        gs = 8 if trial < 16 else 12
        return gs, 20, 30, 0, 0
    if kind == "dense":
        return 20, 30, 40, 10, 0
    if kind == "ld":
        return 20, 30, 40, 0, 10
    if kind == "ld-boundary":
        return 20, 0, 40, 0, 10
    if kind == "no-serial":
        return 10, 0, 20, 0, 0
    raise AssertionError(f"unknown fixture kind {kind}")


def write_fixture(path: Path) -> None:
    specifications = [
        ("gs", 128, 1),
        ("operational", 512, 1),
        ("statistical", 2048, 1),
        ("unstable", 8192, 1),
        ("serial", 32768, 1),
        ("barrett", 131072, 1),
        ("dense", 128, 2),
        ("ld", 512, 128),
        ("ld-boundary", 512, 64),
        ("no-serial", 128, 4),
    ]
    rows: list[dict[str, object]] = []
    for kind, m, delta in specifications:
        taps = f"1;{m - delta}"
        for trial in range(31):
            gs, serial, barrett, dense, ld = measurements(kind, trial)
            rows.append({
                "sample_id": f"{kind}-m{m}",
                "provenance": "winner-contract-fixture:v1",
                "m": m,
                "word_bits": 64,
                "s": 2,
                "h": 3,
                "taps": taps,
                "Delta_min": delta,
                "log2_m_over_delta": math.log2(m / delta),
                "input_distribution": "uniform-full-range:v1",
                "timing_scope": "reduction-steady-state:v1",
                "setup_scope": "modulus-plan:v1",
                "timing_order": "cyclic-method-rotation:v1",
                "aggregation": "median-of-trial-medians:no-outlier-removal:v1",
                "inputs": 8,
                "batch_repeats": 12,
                "warmup_runs": 1,
                "measurement_trials": 31,
                "measurement_trial": trial,
                "seed": 17,
                "Serial_enabled": int(kind not in ("no-serial", "ld-boundary")),
                "Dense_enabled": int(kind == "dense"),
                "Generated_enabled": 0,
                "LopezDahabLoop_enabled": int(kind in ("ld", "ld-boundary")),
                "GS_ns": gs,
                "Serial_ns": serial,
                "BarrettGF2X_ns": barrett,
                "Dense_ns": dense,
                "LopezDahabLoop_ns": ld,
            })
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    analyzer = repository / "bench" / "scripts" / "analyze_winner_panels.py"
    plotter = repository / "bench" / "scripts" / "plot_winner_panels.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-winners-") as directory:
        root = Path(directory)
        source = root / "raw.csv"
        points = root / "points.csv"
        comparisons = root / "comparisons.csv"
        summary = root / "summary.csv"
        figure = root / "winners.svg"
        write_fixture(source)
        command = [
            sys.executable, str(analyzer), "--input", str(source),
            "--points", str(points), "--comparisons", str(comparisons),
            "--summary", str(summary),
        ]
        run(command)
        with points.open(newline="", encoding="utf-8") as stream:
            rows = {row["sample_id"]: row for row in csv.DictReader(stream)}
        expected = {
            "gs-m128": ("GS", "unique-winner"),
            "serial-m32768": ("Serial", "unique-winner"),
            "barrett-m131072": ("BarrettGF2X", "unique-winner"),
            "dense-m128": ("Dense", "unique-winner"),
            "ld-m512": ("LopezDahabLoop", "unique-winner"),
            "ld-boundary-m512": ("LopezDahabLoop", "unique-winner"),
            "no-serial-m128": ("GS", "unique-winner"),
            "operational-m512": ("uncertain", "operational-tie"),
            "statistical-m2048": ("uncertain", "statistical-tie"),
            "unstable-m8192": ("uncertain", "timing-unstable"),
        }
        if {
            sample_id: (row["winner"], row["winner_reason"])
            for sample_id, row in rows.items()
        } != expected:
            raise AssertionError("winner classifications changed")
        if "LopezDahabLoop" not in rows["ld-m512"]["method_set"]:
            raise AssertionError("López-Dahab method set was not preserved")
        if (
            "Serial" in rows["no-serial-m128"]["method_set"].split(";")
            or "Serial:not-enabled" not in rows["no-serial-m128"]["unavailable_methods"]
        ):
            raise AssertionError("disabled Serial was not excluded and labelled")
        if "LopezDahabLoop:degree-assumption" not in rows["gs-m128"][
            "unavailable_methods"
        ]:
            raise AssertionError("method inapplicability was not labelled")
        with comparisons.open(newline="", encoding="utf-8") as stream:
            comparison_rows = list(csv.DictReader(stream))
        if not comparison_rows or any(
            row["comparison_contract"] != "paired-bootstrap-one-percent:v1"
            for row in comparison_rows
        ):
            raise AssertionError("paired comparison contract is missing")
        with summary.open(newline="", encoding="utf-8") as stream:
            summary_rows = {row["m"]: row for row in csv.DictReader(stream)}
        if summary_rows["128"]["Dense_decision"] != "promote-contract-review":
            raise AssertionError("Dense qualification threshold changed")

        plotted = run([
            sys.executable, str(plotter), "--input", str(points),
            "--output", str(figure), "--columns", "3",
            "--boundary-input", str(points),
        ])
        if "panels=6" not in plotted.stdout or "columns=3" not in plotted.stdout:
            raise AssertionError("winner plot did not use the 2x3 contract")
        tree = ET.parse(figure)
        text = " ".join(node.text or "" for node in tree.iter())
        for label in [
            "m = 128", "m = 131072", "no boundary interpolation",
            "log2(h - 1)", "log2(m / Delta_min)",
        ]:
            if label not in text:
                raise AssertionError(f"winner SVG is missing {label!r}")
        if "uncertain=" in text:
            raise AssertionError("winner SVG retained the panel count annotation")
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        cells = tree.findall(".//svg:rect[@class='cell']", namespace)
        if len(cells) != len(rows):
            raise AssertionError("block plot does not contain one cell per measured point")
        boundaries = [
            node for node in tree.findall(".//svg:line", namespace)
            if "predicted-boundary" in node.attrib.get("class", "").split()
        ]
        if len(boundaries) < 2:
            raise AssertionError("predicted winner boundaries were not overlaid")
        boundary_classes = {
            name
            for node in boundaries
            for name in node.attrib.get("class", "").split()
        }
        for name in ["boundary-gs-barrett", "boundary-gs-ld", "boundary-ld-barrett"]:
            if name not in boundary_classes:
                raise AssertionError(f"winner SVG is missing {name!r}")

        numeric_points = root / "numeric-points.csv"
        numeric_figure = root / "numeric-winners.svg"
        numeric_fields = [
            "sample_id", "m", "h", "log2_m_over_delta", "winner",
            "winner_reason", "method_set",
        ]
        with numeric_points.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=numeric_fields)
            writer.writeheader()
            for h, log_ratio in zip((65, 81, 97), (1, 1.25, 2)):
                writer.writerow({
                    "sample_id": f"numeric-h{h}",
                    "m": 128,
                    "h": h,
                    "log2_m_over_delta": log_ratio,
                    "winner": "GS",
                    "winner_reason": "unique-winner",
                    "method_set": "GS;BarrettGF2X",
                })
        run([
            sys.executable, str(plotter), "--input", str(numeric_points),
            "--output", str(numeric_figure), "--mode", "blocks",
        ])
        numeric_tree = ET.parse(numeric_figure)
        numeric_x_grid = sorted(
            float(node.attrib["x1"])
            for node in numeric_tree.findall(".//svg:line[@class='grid']", namespace)
            if node.attrib["x1"] == node.attrib["x2"]
        )
        observed_gap_ratio = (numeric_x_grid[1] - numeric_x_grid[0]) / (
            numeric_x_grid[2] - numeric_x_grid[1]
        )
        expected_gap_ratio = (
            (math.log2(80) - math.log2(64))
            / (math.log2(96) - math.log2(80))
        )
        if not math.isclose(
            observed_gap_ratio, expected_gap_ratio, rel_tol=0.03
        ):
            raise AssertionError(
                "winner SVG uses ordinal rather than numerical log2(h-1) spacing"
            )
        numeric_y_grid = sorted(
            (
                float(node.attrib["y1"])
                for node in numeric_tree.findall(
                    ".//svg:line[@class='grid']", namespace
                )
                if node.attrib["y1"] == node.attrib["y2"]
            ),
            reverse=True,
        )
        observed_y_gap_ratio = (
            (numeric_y_grid[0] - numeric_y_grid[1])
            / (numeric_y_grid[1] - numeric_y_grid[2])
        )
        if not math.isclose(observed_y_gap_ratio, 1 / 3, rel_tol=0.03):
            raise AssertionError(
                "winner SVG uses ordinal rather than numerical log-ratio spacing"
            )

        incomplete = root / "incomplete.csv"
        with source.open(newline="", encoding="utf-8") as stream:
            source_rows = list(csv.DictReader(stream))
        with incomplete.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(source_rows[1:])
        rejected = list(command)
        rejected[rejected.index(str(source))] = str(incomplete)
        run(rejected, succeeds=False)

        duplicate = root / "duplicate.csv"
        duplicate_rows = list(source_rows)
        for row in source_rows[:31]:
            copy = dict(row)
            copy["sample_id"] = "duplicate-support"
            duplicate_rows.append(copy)
        with duplicate.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(duplicate_rows)
        rejected = list(command)
        rejected[rejected.index(str(source))] = str(duplicate)
        run(rejected, succeeds=False)

        mixed = root / "mixed.csv"
        mixed_rows = [dict(row) for row in source_rows]
        mixed_rows[1]["timing_order"] = "different-order:v1"
        with mixed.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(mixed_rows)
        rejected = list(command)
        rejected[rejected.index(str(source))] = str(mixed)
        run(rejected, succeeds=False)

        missing_ld = root / "missing-ld.csv"
        missing_ld_rows = [dict(row) for row in source_rows]
        for row in missing_ld_rows:
            if row["sample_id"] == "ld-m512":
                row["provenance"] = "synthetic-controlled-cartesian-spread-constant-free:v1"
                row["LopezDahabLoop_enabled"] = "0"
                row["LopezDahabLoop_ns"] = "0"
        with missing_ld.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(missing_ld_rows)
        rejected = list(command)
        rejected[rejected.index(str(source))] = str(missing_ld)
        run(rejected, succeeds=False)
    print("winner-panel analysis and SVG contract checks passed")


if __name__ == "__main__":
    main()
