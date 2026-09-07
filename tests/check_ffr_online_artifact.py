#!/usr/bin/env python3
"""Contract checks for the external-data FFR-online artifact driver."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    analyzer = repository / "bench/scripts/analyze_ffr_online_benchmark.py"
    driver = repository / "bench/scripts/reproduce_ffr_online_artifact.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-online-artifact-") as directory:
        root = Path(directory)
        data = root / "data"
        data.mkdir()
        raw = data / "raw.csv"
        fields = [
            "sample_id", "trial", "taps", "m", "h", "Delta_min",
            "input_distribution", "timing_scope", "setup_scope",
            "PlannedFFR_ns", "OnlineFFR_ns", "PlannedFFR_setup_ns",
            "OnlineFFR_setup_ns", "PlannedFFR_plan_bytes",
            "OnlineFFR_workspace_bytes", "git_commit", "git_dirty",
            "binary_sha256", "compiler_flags", "platform", "cpu_affinity",
        ]
        with raw.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for trial in range(31):
                writer.writerow({
                    "sample_id": "online-test", "trial": trial, "taps": "7",
                    "m": 8, "h": 2, "Delta_min": 1,
                    "input_distribution": "uniform-full-range:v1",
                    "timing_scope": "ffr-online-steady-state:v1",
                    "setup_scope": "ffr-online-workspace:v1",
                    "PlannedFFR_ns": 10 + trial / 100,
                    "OnlineFFR_ns": 11 + trial / 100,
                    "PlannedFFR_setup_ns": 20, "OnlineFFR_setup_ns": 2,
                    "PlannedFFR_plan_bytes": 128,
                    "OnlineFFR_workspace_bytes": 64,
                    "git_commit": "a" * 40, "git_dirty": 0,
                    "binary_sha256": "b" * 64, "compiler_flags": "-O3",
                    "platform": "test", "cpu_affinity": 0,
                })
        expected_summary = root / "expected.csv"
        subprocess.run(
            [sys.executable, str(analyzer), "--input", str(raw),
             "--output", str(expected_summary), "--min-trials", "31"],
            cwd=repository, check=True, capture_output=True, text=True,
        )
        config = root / "config.json"
        config.write_text(json.dumps({
            "schema": "exsuwako-ffr-online-artifact:v1",
            "raw_dataset": {
                "file": "raw.csv", "rows": 31, "samples": 1,
                "trials_per_sample": 31, "sha256": sha256(raw),
            },
            "expected_summary": {
                "rows": 1, "sha256": sha256(expected_summary),
            },
        }), encoding="utf-8")
        output = root / "output"
        good = subprocess.run(
            [sys.executable, str(driver), "--config", str(config),
             "--data-root", str(data), "--output", str(output)],
            cwd=repository, capture_output=True, text=True,
        )
        if good.returncode or "summary_rows=1" not in good.stdout:
            raise AssertionError(good.stderr or good.stdout)
        with raw.open("a", encoding="utf-8") as stream:
            stream.write("tampered\n")
        bad = subprocess.run(
            [sys.executable, str(driver), "--config", str(config),
             "--data-root", str(data), "--verify-only"],
            cwd=repository, capture_output=True, text=True,
        )
        if bad.returncode == 0 or "SHA-256 mismatch" not in bad.stderr:
            raise AssertionError("tampered FFR-online artifact was not rejected")
    print("FFR-online artifact driver contract checks passed")


if __name__ == "__main__":
    main()
