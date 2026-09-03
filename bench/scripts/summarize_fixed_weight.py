#!/usr/bin/env python3
"""Summarize fixed-weight random supports without mixing timing trials."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


PROVENANCES = {
    "synthetic-fixed-weight-uniform:v1",
    "synthetic-fixed-weight-uniform-constant-free:v1",
}
TIMING_SCOPE = "reduction-steady-state:v1"
SUMMARY_CONTRACT = "trial-median-then-support-quantiles:v1"
INVARIANT_FIELDS = (
    "provenance",
    "m",
    "word_bits",
    "s",
    "h",
    "taps",
    "Delta_min",
    "feedback_stages",
    "feedback_active_tap_sum",
    "W_fb",
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
    "LopezDahabLoop_enabled",
)
CELL_INVARIANT_FIELDS = (
    "provenance",
    "word_bits",
    "input_distribution",
    "timing_scope",
    "setup_scope",
    "timing_order",
    "aggregation",
    "inputs",
    "batch_repeats",
    "warmup_runs",
    "measurement_trials",
    "Dense_enabled",
    "LopezDahabLoop_enabled",
)
PRIMARY_METRICS = {
    "GS_ns": "nanoseconds-per-reduction",
    "Serial_ns": "nanoseconds-per-reduction",
    "BarrettGF2X_ns": "nanoseconds-per-reduction",
    "Serial/GS": "ratio",
    "BarrettGF2X/GS": "ratio",
    "Delta_min": "exponents",
    "feedback_stages": "stages",
    "feedback_active_tap_sum": "tap-stage-applications",
    "W_fb": "scheduled-coefficient-work",
}


def nearest_rank(values: list[float], probability: float) -> float:
    if not values or not 0 < probability <= 1:
        raise ValueError("nearest-rank quantile requires data and 0 < p <= 1")
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def parse_nonnegative(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid {field}: {row.get(field)!r}") from error
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
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


def enabled_metrics(rows: list[dict[str, str]]) -> dict[str, str]:
    metrics = dict(PRIMARY_METRICS)
    optional = (
        ("Naive_ns", None),
        ("Dense_ns", "Dense_enabled"),
        ("Dense/GS", "Dense_enabled"),
        ("LopezDahabLoop_ns", "LopezDahabLoop_enabled"),
        ("LopezDahabLoop/GS", "LopezDahabLoop_enabled"),
    )
    for metric, enabled_field in optional:
        if enabled_field is None:
            enabled = [parse_nonnegative(row, metric) > 0 for row in rows]
        else:
            try:
                enabled = [int(row[enabled_field]) == 1 for row in rows]
            except (KeyError, ValueError) as error:
                raise ValueError(f"invalid {enabled_field}") from error
        if any(enabled) and not all(enabled):
            raise ValueError(f"mixed enabled state for {metric}")
        if all(enabled):
            metrics[metric] = (
                "ratio" if metric.endswith("/GS")
                else "nanoseconds-per-reduction"
            )
    return metrics


def load_supports(
    path: Path, min_trials: int, min_batch_repeats: int,
    min_warmup_runs: int,
) -> tuple[list[dict[str, object]], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        raw_rows = list(csv.DictReader(stream))
    if not raw_rows:
        raise ValueError("input contains no rows")
    required = {"sample_id", "measurement_trial", *INVARIANT_FIELDS}
    missing = required.difference(raw_rows[0])
    if missing:
        raise ValueError(f"input is missing fields: {', '.join(sorted(missing))}")
    metrics = enabled_metrics(raw_rows)
    missing = set(metrics).difference(raw_rows[0])
    if missing:
        raise ValueError(f"input is missing metrics: {', '.join(sorted(missing))}")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        if row["provenance"] not in PROVENANCES:
            raise ValueError(
                f"sample {row['sample_id']!r} has non-random provenance "
                f"{row['provenance']!r}"
            )
        if row["timing_scope"] != TIMING_SCOPE:
            raise ValueError(f"unexpected timing scope {row['timing_scope']!r}")
        grouped[row["sample_id"]].append(row)

    supports: list[dict[str, object]] = []
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
                f"sample {sample_id!r} does not contain the required complete "
                f"trial set (found {len(rows)}, need at least {min_trials})"
            )
        if int(first["batch_repeats"]) < min_batch_repeats:
            raise ValueError(
                f"sample {sample_id!r} has too few batch repeats"
            )
        if int(first["warmup_runs"]) < min_warmup_runs:
            raise ValueError(f"sample {sample_id!r} has too few warm-up runs")
        if int(first["h"]) < 2 or first["Delta_min"] == "NA":
            raise ValueError("fixed-weight distribution requires nonempty support")
        for row in rows[1:]:
            for field in INVARIANT_FIELDS:
                if row[field] != first[field]:
                    raise ValueError(
                        f"sample {sample_id!r} changes invariant field {field}"
                    )
        m = int(first["m"])
        s = int(first["s"])
        h = int(first["h"])
        taps = parse_taps(first["taps"], m)
        if len(taps) != s or h != s + 1:
            raise ValueError(f"sample {sample_id!r} has inconsistent weight")
        if m - taps[-1] != int(first["Delta_min"]):
            raise ValueError(f"sample {sample_id!r} has inconsistent Delta_min")
        support_key = (m, first["taps"])
        if support_key in support_keys:
            raise ValueError(
                f"duplicate exact support would overweight (m={support_key[0]}, "
                f"taps={support_key[1]})"
            )
        support_keys.add(support_key)

        support: dict[str, object] = {
            "sample_id": sample_id,
            "m": m,
            "s": s,
            "h": h,
            "taps": first["taps"],
            "seed": first["seed"],
            "trial_count": len(rows),
            "summary_contract": SUMMARY_CONTRACT,
        }
        for field in CELL_INVARIANT_FIELDS:
            support[field] = first[field]
        for metric in metrics:
            values = [parse_nonnegative(row, metric) for row in rows]
            if metric.endswith("_ns") or metric.endswith("/GS"):
                if any(value <= 0 for value in values):
                    raise ValueError(
                        f"enabled metric {metric} must be positive"
                    )
            support[metric] = statistics.median(values)
        supports.append(support)
    return supports, metrics


def summarize(
    supports: list[dict[str, object]], metrics: dict[str, str],
    min_supports: int,
) -> list[dict[str, object]]:
    groups: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    for support in supports:
        groups[(int(support["m"]), int(support["h"]))].append(support)
    output: list[dict[str, object]] = []
    for (m, h), rows in sorted(groups.items()):
        if len(rows) < min_supports:
            raise ValueError(
                f"fixed-weight cell (m={m}, h={h}) has {len(rows)} unique "
                f"supports; need at least {min_supports}"
            )
        seeds = {str(row["seed"]) for row in rows}
        if len(seeds) != 1:
            raise ValueError(f"fixed-weight cell (m={m}, h={h}) mixes seeds")
        for field in CELL_INVARIANT_FIELDS:
            values = {str(row[field]) for row in rows}
            if len(values) != 1:
                raise ValueError(
                    f"fixed-weight cell (m={m}, h={h}) mixes {field}"
                )
        for metric, unit in metrics.items():
            values = [float(row[metric]) for row in rows]
            summary_row = {
                "m": m,
                "s": h - 1,
                "h": h,
                "seed": next(iter(seeds)),
                "unique_supports": len(rows),
                "summary_contract": SUMMARY_CONTRACT,
                "metric": metric,
                "unit": unit,
                "median": statistics.median(values),
                "p90": nearest_rank(values, 0.90),
                "p99": nearest_rank(values, 0.99),
            }
            for field in CELL_INVARIANT_FIELDS:
                summary_row[field] = rows[0][field]
            output.append(summary_row)
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--supports", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--min-supports", type=int, default=100)
    parser.add_argument("--min-trials", type=int, default=31)
    parser.add_argument("--min-batch-repeats", type=int, default=12)
    parser.add_argument("--min-warmup-runs", type=int, default=1)
    args = parser.parse_args()
    if (
        args.min_supports <= 0
        or args.min_trials <= 0
        or args.min_batch_repeats <= 0
        or args.min_warmup_runs < 0
    ):
        raise ValueError("sample minima must be positive and warm-up nonnegative")

    supports, metrics = load_supports(
        args.input, args.min_trials, args.min_batch_repeats,
        args.min_warmup_runs,
    )
    summary = summarize(supports, metrics, args.min_supports)
    support_fields = [
        "sample_id", "m", "s", "h", "taps", "seed", "trial_count",
        "summary_contract", *CELL_INVARIANT_FIELDS, *metrics,
    ]
    write_csv(
        args.supports,
        [{field: row[field] for field in support_fields} for row in supports],
    )
    write_csv(args.summary, summary)
    print(
        f"supports={len(supports)} cells="
        f"{len({(row['m'], row['h']) for row in supports})} "
        f"metrics={len(metrics)} contract={SUMMARY_CONTRACT}"
    )


if __name__ == "__main__":
    main()
