#!/usr/bin/env python3
"""Render measured fixed-m winner points and optional predicted boundaries."""

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
DISPLAY_NAMES = {
    "GS": "FFR",
    "Serial": "Serial",
    "BarrettGF2X": "BarrettGF2X",
    "Dense": "Dense",
    "LopezDahabLoop": "LopezDahab",
    "uncertain": "uncertain",
}
BOUNDARY_CLASSES = {
    frozenset(("GS", "BarrettGF2X")): ("boundary-gs-barrett", "FFR–Barrett"),
    frozenset(("GS", "LopezDahabLoop")): (
        "boundary-gs-ld", "FFR–López–Dahab",
    ),
    frozenset(("BarrettGF2X", "LopezDahabLoop")): (
        "boundary-ld-barrett", "López–Dahab–Barrett",
    ),
}
# Pair-specific high-contrast colors chosen to remain visible across the two
# adjacent cool winner fills; they are not intended as literal RGB inverses.
BOUNDARY_COLORS = {
    "boundary-gs-barrett": "#ff6b35",
    "boundary-gs-ld": "#e6b800",
    "boundary-ld-barrett": "#00c7e6",
}


def boundary_class(left: str, right: str) -> str:
    return BOUNDARY_CLASSES.get(
        frozenset((left, right)), ("boundary-other", "other boundary")
    )[0]


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


