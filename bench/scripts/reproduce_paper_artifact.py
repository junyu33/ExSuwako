#!/usr/bin/env python3
"""Verify external trial data and rebuild the paper's reduction artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


SCHEMA = "exsuwako-paper-artifact:v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, object]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema") != SCHEMA:
        raise ValueError(f"{path}: expected schema {SCHEMA}")
    return config


def confined_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"artifact data file must be a confined relative path: {relative}")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"artifact data file escapes data root: {relative}")
    return resolved


def verify_raw(path: Path, expected: dict[str, object]) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(
            f"missing external raw dataset {path}; CSV measurements remain outside Git"
        )
    actual_hash = sha256(path)
    if actual_hash != expected.get("sha256"):
        raise ValueError(f"{path}: SHA-256 mismatch")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {
            "sample_id", "git_commit", "binary_sha256", "metadata_status",
            "driver_command", "benchmark_command", "m", "h", "taps",
            "measurement_trial", "GS_ns", "BarrettGF2X_ns",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing fields {sorted(missing)}")
        rows = 0
        commits: set[str] = set()
        binaries: set[str] = set()
        for row in reader:
            rows += 1
            if row["metadata_status"] != "paper-grade":
                raise ValueError(f"{path}: row {rows + 1} is not paper-grade")
            commits.add(row["git_commit"])
            binaries.add(row["binary_sha256"])
    if rows != expected.get("rows"):
        raise ValueError(f"{path}: expected {expected.get('rows')} rows, found {rows}")
    return {
        "file": path.name,
        "rows": rows,
        "sha256": actual_hash,
        "experiment_commits": sorted(commits),
        "binary_sha256": sorted(binaries),
    }


def run(command: list[str], repository: Path, log: list[dict[str, object]]) -> None:
    completed = subprocess.run(command, cwd=repository, capture_output=True, text=True)
    if completed.returncode:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(
            f"artifact command failed with status {completed.returncode}: {command}"
        )
    record: dict[str, object] = {
        "command": command,
        "stdout": completed.stdout,
    }
    if completed.stderr:
        record["stderr"] = completed.stderr
    log.append(record)
    if completed.stdout:
        print(completed.stdout, end="")


def rebuild(
    repository: Path,
    raw: Path,
    output: Path,
    manifests: list[str],
) -> list[dict[str, object]]:
    output.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    script = repository / "bench" / "scripts"
    files = {name: output / name for name in (
        "winner-points.csv", "winner-comparisons.csv", "winner-summary.csv",
        "winner-cost-predictions.csv", "winner-cost-diagnostics.csv",
        "phase-geometry.svg", "winner-panels.svg", "winner-regions.csv",
        "winner-region-summary.csv", "feedback-depth.svg",
        "fixed-gap-weight.svg", "fixed-weight-gap.svg",
        "setup-amortization.csv", "setup-amortization.svg",
        "work-depth-setup.svg", "work-runtime.svg", "work-runtime-summary.csv",
        "random-geometry-summary.csv", "random-depth.svg", "random-work.svg",
        "operator-schematic.svg", "cost-correlations.csv", "cost-residuals.csv",
        "cost-diagnostics.csv", "paper-portable.csv", "paper-setup-storage.csv",
    )}
    commands = [
        [py, str(script / "analyze_winner_panels.py"), "--input", str(raw),
         "--points", str(files["winner-points.csv"]), "--comparisons",
         str(files["winner-comparisons.csv"]), "--summary",
         str(files["winner-summary.csv"]), "--paper-grade",
         "--allow-metadata-cohorts"],
        [py, str(script / "plot_phase_geometry.py"), "--input", str(raw),
         "--output", str(files["phase-geometry.svg"])],
        [py, str(script / "fit_winner_cost_boundaries.py"), "--input",
         str(files["winner-points.csv"]), "--output",
         str(files["winner-cost-predictions.csv"]), "--diagnostics",
         str(files["winner-cost-diagnostics.csv"])],
        [py, str(script / "plot_winner_panels.py"), "--input",
         str(files["winner-points.csv"]), "--output",
         str(files["winner-panels.svg"]), "--columns", "3", "--mode", "blocks",
         "--title", "Measured winners with fitted cost-model boundaries",
         "--boundary-input", str(files["winner-cost-predictions.csv"])],
        [py, str(script / "summarize_winner_regions.py"), "--input",
         str(files["winner-points.csv"]), "--detail", str(files["winner-regions.csv"]),
         "--summary", str(files["winner-region-summary.csv"])],
        [py, str(script / "plot_feedback_depth.py"), "--input", str(raw),
         "--output", str(files["feedback-depth.svg"])],
        [py, str(script / "plot_phase_slices.py"), "--input",
         str(files["winner-points.csv"]), "--output", str(files["fixed-gap-weight.svg"]),
         "--kind", "weight", "--selections", "1", "64"],
        [py, str(script / "plot_phase_slices.py"), "--input",
         str(files["winner-points.csv"]), "--output", str(files["fixed-weight-gap.svg"]),
         "--kind", "gap", "--selections", "9", "65"],
        [py, str(script / "plot_setup_tradeoff.py"), "--input", str(raw),
         "--amortization-data", str(files["setup-amortization.csv"]),
         "--amortization-figure", str(files["setup-amortization.svg"]),
         "--tradeoff-figure", str(files["work-depth-setup.svg"]),
         "--k-values", "1", "2", "4", "8", "16", "32", "64", "128", "256",
         "512", "1024", "--plot-methods", "BarrettGF2X", "LopezDahabLoop"],
        [py, str(script / "plot_work_random_geometry.py"), "--timing-input", str(raw),
         "--random-manifest", *(str(repository / item) for item in manifests),
         "--work-runtime-figure", str(files["work-runtime.svg"]),
         "--work-runtime-summary", str(files["work-runtime-summary.csv"]),
         "--random-summary", str(files["random-geometry-summary.csv"]),
         "--random-depth-figure", str(files["random-depth.svg"]),
         "--random-work-figure", str(files["random-work.svg"]), "--paper-grade"],
        [py, str(script / "draw_operator_schematic.py"), "--output",
         str(files["operator-schematic.svg"])],
        [py, str(script / "analyze_gs_cost_model.py"), "--input", str(raw),
         "--correlations", str(files["cost-correlations.csv"]), "--residuals",
         str(files["cost-residuals.csv"]), "--diagnostics",
         str(files["cost-diagnostics.csv"]), "--min-trials", "31",
         "--mismatch-threshold", "0.10"],
        [py, str(script / "summarize_paper_tables.py"), "--points",
         str(files["winner-points.csv"]), "--raw", str(raw), "--portable-output",
         str(files["paper-portable.csv"]), "--setup-storage-output",
         str(files["paper-setup-storage.csv"]), "--paper-grade"],
    ]
    log: list[dict[str, object]] = []
    for command in commands:
        run(command, repository, log)
    return log


def output_hashes(output: Path) -> dict[str, str]:
    return {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name not in {"artifact-report.json"}
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("bench/artifact/paper-v1.json")
    )
    parser.add_argument("--data-root", type=Path, default=Path("bench/data"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--write-observed-hashes", type=Path)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[2]
    config_path = args.config if args.config.is_absolute() else repository / args.config
    data_root = args.data_root if args.data_root.is_absolute() else repository / args.data_root
    config = load_config(config_path)
    expected_raw = config.get("raw_dataset")
    manifests = config.get("random_manifests")
    expected_outputs = config.get("expected_outputs")
    if not isinstance(expected_raw, dict) or not isinstance(manifests, list):
        raise ValueError("artifact config has invalid raw_dataset or random_manifests")
    if not isinstance(expected_outputs, dict):
        raise ValueError("artifact config has invalid expected_outputs")
    raw = confined_file(data_root, str(expected_raw.get("file", "")))
    raw_record = verify_raw(raw, expected_raw)
    for manifest in manifests:
        path = repository / str(manifest)
        if not path.is_file():
            raise FileNotFoundError(f"missing tracked manifest {path}")
    print(
        f"raw_rows={raw_record['rows']} raw_sha256={raw_record['sha256']} "
        f"experiment_commits={len(raw_record['experiment_commits'])}"
    )
    if args.verify_only:
        return
    if args.output is None:
        raise ValueError("--output is required unless --verify-only is used")
    output = args.output if args.output.is_absolute() else repository / args.output
    log = rebuild(repository, raw, output, [str(item) for item in manifests])
    hashes = output_hashes(output)
    if args.write_observed_hashes:
        args.write_observed_hashes.write_text(
            json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if expected_outputs and hashes != expected_outputs:
        missing = sorted(set(expected_outputs).difference(hashes))
        extra = sorted(set(hashes).difference(expected_outputs))
        changed = sorted(
            name for name in set(hashes).intersection(expected_outputs)
            if hashes[name] != expected_outputs[name]
        )
        raise ValueError(
            f"artifact output mismatch: missing={missing}, extra={extra}, changed={changed}"
        )
    report = {
        "schema": SCHEMA,
        "repository_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "python": sys.version,
        "platform": platform.platform(),
        "raw_dataset": raw_record,
        "output_sha256": hashes,
        "commands": log,
    }
    (output / "artifact-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"artifact_outputs={len(hashes)} output={output}")


if __name__ == "__main__":
    main()
