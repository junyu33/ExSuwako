#!/usr/bin/env python3
"""Contract checks for work/runtime and random-support geometry plots."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET


TIMING_FIELDS = [
    "sample_id", "m", "h", "taps", "Delta_min", "W_fb", "GS_ns",
    "measurement_trials", "measurement_trial", "timing_scope",
    "GS_source_cost_model", "batch_repeats", "warmup_runs",
    "input_distribution", "metadata_status",
]


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "bench" / "scripts" / "plot_work_random_geometry.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-work-random-") as directory:
        root = Path(directory)
        timing = root / "timing.csv"
        manifests = []
        degrees = (128, 512, 2048, 8192, 32768, 131072)
        with timing.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=TIMING_FIELDS)
            writer.writeheader()
            for m in degrees:
                for support in range(2):
                    for trial in range(3):
                        writer.writerow({
                            "sample_id": f"m{m}-s{support}", "m": m,
                            "h": support + 2, "taps": str(m - support - 1),
                            "Delta_min": support + 1, "W_fb": m * (support + 1),
                            "GS_ns": 10 + support * 10 + trial,
                            "measurement_trials": 3, "measurement_trial": trial,
                            "timing_scope": "reduction-steady-state:v1",
                            "GS_source_cost_model": "scalar-source-v1",
                            "batch_repeats": 12, "warmup_runs": 1,
                            "input_distribution": "uniform-full-range:v1",
                            "metadata_status": "paper-grade",
                        })
        for m in degrees:
            path = root / f"random-m{m}.jsonl"
            manifests.append(path)
            with path.open("w", encoding="utf-8") as stream:
                for s in (1, 2):
                    for sample in range(2):
                        taps = list(range(1 + sample, 1 + sample + s))
                        row = {
                            "sample_id": f"random-m{m}-s{s}-{sample}",
                            "provenance": "synthetic-fixed-weight-uniform-constant-free:v1",
                            "m": m, "taps": taps, "support_sampler": "fixture:v1",
                            "support_seed": 42, "cell_population": "fixture",
                            "requested_supports": 2, "realized_supports": 2,
                            "constant_policy": "absent",
                        }
                        stream.write(json.dumps(row) + "\n")
        command = [
            sys.executable, str(script), "--timing-input", str(timing),
            "--random-manifest", *(str(path) for path in manifests),
            "--work-runtime-figure", str(root / "runtime.svg"),
            "--work-runtime-summary", str(root / "runtime.csv"),
            "--random-summary", str(root / "random.csv"),
            "--random-depth-figure", str(root / "depth.svg"),
            "--random-work-figure", str(root / "work.svg"),
            "--min-trials", "3", "--paper-grade",
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode:
            raise AssertionError(completed.stderr)
        for filename in ("runtime.svg", "depth.svg", "work.svg"):
            text = " ".join(node.text or "" for node in ET.parse(root / filename).iter())
            if "m = 128" not in text or "m = 131072" not in text:
                raise AssertionError(f"{filename} does not contain six panels")
        rows = list(csv.DictReader((root / "random.csv").open(newline="", encoding="utf-8")))
        if len(rows) != 12 or {row["samples"] for row in rows} != {"2"}:
            raise AssertionError("random support cells were not summarized exactly")
        if {row["predictor"] for row in csv.DictReader(
            (root / "runtime.csv").open(newline="", encoding="utf-8")
        )} != {"W_fb"}:
            raise AssertionError("work/runtime summary mislabeled its predictor")
    print("work/runtime and random-geometry contract checks passed")


if __name__ == "__main__":
    main()
