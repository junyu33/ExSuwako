#!/usr/bin/env python3
"""Collect metadata-complete Rabin E2E benchmark rows from a frozen manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA = "exsuwako-rabin-modulus:v1"
ROW_SCHEMA = "rabin-power-of-two-irred:v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output(command: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def linked_library(binary: Path, needle: str) -> str:
    for line in output(["ldd", str(binary)]).splitlines():
        if needle in line and "=>" in line:
            return str(Path(line.split("=>", 1)[1].strip().split()[0]).resolve())
    raise RuntimeError(f"could not resolve {needle} for {binary}")


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unavailable"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        required = {
            "schema", "sample_id", "provenance", "m", "h", "delta_min",
            "taps", "search_seed", "accepted_attempt", "irreducible",
            "certificate", "sage_version",
        }
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError(f"manifest line {line_number} is incomplete")
        m = row["m"]
        taps = row["taps"]
        if row["schema"] != MANIFEST_SCHEMA or not row["irreducible"]:
            raise ValueError(f"manifest line {line_number} is not certified")
        if not isinstance(m, int) or m < 2 or m & (m - 1):
            raise ValueError(f"manifest line {line_number} has invalid m")
        if not isinstance(taps, list) or taps != sorted(set(taps)) or not taps:
            raise ValueError(f"manifest line {line_number} has invalid taps")
        if taps[0] != 0 or taps[-1] >= m:
            raise ValueError(f"manifest line {line_number} has invalid endpoints")
        if row["h"] != len(taps) + 1 or row["delta_min"] != m - taps[-1]:
            raise ValueError(f"manifest line {line_number} has inconsistent geometry")
        rows.append(row)
    if not rows:
        raise ValueError("manifest is empty")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=31)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--serial-max-m", type=int)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--cflags", default="-O3 -std=c11 -Wall -Wextra")
    parser.add_argument("--paper-grade", action="store_true")
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[2]
    binary = args.binary.resolve()
    manifest = args.manifest.resolve()
    if not binary.is_file() or args.trials < 1 or args.warmups < 1:
        raise ValueError("binary must exist and trial counts must be positive")
    if args.serial_max_m is not None and args.serial_max_m < 1:
        raise ValueError("serial-max-m must be positive")
    if args.cpu not in os.sched_getaffinity(0):
        raise ValueError("requested CPU is outside the current affinity set")
    compiler = shutil.which(args.cc)
    if compiler is None:
        raise ValueError(f"compiler not found: {args.cc}")
    git_commit = output(["git", "rev-parse", "HEAD"], repository)
    git_dirty = bool(output(["git", "status", "--porcelain"], repository))
    if args.paper_grade and git_dirty:
        raise ValueError("paper-grade collection requires a clean commit")

    metadata = {
        "metadata_status": "paper-grade" if args.paper_grade else "exploratory",
        "git_commit": git_commit,
        "git_dirty": int(git_dirty),
        "compiler_path": str(Path(compiler).resolve()),
        "compiler_version": output([compiler, "--version"]).splitlines()[0],
        "compiler_flags": args.cflags,
        "gf2x_library": linked_library(binary, "libgf2x"),
        "ntl_library": linked_library(binary, "libntl"),
        "binary_sha256": sha256(binary),
        "manifest_sha256": sha256(manifest),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "cpu_affinity": args.cpu,
        "frequency_policy": json.dumps(
            {
                "governor": read_optional(Path(f"/sys/devices/system/cpu/cpu{args.cpu}/cpufreq/scaling_governor")),
                "energy_performance_preference": read_optional(Path(f"/sys/devices/system/cpu/cpu{args.cpu}/cpufreq/energy_performance_preference")),
                "turbo_disabled": read_optional(Path("/sys/devices/system/cpu/intel_pstate/no_turbo")),
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        "timing_order": "cyclic-method-rotation:v1",
        "square_backend": "scalar-bit-dilation:v1",
        "gcd_backend": "ntl-gf2x-gcd:v1",
        "serial_max_m": "unbounded" if args.serial_max_m is None else args.serial_max_m,
    }

    collected: list[dict[str, object]] = []
    for entry in load_manifest(manifest):
        command = [
            "taskset", "-c", str(args.cpu), str(binary),
            "--m", str(entry["m"]),
            "--taps", ",".join(str(tap) for tap in entry["taps"]),
            "--trials", str(args.trials),
            "--warmups", str(args.warmups),
            "--sample-id", entry["sample_id"],
        ]
        if args.serial_max_m is not None and entry["m"] > args.serial_max_m:
            command.append("--no-serial")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        native_rows = list(csv.DictReader(io.StringIO(result.stdout)))
        if not native_rows:
            raise RuntimeError(f"benchmark emitted no rows for {entry['sample_id']}")
        for row in native_rows:
            if row["schema"] != ROW_SCHEMA or row["sample_id"] != entry["sample_id"]:
                raise RuntimeError("native row does not match the manifest")
            row.update(
                {
                    "provenance": entry["provenance"],
                    "search_seed": entry["search_seed"],
                    "accepted_attempt": entry["accepted_attempt"],
                    "irreducibility_certificate": entry["certificate"],
                    "sage_version": entry["sage_version"],
                    "native_command": shlex.join(command),
                    **metadata,
                }
            )
            collected.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(collected[0]))
        writer.writeheader()
        writer.writerows(collected)
    print(
        f"schema={ROW_SCHEMA} samples={len(load_manifest(manifest))} "
        f"rows={len(collected)} output={args.output}"
    )


if __name__ == "__main__":
    main()
