#!/usr/bin/env python3
"""Contract checks for deterministic distinct fixed-weight manifests."""

from __future__ import annotations

import json
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


def load(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "bench" / "scripts" / "generate_fixed_weight_supports.py"
    )
    with tempfile.TemporaryDirectory(prefix="exsuwako-fixed-manifest-") as directory:
        root = Path(directory)
        first = root / "first.jsonl"
        second = root / "second.jsonl"
        base = [
            sys.executable, str(script), "--m", "8", "16", "--h", "2", "3",
            "--samples", "256", "--seed", "0x4558535557414b4f",
        ]
        completed = run(base + ["--output", str(first)])
        run(base + ["--output", str(second)])
        if first.read_bytes() != second.read_bytes():
            raise AssertionError("fixed-weight manifest is not deterministic")
        entries = load(first)
        counts: dict[tuple[int, int], int] = {}
        seen: set[tuple[int, tuple[int, ...]]] = set()
        for entry in entries:
            m = int(entry["m"])
            taps = tuple(entry["taps"])
            h = len(taps) + 1
            counts[(m, h)] = counts.get((m, h), 0) + 1
            key = (m, taps)
            if key in seen:
                raise AssertionError("manifest contains a duplicate support")
            seen.add(key)
            if (
                taps != tuple(sorted(taps))
                or len(set(taps)) != len(taps)
                or any(tap < 0 or tap >= m for tap in taps)
            ):
                raise AssertionError("manifest contains noncanonical taps")
            expected_sampler = (
                "exhaustive-fixed-weight:v1"
                if int(entry["cell_population"]) <= 256
                else "splitmix64-floyd-distinct:v1"
            )
            if entry["support_sampler"] != expected_sampler:
                raise AssertionError("manifest omitted exact sampler provenance")
        if counts != {(8, 2): 8, (8, 3): 28, (16, 2): 16, (16, 3): 120}:
            raise AssertionError(f"population caps were not exact: {counts}")
        if "capped_cells=m8-h2:8" not in completed.stdout:
            raise AssertionError("population cap was not reported")

        run([
            sys.executable, str(script), "--output", str(root / "duplicate.jsonl"),
            "--m", "8", "8", "--h", "2", "--samples", "2", "--seed", "1",
        ], succeeds=False)
        run([
            sys.executable, str(script), "--output", str(root / "bad.jsonl"),
            "--m", "8", "--h", "1", "--samples", "2", "--seed", "1",
        ], succeeds=False)
    print("fixed-weight manifest contract checks passed")


if __name__ == "__main__":
    main()
