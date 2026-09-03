#!/usr/bin/env python3
"""Plot the validated geometry of phase-diagram samples as fixed-m SVG panels."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


@dataclass(frozen=True)
class GeometryPoint:
    sample_id: str
    m: int
    h: int
    ratio: float | None
    log2_ratio: float | None


def svg_element(tag: str, **attributes: object) -> ET.Element:
    return ET.Element(
        f"{{{SVG_NS}}}{tag}",
        {name.replace("_", "-"): str(value) for name, value in attributes.items()},
    )


def add_text(
    parent: ET.Element, x: float, y: float, value: str, **attributes: object
) -> None:
    element = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}text",
        {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            **{
                name.replace("_", "-"): str(attribute)
                for name, attribute in attributes.items()
            },
        },
    )
    element.text = value


def parse_positive_integer(row: dict[str, str], field: str) -> int:
    try:
        value = int(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid {field}: {row.get(field)!r}") from error
    if value <= 0:
        raise ValueError(f"{field} must be positive, got {value}")
    return value


def load_points(path: Path) -> list[GeometryPoint]:
    required = {"sample_id", "m", "h", "Delta_min", "log2_m_over_delta"}
    samples: dict[str, GeometryPoint] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing phase-geometry fields: {sorted(missing)}")
        for line_number, row in enumerate(reader, 2):
            sample_id = row["sample_id"].strip()
            if not sample_id:
                raise ValueError(f"line {line_number}: empty sample_id")
            m = parse_positive_integer(row, "m")
            h = parse_positive_integer(row, "h")
            delta_text = row["Delta_min"].strip()
            log_text = row["log2_m_over_delta"].strip()
            if delta_text == "NA":
                if h != 1 or log_text:
                    raise ValueError(
                        f"line {line_number}: no-feedback row must have h=1 "
                        "and an empty log2_m_over_delta"
                    )
                point = GeometryPoint(sample_id, m, h, None, None)
            else:
                try:
                    delta = int(delta_text)
                    emitted_log = float(log_text)
                except ValueError as error:
                    raise ValueError(
                        f"line {line_number}: invalid phase coordinate"
                    ) from error
                if not 1 <= delta <= m:
                    raise ValueError(
                        f"line {line_number}: Delta_min must lie in [1,m]"
                    )
                expected_log = math.log2(m / delta)
                if not math.isclose(
                    emitted_log, expected_log, rel_tol=1e-12, abs_tol=1e-12
                ):
                    raise ValueError(
                        f"line {line_number}: log2_m_over_delta does not match "
                        "m and Delta_min"
                    )
                point = GeometryPoint(
                    sample_id, m, h, m / delta, expected_log
                )
            previous = samples.get(sample_id)
            if previous is not None and previous != point:
                raise ValueError(
                    f"line {line_number}: sample {sample_id!r} changed geometry"
                )
            samples[sample_id] = point
    if not samples:
        raise ValueError("phase input contains no samples")
    return sorted(samples.values(), key=lambda point: (point.m, point.h, point.sample_id))


def tick_label(exponent: int) -> str:
    return str(1 << exponent) if exponent <= 12 else f"2^{exponent}"


def render_svg(points: list[GeometryPoint], output: Path) -> tuple[int, int]:
    degrees = sorted({point.m for point in points})
    columns = min(3, len(degrees))
    rows = math.ceil(len(degrees) / columns)
    panel_width, panel_height = 360, 285
    width, height = columns * panel_width, rows * panel_height + 42
    root = svg_element(
        "svg", width=width, height=height, viewBox=f"0 0 {width} {height}"
    )
    title = ET.SubElement(root, f"{{{SVG_NS}}}title")
    title.text = "Phase geometry by fixed modulus degree"
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}"
        ".axis{stroke:#222;stroke-width:1}"
        ".grid{stroke:#ddd;stroke-width:1}"
        ".point{fill:#356aa0;fill-opacity:.72;stroke:#17466f;stroke-width:.7}"
    )
    add_text(
        root, width / 2, 24, "Phase geometry (fixed m panels)",
        text_anchor="middle", font_size=16, font_weight="bold"
    )

    finite_count = 0
    no_feedback_count = 0
    for panel_index, m in enumerate(degrees):
        column = panel_index % columns
        row = panel_index // columns
        ox, oy = column * panel_width, row * panel_height + 38
        left, right, top, bottom = ox + 62, ox + 342, oy + 32, oy + 238
        panel_points = [point for point in points if point.m == m]
        finite = [point for point in panel_points if point.ratio is not None]
        no_feedback = len(panel_points) - len(finite)
        finite_count += len(finite)
        no_feedback_count += no_feedback

        h_values = [point.h for point in panel_points]
        x_min, x_max = min(h_values), max(h_values)
        if x_min == x_max:
            x_min = max(0, x_min - 1)
            x_max += 1
        x_padding = max(0.5, (x_max - x_min) * 0.05)
        x_min -= x_padding
        x_max += x_padding

        logs = [point.log2_ratio for point in finite if point.log2_ratio is not None]
        y_min = math.floor(min(logs)) if logs else 0
        y_max = math.ceil(max(logs)) if logs else 1
        if y_min == y_max:
            y_max += 1

        def map_x(value: float) -> float:
            return left + (value - x_min) / (x_max - x_min) * (right - left)

        def map_y(log_value: float) -> float:
            return bottom - (log_value - y_min) / (y_max - y_min) * (bottom - top)

        add_text(root, (left + right) / 2, oy + 18, f"m = {m}",
                 text_anchor="middle", font_size=14, font_weight="bold")
        for exponent in range(y_min, y_max + 1):
            y = map_y(exponent)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y), "y2": str(y),
                "class": "grid",
            })
            add_text(root, left - 8, y + 4, tick_label(exponent),
                     text_anchor="end", font_size=10)
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(right), "y1": str(bottom),
            "y2": str(bottom), "class": "axis",
        })
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(left), "y1": str(top),
            "y2": str(bottom), "class": "axis",
        })

        unique_h = sorted(set(h_values))
        if len(unique_h) <= 7:
            x_ticks = unique_h
        else:
            x_ticks = sorted({round(x_min + i * (x_max - x_min) / 4) for i in range(5)})
        for value in x_ticks:
            x = map_x(value)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(x), "x2": str(x), "y1": str(bottom),
                "y2": str(bottom + 5), "class": "axis",
            })
            add_text(root, x, bottom + 18, str(value), text_anchor="middle", font_size=10)

        for point in finite:
            ET.SubElement(root, f"{{{SVG_NS}}}circle", {
                "cx": f"{map_x(point.h):.2f}",
                "cy": f"{map_y(point.log2_ratio or 0):.2f}",
                "r": "3.6", "class": "point",
            })
        add_text(root, (left + right) / 2, bottom + 39, "modulus Hamming weight h",
                 text_anchor="middle", font_size=11)
        add_text(root, ox + 13, (top + bottom) / 2,
                 "m / Delta_min (log2 scale)", text_anchor="middle",
                 font_size=11, transform=f"rotate(-90 {ox + 13} {(top + bottom) / 2})")
        if no_feedback:
            add_text(root, right, top + 12,
                     f"no feedback: {no_feedback} (not on log axis)",
                     text_anchor="end", font_size=9)

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return finite_count, no_feedback_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("phase-geometry output must use the .svg extension")
    points = load_points(args.input)
    finite, no_feedback = render_svg(points, args.output)
    print(
        f"panels={len({point.m for point in points})} "
        f"points={finite} no_feedback={no_feedback} output={args.output}"
    )


if __name__ == "__main__":
    main()
