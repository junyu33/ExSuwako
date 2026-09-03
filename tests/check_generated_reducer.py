#!/usr/bin/env python3
"""Generate, compile, and independently check fixed-modulus reducers."""

from __future__ import annotations

import argparse
import csv
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


def run(
    command: list[str], *, succeeds: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    if succeeds and completed.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not succeeds and completed.returncode == 0:
        raise AssertionError(f"invalid command succeeded: {' '.join(command)}")
    return completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--cflags", default="-O3 -std=c11 -Wall -Wextra")
    parser.add_argument("--include", type=Path, required=True)
    parser.add_argument("--gf2x-include", type=Path, required=True)
    args = parser.parse_args()
    generator = (
        Path(__file__).resolve().parents[1]
        / "bench"
        / "scripts"
        / "generate_fixed_reducer.py"
    )
    benchmark_driver = generator.with_name("generated_reducer_benchmark.py")
    cases = [
        ("gs", 1, []),
        ("gs", 2, [0, 1]),
        ("gs", 7, [1, 6]),
        ("gs", 63, [0, 3, 62]),
        ("gs", 64, [0, 7, 63]),
        ("gs", 65, [1, 32, 64]),
        ("gs", 127, [0, 64, 126]),
        ("gs", 129, list(range(0, 129, 7))),
        ("lopez-dahab", 163, [0, 7]),
        ("lopez-dahab", 163, [0, 3, 6, 7]),
        ("lopez-dahab", 233, [0, 74]),
        ("lopez-dahab", 283, [0, 5, 7, 12]),
        ("lopez-dahab", 409, [0, 87]),
        ("lopez-dahab", 192, [1, 63]),
        ("lopez-dahab", 256, [1, 7, 31, 127]),
        ("lopez-dahab", 257, list(range(0, 64, 8))),
        ("lopez-dahab", 257, list(range(0, 128, 8))),
        ("lopez-dahab", 257, list(range(0, 128, 4))),
        ("lopez-dahab", 257, list(range(0, 128, 2))),
    ]
    with tempfile.TemporaryDirectory(prefix="exsuwako-generated-check-") as tmp:
        root = Path(tmp)
        for index, (algorithm, m, taps) in enumerate(cases):
            source = root / f"generated-{index}.c"
            shared = root / f"generated-{index}.so"
            tap_text = ",".join(map(str, taps)) if taps else "-"
            run(
                [
                    sys.executable,
                    str(generator),
                    "--m",
                    str(m),
                    "--taps",
                    tap_text,
                    "--output",
                    str(source),
                    "--algorithm",
                    algorithm,
                ]
            )
            run(
                [
                    args.cc,
                    *shlex.split(args.cflags),
                    "-fPIC",
                    "-shared",
                    f"-I{args.include}",
                    f"-I{args.gf2x_include}",
                    str(source),
                    "-o",
                    str(shared),
                ]
            )
            run(
                [
                    str(args.checker),
                    str(shared),
                    str(m),
                    *map(str, taps),
                ]
            )
        benchmark_output = root / "generated-benchmark.csv"
        run(
            [
                sys.executable,
                str(benchmark_driver),
                "--binary",
                str(args.binary),
                "--output",
                str(benchmark_output),
                "--m",
                "163",
                "--taps",
                "0,3,6,7",
                "--inputs",
                "2",
                "--repeats",
                "4",
                "--seed",
                "0x1",
                "--cc",
                args.cc,
                "--gf2x-prefix",
                str(args.gf2x_include.parent),
                "--algorithm",
                "lopez-dahab",
            ]
        )
        with benchmark_output.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1:
            raise AssertionError("generated benchmark driver emitted wrong row count")
        row = rows[0]
        for field in [
            "Generated_plan_bytes",
            "Generated_setup_ns",
            "Generated_ns",
            "Generated/GS",
            "Generated_generation_ns",
            "Generated_compile_ns",
            "Generated_full_setup_ns",
            "Generated_source_bytes",
            "Generated_shared_object_bytes",
            "Generated_text_bytes",
        ]:
            if float(row[field]) <= 0:
                raise AssertionError(f"generated benchmark field {field} is not positive")
        if row["Generated_enabled"] != "1":
            raise AssertionError("generated benchmark did not enable the plugin")
        if (
            row["Generated_code_model"]
            != "lopez-dahab-algorithm2-fixed-c:v1"
            or row["Generated_code_size_model"] != "elf-text-section:v1"
            or row["Generated_word_bits"] != "64"
            or row["Generated_algorithm"] != "lopez-dahab"
            or row["Generated_applicability"]
            != "arbitrary-weight-and-deg-q-lt-m-minus-W:v1"
        ):
            raise AssertionError("generated benchmark metadata is incorrect")
        invalid_source = root / "invalid-lopez-dahab.c"
        run(
            [
                sys.executable,
                str(generator),
                "--algorithm",
                "lopez-dahab",
                "--m",
                "163",
                "--taps",
                "0,100",
                "--output",
                str(invalid_source),
            ],
            succeeds=False,
        )
        if invalid_source.exists():
            raise AssertionError("invalid Lopez-Dahab source was materialized")
    print(f"generated reducers: ok ({len(cases)} fixed moduli)")


if __name__ == "__main__":
    main()
