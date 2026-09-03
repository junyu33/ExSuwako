#!/usr/bin/env python3
"""Contract checks for the controlled Cartesian support generator."""

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


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def check_grid(
    entries: list[dict[str, object]], weights: list[int], constant_present: bool
) -> None:
    expected_cells = {
        (m, h, delta) for m in [17, 31] for h in weights for delta in [1, 4]
    }
    cells: set[tuple[int, int, int]] = set()
    sample_ids: set[str] = set()
    for entry in entries:
        m = int(entry["m"])
        taps = list(entry["taps"])
        h = len(taps) + 1
        delta = m - max(taps)
        cells.add((m, h, delta))
        sample_ids.add(str(entry["sample_id"]))
        if taps != sorted(set(taps)):
            raise AssertionError("generated taps are not canonical")
        if (0 in taps) != constant_present:
            raise AssertionError("constant policy was not preserved")
        expected_label = "constant-present" if constant_present else "constant-free"
        if expected_label not in str(entry["provenance"]):
            raise AssertionError("constant policy provenance was not preserved")
    if cells != expected_cells:
        raise AssertionError("generator did not emit the full Cartesian grid")
    if len(sample_ids) != len(entries) or len(entries) != len(expected_cells):
        raise AssertionError("controlled support identifiers are not unique")


def main() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "bench" / "scripts" / "generate_controlled_supports.py"
    )
    with tempfile.TemporaryDirectory(prefix="exsuwako-controlled-") as directory:
        root = Path(directory)
        common = [
            sys.executable, str(script), "--m", "17", "31",
            "--h", "2", "3", "5", "--delta-min", "1", "4",
        ]
        absent = root / "absent.jsonl"
        completed = run(common + ["--output", str(absent)])
        if "points=12" not in completed.stdout:
            raise AssertionError("unexpected controlled-grid summary")
        absent_entries = load_jsonl(absent)
        check_grid(absent_entries, [2, 3, 5], constant_present=False)

        repeated = root / "repeated.jsonl"
        run(common + ["--output", str(repeated)])
        if repeated.read_bytes() != absent.read_bytes():
            raise AssertionError("controlled support generation is not deterministic")

        present = root / "present.jsonl"
        run([
            sys.executable, str(script), "--m", "17", "31",
            "--h", "3", "5", "--delta-min", "1", "4",
            "--output", str(present), "--constant-policy", "present",
        ])
        check_grid(load_jsonl(present), [3, 5], constant_present=True)

        run([
            sys.executable, str(script), "--output", str(root / "bad.jsonl"),
            "--m", "8", "--h", "5", "--delta-min", "5",
        ], succeeds=False)
        run([
            sys.executable, str(script), "--output", str(root / "duplicate.jsonl"),
            "--m", "17", "17", "--h", "3", "--delta-min", "1",
        ], succeeds=False)
    print("controlled-support generator contract checks passed")


if __name__ == "__main__":
    main()
