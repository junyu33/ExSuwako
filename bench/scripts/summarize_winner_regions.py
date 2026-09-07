#!/usr/bin/env python3
"""Summarize measured winner regions and persistent Barrett crossovers."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path


WINNERS = {"GS", "Serial", "BarrettGF2X", "Dense", "LopezDahabLoop", "uncertain"}


def load_points(path: Path) -> list[dict[str, str]]:
    required = {
        "sample_id", "m", "word_bits", "h", "Delta_min",
        "log2_m_over_delta", "winner", "winner_reason",
    }
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"winner points are missing fields: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("winner-point input is empty")
    coordinates: set[tuple[int, int, int]] = set()
    for line_number, row in enumerate(rows, 2):
        try:
            coordinate = (int(row["m"]), int(row["h"]), int(row["Delta_min"]))
            word_bits = int(row["word_bits"])
        except ValueError as error:
            raise ValueError(f"line {line_number}: invalid integer coordinate") from error
        if min(coordinate) <= 0 or coordinate[1] < 2 or word_bits <= 0:
            raise ValueError(f"line {line_number}: invalid phase coordinate")
        if coordinate in coordinates:
            raise ValueError(f"line {line_number}: duplicate phase coordinate {coordinate}")
        coordinates.add(coordinate)
        if row["winner"] not in WINNERS:
            raise ValueError(f"line {line_number}: unknown winner {row['winner']!r}")
    return rows


def compress_runs(rows: list[dict[str, str]]) -> str:
    runs: list[str] = []
    for winner, grouped in groupby(rows, key=lambda row: row["winner"]):
        group = list(grouped)
        first, last = int(group[0]["h"]), int(group[-1]["h"])
        interval = str(first) if first == last else f"{first}-{last}"
        runs.append(f"{winner}:{interval}")
    return ";".join(runs)


def detail_rows(points: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    for point in points:
        grouped[(int(point["m"]), int(point["Delta_min"]))].append(point)
    details: list[dict[str, object]] = []
    for (m, delta_min), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: int(row["h"]))
        word_bits_values = {int(row["word_bits"]) for row in rows}
        if len(word_bits_values) != 1:
            raise ValueError(f"(m, Delta_min)=({m}, {delta_min}) mixes word widths")
        word_bits = word_bits_values.pop()
        stable = [row for row in rows if row["winner"] != "uncertain"]
        crossover = ""
        predecessor = ""
        for index, row in enumerate(stable):
            if row["winner"] == "BarrettGF2X" and all(
                later["winner"] == "BarrettGF2X" for later in stable[index:]
            ):
                crossover = int(row["h"])
                if index:
                    predecessor = int(stable[index - 1]["h"])
                break
        outcomes = Counter(row["winner"] for row in rows)
        details.append({
            "m": m,
            "word_bits": word_bits,
            "Delta_min": delta_min,
            "log2_m_over_delta": rows[0]["log2_m_over_delta"],
            "regime": "hard-feedback" if delta_min < word_bits else "ld-applicable",
            "sampled_h_min": min(int(row["h"]) for row in rows),
            "sampled_h_max": max(int(row["h"]) for row in rows),
            "points": len(rows),
            "persistent_Barrett_h": crossover,
            "last_stable_h_before_Barrett": predecessor,
            "GS_wins": outcomes["GS"],
            "Serial_wins": outcomes["Serial"],
            "LopezDahabLoop_wins": outcomes["LopezDahabLoop"],
            "BarrettGF2X_wins": outcomes["BarrettGF2X"],
            "Dense_wins": outcomes["Dense"],
            "uncertain": outcomes["uncertain"],
            "winner_runs": compress_runs(rows),
        })
    return details


def summary_rows(details: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in details:
        grouped[(int(row["m"]), str(row["regime"]))].append(row)
    summaries: list[dict[str, object]] = []
    for (m, regime), rows in sorted(grouped.items()):
        crossovers = [
            int(row["persistent_Barrett_h"])
            for row in rows if row["persistent_Barrett_h"] != ""
        ]
        predecessors = [
            int(row["last_stable_h_before_Barrett"])
            for row in rows if row["last_stable_h_before_Barrett"] != ""
        ]
        summaries.append({
            "m": m,
            "regime": regime,
            "Delta_min_min": min(int(row["Delta_min"]) for row in rows),
            "Delta_min_max": max(int(row["Delta_min"]) for row in rows),
            "Delta_rows": len(rows),
            "persistent_Barrett_rows": len(crossovers),
            "no_persistent_Barrett_rows": len(rows) - len(crossovers),
            "persistent_Barrett_h_min": min(crossovers) if crossovers else "",
            "persistent_Barrett_h_max": max(crossovers) if crossovers else "",
            "pre_crossover_h_min": min(predecessors) if predecessors else "",
            "pre_crossover_h_max": max(predecessors) if predecessors else "",
            "points": sum(int(row["points"]) for row in rows),
            "GS_wins": sum(int(row["GS_wins"]) for row in rows),
            "Serial_wins": sum(int(row["Serial_wins"]) for row in rows),
            "LopezDahabLoop_wins": sum(
                int(row["LopezDahabLoop_wins"]) for row in rows
            ),
            "BarrettGF2X_wins": sum(int(row["BarrettGF2X_wins"]) for row in rows),
            "Dense_wins": sum(int(row["Dense_wins"]) for row in rows),
            "uncertain": sum(int(row["uncertain"]) for row in rows),
        })
    return summaries


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    details = detail_rows(load_points(args.input))
    summaries = summary_rows(details)
    write_csv(args.detail, details)
    write_csv(args.summary, summaries)
    print(
        f"points={sum(int(row['points']) for row in details)} "
        f"delta_rows={len(details)} summary_rows={len(summaries)}"
    )


if __name__ == "__main__":
    main()
