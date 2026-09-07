#!/usr/bin/env python3
"""Plot and validate the exact generalized-Suwako feedback-depth law."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
PALETTE = ("#356aa0", "#3b8f55", "#7651a8", "#e6862a", "#c84b4b", "#4f8c8d")


@dataclass(frozen=True)
class DepthPoint:
    m: int
    delta_min: int
    stages: int


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


def load_points(paths: list[Path]) -> list[DepthPoint]:
    samples: dict[str, DepthPoint] = {}
    coordinates: dict[tuple[int, int], int] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            required = {"sample_id", "m", "Delta_min", "feedback_stages"}
            missing = required.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path} is missing fields: {sorted(missing)}")
            for line_number, row in enumerate(reader, 2):
                try:
                    m = int(row["m"])
                    delta_min = int(row["Delta_min"])
                    stages = int(row["feedback_stages"])
                except ValueError as error:
                    raise ValueError(f"{path}:{line_number}: invalid depth data") from error
                if m <= 0 or not 1 <= delta_min <= m or stages < 0:
                    raise ValueError(f"{path}:{line_number}: invalid depth coordinate")
                expected = math.ceil(math.log2(m / delta_min))
                if stages != expected:
                    raise ValueError(
                        f"{path}:{line_number}: feedback_stages={stages}, expected {expected}"
                    )
                point = DepthPoint(m, delta_min, stages)
                sample_id = row["sample_id"]
                previous = samples.get(sample_id)
                if previous is not None and previous != point:
                    raise ValueError(f"sample {sample_id!r} changes depth geometry")
                samples[sample_id] = point
                coordinate = (m, delta_min)
                prior_stages = coordinates.get(coordinate)
                if prior_stages is not None and prior_stages != stages:
                    raise ValueError(f"coordinate {coordinate} changes stage count")
                coordinates[coordinate] = stages
    if not coordinates:
        raise ValueError("depth input contains no finite-feedback points")
    return [
        DepthPoint(m, delta_min, stages)
        for (m, delta_min), stages in sorted(coordinates.items())
    ]


def render(points: list[DepthPoint], output: Path) -> None:
    degrees = sorted({point.m for point in points})
    if len(degrees) > len(PALETTE):
        raise ValueError(f"at most {len(PALETTE)} modulus degrees can be plotted")
    gap_one = [point for point in points if point.delta_min == 1]
    if {point.m for point in gap_one} != set(degrees):
        raise ValueError("every plotted degree requires a Delta_min=1 point")

    width, height = 1080, 480
    root = element("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height),
        "fill": "#ffffff",
    })
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1.2}"
        ".grid{stroke:#ddd;stroke-width:1}.series{fill:none;stroke-width:2.4}"
        ".point{stroke:#fff;stroke-width:1}.law{fill:none;stroke:#111;"
        "stroke-width:2;stroke-dasharray:7 4}"
    )
    add_text(root, width / 2, 25, "Exact feedback-depth scaling",
             text_anchor="middle", font_size=17, font_weight="bold")

    panels = ((70, 515, "(a) Fixed-m gap sweep"), (615, 1030, "(b) Gap-one scaling"))
    top, bottom = 78, 400
    max_stage = max(point.stages for point in points)
    for left, right, title in panels:
        add_text(root, (left + right) / 2, 55, title,
                 text_anchor="middle", font_size=13, font_weight="bold")
        for stage in range(0, max_stage + 1, 2):
            y = bottom - stage / max_stage * (bottom - top)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y), "y2": str(y),
                "class": "grid",
            })
            add_text(root, left - 9, y + 4, str(stage), text_anchor="end", font_size=9)
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(right), "y1": str(bottom), "y2": str(bottom),
            "class": "axis",
        })
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(left), "y1": str(top), "y2": str(bottom),
            "class": "axis",
        })

    left, right, _ = panels[0]
    max_log_delta = max(math.log2(point.delta_min) for point in points)
    for exponent in range(0, math.floor(max_log_delta) + 1, 2):
        x = left + exponent / max_log_delta * (right - left)
        add_text(root, x, bottom + 19, str(exponent), text_anchor="middle", font_size=9)
    for index, m in enumerate(degrees):
        color = PALETTE[index]
        series = sorted((point for point in points if point.m == m), key=lambda p: p.delta_min)
        coordinates = [
            (
                left + math.log2(point.delta_min) / max_log_delta * (right - left),
                bottom - point.stages / max_stage * (bottom - top),
            )
            for point in series
        ]
        ET.SubElement(root, f"{{{SVG_NS}}}polyline", {
            "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates),
            "class": "series", "stroke": color,
        })
        for x, y in coordinates:
            ET.SubElement(root, f"{{{SVG_NS}}}circle", {
                "cx": f"{x:.2f}", "cy": f"{y:.2f}", "r": "3.2",
                "fill": color, "class": "point",
            })

    left, right, _ = panels[1]
    log_degrees = [math.log2(point.m) for point in gap_one]
    x_min, x_max = min(log_degrees), max(log_degrees)
    for exponent in range(math.ceil(x_min), math.floor(x_max) + 1, 2):
        x = left + (exponent - x_min) / (x_max - x_min) * (right - left)
        add_text(root, x, bottom + 19, str(exponent), text_anchor="middle", font_size=9)
    law_coordinates = []
    for exponent in (x_min, x_max):
        law_coordinates.append((
            left + (exponent - x_min) / (x_max - x_min) * (right - left),
            bottom - exponent / max_stage * (bottom - top),
        ))
    ET.SubElement(root, f"{{{SVG_NS}}}polyline", {
        "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in law_coordinates),
        "class": "law",
    })
    for index, point in enumerate(sorted(gap_one, key=lambda item: item.m)):
        x = left + (math.log2(point.m) - x_min) / (x_max - x_min) * (right - left)
        y = bottom - point.stages / max_stage * (bottom - top)
        ET.SubElement(root, f"{{{SVG_NS}}}circle", {
            "cx": f"{x:.2f}", "cy": f"{y:.2f}", "r": "5",
            "fill": PALETTE[index], "class": "point",
        })

    add_text(root, 292, 447, "log2(Delta_min)", text_anchor="middle", font_size=11)
    add_text(root, 823, 447, "log2(m)", text_anchor="middle", font_size=11)
    for x in (21, 565):
        add_text(root, x, (top + bottom) / 2, "feedback stages D_fb",
                 text_anchor="middle", font_size=11,
                 transform=f"rotate(-90 {x} {(top + bottom) / 2})")

    legend_x = 80.0
    for index, m in enumerate(degrees):
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": f"{legend_x:.2f}", "x2": f"{legend_x + 15:.2f}",
            "y1": "470", "y2": "470", "stroke": PALETTE[index], "stroke-width": "3",
        })
        add_text(root, legend_x + 19, 474, f"m={m}", font_size=8)
        legend_x += 48 + 4.7 * len(str(m))

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("feedback-depth output must use the .svg extension")
    points = load_points(args.input)
    render(points, args.output)
    print(
        f"degrees={len({point.m for point in points})} "
        f"coordinates={len(points)} output={args.output}"
    )


if __name__ == "__main__":
    main()
