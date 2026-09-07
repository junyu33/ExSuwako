#!/usr/bin/env python3
"""Fit fixed-degree source-cost models and predict winner boundaries."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


MODEL_METHODS = ("GS", "BarrettGF2X", "LopezDahabLoop")


def parse_taps(value: str, line_number: int) -> tuple[int, ...]:
    try:
        taps = tuple(int(item) for item in value.split(";") if item)
    except ValueError as error:
        raise ValueError(f"line {line_number}: invalid tap list") from error
    if tuple(sorted(set(taps))) != taps:
        raise ValueError(f"line {line_number}: taps are not canonical")
    return taps


def gs_word_work(m: int, word_bits: int, taps: tuple[int, ...]) -> int:
    """Portable scalar word blocks in feedback closure plus final assembly."""
    work = sum(math.ceil((m - tap) / word_bits) for tap in taps)
    for tap in taps:
        shift = m - tap
        while shift < m:
            work += math.ceil((m - shift) / word_bits)
            shift *= 2
    return work


def affine_fit(points: list[tuple[float, float]], label: str) -> tuple[float, float]:
    if len(points) < 2:
        raise ValueError(f"{label}: need at least two calibration points")
    mean_x = statistics.fmean(x for x, _ in points)
    mean_y = statistics.fmean(y for _, y in points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        raise ValueError(f"{label}: calibration predictor is constant")
    slope = sum(
        (x - mean_x) * (y - mean_y) for x, y in points
    ) / denominator
    return mean_y - slope * mean_x, slope


def format_number(value: float) -> str:
    return f"{value:.12g}"


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    required = {
        "sample_id", "m", "word_bits", "h", "taps", "Delta_min",
        "log2_m_over_delta", "method_set", "winner", "winner_reason",
        "GS_median_ns", "BarrettGF2X_median_ns",
        "LopezDahabLoop_median_ns",
    }
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        missing = required.difference(fields)
        if missing:
            raise ValueError(f"winner input is missing fields: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("winner input contains no rows")
    seen: set[tuple[int, int, float]] = set()
    for line_number, row in enumerate(rows, 2):
        try:
            m = int(row["m"])
            word_bits = int(row["word_bits"])
            h = int(row["h"])
            delta = int(row["Delta_min"])
            log_ratio = float(row["log2_m_over_delta"])
            gs_ns = float(row["GS_median_ns"])
            barrett_ns = float(row["BarrettGF2X_median_ns"])
        except ValueError as error:
            raise ValueError(f"line {line_number}: invalid numeric field") from error
        taps = parse_taps(row["taps"], line_number)
        coordinate = (m, h, log_ratio)
        if coordinate in seen:
            raise ValueError(f"line {line_number}: duplicate phase coordinate")
        seen.add(coordinate)
        if (
            m <= 0 or word_bits <= 0 or h != len(taps) + 1
            or delta <= 0 or delta > m
            or not math.isclose(log_ratio, math.log2(m / delta), abs_tol=1e-12)
            or gs_ns <= 0 or barrett_ns <= 0
        ):
            raise ValueError(f"line {line_number}: inconsistent winner point")
        methods = row["method_set"].split(";")
        if "GS" not in methods or "BarrettGF2X" not in methods:
            raise ValueError(f"line {line_number}: missing mandatory model method")
        if "LopezDahabLoop" in methods:
            try:
                if float(row["LopezDahabLoop_median_ns"]) <= 0:
                    raise ValueError
            except ValueError as error:
                raise ValueError(
                    f"line {line_number}: invalid Lopez-Dahab median"
                ) from error
    return fields, rows


def errors(
    rows: list[dict[str, str]], predictor: str, response: str,
    intercept: float, slope: float,
) -> tuple[float, float]:
    absolute: list[float] = []
    relative: list[float] = []
    for row in rows:
        if not row[predictor] or not row[response]:
            continue
        observed = float(row[response])
        residual = abs(observed - (intercept + slope * float(row[predictor])))
        absolute.append(residual)
        relative.append(residual / observed)
    if not absolute:
        return math.nan, math.nan
    return statistics.fmean(absolute), statistics.fmean(relative)


def fit_and_predict(
    fields: list[str], rows: list[dict[str, str]], output: Path, diagnostics: Path,
) -> None:
    groups: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        m = int(row["m"])
        taps = parse_taps(row["taps"], 0)
        word_bits = int(row["word_bits"])
        row["measured_winner"] = row["winner"]
        row["C_GS"] = str(gs_word_work(m, word_bits, taps))
        row["C_LD"] = (
            str(math.ceil(m / word_bits) * len(taps))
            if "LopezDahabLoop" in row["method_set"].split(";") else ""
        )
        groups[m].append(row)

    diagnostic_rows: list[dict[str, str]] = []
    for m, group in sorted(groups.items()):
        ordered = sorted(
            group,
            key=lambda row: (
                int(row["h"]), -float(row["log2_m_over_delta"]),
                row["sample_id"],
            ),
        )
        for index, row in enumerate(ordered):
            row["cost_model_split"] = "calibration" if index % 2 == 0 else "holdout"
        calibration = [row for row in ordered if row["cost_model_split"] == "calibration"]
        holdout = [row for row in ordered if row["cost_model_split"] == "holdout"]

        gs_fit = affine_fit(
            [(float(row["C_GS"]), float(row["GS_median_ns"])) for row in calibration],
            f"m={m} GS",
        )
        ld_calibration = [
            row for row in calibration
            if row["C_LD"] and row["LopezDahabLoop_median_ns"]
        ]
        ld_fit = affine_fit(
            [(float(row["C_LD"]), float(row["LopezDahabLoop_median_ns"]))
             for row in ld_calibration],
            f"m={m} Lopez-Dahab",
        )
        barrett_constant = statistics.median(
            float(row["BarrettGF2X_median_ns"]) for row in calibration
        )

        models = {
            "GS": ("C_GS", "GS_median_ns", *gs_fit),
            "LopezDahabLoop": (
                "C_LD", "LopezDahabLoop_median_ns", *ld_fit,
            ),
        }
        for method, (predictor, response, intercept, slope) in models.items():
            mae, mare = errors(holdout, predictor, response, intercept, slope)
            diagnostic_rows.append({
                "m": str(m), "method": method, "model": "affine-source-work:v1",
                "predictor": predictor, "calibration_points": str(sum(
                    bool(row[predictor] and row[response]) for row in calibration
                )), "holdout_points": str(sum(
                    bool(row[predictor] and row[response]) for row in holdout
                )), "intercept_ns": format_number(intercept),
                "slope_ns_per_work": format_number(slope),
                "holdout_mae_ns": format_number(mae),
                "holdout_mean_relative_error": format_number(mare),
            })
        barrett_holdout = [float(row["BarrettGF2X_median_ns"]) for row in holdout]
        diagnostic_rows.append({
            "m": str(m), "method": "BarrettGF2X", "model": "fixed-m-median:v1",
            "predictor": "constant", "calibration_points": str(len(calibration)),
            "holdout_points": str(len(barrett_holdout)),
            "intercept_ns": format_number(barrett_constant),
            "slope_ns_per_work": "0",
            "holdout_mae_ns": format_number(statistics.fmean(
                abs(value - barrett_constant) for value in barrett_holdout
            )),
            "holdout_mean_relative_error": format_number(statistics.fmean(
                abs(value - barrett_constant) / value for value in barrett_holdout
            )),
        })

        for row in ordered:
            predictions = {
                "GS": gs_fit[0] + gs_fit[1] * float(row["C_GS"]),
                "BarrettGF2X": barrett_constant,
            }
            row["GS_predicted_ns"] = format_number(predictions["GS"])
            row["BarrettGF2X_predicted_ns"] = format_number(barrett_constant)
            row["LopezDahabLoop_predicted_ns"] = ""
            if row["C_LD"]:
                predictions["LopezDahabLoop"] = (
                    ld_fit[0] + ld_fit[1] * float(row["C_LD"])
                )
                row["LopezDahabLoop_predicted_ns"] = format_number(
                    predictions["LopezDahabLoop"]
                )
            row["winner"] = min(predictions, key=predictions.get)
            row["winner_reason"] = "cost-model-prediction"

    extra_fields = [
        "measured_winner", "cost_model_split", "C_GS", "C_LD",
        "GS_predicted_ns", "BarrettGF2X_predicted_ns",
        "LopezDahabLoop_predicted_ns",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields + extra_fields)
        writer.writeheader()
        writer.writerows(rows)

    diagnostic_fields = [
        "m", "method", "model", "predictor", "calibration_points",
        "holdout_points", "intercept_ns", "slope_ns_per_work",
        "holdout_mae_ns", "holdout_mean_relative_error",
    ]
    diagnostics.parent.mkdir(parents=True, exist_ok=True)
    with diagnostics.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=diagnostic_fields)
        writer.writeheader()
        writer.writerows(diagnostic_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    args = parser.parse_args()
    fields, rows = load_rows(args.input)
    fit_and_predict(fields, rows, args.output, args.diagnostics)
    print(
        f"points={len(rows)} degrees={len({row['m'] for row in rows})} "
        f"output={args.output} diagnostics={args.diagnostics}"
    )


if __name__ == "__main__":
    main()
