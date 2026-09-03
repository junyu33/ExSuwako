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
        "feedback_active_tap_sum": "2",
        "W_fb": "10",
        "GS_source_cost_model": "scalar-source-v1",
        "GS_source_aligned_word_contributions": "1",
        "GS_source_cross_word_contributions": "4",
        "GS_source_word_shifts": "9",
        "GS_source_word_xors": "9",
        "GS_source_logical_word_reads": "7",
        "GS_source_logical_word_writes": "5",
        "GS_source_scratch_words": "2",
        "plan_storage_model": "requested-owned-bytes:v1",
        "input_distribution": "uniform-full-range:v1",
        "timing_scope": "reduction-steady-state:v1",
        "setup_scope": "modulus-plan:v1",
        "timing_order": "cyclic-method-rotation:v1",
        "Dense_enabled": "0",
        "Dense_matrix_limit_bytes": "67108864",
        "Generated_enabled": "0",
        "LopezDahabLoop_enabled": "0",
    }
    for field, value in expected.items():
        if row[field] != value:
            raise AssertionError(f"{field}: expected {value!r}, got {row[field]!r}")
    for field in [
        "GS_ns", "Serial_ns", "BarrettGF2X_ns",
        "Serial/GS", "BarrettGF2X/GS",
    ]:
        if float(row[field]) <= 0:
            raise AssertionError(
                f"primary matched-comparison field {field} must be positive"
            )
    for field in [
        "GS_setup_ns", "Serial_setup_ns", "Naive_setup_ns",
        "BarrettGF2X_setup_ns", "Dense_setup_ns",
        "Generated_setup_ns",
        "LopezDahabLoop_setup_ns",
    ]:
        if float(row[field]) < 0:
            raise AssertionError(f"{field} must be nonnegative")
    for field in [
        "GS_plan_bytes", "Serial_plan_bytes", "Naive_plan_bytes",
        "BarrettGF2X_plan_bytes",
    ]:
        if int(row[field]) <= 0:
            raise AssertionError(f"{field} must be positive")
    for field in [
        "Dense_plan_bytes", "Dense_setup_ns", "Dense_ns", "Dense/GS"
    ]:
        if float(row[field]) != 0:
            raise AssertionError(f"disabled dense field {field} must be zero")
    for field in [
        "Generated_plan_bytes", "Generated_setup_ns", "Generated_ns",
        "Generated/GS",
    ]:
        if float(row[field]) != 0:
            raise AssertionError(f"disabled generated field {field} must be zero")

    lopez_dahab = parse_one_row(
        run(
            base
            + [
                "0,3,6,7", "2", "4", "163", "0x1", "no-naive",
                "with-lopez-dahab",
            ]
        ).stdout
    )
    if lopez_dahab["LopezDahabLoop_enabled"] != "1":
        raise AssertionError("loop Lopez-Dahab baseline was not enabled")
    for field in [
        "LopezDahabLoop_plan_bytes", "LopezDahabLoop_setup_ns",
        "LopezDahabLoop_ns", "LopezDahabLoop/GS",
    ]:
        if float(lopez_dahab[field]) <= 0:
            raise AssertionError(f"enabled loop Lopez-Dahab field {field} is invalid")
    run(
        base
        + [
            "0,100", "1", "4", "163", "0x1", "no-naive",
            "with-lopez-dahab",
        ],
        succeeds=False,
    )

    for field in [
        "LopezDahabLoop_plan_bytes", "LopezDahabLoop_setup_ns",
        "LopezDahabLoop_ns", "LopezDahabLoop/GS",
    ]:
        if float(row[field]) != 0:
            raise AssertionError(
                f"disabled loop Lopez-Dahab field {field} must be zero"
            )

    dense = parse_one_row(
        run(
            base
            + ["0,3,7", "2", "1", "16", "0x1", "no-naive", "with-dense"]
        ).stdout
    )
    if dense["Dense_enabled"] != "1":
        raise AssertionError("dense baseline was not enabled")
    if (
        int(dense["Dense_plan_bytes"]) <= 0
        or float(dense["Dense_setup_ns"]) < 0
    ):
        raise AssertionError("dense setup/storage measurements are invalid")
    if float(dense["Dense_ns"]) <= 0 or float(dense["Dense/GS"]) <= 0:
        raise AssertionError("dense steady-state measurements are invalid")
    run(
        base + ["0,3,7", "1", "1", "16", "0x1", "with-dense"],
        succeeds=False,
    )

    empty = parse_one_row(
        run(base + ["-", "2", "1", "16", "0x2"]).stdout
    )
    if (
        empty["s"], empty["h"], empty["taps"], empty["Delta_min"],
        empty["feedback_stages"], empty["active_tap_counts"],
        empty["feedback_active_tap_sum"], empty["W_fb"],
        empty["GS_source_cost_model"],
        empty["GS_source_aligned_word_contributions"],
        empty["GS_source_cross_word_contributions"],
        empty["GS_source_word_shifts"], empty["GS_source_word_xors"],
        empty["GS_source_logical_word_reads"],
        empty["GS_source_logical_word_writes"],
        empty["GS_source_scratch_words"],
        empty["plan_storage_model"],
    ) != (
        "0",
        "1",
        "-",
        "NA",
        "0",
        "-",
        "0",
        "0",
        "scalar-source-v1",
        "0",
        "0",
        "1",
        "0",
        "3",
        "4",
        "2",
        "requested-owned-bytes:v1",
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
            {
                "sample_id": "gap-one",
                "provenance": "synthetic-boundary:v1",
                "m": 16,
                "taps": [15],
            },
            {
                "sample_id": "aligned-word",
                "provenance": "synthetic-boundary:v1",
                "m": 128,
                "taps": [0, 64],
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
            "--with-dense",
        ]
        run(command)
        with output.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if [row["sample_id"] for row in rows] != [
            "empty",
            "exact-0-3-7",
            "constant-only",
            "gap-one",
            "aligned-word",
        ]:
            raise AssertionError("manifest sample identifiers were not preserved")
        if [row["provenance"] for row in rows] != [
            "synthetic-boundary:v1",
            "hand-constructed-example:v1",
            "synthetic-boundary:v1",
            "synthetic-boundary:v1",
            "synthetic-boundary:v1",
        ]:
            raise AssertionError("manifest provenance was not preserved")
        if [row["taps"] for row in rows] != [
            "-", "0;3;7", "0", "15", "0;64"
        ]:
            raise AssertionError("manifest tap lists were not preserved")
        if [row["feedback_stages"] for row in rows] != [
            "0", "1", "0", "4", "1"
        ]:
            raise AssertionError("incorrect derived feedback-stage counts")
        if [row["active_tap_counts"] for row in rows] != [
            "-", "2", "-", "1;1;1;1", "1"
        ]:
            raise AssertionError("incorrect derived active-tap profiles")
        if [row["feedback_active_tap_sum"] for row in rows] != [
            "0", "2", "0", "4", "1"
        ]:
            raise AssertionError("incorrect active-tap sums")
        if [row["W_fb"] for row in rows] != ["0", "10", "0", "49", "64"]:
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
            float(row[field]) <= 0
            for row in rows
            for field in [
                "GS_ns", "Serial_ns", "BarrettGF2X_ns",
                "Serial/GS", "BarrettGF2X/GS",
            ]
        ):
            raise AssertionError(
                "primary matched reducer measurements were not preserved"
            )
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
                "BarrettGF2X_setup_ns", "Dense_setup_ns",
                "Generated_setup_ns",
            ]
        ):
            raise AssertionError("setup timings must be nonnegative")
        if any(
            row["plan_storage_model"] != "requested-owned-bytes:v1"
            for row in rows
        ):
            raise AssertionError("plan-storage model was not preserved")
        if any(
            int(row[field]) <= 0
            for row in rows
            for field in [
                "GS_plan_bytes", "Serial_plan_bytes", "BarrettGF2X_plan_bytes"
            ]
        ):
            raise AssertionError("required plan-storage fields must be positive")
        if any(int(row["Naive_plan_bytes"]) != 0 for row in rows):
            raise AssertionError("disabled Naive plan storage must be zero")
        if any(
            row["Dense_enabled"] != "1"
            or int(row["Dense_plan_bytes"]) <= 0
            or float(row["Dense_ns"]) <= 0
            for row in rows
        ):
            raise AssertionError("enabled Dense measurements must be positive")

        ld_manifest = root / "lopez-dahab.jsonl"
        ld_output = root / "lopez-dahab.csv"
        ld_manifest.write_text(
            json.dumps({
                "sample_id": "ld-pentanomial-m163",
                "provenance": "lopez-dahab-domain-test:v1",
                "m": 163,
                "taps": [0, 3, 6, 7],
            }) + "\n",
            encoding="utf-8",
        )
        ld_command = [
            sys.executable,
            str(driver),
            "--binary",
            str(binary),
            "--manifest",
            str(ld_manifest),
            "--output",
            str(ld_output),
            "--inputs",
            "2",
            "--repeats",
            "4",
            "--seed",
            "19",
            "--no-naive",
            "--with-lopez-dahab",
        ]
        run(ld_command)
        with ld_output.open(newline="", encoding="utf-8") as stream:
            ld_rows = list(csv.DictReader(stream))
        if len(ld_rows) != 1:
            raise AssertionError("expected one loop Lopez-Dahab phase row")
        ld_row = ld_rows[0]
        if (
            ld_row["LopezDahabLoop_enabled"] != "1"
            or int(ld_row["LopezDahabLoop_plan_bytes"]) <= 0
            or float(ld_row["LopezDahabLoop_setup_ns"]) < 0
            or float(ld_row["LopezDahabLoop_ns"]) <= 0
            or float(ld_row["LopezDahabLoop/GS"]) <= 0
        ):
            raise AssertionError(
                "enabled loop Lopez-Dahab phase measurements are invalid"
            )
        run(
            [argument for argument in ld_command if argument != "--no-naive"],
            succeeds=False,
        )
        run(ld_command + ["--with-dense"], succeeds=False)
        run(
            [
                sys.executable, str(driver), "--binary", str(binary),
                "--output", str(root / "random-ld.csv"), "--m", "163",
                "--s", "4", "--no-naive", "--with-lopez-dahab",
            ],
            succeeds=False,
        )
        invalid_ld_manifest = root / "invalid-lopez-dahab.jsonl"
        invalid_ld_output = root / "invalid-lopez-dahab.csv"
        invalid_ld_manifest.write_text(
            json.dumps({
                "sample_id": "ld-invalid-high-tap",
                "provenance": "lopez-dahab-domain-test:v1",
                "m": 163,
                "taps": [0, 100],
            }) + "\n",
            encoding="utf-8",
        )
        invalid_ld_command = list(ld_command)
        invalid_ld_command[invalid_ld_command.index(str(ld_manifest))] = str(
            invalid_ld_manifest
        )
        invalid_ld_command[invalid_ld_command.index(str(ld_output))] = str(
            invalid_ld_output
        )
        run(invalid_ld_command, succeeds=False)

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
            "Delta_min", "feedback_stages", "active_tap_counts",
            "feedback_active_tap_sum", "W_fb",
            "GS_source_cost_model",
            "GS_source_aligned_word_contributions",
            "GS_source_cross_word_contributions",
            "GS_source_word_shifts", "GS_source_word_xors",
            "GS_source_logical_word_reads",
            "GS_source_logical_word_writes", "GS_source_scratch_words",
            "plan_storage_model", "GS_plan_bytes", "Serial_plan_bytes",
            "Naive_plan_bytes", "BarrettGF2X_plan_bytes",
            "Dense_plan_bytes", "Dense_enabled", "Dense_matrix_limit_bytes",
            "Generated_plan_bytes", "Generated_enabled",
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
