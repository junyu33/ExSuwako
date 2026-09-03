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
    expected = {
        "m": "16",
        "word_bits": "64",
        "s": "3",
        "h": "4",
        "taps": "0;3;7",
        "Delta_min": "9",
        "feedback_stages": "1",
        "active_tap_counts": "2",
        "input_distribution": "uniform-full-range:v1",
        "timing_scope": "reduction-steady-state:v1",
        "setup_scope": "modulus-plan:v1",
        "timing_order": "cyclic-method-rotation:v1",
    }
    for field, value in expected.items():
        if row[field] != value:
            raise AssertionError(f"{field}: expected {value!r}, got {row[field]!r}")
    for field in [
        "GS_setup_ns", "Serial_setup_ns", "Naive_setup_ns",
        "BarrettGF2X_setup_ns",
    ]:
        if float(row[field]) < 0:
            raise AssertionError(f"{field} must be nonnegative")

    empty = parse_one_row(
        run(base + ["-", "2", "1", "16", "0x2"]).stdout
    )
    if (
        empty["s"], empty["h"], empty["taps"], empty["Delta_min"],
        empty["feedback_stages"], empty["active_tap_counts"],
    ) != (
        "0",
        "1",
        "-",
        "NA",
        "0",
        "-",
    ):
        raise AssertionError(f"unexpected empty-support row: {empty}")

    for invalid in ["3,2", "2,2", "16", "0,", "x", ""]:
        run(base + [invalid, "1", "1", "16", "0x3", "no-naive"], succeeds=False)
    run(base + ["0,3,7", "1", "1", "16", "0", "no-naive"], succeeds=False)


