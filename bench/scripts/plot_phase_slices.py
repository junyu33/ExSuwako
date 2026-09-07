#!/usr/bin/env python3
"""Plot fixed-gap and fixed-weight timing slices relative to FFR (key GS)."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
SERIES_COLORS = ("#237a44", "#69b578", "#68419b", "#a783cc")


@dataclass(frozen=True)
class Point:
    m: int
    h: int
    delta_min: int
    log_ratio: float
    winner_reason: str
    gs_ns: float
    barrett_ns: float
    ld_ns: float | None


def element(tag: str, **attributes: object) -> ET.Element:
    return ET.Element(
        f"{{{SVG_NS}}}{tag}",
        {name.replace("_", "-"): str(value) for name, value in attributes.items()},
    )


def add_text(parent: ET.Element, x: float, y: float, value: str, **attributes: object) -> None:
    node = ET.SubElement(parent, f"{{{SVG_NS}}}text", {
        "x": f"{x:.2f}", "y": f"{y:.2f}",
        **{name.replace("_", "-"): str(item) for name, item in attributes.items()},
    })
    node.text = value


def positive(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise ValueError(f"invalid {field}: {row.get(field)!r}") from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return value


def load_points(path: Path) -> list[Point]:
    required = {
        "m", "h", "Delta_min", "log2_m_over_delta", "winner_reason",
        "GS_median_ns", "BarrettGF2X_median_ns", "LopezDahabLoop_median_ns",
    }
    points: list[Point] = []
    coordinates: set[tuple[int, int, int]] = set()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"winner points are missing fields: {sorted(missing)}")
        for line_number, row in enumerate(reader, 2):
            try:
                m, h, delta_min = int(row["m"]), int(row["h"]), int(row["Delta_min"])
                log_ratio = float(row["log2_m_over_delta"])
            except ValueError as error:
                raise ValueError(f"line {line_number}: invalid phase coordinate") from error
            coordinate = (m, h, delta_min)
            if coordinate in coordinates:
                raise ValueError(f"line {line_number}: duplicate coordinate {coordinate}")
            coordinates.add(coordinate)
            expected_log = math.log2(m / delta_min)
            if not math.isclose(log_ratio, expected_log, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"line {line_number}: inconsistent feedback coordinate")
            ld_text = row["LopezDahabLoop_median_ns"]
            points.append(Point(
                m, h, delta_min, log_ratio, row["winner_reason"],
                positive(row, "GS_median_ns"),
                positive(row, "BarrettGF2X_median_ns"),
                positive(row, "LopezDahabLoop_median_ns") if ld_text else None,
            ))
    if not points:
        raise ValueError("winner-point input is empty")
    return points


def selected_series(
    panel: list[Point], kind: str, selections: list[int]
) -> list[tuple[str, str, list[tuple[float, float, bool]]]]:
    series: list[tuple[str, str, list[tuple[float, float, bool]]]] = []
    for selection_index, selection in enumerate(selections):
        chosen = [
            point for point in panel
            if (point.delta_min if kind == "weight" else point.h) == selection
        ]
        if not chosen:
            raise ValueError(f"panel m={panel[0].m} lacks selected value {selection}")
        chosen.sort(key=lambda point: point.h if kind == "weight" else point.log_ratio)
        x_values = [
            math.log2(point.h - 1) if kind == "weight" else point.log_ratio
            for point in chosen
        ]
        uncertain = [point.winner_reason != "unique-winner" for point in chosen]
        label_name = "Delta_min" if kind == "weight" else "h"
        barrett = [
            (x, math.log2(point.barrett_ns / point.gs_ns), flag)
            for x, point, flag in zip(x_values, chosen, uncertain)
        ]
        series.append((f"Barrett, {label_name}={selection}", SERIES_COLORS[selection_index], barrett))
        ld = [
            (x, math.log2(point.ld_ns / point.gs_ns), flag)
            for x, point, flag in zip(x_values, chosen, uncertain)
            if point.ld_ns is not None
        ]
        if ld:
            series.append((f"López–Dahab, {label_name}={selection}", SERIES_COLORS[selection_index + 2], ld))
    return series


def render(points: list[Point], output: Path, kind: str, selections: list[int]) -> None:
    degrees = sorted({point.m for point in points})
    if len(degrees) != 6:
        raise ValueError("phase-slice figure requires exactly six modulus degrees")
    panels = {
        m: selected_series([point for point in points if point.m == m], kind, selections)
        for m in degrees
    }
    all_coordinates = [coordinate for series in panels.values() for _, _, values in series for coordinate in values]
    y_min = math.floor(min(y for _, y, _ in all_coordinates))
    y_max = math.ceil(max(y for _, y, _ in all_coordinates))
    y_min, y_max = min(y_min, -1), max(y_max, 1)

    panel_width, panel_height = 365, 282
    width, height = panel_width * 3, 76 + panel_height * 2
    root = element("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#fff",
    })
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1}"
        ".grid{stroke:#ddd;stroke-width:1}.tie{stroke:#111;stroke-width:1.8}"
        ".series{fill:none;stroke-width:2}.certain{stroke:#fff;stroke-width:.8}"
        ".uncertain{fill:#fff;stroke:#777;stroke-width:2}"
    )
    heading = "Fixed-gap weight sweeps" if kind == "weight" else "Fixed-weight feedback sweeps"
    add_text(root, width / 2, 23, heading, text_anchor="middle", font_size=16, font_weight="bold")

    legend_series = panels[degrees[0]]
    legend_x = 20.0
    for label, color, _ in legend_series:
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": f"{legend_x:.2f}", "x2": f"{legend_x + 17:.2f}",
            "y1": "46", "y2": "46", "stroke": color, "stroke-width": "3",
        })
        add_text(root, legend_x + 22, 50, label, font_size=8)
        legend_x += 48 + 4.8 * len(label)

    for panel_index, m in enumerate(degrees):
        column, row = panel_index % 3, panel_index // 3
        ox, oy = column * panel_width, 64 + row * panel_height
        left, right, top, bottom = ox + 61, ox + 347, oy + 34, oy + 230
        series = panels[m]
        xs = [x for _, _, values in series for x, _, _ in values]
        x_min, x_max = min(xs), max(xs)
        if x_min == x_max:
            x_min -= 0.5; x_max += 0.5

        def map_x(value: float) -> float:
            return left + (value - x_min) / (x_max - x_min) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

        add_text(root, (left + right) / 2, oy + 18, f"m = {m}",
                 text_anchor="middle", font_size=13, font_weight="bold")
        for exponent in range(y_min, y_max + 1, 2):
            y = map_y(exponent)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y), "y2": str(y),
                "class": "grid",
            })
            add_text(root, left - 7, y + 3, str(exponent), text_anchor="end", font_size=8)
        tie_y = map_y(0)
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(right), "y1": str(tie_y), "y2": str(tie_y),
            "class": "tie",
        })
        for label, color, values in series:
            ET.SubElement(root, f"{{{SVG_NS}}}polyline", {
                "points": " ".join(f"{map_x(x):.2f},{map_y(y):.2f}" for x, y, _ in values),
                "stroke": color, "class": "series",
            })
            for x, y, uncertain in values:
                ET.SubElement(root, f"{{{SVG_NS}}}circle", {
                    "cx": f"{map_x(x):.2f}", "cy": f"{map_y(y):.2f}", "r": "3.2",
                    "fill": color, "class": "uncertain" if uncertain else "certain",
                })
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "fill": "none", "class": "axis",
        })
        for value in range(math.ceil(x_min), math.floor(x_max) + 1, 2):
            add_text(root, map_x(value), bottom + 17, str(value), text_anchor="middle", font_size=8)
        x_label = "log2(h - 1)" if kind == "weight" else "log2(m / Delta_min)"
        add_text(root, (left + right) / 2, bottom + 36, x_label,
                 text_anchor="middle", font_size=10)
        add_text(root, ox + 13, (top + bottom) / 2, "log2(T_method / T_FFR)",
                 text_anchor="middle", font_size=9,
                 transform=f"rotate(-90 {ox + 13} {(top + bottom) / 2})")

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("weight", "gap"), required=True)
    parser.add_argument("--selections", type=int, nargs=2, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("phase-slice output must use the .svg extension")
    if len(set(args.selections)) != 2 or any(value <= 0 for value in args.selections):
        raise ValueError("phase slices require two distinct positive selections")
    points = load_points(args.input)
    render(points, args.output, args.kind, args.selections)
    print(f"kind={args.kind} panels=6 selections={args.selections} output={args.output}")


if __name__ == "__main__":
    main()
