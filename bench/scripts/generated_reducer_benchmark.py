#!/usr/bin/env python3
"""Generate, compile, and benchmark one fixed-modulus reducer."""

from __future__ import annotations

import argparse
import csv
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

from generate_fixed_reducer import generate_source, parse_taps


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def text_section_bytes(size_tool: str, shared_object: Path) -> int:
    completed = run([size_tool, "-A", str(shared_object)])
    for line in completed.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == ".text":
            return int(fields[1])
    raise RuntimeError("size tool did not report a .text section")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--taps", required=True)
    parser.add_argument("--inputs", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=12)
    parser.add_argument("--seed", default="0x9e3779b97f4a7c15")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--cflags", default="-O3 -std=c11 -Wall -Wextra")
    parser.add_argument("--gf2x-prefix", type=Path, default=Path("/usr/local"))
    parser.add_argument("--size-tool", default="size")
    args = parser.parse_args()
    if args.inputs <= 0 or args.repeats <= 0:
        raise ValueError("inputs and repeats must be positive")
    taps = parse_taps(args.taps, args.m)

    repository = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="exsuwako-generated-bench-") as tmp:
        root = Path(tmp)
        source_path = root / "fixed_reducer.c"
        shared_path = root / "fixed_reducer.so"

        started = time.perf_counter_ns()
        source = generate_source(args.m, taps)
        source_path.write_text(source, encoding="utf-8")
        generation_ns = time.perf_counter_ns() - started

        compile_command = [
            args.cc,
            *shlex.split(args.cflags),
            "-fPIC",
            "-shared",
            f"-I{repository / 'include'}",
            f"-I{args.gf2x_prefix / 'include'}",
            str(source_path),
            "-o",
            str(shared_path),
        ]
        started = time.perf_counter_ns()
        run(compile_command)
        compile_ns = time.perf_counter_ns() - started

        benchmark = run(
            [
                str(args.binary),
                "--taps",
                args.taps,
                str(args.inputs),
                str(args.repeats),
                str(args.m),
                args.seed,
                "no-naive",
                f"generated={shared_path}",
            ]
        )
        rows = list(csv.DictReader(benchmark.stdout.splitlines()))
        if len(rows) != 1:
            raise RuntimeError(f"expected one benchmark row, got {len(rows)}")
        row = rows[0]
        row["Generated_generation_ns"] = str(generation_ns)
        row["Generated_compile_ns"] = str(compile_ns)
        row["Generated_full_setup_ns"] = str(
            generation_ns + compile_ns + float(row["Generated_setup_ns"])
        )
        row["Generated_source_bytes"] = str(len(source.encode("utf-8")))
        row["Generated_shared_object_bytes"] = str(shared_path.stat().st_size)
        row["Generated_text_bytes"] = str(
            text_section_bytes(args.size_tool, shared_path)
        )
        row["Generated_code_model"] = "fixed-unrolled-c-v1"
        row["Generated_code_size_model"] = "elf-text-section:v1"
        row["Generated_word_bits"] = "64"
        row["Generated_cc"] = args.cc
        row["Generated_cflags"] = args.cflags + " -fPIC -shared"
        row["Generated_size_tool"] = args.size_tool

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    print(
        f"Generated={row['Generated_ns']}ns GS={row['GS_ns']}ns "
        f"text={row['Generated_text_bytes']} bytes "
        f"full_setup={row['Generated_full_setup_ns']}ns"
    )


if __name__ == "__main__":
    main()