def check_manifest(binary: Path, driver: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="exsuwako-manifest-") as directory:
        root = Path(directory)
        manifest = root / "supports.jsonl"
        output = root / "results.csv"
        entries = [
            {
                "sample_id": "empty",
                "provenance": "synthetic-boundary:v1",
                "m": 16,
                "taps": [],
            },
            {
                "sample_id": "exact-0-3-7",
                "provenance": "hand-constructed-example:v1",
                "m": 16,
                "taps": [0, 3, 7],
            },
            {
                "sample_id": "constant-only",
                "provenance": "synthetic-boundary:v1",
                "m": 16,
                "taps": [0],
            },
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
        if [row["sample_id"] for row in rows] != [
            "empty",
            "exact-0-3-7",
            "constant-only",
        ]:
            raise AssertionError("manifest sample identifiers were not preserved")
        if [row["provenance"] for row in rows] != [
            "synthetic-boundary:v1",
            "hand-constructed-example:v1",
            "synthetic-boundary:v1",
        ]:
            raise AssertionError("manifest provenance was not preserved")
        if [row["taps"] for row in rows] != ["-", "0;3;7", "0"]:
            raise AssertionError("manifest tap lists were not preserved")
        if [row["feedback_stages"] for row in rows] != ["0", "1", "0"]:
            raise AssertionError("incorrect derived feedback-stage counts")
        if [row["active_tap_counts"] for row in rows] != ["-", "2", "-"]:
            raise AssertionError("incorrect derived active-tap profiles")
        if [row["W_fb"] for row in rows] != ["0", "10", "0"]:
            raise AssertionError("incorrect derived scheduled work")
        if any(
            row["input_distribution"] != "uniform-full-range:v1"
            for row in rows
        ):
            raise AssertionError("input distribution was not preserved")
        if any(
            row["timing_scope"] != "reduction-steady-state:v1"
            for row in rows
        ):
            raise AssertionError("timing scope was not preserved")
        if any(row["setup_scope"] != "modulus-plan:v1" for row in rows):
            raise AssertionError("setup scope was not preserved")
        if any(
            row["timing_order"] != "cyclic-method-rotation:v1"
            for row in rows
        ):
            raise AssertionError("timing order was not preserved")
        if any(
            row["aggregation"]
            != "median-of-trial-medians:no-outlier-removal:v1"
            for row in rows
        ):
            raise AssertionError("aggregation contract was not preserved")
        if any(
            (row["inputs"], row["batch_repeats"], row["warmup_runs"],
             row["measurement_trials"], row["measurement_trial"])
            != ("2", "1", "0", "1", "0")
            for row in rows
        ):
            raise AssertionError("measurement parameters were not preserved")
        if any(
            float(row[field]) < 0
            for row in rows
            for field in [
                "GS_setup_ns", "Serial_setup_ns", "Naive_setup_ns",
                "BarrettGF2X_setup_ns",
            ]
        ):
            raise AssertionError("setup timings must be nonnegative")

        invalid_manifests = [
            [
                {
                    "sample_id": "duplicate",
                    "provenance": "test:v1",
                    "m": 16,
                    "taps": [1],
                },
                {
                    "sample_id": "duplicate",
                    "provenance": "test:v1",
                    "m": 16,
                    "taps": [2],
                },
            ],
            [
                {
                    "sample_id": "unordered",
                    "provenance": "test:v1",
                    "m": 16,
                    "taps": [3, 2],
                }
            ],
            [
                {
                    "sample_id": "out-of-range",
                    "provenance": "test:v1",
                    "m": 16,
                    "taps": [16],
                }
            ],
            [{"sample_id": "missing-provenance", "m": 16, "taps": [1]}],
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

        random_output = root / "random.csv"
        random_command = [
            sys.executable,
            str(driver),
            "--binary",
            str(binary),
            "--output",
            str(random_output),
            "--m",
            "16",
            "--s",
            "3",
            "--samples",
            "2",
            "--inputs",
            "1",
            "--repeats",
            "1",
            "--seed",
            "17",
            "--no-naive",
        ]
        run(random_command)
        with random_output.open(newline="", encoding="utf-8") as stream:
            random_rows = list(csv.DictReader(stream))
        if len(random_rows) != 2:
            raise AssertionError("random driver did not preserve both samples")
        if any(
            row["provenance"] != "synthetic-fixed-weight-uniform:v1"
            for row in random_rows
        ):
            raise AssertionError("random support provenance is incorrect")
        if len({row["sample_id"] for row in random_rows}) != 2 or any(
            "-seed" not in row["sample_id"] for row in random_rows
        ):
            raise AssertionError("random sample identifiers are not stable")

        trial_output = root / "random-trials.csv"
        trial_command = list(random_command)
        trial_command[trial_command.index(str(random_output))] = str(trial_output)
        trial_command.extend(
            ["--warmup-runs", "1", "--measurement-trials", "3"]
        )
        run(trial_command)
        with trial_output.open(newline="", encoding="utf-8") as stream:
            trial_rows = list(csv.DictReader(stream))
        if len(trial_rows) != 6:
            raise AssertionError("measurement trials did not preserve raw rows")
        trials_by_sample: dict[str, list[str]] = {}
        for row in trial_rows:
            trials_by_sample.setdefault(row["sample_id"], []).append(
                row["measurement_trial"]
            )
            if (row["warmup_runs"], row["measurement_trials"]) != ("1", "3"):
                raise AssertionError("trial metadata is incorrect")
        if any(trials != ["0", "1", "2"] for trials in trials_by_sample.values()):
            raise AssertionError("measurement-trial indices are incomplete")

        repeated_output = root / "random-repeated.csv"
        repeated_command = list(random_command)
        repeated_command[repeated_command.index(str(random_output))] = str(
            repeated_output
        )
        run(repeated_command)
        with repeated_output.open(newline="", encoding="utf-8") as stream:
            repeated_rows = list(csv.DictReader(stream))
        deterministic_fields = [
            "sample_id", "provenance", "m", "s", "h", "taps",
            "Delta_min", "feedback_stages", "active_tap_counts", "W_fb",
            "seed",
        ]
        if [
            tuple(row[field] for field in deterministic_fields)
            for row in random_rows
        ] != [
            tuple(row[field] for field in deterministic_fields)
            for row in repeated_rows
        ]:
            raise AssertionError("identical driver seeds changed sampled cases")

        regression_manifest = (
            driver.parent.parent / "manifests" / "regression_supports.jsonl"
        )
        regression_output = root / "regression-supports.csv"
        regression_command = [
            sys.executable,
            str(driver),
            "--binary",
            str(binary),
            "--manifest",
            str(regression_manifest),
            "--output",
            str(regression_output),
            "--inputs",
            "1",
            "--repeats",
            "1",
            "--seed",
            "17",
            "--no-naive",
        ]
        run(regression_command)
        with regression_output.open(newline="", encoding="utf-8") as stream:
            regression_rows = list(csv.DictReader(stream))
        if [row["sample_id"] for row in regression_rows] != [
            "regression-empty-m1",
            "regression-dense-m17",
            "regression-word-boundary-m65",
            "regression-constant-free-m127",
        ]:
            raise AssertionError("versioned regression manifest was not replayed")


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
