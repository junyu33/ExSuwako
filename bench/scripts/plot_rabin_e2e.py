#!/usr/bin/env python3
"""Plot complete Rabin-test scaling and ratios from analyzed E2E data."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


COLORS = {
    "FFR": "#0072B2",
    "BarrettGF2X": "#D55E00",
    "Serial": "#CC79A7",
    "NTL-IterIrredTest": "#009E73",
}
LABELS = {
    "FFR": "FFR",
    "BarrettGF2X": "BarrettGF2X",
    "Serial": "Serial",
    "NTL-IterIrredTest": "NTL IterIrredTest",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plt.rcParams["svg.hashsalt"] = "exsuwako-rabin-v1"
    with args.input.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Rabin summary is empty")

    points: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[int, str]] = set()
    for row in rows:
        m = int(row["m"])
        method = row["method"]
        key = (m, method)
        if key in seen:
            raise ValueError(f"duplicate Rabin point {key}")
        seen.add(key)
        if int(row["trials"]) < 31:
            raise ValueError(f"{key} has fewer than 31 trials")
        points[method].append(row)

    fig, (time_ax, ratio_ax) = plt.subplots(1, 2, figsize=(7.2, 2.8))
    for method in ("FFR", "BarrettGF2X", "NTL-IterIrredTest", "Serial"):
        selected = sorted(points.get(method, []), key=lambda row: int(row["m"]))
        if not selected:
            continue
        x = [math.log2(int(row["m"])) for row in selected]
        times = [float(row["median_e2e_ns"]) / 1e6 for row in selected]
        low = [float(row["median_ci_low_ns"]) / 1e6 for row in selected]
        high = [float(row["median_ci_high_ns"]) / 1e6 for row in selected]
        time_ax.errorbar(
            x,
            times,
            yerr=[[value - lo for value, lo in zip(times, low)],
                  [hi - value for value, hi in zip(times, high)]],
            marker="o",
            linewidth=1.6,
            markersize=4,
            capsize=2,
            color=COLORS[method],
            label=LABELS[method],
        )
        if method != "FFR":
            ratios = [float(row["method_over_FFR"]) for row in selected]
            ratio_low = [float(row["ratio_ci_low"]) for row in selected]
            ratio_high = [float(row["ratio_ci_high"]) for row in selected]
            ratio_ax.errorbar(
                x,
                ratios,
                yerr=[[value - lo for value, lo in zip(ratios, ratio_low)],
                      [hi - value for value, hi in zip(ratios, ratio_high)]],
                marker="o",
                linewidth=1.6,
                markersize=4,
                capsize=2,
                color=COLORS[method],
                label=LABELS[method],
            )

    ticks = [7, 9, 11, 13]
    for axis in (time_ax, ratio_ax):
        axis.set_xticks(ticks)
        axis.set_xticklabels([str(value) for value in ticks])
        axis.set_xlabel(r"$\log_2 m$")
        axis.grid(True, alpha=0.25, linewidth=0.6)
    time_ax.set_yscale("log", base=2)
    time_ax.set_ylabel("complete Rabin test (ms)")
    time_ax.legend(frameon=False, fontsize=7)
    ratio_ax.axhline(1, color="black", linewidth=0.8)
    ratio_ax.set_yscale("log", base=2)
    ratio_ax.set_ylabel("complete time / FFR time")
    ratio_ax.legend(frameon=False, fontsize=7)
    fig.tight_layout(pad=0.5, w_pad=1.1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
