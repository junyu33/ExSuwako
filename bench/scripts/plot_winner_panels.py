#!/usr/bin/env python3
"""Render measured fixed-m winner points without interpolated boundaries."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
COLORS = {
    "GS": "#356aa0",
    "Serial": "#e6862a",
    "BarrettGF2X": "#3b8f55",
    "Dense": "#c84b4b",
    "LopezDahabLoop": "#7651a8",
    "uncertain": "#999999",
}


@dataclass(frozen=True)
class WinnerPoint:
    sample_id: str
    m: int
    h: int
    log_ratio: float
    winner: str
    reason: str
    lopez_dahab_enabled: bool


def element(tag: str, **attributes: object) -> ET.Element:
    return ET.Element(
        f"{{{SVG_NS}}}{tag}",
        {name.replace("_", "-"): str(value) for name, value in attributes.items()},
    )


def add_text(
    parent: ET.Element, x: float, y: float, value: str, **attributes: object
) -> None:
    node = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}text",
        {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            **{
                key.replace("_", "-"): str(item)
                for key, item in attributes.items()
            },
        },
    )
    node.text = value


def load_points(path: Path) -> list[WinnerPoint]:
    required = {
        "sample_id", "m", "h", "log2_m_over_delta", "winner",
        "winner_reason", "method_set",
    }
    points: list[WinnerPoint] = []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"winner input is missing fields: {sorted(missing)}")
        for line_number, row in enumerate(reader, 2):
            try:
                m = int(row["m"])
                h = int(row["h"])
                log_ratio = float(row["log2_m_over_delta"])
            except ValueError as error:
                raise ValueError(f"line {line_number}: invalid phase coordinate") from error
            winner = row["winner"]
            if m <= 0 or h < 2 or not math.isfinite(log_ratio):
                raise ValueError(f"line {line_number}: invalid phase coordinate")
            if winner not in COLORS:
                raise ValueError(f"line {line_number}: unknown winner {winner!r}")
            if winner == "uncertain" and row["winner_reason"] == "unique-winner":
                raise ValueError(f"line {line_number}: inconsistent uncertainty")
            points.append(WinnerPoint(
                row["sample_id"], m, h, log_ratio, winner,
                row["winner_reason"], "LopezDahabLoop" in row["method_set"].split(";"),
            ))
    if not points:
        raise ValueError("winner input contains no points")
    return points


def render(points: list[WinnerPoint], output: Path, columns: int) -> None:
    degrees = sorted({point.m for point in points})
    columns = min(columns, len(degrees))
    panel_rows = math.ceil(len(degrees) / columns)
    panel_width, panel_height = 365, 282
    width = panel_width * columns
    height = 76 + panel_height * panel_rows
    root = element("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    title = ET.SubElement(root, f"{{{SVG_NS}}}title")
    title.text = "Measured reduction winners by fixed modulus degree"
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1}"
        ".grid{stroke:#ddd;stroke-width:1}.ld{stroke:#111;stroke-width:2}"
    )
    add_text(
        root, width / 2, 22, "Measured winners (no boundary interpolation)",
        text_anchor="middle", font_size=16, font_weight="bold",
    )

    legend_x = 18.0
    for winner in COLORS:
        ET.SubElement(root, f"{{{SVG_NS}}}circle", {
            "cx": f"{legend_x:.2f}", "cy": "45", "r": "4",
            "fill": COLORS[winner],
        })
        add_text(root, legend_x + 7, 49, winner, font_size=9)
        legend_x += 27 + 5.2 * len(winner)

    for panel_index, m in enumerate(degrees):
        column = panel_index % columns
        panel_row = panel_index // columns
        ox = column * panel_width
        oy = 65 + panel_row * panel_height
        left, right, top, bottom = ox + 62, ox + 347, oy + 34, oy + 230
        panel = [point for point in points if point.m == m]
        h_values = [point.h for point in panel]
        logs = [point.log_ratio for point in panel]
        x_min, x_max = min(h_values), max(h_values)
        if x_min == x_max:
            x_min -= 1
            x_max += 1
        y_min, y_max = math.floor(min(logs)), math.ceil(max(logs))
        if y_min == y_max:
            y_max += 1

        def map_x(value: float) -> float:
            return left + (value - x_min) / (x_max - x_min) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

        add_text(
            root, (left + right) / 2, oy + 18, f"m = {m}",
            text_anchor="middle", font_size=13, font_weight="bold",
        )
        for exponent in range(y_min, y_max + 1):
            y = map_y(exponent)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y),
                "y2": str(y), "class": "grid",
            })
            add_text(root, left - 7, y + 3, f"2^{exponent}", text_anchor="end", font_size=9)
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(right), "y1": str(bottom),
            "y2": str(bottom), "class": "axis",
        })
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(left), "y1": str(top),
            "y2": str(bottom), "class": "axis",
        })
        for h in sorted(set(h_values)):
            x = map_x(h)
            add_text(root, x, bottom + 17, str(h), text_anchor="middle", font_size=9)
        for point in panel:
            x, y = map_x(point.h), map_y(point.log_ratio)
            if point.winner == "uncertain":
                ET.SubElement(root, f"{{{SVG_NS}}}line", {
                    "x1": f"{x - 4:.2f}", "x2": f"{x + 4:.2f}",
                    "y1": f"{y - 4:.2f}", "y2": f"{y + 4:.2f}",
                    "stroke": COLORS["uncertain"], "stroke-width": "2",
                })
                ET.SubElement(root, f"{{{SVG_NS}}}line", {
                    "x1": f"{x - 4:.2f}", "x2": f"{x + 4:.2f}",
                    "y1": f"{y + 4:.2f}", "y2": f"{y - 4:.2f}",
                    "stroke": COLORS["uncertain"], "stroke-width": "2",
                })
            else:
                attributes = {
                    "cx": f"{x:.2f}", "cy": f"{y:.2f}", "r": "4",
                    "fill": COLORS[point.winner],
                }
                if point.lopez_dahab_enabled:
                    attributes["class"] = "ld"
                ET.SubElement(root, f"{{{SVG_NS}}}circle", attributes)
        counts = Counter(point.winner for point in panel)
        add_text(
            root, right, top + 10,
            f"n={len(panel)}, uncertain={counts['uncertain']}",
            text_anchor="end", font_size=9,
        )
        add_text(
            root, (left + right) / 2, bottom + 36, "modulus Hamming weight h",
            text_anchor="middle", font_size=10,
        )
        add_text(
            root, ox + 14, (top + bottom) / 2, "m / Delta_min (log2)",
            text_anchor="middle", font_size=10,
            transform=f"rotate(-90 {ox + 14} {(top + bottom) / 2})",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=3)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("winner-panel output must use the .svg extension")
    if args.columns <= 0:
        raise ValueError("columns must be positive")
    points = load_points(args.input)
    render(points, args.output, args.columns)
    outcomes = Counter(point.winner for point in points)
    print(
        f"panels={len({point.m for point in points})} points={len(points)} "
        f"uncertain={outcomes['uncertain']} columns={args.columns} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
