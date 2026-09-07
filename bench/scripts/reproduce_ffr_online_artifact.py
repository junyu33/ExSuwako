#!/usr/bin/env python3
"""Verify and rebuild the isolated planned-versus-online FFR artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


SCHEMA = "exsuwako-ffr-online-artifact:v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def confined_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"artifact data file must be confined: {relative}")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"artifact data file escapes data root: {relative}")
    return resolved


def verify_raw(path: Path, expected: dict[str, object]) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"missing external FFR-online dataset {path}")
    actual_hash = sha256(path)
    if actual_hash != expected.get("sha256"):
        raise ValueError(f"{path}: SHA-256 mismatch")
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "sample_id", "trial", "taps", "m", "h", "Delta_min",
        "input_distribution", "timing_scope", "setup_scope",
        "PlannedFFR_ns", "OnlineFFR_ns", "git_commit", "git_dirty",
        "binary_sha256", "compiler_flags", "platform", "cpu_affinity",
    }
    missing = required.difference(rows[0] if rows else {})
    if missing:
        raise ValueError(f"{path}: missing fields {sorted(missing)}")
    if len(rows) != expected.get("rows"):
        raise ValueError(
            f"{path}: expected {expected.get('rows')} rows, found {len(rows)}"
        )
    grouped: dict[str, set[int]] = {}
    for row in rows:
        if row["input_distribution"] != "uniform-full-range:v1":
            raise ValueError(f"{path}: mixed input distribution")
        if row["timing_scope"] != "ffr-online-steady-state:v1":
            raise ValueError(f"{path}: mixed timing scope")
        if row["setup_scope"] != "ffr-online-workspace:v1":
            raise ValueError(f"{path}: mixed setup scope")
        trials = grouped.setdefault(row["sample_id"], set())
        trial = int(row["trial"])
        if trial in trials:
            raise ValueError(f"{path}: duplicate trial for {row['sample_id']}")
        trials.add(trial)
    if len(grouped) != expected.get("samples"):
        raise ValueError(
            f"{path}: expected {expected.get('samples')} samples, "
            f"found {len(grouped)}"
        )
    expected_trials = expected.get("trials_per_sample")
    if any(len(trials) != expected_trials for trials in grouped.values()):
        raise ValueError(f"{path}: unexpected trial count")
    return {
        "rows": len(rows),
        "samples": len(grouped),
        "sha256": actual_hash,
        "experiment_commits": sorted({row["git_commit"] for row in rows}),
        "binary_sha256": sorted({row["binary_sha256"] for row in rows}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path,
        default=Path("bench/artifact/ffr-online-v1.json"),
    )
    parser.add_argument("--data-root", type=Path, default=Path("bench/data"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[2]
    config_path = args.config if args.config.is_absolute() else repository / args.config
    data_root = args.data_root if args.data_root.is_absolute() else repository / args.data_root
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != SCHEMA:
        raise ValueError(f"{config_path}: expected schema {SCHEMA}")
    expected_raw = config.get("raw_dataset")
    expected_summary = config.get("expected_summary")
    if not isinstance(expected_raw, dict) or not isinstance(expected_summary, dict):
        raise ValueError(f"{config_path}: invalid artifact contract")
    raw = confined_file(data_root, str(expected_raw.get("file", "")))
    raw_record = verify_raw(raw, expected_raw)
    print(
        f"raw_rows={raw_record['rows']} samples={raw_record['samples']} "
        f"raw_sha256={raw_record['sha256']}"
    )
    if args.verify_only:
        return
    if args.output is None:
        raise ValueError("--output is required unless --verify-only is used")
    output = args.output if args.output.is_absolute() else repository / args.output
    output.mkdir(parents=True, exist_ok=True)
    summary = output / "representative-summary.csv"
    completed = subprocess.run(
        [
            sys.executable,
            str(repository / "bench/scripts/analyze_ffr_online_benchmark.py"),
            "--input", str(raw), "--output", str(summary), "--min-trials", "31",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    observed_rows = count_rows(summary)
    observed_hash = sha256(summary)
    if observed_rows != expected_summary.get("rows"):
        raise ValueError(f"{summary}: unexpected row count {observed_rows}")
    if observed_hash != expected_summary.get("sha256"):
        raise ValueError(f"{summary}: SHA-256 mismatch")
    report = {
        "schema": SCHEMA,
        "repository_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "raw_dataset": raw_record,
        "summary": {
            "rows": observed_rows,
            "sha256": observed_hash,
        },
    }
    (output / "artifact-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"summary_rows={observed_rows} summary_sha256={observed_hash}")


if __name__ == "__main__":
    main()
