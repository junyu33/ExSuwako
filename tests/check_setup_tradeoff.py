#!/usr/bin/env python3
"""Contract checks for setup amortization and work/depth/setup figures."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


FIELDS = [
    "sample_id", "m", "h", "taps", "Delta_min", "feedback_stages", "W_fb",
    "provenance", "git_commit", "compiler_version", "compiler_flags",
    "gf2x_library", "platform", "machine", "hostname", "cpu_affinity",
    "frequency_policy", "word_bits", "input_distribution", "implementation",
    "multiplication_backend", "seed", "plan_storage_model",
    "timing_scope", "setup_scope", "measurement_trials", "measurement_trial",
    "GS_setup_ns", "GS_ns", "Serial_setup_ns", "Serial_ns",
    "BarrettGF2X_setup_ns", "BarrettGF2X_ns", "LopezDahabLoop_setup_ns",
    "LopezDahabLoop_ns",
]


def run(plotter: Path, source: Path, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        sys.executable, str(plotter), "--input", str(source),
        "--amortization-data", str(root / "amortization.csv"),
        "--amortization-figure", str(root / "amortization.svg"),
        "--tradeoff-figure", str(root / "tradeoff.svg"),
        "--k-values", "1", "4", "16",
        "--plot-methods", "Serial", "BarrettGF2X",
    ], capture_output=True, text=True)


def write_fixture(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for m in (128, 512, 2048, 8192, 32768, 131072):
            stages = m.bit_length() - 1
            for support in (0, 1):
                for trial in range(3):
                    writer.writerow({
                        "sample_id": f"m{m}-s{support}", "m": m,
                        "h": 3 + support * 2, "taps": f"1;{m - 1}",
                        "Delta_min": 1, "feedback_stages": stages,
                        "W_fb": m * (support + 1),
                        "provenance": "fixture:v1", "git_commit": "0123456789abcdef",
                        "compiler_version": "fixture cc 1", "compiler_flags": "-O3",
                        "gf2x_library": "/fixture/libgf2x.so", "platform": "fixture-os",
                        "machine": "x86_64", "hostname": "fixture-host",
                        "cpu_affinity": "3", "frequency_policy": "fixture-fixed",
                        "word_bits": "64", "input_distribution": "uniform-full-range:v1",
                        "implementation": "portable-scalar-c:v1",
                        "multiplication_backend": "gf2x:v1", "seed": "42",
                        "plan_storage_model": "requested-owned-bytes:v1",
                        "timing_scope": "reduction-steady-state:v1",
                        "setup_scope": "modulus-plan:v1",
                        "measurement_trials": 3, "measurement_trial": trial,
                        "GS_setup_ns": 100 + trial, "GS_ns": 20 + support,
                        "Serial_setup_ns": 30, "Serial_ns": 40 + support,
                        "BarrettGF2X_setup_ns": 500 + trial,
                        "BarrettGF2X_ns": 10 + support,
                        "LopezDahabLoop_setup_ns": 0,
                        "LopezDahabLoop_ns": 0,
                    })


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    plotter = repository / "bench" / "scripts" / "plot_setup_tradeoff.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-setup-tradeoff-") as directory:
        root = Path(directory)
        source = root / "raw.csv"
        write_fixture(source)
        completed = run(plotter, source, root)
        if completed.returncode:
            raise AssertionError(completed.stderr)
        with (root / "amortization.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        selected = next(
            row for row in rows
            if row["sample_id"] == "m128-s0" and row["method"] == "GS"
            and row["K"] == "4"
        )
        if float(selected["setup_median_ns"]) != 101.0:
            raise AssertionError("setup median was not preserved")
        if float(selected["amortized_median_components_ns"]) != 45.25:
            raise AssertionError("setup amortization formula is incorrect")
        if selected["compiler_version"] != "fixture cc 1" or selected["seed"] != "42":
            raise AssertionError("derived rows dropped experiment provenance")
        for name in ("amortization.svg", "tradeoff.svg"):
            tree = ET.parse(root / name)
            text = " ".join(node.text or "" for node in tree.iter())
            if "m = 128" not in text or "m = 131072" not in text:
                raise AssertionError(f"{name} does not contain six panels")

        bad = root / "bad.csv"
        write_fixture(bad)
        rows = list(csv.DictReader(bad.open(newline="", encoding="utf-8")))
        rows[0]["setup_scope"] = "hidden-setup"
        with bad.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        if run(plotter, bad, root).returncode == 0:
            raise AssertionError("incompatible setup scope was accepted")
    print("setup amortization and tradeoff contract checks passed")


if __name__ == "__main__":
    main()
