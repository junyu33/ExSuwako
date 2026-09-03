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

        constant_free = root / "constant-free.jsonl"
        run(base + [
            "--output", str(constant_free), "--constant-policy", "absent"
        ])
        constant_free_entries = load(constant_free)
        if any(0 in entry["taps"] for entry in constant_free_entries):
            raise AssertionError("constant-free manifest contains tap zero")
        constant_free_counts: dict[tuple[int, int], int] = {}
        for entry in constant_free_entries:
            key = (int(entry["m"]), len(entry["taps"]) + 1)
            constant_free_counts[key] = constant_free_counts.get(key, 0) + 1
            if (
                entry["provenance"]
                != "synthetic-fixed-weight-uniform-constant-free:v1"
                or entry["constant_policy"] != "absent"
            ):
                raise AssertionError("constant-free provenance is incomplete")
        if constant_free_counts != {
            (8, 2): 7, (8, 3): 21, (16, 2): 15, (16, 3): 105
        }:
            raise AssertionError(
                f"constant-free population caps are wrong: {constant_free_counts}"
            )

        run([
            sys.executable, str(script), "--output", str(root / "duplicate.jsonl"),
            "--m", "8", "8", "--h", "2", "--samples", "2", "--seed", "1",
        ], succeeds=False)
        run([
            sys.executable, str(script), "--output", str(root / "bad.jsonl"),
            "--m", "8", "--h", "1", "--samples", "2", "--seed", "1",
        ], succeeds=False)

        frozen = root / "frozen"
        freeze_script = script.with_name("freeze_winner_manifests.py")
        completed = run([
            sys.executable, str(freeze_script), "--output-dir", str(frozen)
        ])
        frozen_files = sorted(frozen.glob("*.jsonl"))
        if len(frozen_files) != 46:
            raise AssertionError(
                f"winner suite emitted {len(frozen_files)} files instead of 46"
            )
        frozen_entries = [entry for path in frozen_files for entry in load(path)]
        if len(frozen_entries) != 11706:
            raise AssertionError(
                f"winner suite emitted {len(frozen_entries)} points"
            )
        if any(
            0 in entry["taps"]
            for entry in frozen_entries
            if entry["provenance"]
            == "synthetic-fixed-weight-uniform-constant-free:v1"
        ):
            raise AssertionError("frozen random panels are not constant-free")
        if "suite=classical-winner-phase-diagram:v1" not in completed.stdout:
            raise AssertionError("winner suite did not report its contract")
    print("fixed-weight manifest contract checks passed")


if __name__ == "__main__":
    main()
