#!/usr/bin/env python3
"""Plot scheduled work versus runtime and fixed-weight random geometry."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
RANDOM_PROVENANCE = "synthetic-fixed-weight-uniform-constant-free:v1"


@dataclass(frozen=True)
class TimingPoint:
    m: int
    h: int
    delta_min: int
    work: int
    runtime_ns: float


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


def ranks(values: list[float]) -> list[float]:
    result = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=values.__getitem__)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + end + 1) / 2
        for index in ordered[start:end]:
            result[index] = rank
        start = end
    return result


def pearson(left: list[float], right: list[float]) -> float:
    left_mean, right_mean = statistics.fmean(left), statistics.fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_norm = sum((x - left_mean) ** 2 for x in left)
    right_norm = sum((y - right_mean) ** 2 for y in right)
    if left_norm == 0 or right_norm == 0:
        raise ValueError("correlation requires variation on both axes")
    return numerator / math.sqrt(left_norm * right_norm)


def load_timing(
    paths: list[Path], min_trials: int, min_batch_repeats: int,
    min_warmup_runs: int, paper_grade: bool,
) -> list[TimingPoint]:
    required = {
        "sample_id", "m", "h", "taps", "Delta_min", "W_fb", "GS_ns",
        "measurement_trials", "measurement_trial", "timing_scope",
        "GS_source_cost_model", "batch_repeats", "warmup_runs",
        "input_distribution", "metadata_status",
    }
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            missing = required.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path}: missing fields: {sorted(missing)}")
            for line_number, row in enumerate(reader, 2):
                if row["timing_scope"] != "reduction-steady-state:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible timing scope")
                if row["GS_source_cost_model"] != "scalar-source-v1":
                    raise ValueError(f"{path}:{line_number}: incompatible cost model")
                if row["input_distribution"] != "uniform-full-range:v1":
                    raise ValueError(f"{path}:{line_number}: incompatible input distribution")
                if paper_grade and row["metadata_status"] != "paper-grade":
                    raise ValueError(f"{path}:{line_number}: non-paper-grade timing row")
                key = (row["sample_id"], int(row["measurement_trial"]))
                if key in seen:
                    raise ValueError(f"{path}:{line_number}: duplicate sample/trial {key}")
                seen.add(key)
                grouped[row["sample_id"]].append(row)
    if not grouped:
        raise ValueError("timing input is empty")

    points: list[TimingPoint] = []
    coordinates: set[tuple[int, int, int]] = set()
    invariants = (
        "m", "h", "taps", "Delta_min", "W_fb", "measurement_trials",
        "batch_repeats", "warmup_runs", "input_distribution", "metadata_status",
    )
    for sample_id, rows in grouped.items():
        first = rows[0]
        if any(row[field] != first[field] for row in rows[1:] for field in invariants):
            raise ValueError(f"{sample_id}: timing invariants changed")
        declared = int(first["measurement_trials"])
        trials = sorted(int(row["measurement_trial"]) for row in rows)
        if trials != list(range(declared)) or declared < min_trials:
            raise ValueError(f"{sample_id}: incomplete measurement trials")
        if int(first["batch_repeats"]) < min_batch_repeats:
            raise ValueError(f"{sample_id}: too few batch repeats")
        if int(first["warmup_runs"]) < min_warmup_runs:
            raise ValueError(f"{sample_id}: too few warm-up runs")
        m, h = int(first["m"]), int(first["h"])
        delta_min, work = int(first["Delta_min"]), int(first["W_fb"])
        coordinate = (m, h, delta_min)
        if coordinate in coordinates:
            raise ValueError(f"duplicate phase coordinate {coordinate}")
        coordinates.add(coordinate)
        runtimes = [float(row["GS_ns"]) for row in rows]
        if work <= 0 or any(not math.isfinite(value) or value <= 0 for value in runtimes):
            raise ValueError(f"{sample_id}: work and runtime must be positive")
        points.append(TimingPoint(m, h, delta_min, work, statistics.median(runtimes)))
    return sorted(points, key=lambda point: (point.m, point.work, point.h))


def scheduled_geometry(m: int, taps: list[int]) -> tuple[int, int]:
    distances = [m - tap for tap in taps]
    delta_min = min(distances)
    stages = math.ceil(math.log2(m / delta_min))
    work = 0
    for distance in distances:
        scaled = distance
        while scaled < m:
            work += m - scaled
            scaled *= 2
    return stages, work


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def load_random_manifests(paths: list[Path]) -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    identities: set[str] = set()
    supports: set[tuple[int, tuple[int, ...]]] = set()
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"{path}:{line_number}: invalid JSON") from error
                required = {
                    "sample_id", "provenance", "m", "taps", "support_sampler",
                    "support_seed", "cell_population", "requested_supports",
                    "realized_supports", "constant_policy",
                }
                missing = required.difference(row)
                if missing:
                    raise ValueError(f"{path}:{line_number}: missing {sorted(missing)}")
                sample_id = str(row["sample_id"])
                if sample_id in identities:
                    raise ValueError(f"duplicate random sample_id {sample_id}")
                identities.add(sample_id)
                m = int(row["m"])
                taps = [int(tap) for tap in row["taps"]]
                if (row["provenance"] != RANDOM_PROVENANCE
                        or row["constant_policy"] != "absent"):
                    raise ValueError(f"{sample_id}: incompatible random-support contract")
                if taps != sorted(set(taps)) or not taps or taps[0] <= 0 or taps[-1] >= m:
                    raise ValueError(f"{sample_id}: noncanonical constant-free taps")
                support_key = (m, tuple(taps))
                if support_key in supports:
                    raise ValueError(f"duplicate random support {support_key}")
                supports.add(support_key)
                stages, work = scheduled_geometry(m, taps)
                samples.append({
                    "sample_id": sample_id, "m": m, "s": len(taps),
                    "taps": ";".join(str(tap) for tap in taps),
                    "feedback_stages": stages, "W_fb": work,
                    "support_sampler": str(row["support_sampler"]),
                    "support_seed": str(row["support_seed"]),
                    "cell_population": str(row["cell_population"]),
                    "requested_supports": int(row["requested_supports"]),
                    "realized_supports": int(row["realized_supports"]),
                    "provenance": str(row["provenance"]),
                })
    if not samples:
        raise ValueError("random-support manifests are empty")
    return samples


def summarize_random(samples: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    for sample in samples:
        grouped[(int(sample["m"]), int(sample["s"]))].append(sample)
    rows: list[dict[str, object]] = []
    for (m, s), cell in sorted(grouped.items()):
        invariant_fields = (
            "support_sampler", "support_seed", "cell_population",
            "requested_supports", "realized_supports", "provenance",
        )
        first = cell[0]
        if any(item[field] != first[field] for item in cell[1:] for field in invariant_fields):
            raise ValueError(f"random cell {(m, s)} changes manifest metadata")
        if len(cell) != int(first["realized_supports"]):
            raise ValueError(f"random cell {(m, s)} is incomplete")
        depths = [float(item["feedback_stages"]) for item in cell]
        works = [float(item["W_fb"]) for item in cell]
        row: dict[str, object] = {
            "m": m, "s": s, "h": s + 1, "samples": len(cell),
            **{field: first[field] for field in invariant_fields},
        }
        for name, values in (("depth", depths), ("work", works)):
            row[f"{name}_median"] = statistics.median(values)
            row[f"{name}_p90"] = nearest_rank(values, 0.90)
            row[f"{name}_p99"] = nearest_rank(values, 0.99)
        row["normalized_work_median"] = float(row["work_median"]) / m
        row["normalized_work_p90"] = float(row["work_p90"]) / m
        row["normalized_work_p99"] = float(row["work_p99"]) / m
        rows.append(row)
    degrees = sorted({int(row["m"]) for row in rows})
    if len(degrees) != 6:
        raise ValueError("random-support figures require exactly six degrees")
    weight_sets = {m: {int(row["s"]) for row in rows if int(row["m"]) == m} for m in degrees}
    if len({tuple(sorted(weights)) for weights in weight_sets.values()}) != 1:
        raise ValueError("random-support degrees do not share one weight grid")
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def figure_root(title: str) -> ET.Element:
    root = element("svg", width=1095, height=630, viewBox="0 0 1095 630")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": "1095", "height": "630", "fill": "#fff",
    })
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = (
        "text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1}"
        ".grid{stroke:#ddd;stroke-width:1}.series{fill:none;stroke-width:2}"
        ".quantile{fill:none;stroke-width:1.5}.point{stroke:#fff;stroke-width:.5}"
    )
    add_text(root, 547.5, 24, title, text_anchor="middle", font_size=16, font_weight="bold")
    return root


def panel_box(root: ET.Element, index: int, m: int) -> tuple[float, float, float, float, float]:
    panel_width, panel_height = 365, 292
    column, row = index % 3, index // 3
    ox, oy = column * panel_width, 45 + row * panel_height
    left, right, top, bottom = ox + 61, ox + 347, oy + 34, oy + 238
    add_text(root, (left + right) / 2, oy + 19, f"m = {m}",
             text_anchor="middle", font_size=13, font_weight="bold")
    return ox, left, right, top, bottom


def render_work_runtime(path: Path, points: list[TimingPoint]) -> list[dict[str, object]]:
    degrees = sorted({point.m for point in points})
    if len(degrees) != 6:
        raise ValueError("work/runtime figure requires exactly six degrees")
    root = figure_root("Scheduled active-tap work versus FFR runtime")
    summaries: list[dict[str, object]] = []
    for index, m in enumerate(degrees):
        ox, left, right, top, bottom = panel_box(root, index, m)
        panel = [point for point in points if point.m == m]
        xs = [math.log2(point.work) for point in panel]
        ys = [math.log2(point.runtime_ns) for point in panel]
        x_min, x_max = math.floor(min(xs)), math.ceil(max(xs))
        y_min, y_max = math.floor(min(ys)), math.ceil(max(ys))
        rho = pearson(ranks(xs), ranks(ys))
        summaries.append({
            "m": m, "supports": len(panel), "predictor": "W_fb",
            "predictor_kind": "formal-scheduled-coefficient-work",
            "response": "GS_ns", "response_unit": "nanoseconds-per-reduction",
            "runtime_aggregation": "median-over-complete-trials",
            "correlation_scope": "within-fixed-m-controlled-supports",
            "timing_scope": "reduction-steady-state:v1",
            "cost_model": "scalar-source-v1", "spearman_rho": f"{rho:.9g}",
        })

        def map_x(value: float) -> float:
            return left + (value - x_min) / max(1, x_max - x_min) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / max(1, y_max - y_min) * (bottom - top)

        for value in range(y_min, y_max + 1):
            y = map_y(value)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {"x1": str(left), "x2": str(right),
                "y1": str(y), "y2": str(y), "class": "grid"})
            add_text(root, left - 7, y + 3, str(value), text_anchor="end", font_size=8)
        for x, y in zip(xs, ys):
            ET.SubElement(root, f"{{{SVG_NS}}}circle", {
                "cx": f"{map_x(x):.2f}", "cy": f"{map_y(y):.2f}", "r": "2.7",
                "fill": "#246b91",
                "class": "point",
            })
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {"x": str(left), "y": str(top),
            "width": str(right-left), "height": str(bottom-top), "fill": "none", "class": "axis"})
        for value in range(x_min, x_max + 1, 3):
            add_text(root, map_x(value), bottom + 17, str(value), text_anchor="middle", font_size=8)
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "x": str(right - 91), "y": str(top + 3), "width": "88", "height": "15",
            "fill": "#fff", "fill-opacity": ".88",
        })
        add_text(root, right - 5, top + 14, f"Spearman ρ = {rho:.3f}",
                 text_anchor="end", font_size=8)
        add_text(root, (left + right) / 2, bottom + 36, "log2(W_fb)", text_anchor="middle", font_size=10)
        add_text(root, ox + 13, (top + bottom) / 2, "log2(FFR ns)", text_anchor="middle",
                 font_size=9, transform=f"rotate(-90 {ox+13} {(top+bottom)/2})")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return summaries


def render_random_metric(path: Path, rows: list[dict[str, object]], metric: str) -> None:
    is_depth = metric == "depth"
    title = "Random-support feedback depth versus s" if is_depth else "Random-support scheduled work versus s"
    root = figure_root(title)
    degrees = sorted({int(row["m"]) for row in rows})
    colors = (("median", "#237a44"), ("p90", "#68419b"), ("p99", "#d9822b"))
    legend_x = 25.0
    for quantile, color in colors:
        ET.SubElement(root, f"{{{SVG_NS}}}line", {"x1": str(legend_x),
            "x2": str(legend_x + 18), "y1": "40", "y2": "40", "stroke": color,
            "stroke-width": "2"})
        add_text(root, legend_x + 23, 44, quantile, font_size=8)
        legend_x += 72
    for index, m in enumerate(degrees):
        ox, left, right, top, bottom = panel_box(root, index, m)
        panel = sorted((row for row in rows if int(row["m"]) == m), key=lambda row: int(row["s"]))
        xs = [math.log2(int(row["s"])) for row in panel]
        if is_depth:
            series = {q: [float(row[f"depth_{q}"]) for row in panel] for q, _ in colors}
            y_label = "feedback stages"
        else:
            series = {q: [math.log2(float(row[f"normalized_work_{q}"])) for row in panel] for q, _ in colors}
            y_label = "log2(W_fb / m)"
        all_y = [value for values in series.values() for value in values]
        y_min, y_max = math.floor(min(all_y)), math.ceil(max(all_y))

        def map_x(value: float) -> float:
            return left + (value - min(xs)) / max(1, max(xs) - min(xs)) * (right - left)

        def map_y(value: float) -> float:
            return bottom - (value - y_min) / max(1, y_max - y_min) * (bottom - top)

        for value in range(y_min, y_max + 1, max(1, math.ceil((y_max-y_min)/4))):
            y = map_y(value)
            ET.SubElement(root, f"{{{SVG_NS}}}line", {"x1": str(left), "x2": str(right),
                "y1": str(y), "y2": str(y), "class": "grid"})
            add_text(root, left - 7, y + 3, str(value), text_anchor="end", font_size=8)
        for quantile, color in colors:
            ET.SubElement(root, f"{{{SVG_NS}}}polyline", {
                "points": " ".join(f"{map_x(x):.2f},{map_y(y):.2f}" for x, y in zip(xs, series[quantile])),
                "stroke": color, "class": "quantile",
            })
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {"x": str(left), "y": str(top),
            "width": str(right-left), "height": str(bottom-top), "fill": "none", "class": "axis"})
        for value in range(math.ceil(min(xs)), math.floor(max(xs)) + 1):
            add_text(root, map_x(value), bottom + 17, str(value), text_anchor="middle", font_size=8)
        add_text(root, (left + right) / 2, bottom + 36, "log2(s)", text_anchor="middle", font_size=10)
        add_text(root, ox + 13, (top + bottom) / 2, y_label, text_anchor="middle", font_size=9,
                 transform=f"rotate(-90 {ox+13} {(top+bottom)/2})")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timing-input", type=Path, nargs="+", required=True)
    parser.add_argument("--random-manifest", type=Path, nargs="+", required=True)
    parser.add_argument("--work-runtime-figure", type=Path, required=True)
    parser.add_argument("--work-runtime-summary", type=Path, required=True)
    parser.add_argument("--random-summary", type=Path, required=True)
    parser.add_argument("--random-depth-figure", type=Path, required=True)
    parser.add_argument("--random-work-figure", type=Path, required=True)
    parser.add_argument("--min-trials", type=int, default=31)
    parser.add_argument("--min-batch-repeats", type=int, default=12)
    parser.add_argument("--min-warmup-runs", type=int, default=1)
    parser.add_argument("--paper-grade", action="store_true")
    args = parser.parse_args()
    figures = (args.work_runtime_figure, args.random_depth_figure, args.random_work_figure)
    if any(path.suffix.lower() != ".svg" for path in figures):
        raise ValueError("figure outputs must use the .svg extension")
    if (args.min_trials <= 0 or args.min_batch_repeats <= 0
            or args.min_warmup_runs < 0):
        raise ValueError("timing minima must be positive and warm-up nonnegative")
    timing = load_timing(
        args.timing_input, args.min_trials, args.min_batch_repeats,
        args.min_warmup_runs, args.paper_grade,
    )
    random_rows = summarize_random(load_random_manifests(args.random_manifest))
    correlations = render_work_runtime(args.work_runtime_figure, timing)
    write_csv(args.work_runtime_summary, correlations)
    write_csv(args.random_summary, random_rows)
    render_random_metric(args.random_depth_figure, random_rows, "depth")
    render_random_metric(args.random_work_figure, random_rows, "work")
    print(f"timing_supports={len(timing)} random_supports={sum(int(row['samples']) for row in random_rows)}")


if __name__ == "__main__":
    main()
