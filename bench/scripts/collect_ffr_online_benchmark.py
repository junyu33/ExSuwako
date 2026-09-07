#!/usr/bin/env python3
"""Collect the isolated planned-versus-online FFR representative slices."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
from pathlib import Path


TIMING_SCOPE = "ffr-online-steady-state:v1"
SETUP_SCOPE = "ffr-online-workspace:v1"
PROVENANCE = "ffr-online-representative-slice:v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_output(command: list[str], cwd: Path) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def load_manifest(path: Path) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            sample_id = value.get("sample_id")
            m = value.get("m")
            taps = value.get("taps")
            if not isinstance(sample_id, str) or sample_id in seen:
                raise ValueError(f"manifest line {line_number}: bad sample_id")
            if value.get("provenance") != PROVENANCE:
                raise ValueError(f"manifest line {line_number}: bad provenance")
            if not isinstance(m, int) or m <= 0 or not isinstance(taps, list):
                raise ValueError(f"manifest line {line_number}: bad m/taps")
            if taps != sorted(set(taps)) or any(
                not isinstance(tap, int) or tap < 0 or tap >= m for tap in taps
            ):
                raise ValueError(f"manifest line {line_number}: noncanonical taps")
            seen.add(sample_id)
            values.append(value)
    if not values:
        raise ValueError("empty manifest")
    return values


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unavailable"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inputs", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=12)
    parser.add_argument("--trials", type=int, default=31)
    parser.add_argument("--seed", type=lambda value: int(value, 0),
                        default=0x4F4E4C494E455631)
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if min(args.inputs, args.repeats, args.trials) <= 0 or args.seed <= 0:
        raise ValueError("inputs, repeats, trials, and seed must be positive")

    repository = Path(__file__).resolve().parents[2]
    binary = args.binary.resolve()
    manifest = args.manifest.resolve()
    if not binary.is_file():
        raise ValueError("benchmark binary does not exist")
    entries = load_manifest(manifest)
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("limit must be positive")
        entries = entries[: args.limit]
    affinity = sorted(os.sched_getaffinity(0))
    cpu = args.cpu if args.cpu is not None else affinity[0]
    if cpu not in affinity:
        raise ValueError(f"CPU {cpu} is outside affinity set {affinity}")

    git_commit = command_output(["git", "rev-parse", "HEAD"], repository)
    git_dirty = bool(command_output(["git", "status", "--porcelain"], repository))
    metadata = {
        "metadata_status": "recorded-exploratory",
        "git_commit": git_commit,
        "git_dirty": int(git_dirty),
        "binary_sha256": sha256(binary),
        "compiler_flags": "-O3 -std=c11 -Wall -Wextra",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "cpu_affinity": cpu,
        "frequency_policy": json.dumps(
            {
                "governor": read_optional(
                    Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
                ),
                "energy_performance_preference": read_optional(
                    Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/energy_performance_preference")
                ),
                "turbo_disabled": read_optional(
                    Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        "implementation": "portable-scalar-c-online:v1",
        "multiplication_backend": "not-applicable",
    }

    rows: list[dict[str, object]] = []
    for index, entry in enumerate(entries):
        m = int(entry["m"])
        taps = list(entry["taps"])
        seed = (args.seed + index) & ((1 << 64) - 1)
        tap_argument = ",".join(str(tap) for tap in taps) if taps else "-"
        native = [
            str(binary), tap_argument, str(args.inputs), str(args.repeats),
            str(args.trials), str(m), str(seed),
        ]
        command = ["taskset", "-c", str(cpu), *native]
        completed = subprocess.run(
            command, cwd=repository, check=True, capture_output=True, text=True
        )
        native_rows = list(csv.DictReader(io.StringIO(completed.stdout)))
        if len(native_rows) != args.trials:
            raise RuntimeError(
                f"{entry['sample_id']}: expected {args.trials} rows, "
                f"got {len(native_rows)}"
            )
        for trial, row in enumerate(native_rows):
            if (
                int(row["m"]) != m
                or int(row["s"]) != len(taps)
                or row["timing_scope"] != TIMING_SCOPE
                or row["setup_scope"] != SETUP_SCOPE
                or int(row["trial"]) != trial
            ):
                raise RuntimeError(f"{entry['sample_id']}: native contract mismatch")
            enriched: dict[str, object] = {
                "sample_id": entry["sample_id"],
                "provenance": entry["provenance"],
                "taps": ";".join(str(tap) for tap in taps) if taps else "-",
                "inputs": args.inputs,
                "batch_repeats": args.repeats,
                "warmup_runs": 1,
                "measurement_trials": args.trials,
                "native_command": " ".join(native),
                **row,
                **metadata,
            }
            rows.append(enriched)
        print(f"completed {index + 1}/{len(entries)} {entry['sample_id']}", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} output={args.output}")


if __name__ == "__main__":
    main()
