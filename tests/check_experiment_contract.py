#!/usr/bin/env python3
"""Regression checks for exact tap-list and JSONL manifest inputs."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], *, succeeds: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    if succeeds and completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not succeeds and completed.returncode == 0:
        raise AssertionError(f"invalid command succeeded: {' '.join(command)}")
    return completed


def parse_one_row(output: str) -> dict[str, str]:
    rows = list(csv.DictReader(output.splitlines()))
    if len(rows) != 1:
        raise AssertionError(f"expected one CSV row, got {len(rows)}")
    return rows[0]


def check_exact_cli(binary: Path) -> None:
    base = [str(binary), "--taps"]
    row = parse_one_row(
        run(base + ["0,3,7", "2", "1", "16", "0x1"]).stdout
    )
    expected = {"m": "16", "s": "3", "h": "4", "taps": "0;3;7", "Delta_min": "9"}
    for field, value in expected.items():
        if row[field] != value:
            raise AssertionError(f"{field}: expected {value!r}, got {row[field]!r}")

    empty = parse_one_row(
        run(base + ["-", "2", "1", "16", "0x2"]).stdout
    )
    if (empty["s"], empty["h"], empty["taps"], empty["Delta_min"]) != (
        "0",
        "1",
        "-",
        "NA",
    ):
        raise AssertionError(f"unexpected empty-support row: {empty}")

    for invalid in ["3,2", "2,2", "16", "0,", "x", ""]:
        run(base + [invalid, "1", "1", "16", "0x3", "no-naive"], succeeds=False)


def check_manifest(binary: Path, driver: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="exsuwako-manifest-") as directory:
        root = Path(directory)
        manifest = root / "supports.jsonl"
        output = root / "results.csv"
        entries = [
            {"sample_id": "empty", "m": 16, "taps": []},
            {"sample_id": "exact-0-3-7", "m": 16, "taps": [0, 3, 7]},
        ]
        manifest.write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries),
            encoding="utf-8",
        )
        command = [
            sys.executable,
            str(driver),
            "--binary",
            str(binary),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
            "--inputs",
            "2",
            "--repeats",
            "1",
            "--seed",
            "17",
            "--no-naive",
        ]
        run(command)
        with output.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if [row["sample_id"] for row in rows] != ["empty", "exact-0-3-7"]:
            raise AssertionError("manifest sample identifiers were not preserved")
        if [row["taps"] for row in rows] != ["-", "0;3;7"]:
            raise AssertionError("manifest tap lists were not preserved")

        invalid_manifests = [
            [
                {"sample_id": "duplicate", "m": 16, "taps": [1]},
                {"sample_id": "duplicate", "m": 16, "taps": [2]},
            ],
            [{"sample_id": "unordered", "m": 16, "taps": [3, 2]}],
            [{"sample_id": "out-of-range", "m": 16, "taps": [16]}],
        ]
        for index, invalid_entries in enumerate(invalid_manifests):
            invalid = root / f"invalid-{index}.jsonl"
            invalid.write_text(
                "".join(json.dumps(entry) + "\n" for entry in invalid_entries),
                encoding="utf-8",
            )
            invalid_command = list(command)
            invalid_command[invalid_command.index(str(manifest))] = str(invalid)
            run(invalid_command, succeeds=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()

    binary = args.binary.resolve()
    driver = (
        Path(__file__).resolve().parents[1]
        / "bench"
        / "scripts"
        / "phase_diagram_benchmark.py"
    )
    check_exact_cli(binary)
    check_manifest(binary, driver)
    print("experiment input contract checks passed")


if __name__ == "__main__":
    main()
