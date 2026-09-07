#!/usr/bin/env python3
"""Contract checks for the external-data paper artifact driver."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    script = repository / "bench" / "scripts" / "reproduce_paper_artifact.py"
    with tempfile.TemporaryDirectory(prefix="exsuwako-artifact-driver-") as directory:
        root = Path(directory)
        data = root / "data"
        data.mkdir()
        raw = data / "raw.csv"
        fields = [
            "sample_id", "git_commit", "binary_sha256", "metadata_status",
            "driver_command", "benchmark_command", "m", "h", "taps",
            "measurement_trial", "GS_ns", "BarrettGF2X_ns",
        ]
        with raw.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "sample_id": "test", "git_commit": "a" * 40,
                "binary_sha256": "b" * 64, "metadata_status": "paper-grade",
                "driver_command": "driver", "benchmark_command": "benchmark",
                "m": 8, "h": 2, "taps": "7", "measurement_trial": 0,
                "GS_ns": 1, "BarrettGF2X_ns": 2,
            })
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        config = root / "config.json"
        config.write_text(json.dumps({
            "schema": "exsuwako-paper-artifact:v1",
            "raw_dataset": {"file": "raw.csv", "rows": 1, "sha256": digest},
            "random_manifests": [], "expected_outputs": {},
        }), encoding="utf-8")
        good = subprocess.run([
            sys.executable, str(script), "--config", str(config),
            "--data-root", str(data), "--verify-only",
        ], capture_output=True, text=True)
        if good.returncode or "raw_rows=1" not in good.stdout:
            raise AssertionError(good.stderr or good.stdout)
        raw.write_text(raw.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
        bad = subprocess.run([
            sys.executable, str(script), "--config", str(config),
            "--data-root", str(data), "--verify-only",
        ], capture_output=True, text=True)
        if bad.returncode == 0 or "SHA-256 mismatch" not in bad.stderr:
            raise AssertionError("tampered raw artifact was not rejected")
    print("paper artifact driver contract checks passed")


if __name__ == "__main__":
    main()
