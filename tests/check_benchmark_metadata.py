#!/usr/bin/env python3
"""Contract checks for captured and emitted benchmark metadata."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], succeeds: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    if (completed.returncode == 0) != succeeds:
        raise AssertionError(
            f"unexpected command status {completed.returncode}:\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    repository = Path(__file__).resolve().parents[1]
    capture = repository / "bench" / "scripts" / "capture_benchmark_metadata.py"
    driver = repository / "bench" / "scripts" / "phase_diagram_benchmark.py"
    cpu = min(os.sched_getaffinity(0))
    with tempfile.TemporaryDirectory(prefix="exsuwako-metadata-") as directory:
        root = Path(directory)
        metadata_path = root / "metadata.json"
        run([
            sys.executable, str(capture), "--binary", str(binary),
            "--output", str(metadata_path), "--cc", "cc",
            "--cflags", "-O3 -std=c11 -Wall -Wextra", "--cpu", str(cpu),
        ])
        metadata = json.loads(metadata_path.read_text())
        if (
            metadata["metadata_schema"] != "exsuwako-native-platform:v1"
            or metadata["cpu_affinity"] != cpu
            or not Path(metadata["gf2x_library"]).is_file()
            or len(metadata["binary_sha256"]) != 64
        ):
            raise AssertionError("captured benchmark metadata is incomplete")

        manifest = root / "manifest.jsonl"
        manifest.write_text(
            json.dumps({
                "sample_id": "metadata-smoke",
                "provenance": "metadata-contract:v1",
                "m": 17,
                "taps": [1, 16],
            }) + "\n",
            encoding="utf-8",
        )
        output = root / "output.csv"
        base = [
            sys.executable, str(driver), "--binary", str(binary),
            "--manifest", str(manifest), "--output", str(output),
            "--inputs", "1", "--repeats", "3", "--seed", "1",
            "--no-naive",
        ]
        run(base + ["--metadata", str(metadata_path)])
        with output.open(newline="", encoding="utf-8") as stream:
            row = next(csv.DictReader(stream))
        if (
            row["metadata_status"] != "recorded-exploratory"
            or row["git_commit"] != metadata["git_commit"]
            or row["binary_sha256"] != metadata["binary_sha256"]
            or row["cpu_affinity"] != str(cpu)
            or "reduction_benchmark" not in row["benchmark_command"]
            or "phase_diagram_benchmark.py" not in row["driver_command"]
        ):
            raise AssertionError("phase output did not preserve run metadata")

        run(base + ["--paper-grade"], succeeds=False)
        dirty = dict(metadata)
        dirty["git_dirty"] = True
        dirty_path = root / "dirty.json"
        dirty_path.write_text(json.dumps(dirty), encoding="utf-8")
        run(base + ["--metadata", str(dirty_path), "--paper-grade"], succeeds=False)
    print("benchmark metadata contract checks passed")


if __name__ == "__main__":
    main()
