#!/usr/bin/env python3
"""Summarize the isolated planned-versus-online FFR experiment."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_ratio(rows: list[dict[str, str]], seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    ratios: list[float] = []
    for _ in range(10_000):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        planned = statistics.median(float(row["PlannedFFR_ns"]) for row in sample)
        online = statistics.median(float(row["OnlineFFR_ns"]) for row in sample)
        ratios.append(online / planned)
    return percentile(ratios, 0.025), percentile(ratios, 0.975)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-trials", type=int, default=31)
    args = parser.parse_args()
    with args.input.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["timing_scope"] != "ffr-online-steady-state:v1":
            raise ValueError("mixed timing scope")
        grouped[row["sample_id"]].append(row)

    summaries: list[dict[str, object]] = []
    for index, (sample_id, group) in enumerate(sorted(grouped.items())):
        if len(group) < args.min_trials:
            raise ValueError(f"{sample_id}: only {len(group)} trials")
        if len({int(row["trial"]) for row in group}) != len(group):
            raise ValueError(f"{sample_id}: duplicate trial")
        planned = statistics.median(float(row["PlannedFFR_ns"]) for row in group)
        online = statistics.median(float(row["OnlineFFR_ns"]) for row in group)
        planned_setup = statistics.median(
            float(row["PlannedFFR_setup_ns"]) for row in group
        )
        online_setup = statistics.median(
            float(row["OnlineFFR_setup_ns"]) for row in group
        )
        low, high = bootstrap_ratio(group, 0x4F4E4C494E45 + index)
        first = group[0]
        summaries.append(
            {
                "sample_id": sample_id,
                "m": first["m"],
                "h": first["h"],
                "Delta_min": first["Delta_min"],
                "taps": first["taps"],
                "trials": len(group),
                "PlannedFFR_ns_median": f"{planned:.3f}",
                "OnlineFFR_ns_median": f"{online:.3f}",
                "Online_over_Planned": f"{online / planned:.6f}",
                "ratio_ci_low": f"{low:.6f}",
                "ratio_ci_high": f"{high:.6f}",
                "PlannedFFR_setup_ns_median": f"{planned_setup:.3f}",
                "OnlineFFR_setup_ns_median": f"{online_setup:.3f}",
                "Planned_K1_estimate_ns": f"{planned_setup + planned:.3f}",
                "Online_K1_estimate_ns": f"{online_setup + online:.3f}",
                "Online_over_Planned_K1_estimate": (
                    f"{(online_setup + online) / (planned_setup + planned):.6f}"
                ),
                "PlannedFFR_plan_bytes": first["PlannedFFR_plan_bytes"],
                "OnlineFFR_workspace_bytes": first["OnlineFFR_workspace_bytes"],
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print(f"samples={len(summaries)} output={args.output}")


if __name__ == "__main__":
    main()
