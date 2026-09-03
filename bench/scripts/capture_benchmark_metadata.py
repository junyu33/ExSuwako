#!/usr/bin/env python3
"""Capture a reviewable metadata snapshot for native benchmark runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


SCHEMA = "exsuwako-native-platform:v1"


def command_output(command: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def resolve_gf2x(binary: Path) -> str:
    ldd = shutil.which("ldd")
    if ldd:
        output = command_output([ldd, str(binary)])
        for line in output.splitlines():
            if "libgf2x" in line and "=>" in line:
                candidate = line.split("=>", 1)[1].strip().split()[0]
                return str(Path(candidate).resolve())
    raise RuntimeError("could not resolve the linked gf2x library with ldd")


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unavailable"


def frequency_policy(cpu: int) -> dict[str, str]:
    cpu_root = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq")
    return {
        "governor": read_optional(cpu_root / "scaling_governor"),
        "energy_performance_preference": read_optional(
            cpu_root / "energy_performance_preference"
        ),
        "turbo_disabled": read_optional(
            Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
        ),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--cflags", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file() or args.cpu < 0:
        raise ValueError("binary must exist and cpu must be nonnegative")
    affinity = os.sched_getaffinity(0)
    if args.cpu not in affinity:
        raise ValueError(
            f"cpu {args.cpu} is outside the current affinity set {sorted(affinity)}"
        )
    repository = Path(__file__).resolve().parents[2]
    compiler = shutil.which(args.cc)
    if compiler is None:
        raise ValueError(f"compiler not found: {args.cc}")
    status = command_output(["git", "status", "--porcelain"], repository)
    metadata = {
        "metadata_schema": SCHEMA,
        "git_commit": command_output(["git", "rev-parse", "HEAD"], repository),
        "git_dirty": bool(status),
        "compiler_path": str(Path(compiler).resolve()),
        "compiler_version": command_output([compiler, "--version"]).splitlines()[0],
        "compiler_flags": args.cflags,
        "gf2x_library": resolve_gf2x(binary),
        "binary_sha256": sha256(binary),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "cpu_affinity": args.cpu,
        "frequency_policy": frequency_policy(args.cpu),
        "implementation": "portable-scalar-c:v1",
        "multiplication_backend": "gf2x:v1",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"schema={SCHEMA} commit={metadata['git_commit']} "
        f"dirty={int(metadata['git_dirty'])} cpu={args.cpu} output={args.output}"
    )


if __name__ == "__main__":
    main()