def render(
    points: list[WinnerPoint], output: Path, columns: int, mode: str, heading: str,
    boundary_points: list[WinnerPoint] | None,
) -> None:
    degrees = sorted({point.m for point in points})
    columns = min(columns, len(degrees))
    panel_rows = math.ceil(len(degrees) / columns)
    panel_width, panel_height = 365, 282
    width = panel_width * columns
    height = 76 + panel_height * panel_rows
    root = element("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height),
        "fill": "#ffffff",
    })
    title = ET.SubElement(root, f"{{{SVG_NS}}}title")
    title.text = "Measured reduction winners by fixed modulus degree"
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1}"
        ".grid{stroke:#ddd;stroke-width:1}.cell{stroke:#fff;stroke-width:.65}"
        ".predicted-boundary{stroke-width:4;stroke-linecap:round}"
        f".boundary-gs-barrett{{stroke:{BOUNDARY_COLORS['boundary-gs-barrett']}}}"
        f".boundary-gs-ld{{stroke:{BOUNDARY_COLORS['boundary-gs-ld']}}}"
        f".boundary-ld-barrett{{stroke:{BOUNDARY_COLORS['boundary-ld-barrett']}}}"
    )
    add_text(
        root, width / 2, 22, heading,
        text_anchor="middle", font_size=16, font_weight="bold",
    )

    legend_x = 18.0
    observed_winners = set(point.winner for point in points)
    for winner in COLORS:
        if winner not in observed_winners:
            continue
        if mode == "blocks":
            ET.SubElement(root, f"{{{SVG_NS}}}rect", {
                "x": f"{legend_x - 4:.2f}", "y": "41", "width": "8",
                "height": "8", "fill": COLORS[winner],
            })
        else:
            ET.SubElement(root, f"{{{SVG_NS}}}circle", {
                "cx": f"{legend_x:.2f}", "cy": "45", "r": "4",
                "fill": COLORS[winner],
            })
        display_name = DISPLAY_NAMES[winner]
        add_text(root, legend_x + 7, 49, display_name, font_size=12)
        legend_x += 27 + 6.7 * len(display_name)
    if boundary_points is not None:
        for interface_class, label in BOUNDARY_CLASSES.values():
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": f"{legend_x - 4:.2f}", "x2": f"{legend_x + 14:.2f}",
                "y1": "45", "y2": "45",
                "class": f"predicted-boundary {interface_class}",
            })
            add_text(root, legend_x + 19, 49, label, font_size=12)
            legend_x += 42 + 6.7 * len(label)

    for panel_index, m in enumerate(degrees):
        column = panel_index % columns
        panel_row = panel_index // columns
        ox = column * panel_width
        oy = 65 + panel_row * panel_height
        left, right, top, bottom = ox + 62, ox + 347, oy + 34, oy + 230
        panel = [point for point in points if point.m == m]
        h_values = sorted({point.h for point in panel})
        log_values = sorted({point.log_ratio for point in panel})
        h_indices = {h: index for index, h in enumerate(h_values)}
        log_indices = {
            log_ratio: index for index, log_ratio in enumerate(log_values)
        }
        x_min, x_max = -0.5, len(h_values) - 0.5
        y_min, y_max = -0.5, len(log_values) - 0.5

        def map_x(value: float) -> float:
            return left + (value - x_min) / (x_max - x_min) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "fill": "#f5f5f5",
        })
        add_text(
            root, (left + right) / 2, oy + 18, f"m = {m}",
            text_anchor="middle", font_size=13, font_weight="bold",
        )
        for index, log_ratio in enumerate(log_values):
            y = map_y(index)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y),
                "y2": str(y), "class": "grid",
            })
            label = f"{log_ratio:g}"
            add_text(root, left - 7, y + 4, label, text_anchor="end", font_size=11)
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(right), "y1": str(bottom),
            "y2": str(bottom), "class": "axis",
        })
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(left), "y1": str(top),
            "y2": str(bottom), "class": "axis",
        })
        labelled_h = {h for h in h_values if (h - 1) & (h - 2) == 0}
        labelled_h.update((h_values[0], h_values[-1]))
        for h in h_values:
            x = map_x(h_indices[h])
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(x), "x2": str(x), "y1": str(top),
                "y2": str(bottom), "class": "grid",
            })
            if h in labelled_h:
                log_weight = math.log2(h - 1)
                tick_label = (
                    str(round(log_weight))
                    if log_weight.is_integer()
                    else f"{log_weight:.2f}"
                )
                add_text(
                    root, x, bottom + 17, tick_label,
                    text_anchor="middle", font_size=11,
                )
        for point in panel:
            x_coordinate = h_indices[point.h]
            y_coordinate = log_indices[point.log_ratio]
            x, y = map_x(x_coordinate), map_y(y_coordinate)
            if mode == "blocks":
                ET.SubElement(root, f"{{{SVG_NS}}}rect", {
                    "x": f"{map_x(x_coordinate - 0.5):.2f}",
                    "y": f"{map_y(y_coordinate + 0.5):.2f}",
                    "width": f"{map_x(x_coordinate + 0.5) - map_x(x_coordinate - 0.5):.2f}",
                    "height": f"{map_y(y_coordinate - 0.5) - map_y(y_coordinate + 0.5):.2f}",
                    "fill": COLORS[point.winner], "class": "cell",
                })
            elif point.winner == "uncertain":
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
                ET.SubElement(root, f"{{{SVG_NS}}}circle", attributes)
        if boundary_points is not None:
            predicted_panel = [point for point in boundary_points if point.m == m]
            predicted = {
                (point.h, point.log_ratio): point.winner
                for point in predicted_panel
            }
            measured_coordinates = {
                (point.h, point.log_ratio) for point in panel
            }
            if set(predicted) != measured_coordinates:
                raise ValueError(
                    f"boundary predictions do not match measured coordinates for m={m}"
                )
            for y_index, log_ratio in enumerate(log_values):
                for x_index, h in enumerate(h_values):
                    winner = predicted.get((h, log_ratio))
                    if winner is None:
                        continue
                    if x_index + 1 < len(h_values):
                        right_winner = predicted.get(
                            (h_values[x_index + 1], log_ratio)
                        )
                        if right_winner is not None and right_winner != winner:
                            interface_class = boundary_class(winner, right_winner)
                            x = map_x(x_index + 0.5)
                            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                                "x1": f"{x:.2f}", "x2": f"{x:.2f}",
                                "y1": f"{map_y(y_index - 0.5):.2f}",
                                "y2": f"{map_y(y_index + 0.5):.2f}",
                                "class": f"predicted-boundary {interface_class}",
                            })
                    if y_index + 1 < len(log_values):
                        upper_winner = predicted.get(
                            (h, log_values[y_index + 1])
                        )
                        if upper_winner is not None and upper_winner != winner:
                            interface_class = boundary_class(winner, upper_winner)
                            y = map_y(y_index + 0.5)
                            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                                "x1": f"{map_x(x_index - 0.5):.2f}",
                                "x2": f"{map_x(x_index + 0.5):.2f}",
                                "y1": f"{y:.2f}", "y2": f"{y:.2f}",
                                "class": f"predicted-boundary {interface_class}",
                            })
        # Redraw the axes after the cells so the plot boundary remains crisp.
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "fill": "none", "class": "axis",
        })
        add_text(
            root, (left + right) / 2, bottom + 36,
            "log2(h - 1)",
            text_anchor="middle", font_size=13,
        )
        add_text(
            root, ox + 14, (top + bottom) / 2, "log2(m / Delta_min)",
            text_anchor="middle", font_size=13,
            transform=f"rotate(-90 {ox + 14} {(top + bottom) / 2})",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--mode", choices=("blocks", "points"), default="blocks")
    parser.add_argument(
        "--title", default="Measured winners (block cells; no boundary interpolation)",
    )
    parser.add_argument(
        "--boundary-input", type=Path,
        help="optional winner-point CSV whose adjacent class changes are overlaid",
    )
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("winner-panel output must use the .svg extension")
    if args.columns <= 0:
        raise ValueError("columns must be positive")
    points = load_points(args.input)
    boundary_points = load_points(args.boundary_input) if args.boundary_input else None
    render(
        points, args.output, args.columns, args.mode, args.title, boundary_points,
    )
    outcomes = Counter(point.winner for point in points)
    print(
        f"panels={len({point.m for point in points})} points={len(points)} "
        f"uncertain={outcomes['uncertain']} columns={args.columns} "
        f"mode={args.mode} output={args.output}"
    )


if __name__ == "__main__":
    main()
