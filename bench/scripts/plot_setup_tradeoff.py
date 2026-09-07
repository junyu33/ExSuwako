#!/usr/bin/env python3
"""Derive setup amortization and render setup/work/depth figures."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
METHODS = (
    "GS", "Serial", "BarrettGF2X", "LopezDahabLoop", "Dense", "Naive",
    "Generated",
)
COLORS = {
    "Serial": "#d9822b",
    "BarrettGF2X": "#237a44",
    "LopezDahabLoop": "#68419b",
    "Dense": "#b23a48",
    "Naive": "#777777",
    "Generated": "#167d9a",
}
LABELS = {
    "BarrettGF2X": "Barrett",
    "LopezDahabLoop": "López–Dahab",
}
METADATA_FIELDS = (
    "provenance", "git_commit", "compiler_version", "compiler_flags",
    "gf2x_library", "platform", "machine", "hostname", "cpu_affinity",
    "frequency_policy", "word_bits", "input_distribution", "timing_scope",
    "setup_scope", "implementation", "multiplication_backend", "seed",
    "plan_storage_model",
)


@dataclass(frozen=True)
class Support:
    sample_id: str
    m: int
    h: int
    taps: str
    delta_min: int
    stages: int
    work: int
    metadata: dict[str, str]
    setup_ns: dict[str, float]
    reduce_ns: dict[str, float]


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


def numeric(row: dict[str, str], field: str, line: str, nonnegative: bool = False) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise ValueError(f"{line}: invalid {field}: {row.get(field)!r}") from error
    if not math.isfinite(value) or (value < 0 if nonnegative else value <= 0):
        qualifier = "nonnegative" if nonnegative else "positive"
        raise ValueError(f"{line}: {field} must be finite and {qualifier}")
    return value


def load_supports(paths: list[Path]) -> list[Support]:
    required = {
        "sample_id", "m", "h", "taps", "Delta_min", "feedback_stages",
        "W_fb", "timing_scope", "setup_scope", "measurement_trials",
        "measurement_trial", "GS_setup_ns", "GS_ns",
        "BarrettGF2X_setup_ns", "BarrettGF2X_ns",
    }.union(METADATA_FIELDS)
    grouped: dict[str, list[tuple[dict[str, str], str]]] = {}
    seen_trials: set[tuple[str, int]] = set()
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            missing = required.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path}: missing fields: {sorted(missing)}")
            for line_number, row in enumerate(reader, 2):
                where = f"{path}:{line_number}"
                if row["timing_scope"] != "reduction-steady-state:v1":
                    raise ValueError(f"{where}: incompatible timing_scope")
                if row["setup_scope"] != "modulus-plan:v1":
                    raise ValueError(f"{where}: incompatible setup_scope")
                try:
                    trial = int(row["measurement_trial"])
                except ValueError as error:
                    raise ValueError(f"{where}: invalid measurement_trial") from error
                key = (row["sample_id"], trial)
                if key in seen_trials:
                    raise ValueError(f"{where}: duplicate sample/trial {key}")
                seen_trials.add(key)
                grouped.setdefault(row["sample_id"], []).append((row, where))
    if not grouped:
        raise ValueError("setup-tradeoff input is empty")

    supports: list[Support] = []
    coordinates: set[tuple[int, int, int]] = set()
    invariant_fields = (
        "m", "h", "taps", "Delta_min", "feedback_stages", "W_fb",
        "measurement_trials", "timing_scope", "setup_scope",
    ) + METADATA_FIELDS
    for sample_id, records in grouped.items():
        first, first_where = records[0]
        for row, where in records[1:]:
            changed = [field for field in invariant_fields if row[field] != first[field]]
            if changed:
                raise ValueError(f"{where}: within-support fields changed: {changed}")
        try:
            m = int(first["m"])
            h = int(first["h"])
            delta_min = int(first["Delta_min"])
            stages = int(first["feedback_stages"])
            work = int(first["W_fb"])
            trial_count = int(first["measurement_trials"])
        except ValueError as error:
            raise ValueError(f"{first_where}: invalid support geometry") from error
        trials = sorted(int(row["measurement_trial"]) for row, _ in records)
        if trials != list(range(trial_count)):
            raise ValueError(f"{sample_id}: incomplete measurement trials")
        if stages != math.ceil(math.log2(m / delta_min)):
            raise ValueError(f"{sample_id}: feedback depth disagrees with geometry")
        coordinate = (m, h, delta_min)
        if coordinate in coordinates:
            raise ValueError(f"duplicate phase coordinate {coordinate}")
        coordinates.add(coordinate)

        setup: dict[str, float] = {}
        reduction: dict[str, float] = {}
        for method in METHODS:
            setup_field, reduction_field = f"{method}_setup_ns", f"{method}_ns"
            if setup_field not in first or reduction_field not in first:
                continue
            reduction_values = [
                numeric(row, reduction_field, where, nonnegative=True)
                for row, where in records
            ]
            if not any(value > 0 for value in reduction_values):
                continue
            if not all(value > 0 for value in reduction_values):
                raise ValueError(f"{sample_id}: partially enabled {method}")
            setup_values = [
                numeric(row, setup_field, where, nonnegative=True)
                for row, where in records
            ]
            setup[method] = statistics.median(setup_values)
            reduction[method] = statistics.median(reduction_values)
        if "GS" not in reduction or "BarrettGF2X" not in reduction:
            raise ValueError(f"{sample_id}: GS and Barrett must both be enabled")
        supports.append(Support(
            sample_id, m, h, first["taps"], delta_min, stages, work,
            {field: first[field] for field in METADATA_FIELDS}, setup, reduction,
        ))
    return sorted(supports, key=lambda item: (item.m, item.delta_min, item.h))


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def write_amortization(path: Path, supports: list[Support], k_values: list[int]) -> None:
    fields = [
        "sample_id", "m", "h", "taps", "Delta_min", "feedback_stages",
        "W_fb", *METADATA_FIELDS, "method", "K", "setup_median_ns", "reduce_median_ns",
        "total_median_components_ns", "amortized_median_components_ns",
        "ratio_to_GS",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for support in supports:
            for k in k_values:
                gs_average = support.reduce_ns["GS"] + support.setup_ns["GS"] / k
                for method in METHODS:
                    if method not in support.reduce_ns:
                        continue
                    total = support.setup_ns[method] + k * support.reduce_ns[method]
                    average = total / k
                    writer.writerow({
                        "sample_id": support.sample_id,
                        "m": support.m,
                        "h": support.h,
                        "taps": support.taps,
                        "Delta_min": support.delta_min,
                        "feedback_stages": support.stages,
                        "W_fb": support.work,
                        **support.metadata,
                        "method": method,
                        "K": k,
                        "setup_median_ns": f"{support.setup_ns[method]:.9g}",
                        "reduce_median_ns": f"{support.reduce_ns[method]:.9g}",
                        "total_median_components_ns": f"{total:.9g}",
                        "amortized_median_components_ns": f"{average:.9g}",
                        "ratio_to_GS": f"{average / gs_average:.9g}",
                    })


def add_common_style(root: ET.Element) -> None:
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1}"
        ".grid{stroke:#ddd;stroke-width:1}.zero{stroke:#111;stroke-width:1.8}"
        ".series{fill:none;stroke-width:2}.band{stroke:none;opacity:.14}"
    )


def panel_layout(root: ET.Element, index: int, m: int) -> tuple[float, float, float, float, float]:
    panel_width, panel_height = 365, 282
    column, row = index % 3, index // 3
    ox, oy = column * panel_width, 66 + row * panel_height
    left, right, top, bottom = ox + 61, ox + 347, oy + 34, oy + 230
    add_text(root, (left + right) / 2, oy + 18, f"m = {m}",
             text_anchor="middle", font_size=13, font_weight="bold")
    return ox, left, right, top, bottom


def render_amortization(
    path: Path, supports: list[Support], k_values: list[int], competitors: list[str]
) -> None:
    degrees = sorted({support.m for support in supports})
    if len(degrees) != 6:
        raise ValueError("setup-amortization figure requires exactly six degrees")
    aggregates: dict[tuple[int, str, int], tuple[float, float, float]] = {}
    for m in degrees:
        panel = [support for support in supports if support.m == m]
        for method in competitors:
            matched = [support for support in panel if method in support.reduce_ns]
            for k in k_values:
                ratios = [
                    math.log2(
                        (support.reduce_ns[method] + support.setup_ns[method] / k)
                        / (support.reduce_ns["GS"] + support.setup_ns["GS"] / k)
                    )
                    for support in matched
                ]
                if ratios:
                    aggregates[(m, method, k)] = (
                        nearest_rank(ratios, 0.10), statistics.median(ratios),
                        nearest_rank(ratios, 0.90),
                    )
    values = [value for triple in aggregates.values() for value in triple]
    y_min = min(math.floor(min(values)), -1)
    y_max = max(math.ceil(max(values)), 1)
    x_values = [math.log2(k) for k in k_values]
    x_min, x_max = min(x_values), max(x_values)

    width, height = 1095, 630
    root = element("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#fff",
    })
    add_common_style(root)
    add_text(root, width / 2, 23, "Setup amortization over measured cells",
             text_anchor="middle", font_size=16, font_weight="bold")
    legend_x = 28.0
    for method in competitors:
        color = COLORS[method]
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(legend_x), "x2": str(legend_x + 18), "y1": "47", "y2": "47",
            "stroke": color, "stroke-width": "3",
        })
        label = LABELS.get(method, method)
        add_text(root, legend_x + 23, 51, f"{label}/GS median (p10–p90)", font_size=8)
        legend_x += 105 + 5.0 * len(label)

    for index, m in enumerate(degrees):
        ox, left, right, top, bottom = panel_layout(root, index, m)

        def map_x(value: float) -> float:
            return left + (value - x_min) / (x_max - x_min) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

        for value in range(y_min, y_max + 1, 2):
            y = map_y(value)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y), "y2": str(y),
                "class": "grid",
            })
            add_text(root, left - 7, y + 3, str(value), text_anchor="end", font_size=8)
        ET.SubElement(root, f"{{{SVG_NS}}}line", {
            "x1": str(left), "x2": str(right), "y1": str(map_y(0)),
            "y2": str(map_y(0)), "class": "zero",
        })
        for method in competitors:
            rows = [
                (math.log2(k), aggregates[(m, method, k)])
                for k in k_values if (m, method, k) in aggregates
            ]
            if not rows:
                continue
            color = COLORS[method]
            upper = [(map_x(x), map_y(stats[2])) for x, stats in rows]
            lower = [(map_x(x), map_y(stats[0])) for x, stats in reversed(rows)]
            ET.SubElement(root, f"{{{SVG_NS}}}polygon", {
                "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in upper + lower),
                "fill": color, "class": "band",
            })
            medians = [(map_x(x), map_y(stats[1])) for x, stats in rows]
            ET.SubElement(root, f"{{{SVG_NS}}}polyline", {
                "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in medians),
                "stroke": color, "class": "series",
            })
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "fill": "none", "class": "axis",
        })
        for value in range(math.ceil(x_min), math.floor(x_max) + 1, 4):
            add_text(root, map_x(value), bottom + 17, str(value), text_anchor="middle", font_size=8)
        add_text(root, (left + right) / 2, bottom + 36, "log2(K)",
                 text_anchor="middle", font_size=10)
        add_text(root, ox + 13, (top + bottom) / 2, "median log2(T_method / T_GS)",
                 text_anchor="middle", font_size=8,
                 transform=f"rotate(-90 {ox + 13} {(top + bottom) / 2})")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def color_for(value: float, low: float, high: float) -> str:
    fraction = 0.5 if high == low else (value - low) / (high - low)
    start, end = (244, 236, 200), (30, 74, 140)
    rgb = tuple(round(a + fraction * (b - a)) for a, b in zip(start, end))
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


def render_tradeoff(path: Path, supports: list[Support]) -> None:
    degrees = sorted({support.m for support in supports})
    if len(degrees) != 6:
        raise ValueError("setup tradeoff figure requires exactly six degrees")
    setup_logs = [math.log2(support.setup_ns["GS"] + 1) for support in supports]
    setup_min, setup_max = min(setup_logs), max(setup_logs)
    width, height = 1095, 630
    root = element("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#fff",
    })
    add_common_style(root)
    add_text(root, width / 2, 23, "GS work–feedback-depth–setup tradeoff",
             text_anchor="middle", font_size=16, font_weight="bold")
    legend_left, legend_right = 408.0, 688.0
    for step in range(80):
        x = legend_left + step * (legend_right - legend_left) / 80
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": f"{x:.2f}", "y": "39", "width": "4", "height": "9",
            "fill": color_for(setup_min + (setup_max - setup_min) * step / 79,
                              setup_min, setup_max),
        })
    add_text(root, legend_left - 7, 47, f"{setup_min:.1f}", text_anchor="end", font_size=8)
    add_text(root, legend_right + 8, 47, f"{setup_max:.1f}", font_size=8)
    add_text(root, width / 2, 61, "color = log2(GS setup ns + 1)",
             text_anchor="middle", font_size=8)

    for index, m in enumerate(degrees):
        ox, left, right, top, bottom = panel_layout(root, index, m)
        panel = [support for support in supports if support.m == m]
        xs = [math.log2(support.work + 1) for support in panel]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = 0, max(support.stages for support in panel)

        def map_x(value: float) -> float:
            return left + (value - x_min) / (x_max - x_min) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / max(1, y_max - y_min) * (bottom - top)

        for value in range(0, y_max + 1, max(1, math.ceil(y_max / 4))):
            y = map_y(value)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {
                "x1": str(left), "x2": str(right), "y1": str(y), "y2": str(y),
                "class": "grid",
            })
            add_text(root, left - 7, y + 3, str(value), text_anchor="end", font_size=8)
        for support in panel:
            setup_log = math.log2(support.setup_ns["GS"] + 1)
            ET.SubElement(root, f"{{{SVG_NS}}}circle", {
                "cx": f"{map_x(math.log2(support.work + 1)):.2f}",
                "cy": f"{map_y(support.stages):.2f}", "r": "2.8",
                "fill": color_for(setup_log, setup_min, setup_max),
                "stroke": "#fff", "stroke-width": ".45",
            })
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": str(left), "y": str(top), "width": str(right - left),
            "height": str(bottom - top), "fill": "none", "class": "axis",
        })
        for value in range(math.ceil(x_min), math.floor(x_max) + 1, 3):
            add_text(root, map_x(value), bottom + 17, str(value), text_anchor="middle", font_size=8)
        add_text(root, (left + right) / 2, bottom + 36, "log2(W_fb + 1)",
                 text_anchor="middle", font_size=10)
        add_text(root, ox + 13, (top + bottom) / 2, "feedback stages",
                 text_anchor="middle", font_size=9,
                 transform=f"rotate(-90 {ox + 13} {(top + bottom) / 2})")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--amortization-data", type=Path, required=True)
    parser.add_argument("--amortization-figure", type=Path, required=True)
    parser.add_argument("--tradeoff-figure", type=Path, required=True)
    parser.add_argument("--k-values", type=int, nargs="+", required=True)
    parser.add_argument("--plot-methods", nargs="+", required=True)
    args = parser.parse_args()
    if any(path.suffix.lower() != ".svg" for path in (
        args.amortization_figure, args.tradeoff_figure
    )):
        raise ValueError("figure outputs must use the .svg extension")
    if (len(args.k_values) < 2 or any(k <= 0 for k in args.k_values)
            or len(set(args.k_values)) != len(args.k_values)):
        raise ValueError("at least two distinct positive K values are required")
    competitors = list(dict.fromkeys(args.plot_methods))
    if any(method == "GS" or method not in METHODS for method in competitors):
        raise ValueError("plot methods must be known non-GS methods")
    k_values = sorted(args.k_values)
    supports = load_supports(args.input)
    absent = [
        method for method in competitors
        if not any(method in support.reduce_ns for support in supports)
    ]
    if absent:
        raise ValueError(f"plot methods have no measurements: {absent}")
    write_amortization(args.amortization_data, supports, k_values)
    render_amortization(args.amortization_figure, supports, k_values, competitors)
    render_tradeoff(args.tradeoff_figure, supports)
    print(
        f"supports={len(supports)} K={k_values} "
        f"amortization={args.amortization_figure} tradeoff={args.tradeoff_figure}"
    )


if __name__ == "__main__":
    main()
