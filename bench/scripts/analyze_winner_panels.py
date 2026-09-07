#!/usr/bin/env python3
"""Classify per-support reduction winners without forcing uncertain points."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


BOOTSTRAP_RESAMPLES = 10_000
TIMING_SCOPE = "reduction-steady-state:v1"
WINNER_CONTRACT = "paired-bootstrap-one-percent:v1"
METHOD_FIELDS = {
    "GS": "GS_ns",
    "Serial": "Serial_ns",
    "BarrettGF2X": "BarrettGF2X_ns",
    "Dense": "Dense_ns",
    "LopezDahabLoop": "LopezDahabLoop_ns",
}
INVARIANT_FIELDS = (
    "provenance",
    "m",
    "word_bits",
    "s",
    "h",
    "taps",
    "Delta_min",
    "log2_m_over_delta",
    "input_distribution",
    "timing_scope",
    "setup_scope",
    "timing_order",
    "aggregation",
    "inputs",
    "batch_repeats",
    "warmup_runs",
    "measurement_trials",
    "seed",
    "Dense_enabled",
    "Generated_enabled",
    "LopezDahabLoop_enabled",
)
PAPER_METADATA_FIELDS = (
    "metadata_schema", "git_commit", "git_dirty", "compiler_path",
    "compiler_version", "compiler_flags", "gf2x_library", "binary_sha256",
    "platform", "machine", "hostname", "cpu_affinity", "frequency_policy",
    "implementation", "multiplication_backend",
)


def quantile_nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def bootstrap_median_interval(
    values: list[float], identity: str
) -> tuple[float, float]:
    seed = int.from_bytes(
        hashlib.sha256(identity.encode("utf-8")).digest()[:8], "little"
    )
    rng = random.Random(seed)
    count = len(values)
    estimates = [
        statistics.median(values[rng.randrange(count)] for _ in range(count))
        for _ in range(BOOTSTRAP_RESAMPLES)
    ]
    return (
        quantile_nearest_rank(estimates, 0.025),
        quantile_nearest_rank(estimates, 0.975),
    )


def positive_float(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid {field}: {row.get(field)!r}") from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return value


def parse_taps(value: str, m: int) -> list[int]:
    if value == "-":
        return []
    try:
        taps = [int(text) for text in value.split(";")]
    except ValueError as error:
        raise ValueError(f"invalid serialized taps {value!r}") from error
    if taps != sorted(set(taps)) or any(tap < 0 or tap >= m for tap in taps):
        raise ValueError(f"noncanonical serialized taps {value!r}")
    return taps


def enabled_methods(row: dict[str, str]) -> list[str]:
    try:
        dense = int(row["Dense_enabled"])
        generated = int(row["Generated_enabled"])
        lopez_dahab = int(row["LopezDahabLoop_enabled"])
    except (KeyError, ValueError) as error:
        raise ValueError("invalid optional-method state") from error
    if dense not in (0, 1) or generated not in (0, 1) or lopez_dahab not in (0, 1):
        raise ValueError("optional-method states must be binary")
    if generated:
        raise ValueError("generated reducers are outside the winner contract")
    try:
        serial = int(row.get("Serial_enabled", "1"))
    except ValueError as error:
        raise ValueError("invalid Serial state") from error
    if serial not in (0, 1):
        raise ValueError("Serial state must be binary")
    methods = ["GS"]
    if serial:
        methods.append("Serial")
    methods.append("BarrettGF2X")
    if dense:
        methods.append("Dense")
    if lopez_dahab:
        methods.append("LopezDahabLoop")
    return methods


def load_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            file_rows = list(reader)
        if not file_rows:
            raise ValueError(f"input {path} contains no rows")
        required = {"sample_id", "measurement_trial", *INVARIANT_FIELDS}
        required.update(METHOD_FIELDS.values())
        missing = required.difference(file_rows[0])
        if missing:
            raise ValueError(
                f"input {path} is missing fields: {', '.join(sorted(missing))}"
            )
        rows.extend(file_rows)
    return rows


def analyze_supports(
    raw_rows: list[dict[str, str]], min_trials: int,
    min_batch_repeats: int, min_warmup_runs: int, paper_grade: bool,
    allow_metadata_cohorts: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        if row["timing_scope"] != TIMING_SCOPE:
            raise ValueError(f"unexpected timing scope {row['timing_scope']!r}")
        if paper_grade:
            missing = [field for field in PAPER_METADATA_FIELDS if not row.get(field)]
            if missing or row.get("metadata_status") != "paper-grade":
                raise ValueError(
                    "paper-grade winner input lacks frozen metadata: "
                    + ", ".join(missing)
                )
            if row["git_dirty"] != "0":
                raise ValueError("paper-grade winner input records a dirty tree")
        grouped[row["sample_id"]].append(row)

    points: list[dict[str, object]] = []
    comparisons: list[dict[str, object]] = []
    support_keys: set[tuple[int, str]] = set()
    for sample_id, rows in grouped.items():
        first = rows[0]
        declared_trials = int(first["measurement_trials"])
        trial_indices = sorted(int(row["measurement_trial"]) for row in rows)
        if (
            declared_trials != len(rows)
            or trial_indices != list(range(declared_trials))
            or len(rows) < min_trials
        ):
            raise ValueError(
                f"sample {sample_id!r} has an incomplete trial sequence"
            )
        if int(first["batch_repeats"]) < min_batch_repeats:
            raise ValueError(f"sample {sample_id!r} has too few batch repeats")
        if int(first["warmup_runs"]) < min_warmup_runs:
            raise ValueError(f"sample {sample_id!r} has too few warm-up runs")
        for row in rows[1:]:
            for field in INVARIANT_FIELDS:
                if row[field] != first[field]:
                    raise ValueError(
                        f"sample {sample_id!r} changes invariant field {field}"
                    )
        serial_states = {row.get("Serial_enabled", "1") for row in rows}
        if len(serial_states) != 1:
            raise ValueError(f"sample {sample_id!r} changes Serial state")

        m = int(first["m"])
        s = int(first["s"])
        h = int(first["h"])
        taps = parse_taps(first["taps"], m)
        if not taps or len(taps) != s or h != s + 1:
            raise ValueError("winner panels require a nonempty consistent support")
        delta_min = m - taps[-1]
        if delta_min != int(first["Delta_min"]):
            raise ValueError(f"sample {sample_id!r} has inconsistent Delta_min")
        expected_log = math.log2(m / delta_min)
        if not math.isclose(
            expected_log, float(first["log2_m_over_delta"]),
            rel_tol=1e-12, abs_tol=1e-12,
        ):
            raise ValueError(f"sample {sample_id!r} has inconsistent phase coordinate")
        support_key = (m, first["taps"])
        if support_key in support_keys:
            raise ValueError(
                f"duplicate exact support (m={m}, taps={first['taps']})"
            )
        support_keys.add(support_key)

        methods = enabled_methods(first)
        word_bits = int(first["word_bits"])
        if "LopezDahabLoop" in methods and delta_min < word_bits:
            raise ValueError(
                f"sample {sample_id!r} enables López-Dahab outside its domain"
            )
        if (
            first["provenance"].startswith("synthetic-controlled-")
            and delta_min >= word_bits
            and "Dense" not in methods
            and "LopezDahabLoop" not in methods
        ):
            raise ValueError(
                f"sample {sample_id!r} omits applicable López-Dahab baseline"
            )
        method_values: dict[str, list[float]] = {}
        method_medians: dict[str, float] = {}
        method_intervals: dict[str, tuple[float, float]] = {}
        relative_half_widths: dict[str, float] = {}
        for method in methods:
            field = METHOD_FIELDS[method]
            values = [positive_float(row, field) for row in rows]
            median = statistics.median(values)
            low, high = bootstrap_median_interval(
                values, f"{sample_id}:{method}:median"
            )
            method_values[method] = values
            method_medians[method] = median
            method_intervals[method] = (low, high)
            relative_half_widths[method] = (high - low) / (2 * median)

        fastest = min(methods, key=method_medians.__getitem__)
        pairwise: dict[str, tuple[float, float, float]] = {}
        for competitor in methods:
            if competitor == fastest:
                continue
            ratios = [
                left / right for left, right in zip(
                    method_values[fastest], method_values[competitor]
                )
            ]
            ratio_median = statistics.median(ratios)
            low, high = bootstrap_median_interval(
                ratios, f"{sample_id}:{fastest}/{competitor}:paired"
            )
            pairwise[competitor] = (ratio_median, low, high)
            comparisons.append({
                "sample_id": sample_id,
                "m": m,
                "h": h,
                "Delta_min": delta_min,
                "candidate": fastest,
                "competitor": competitor,
                "median_ratio": ratio_median,
                "ci95_low": low,
                "ci95_high": high,
                "comparison_contract": WINNER_CONTRACT,
            })

        if any(width > 0.01 for width in relative_half_widths.values()):
            winner = "uncertain"
            reason = "timing-unstable"
        elif any(values[0] > 0.99 for values in pairwise.values()):
            winner = "uncertain"
            reason = "operational-tie"
        elif any(values[2] >= 1.0 for values in pairwise.values()):
            winner = "uncertain"
            reason = "statistical-tie"
        else:
            winner = fastest
            reason = "unique-winner"

        unavailable: list[str] = []
        if "Serial" not in methods:
            unavailable.append("Serial:not-enabled")
        if "Dense" not in methods:
            unavailable.append("Dense:not-enabled")
        if "LopezDahabLoop" not in methods:
            ld_reason = "degree-assumption" if delta_min < int(first["word_bits"]) else "not-measured"
            unavailable.append(f"LopezDahabLoop:{ld_reason}")
        point: dict[str, object] = {
            "sample_id": sample_id,
            "provenance": first["provenance"],
            "m": m,
            "word_bits": word_bits,
            "s": s,
            "h": h,
            "taps": first["taps"],
            "Delta_min": delta_min,
            "log2_m_over_delta": expected_log,
            "trial_count": len(rows),
            "method_set": ";".join(methods),
            "unavailable_methods": ";".join(unavailable) or "-",
            "fastest_median_method": fastest,
            "winner": winner,
            "winner_reason": reason,
            "winner_contract": WINNER_CONTRACT,
        }
        for field in PAPER_METADATA_FIELDS:
            point[field] = first.get(field, "")
        for method in METHOD_FIELDS:
            if method in methods:
                low, high = method_intervals[method]
                point[f"{method}_median_ns"] = method_medians[method]
                point[f"{method}_ci95_low"] = low
                point[f"{method}_ci95_high"] = high
                point[f"{method}_relative_half_width"] = relative_half_widths[method]
            else:
                point[f"{method}_median_ns"] = ""
                point[f"{method}_ci95_low"] = ""
                point[f"{method}_ci95_high"] = ""
                point[f"{method}_relative_half_width"] = ""
        points.append(point)
    if paper_grade:
        cohort_fields = {"git_commit", "binary_sha256"}
        fixed_fields = (
            field for field in PAPER_METADATA_FIELDS
            if not allow_metadata_cohorts or field not in cohort_fields
        )
        for field in fixed_fields:
            values = {str(point[field]) for point in points}
            if len(values) != 1:
                raise ValueError(f"paper-grade inputs mix metadata field {field}")
        if allow_metadata_cohorts:
            commit_to_binary: dict[str, set[str]] = defaultdict(set)
            binary_to_commit: dict[str, set[str]] = defaultdict(set)
            for point in points:
                commit = str(point["git_commit"])
                binary = str(point["binary_sha256"])
                commit_to_binary[commit].add(binary)
                binary_to_commit[binary].add(commit)
            if any(len(values) != 1 for values in commit_to_binary.values()):
                raise ValueError("one paper-grade commit maps to multiple binaries")
            if any(len(values) != 1 for values in binary_to_commit.values()):
                raise ValueError("one paper-grade binary maps to multiple commits")
    points.sort(key=lambda row: (int(row["m"]), int(row["h"]), int(row["Delta_min"])))
    return points, comparisons


def summary_rows(points: list[dict[str, object]]) -> list[dict[str, object]]:
    by_m: dict[int, list[dict[str, object]]] = defaultdict(list)
    for point in points:
        by_m[int(point["m"])].append(point)
    rows: list[dict[str, object]] = []
    for m, panel in sorted(by_m.items()):
        outcomes = Counter(str(point["winner"]) for point in panel)
        reasons = Counter(str(point["winner_reason"]) for point in panel)
        unstable = reasons["timing-unstable"]
        dense_points = [
            point for point in panel if "Dense" in str(point["method_set"]).split(";")
        ]
        dense_near = 0
        for point in dense_points:
            widths = [
                float(point[f"{method}_relative_half_width"])
                for method in ("GS", "Serial", "BarrettGF2X", "Dense")
            ]
            primary = min(
                float(point[f"{method}_median_ns"])
                for method in ("GS", "Serial", "BarrettGF2X")
            )
            if max(widths) <= 0.01 and float(point["Dense_median_ns"]) <= 1.10 * primary:
                dense_near += 1
        rows.append({
            "m": m,
            "points": len(panel),
            "GS_wins": outcomes["GS"],
            "Serial_wins": outcomes["Serial"],
            "BarrettGF2X_wins": outcomes["BarrettGF2X"],
            "Dense_wins": outcomes["Dense"],
            "LopezDahabLoop_wins": outcomes["LopezDahabLoop"],
            "uncertain": outcomes["uncertain"],
            "timing_unstable": unstable,
            "operational_ties": reasons["operational-tie"],
            "statistical_ties": reasons["statistical-tie"],
            "unstable_fraction": unstable / len(panel),
            "Dense_screen_points": len(dense_points),
            "Dense_within_1_10": dense_near,
            "Dense_decision": (
                "not-measured" if not dense_points
                else "promote-contract-review" if dense_near
                else "diagnostic-only"
            ),
            "recommended_trials": (
                63 if unstable / len(panel) > 0.05 and int(panel[0]["trial_count"]) == 31
                else 127 if unstable / len(panel) > 0.05 and int(panel[0]["trial_count"]) == 63
                else "retain"
            ),
            "winner_contract": WINNER_CONTRACT,
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty analysis table")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--comparisons", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--min-trials", type=int, default=31)
    parser.add_argument("--min-batch-repeats", type=int, default=12)
    parser.add_argument("--min-warmup-runs", type=int, default=1)
    parser.add_argument("--paper-grade", action="store_true")
    parser.add_argument(
        "--allow-metadata-cohorts", action="store_true",
        help="allow multiple one-to-one git-commit/binary cohorts",
    )
    args = parser.parse_args()
    if (
        args.min_trials <= 0 or args.min_batch_repeats <= 0
        or args.min_warmup_runs < 0
    ):
        raise ValueError("trial minima must be positive and warm-up nonnegative")
    points, comparisons = analyze_supports(
        load_rows(args.input), args.min_trials, args.min_batch_repeats,
        args.min_warmup_runs, args.paper_grade, args.allow_metadata_cohorts,
    )
    write_csv(args.points, points)
    write_csv(args.comparisons, comparisons)
    summary = summary_rows(points)
    write_csv(args.summary, summary)
    print(
        f"points={len(points)} panels={len(summary)} "
        f"uncertain={sum(row['winner'] == 'uncertain' for row in points)} "
        f"contract={WINNER_CONTRACT}"
    )


if __name__ == "__main__":
    main()
