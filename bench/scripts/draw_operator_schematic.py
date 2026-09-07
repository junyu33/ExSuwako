#!/usr/bin/env python3
"""Draw the explanatory sparse-Frobenius operator construction."""

from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def node(tag: str, **attributes: object) -> ET.Element:
    return ET.Element(
        f"{{{SVG_NS}}}{tag}",
        {name.replace("_", "-"): str(value) for name, value in attributes.items()},
    )


def text(parent: ET.Element, x: float, y: float, value: str, **attributes: object) -> None:
    item = ET.SubElement(parent, f"{{{SVG_NS}}}text", {
        "x": f"{x:.1f}", "y": f"{y:.1f}",
        **{name.replace("_", "-"): str(value) for name, value in attributes.items()},
    })
    item.text = value


def line(parent: ET.Element, x1: float, y1: float, x2: float, y2: float,
         css_class: str = "line", arrow: bool = False) -> None:
    attributes = {
        "x1": str(x1), "y1": str(y1), "x2": str(x2), "y2": str(y2),
        "class": css_class,
    }
    if arrow:
        attributes["marker-end"] = "url(#arrow)"
    ET.SubElement(parent, f"{{{SVG_NS}}}line", attributes)


def rounded_box(parent: ET.Element, x: float, y: float, width: float,
                height: float, css_class: str) -> None:
    ET.SubElement(parent, f"{{{SVG_NS}}}rect", {
        "x": str(x), "y": str(y), "width": str(width), "height": str(height),
        "rx": "9", "ry": "9", "class": css_class,
    })


def stage(parent: ET.Element, x: float, label: str, power: str,
          active: str) -> None:
    rounded_box(parent, x, 245, 176, 112, "stage")
    text(parent, x + 88, 270, label, text_anchor="middle", css_class="stage-title")
    text(parent, x + 88, 298, f"I + U{power}", text_anchor="middle", css_class="formula")
    text(parent, x + 88, 323, "old ⊕ shifted copies(old)",
         text_anchor="middle", css_class="small")
    text(parent, x + 88, 344, active, text_anchor="middle", css_class="tiny")


def example_stage(parent: ET.Element, x: float, title: str,
                  shifts: str, detail: str) -> None:
    rounded_box(parent, x, 488, 205, 104, "example")
    text(parent, x + 102.5, 515, title, text_anchor="middle", css_class="stage-title")
    text(parent, x + 102.5, 544, shifts, text_anchor="middle", css_class="formula")
    text(parent, x + 102.5, 570, detail, text_anchor="middle", css_class="tiny")


def render(output: Path) -> None:
    width, height = 1320, 720
    root = node("svg", width=width, height=height, viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height),
        "fill": "#ffffff",
    })
    definitions = ET.SubElement(root, f"{{{SVG_NS}}}defs")
    marker = ET.SubElement(definitions, f"{{{SVG_NS}}}marker", {
        "id": "arrow", "viewBox": "0 0 10 10", "refX": "9", "refY": "5",
        "markerWidth": "7", "markerHeight": "7", "orient": "auto-start-reverse",
    })
    ET.SubElement(marker, f"{{{SVG_NS}}}path", {"d": "M 0 0 L 10 5 L 0 10 z", "fill": "#334155"})
    style = ET.SubElement(root, f"{{{SVG_NS}}}style")
    style.text = """
text{font-family:DejaVu Sans,sans-serif;fill:#172033}
.title{font-size:25px;font-weight:700}.subtitle{font-size:13px;fill:#9a3412}
.formula{font-size:17px;font-family:DejaVu Serif,serif}.body{font-size:14px}
.small{font-size:12px}.tiny{font-size:11px;fill:#475569}
.stage-title{font-size:14px;font-weight:700}.section{font-size:16px;font-weight:700}
.definition{fill:#f4f7fb;stroke:#9aabc0;stroke-width:1.4}
.identity{fill:#eef8f1;stroke:#3f8b5f;stroke-width:1.6}
.stage{fill:#f7f3ff;stroke:#7755a5;stroke-width:1.8}
.state{fill:#eaf3fb;stroke:#3676a5;stroke-width:1.6}
.example{fill:#fff8e8;stroke:#c77b24;stroke-width:1.5}
.note{fill:#f8fafc;stroke:#a8b2c1;stroke-width:1.2;stroke-dasharray:5 4}
.line{stroke:#334155;stroke-width:1.8}.guide{stroke:#94a3b8;stroke-width:1.3}
"""

    text(root, width / 2, 38, "Sparse Frobenius construction of (I + U)⁻¹",
         text_anchor="middle", css_class="title")
    text(root, width / 2, 63,
         "CONSTRUCTION DIAGRAM — algebraic dependencies only; not measured timing or circuit depth",
         text_anchor="middle", css_class="subtitle")

    rounded_box(root, 42, 88, 455, 112, "definition")
    text(root, 62, 114, "Feedback operator on the truncated m-bit space",
         css_class="section")
    text(root, 62, 145, "U = ⊕ₜ∈T₊ N^Δₜ,     Δₜ = m − t,     NᵈX = X ≫ d",
         css_class="formula")
    text(root, 62, 174, "T₊ = T ∩ {1,…,m−1}; tap t=0 has distance m and no feedback stage.",
         css_class="small")

    rounded_box(root, 520, 88, 758, 112, "identity")
    text(root, 540, 114, "Characteristic-two factorization",
         css_class="section")
    text(root, 540, 145,
         "(I + U)⁻¹ = ∏ₖ₌₀ʳ⁻¹ (I + U^(2^k)),     r = ⌈log₂(m / Δ_min)⌉",
         css_class="formula")
    text(root, 540, 174,
         "(I + U) ∏ₖ₌₀ʳ⁻¹(I + U^(2^k)) = I + U^(2^r) = I",
         css_class="small")

    text(root, 42, 230, "Synchronous state construction", css_class="section")
    rounded_box(root, 42, 268, 78, 66, "state")
    text(root, 81, 296, "X₀", text_anchor="middle", css_class="formula")
    text(root, 81, 317, "= H", text_anchor="middle", css_class="small")
    line(root, 120, 301, 155, 301, arrow=True)

    stage(root, 155, "stage k = 0", "", "active when Δₜ < m")
    line(root, 331, 301, 365, 301, arrow=True)
    rounded_box(root, 365, 276, 60, 50, "state")
    text(root, 395, 307, "X₁", text_anchor="middle", css_class="formula")
    line(root, 425, 301, 454, 301, arrow=True)

    stage(root, 454, "stage k = 1", "²", "active when 2Δₜ < m")
    line(root, 630, 301, 664, 301, arrow=True)
    rounded_box(root, 664, 276, 60, 50, "state")
    text(root, 694, 307, "X₂", text_anchor="middle", css_class="formula")
    line(root, 724, 301, 753, 301, arrow=True)

    stage(root, 753, "stage k = 2", "⁴", "active when 4Δₜ < m")
    line(root, 929, 301, 966, 301, arrow=True)
    text(root, 988, 307, "⋯", text_anchor="middle", css_class="formula")
    line(root, 1008, 301, 1038, 301, arrow=True)

    rounded_box(root, 1038, 245, 176, 112, "stage")
    text(root, 1126, 270, "stage k = r−1", text_anchor="middle", css_class="stage-title")
    text(root, 1126, 298, "I + U^(2^(r−1))", text_anchor="middle", css_class="formula")
    text(root, 1126, 323, "same immutable old", text_anchor="middle", css_class="small")
    text(root, 1126, 344, "then U^(2^r) = 0", text_anchor="middle", css_class="tiny")
    line(root, 1214, 301, 1241, 301, arrow=True)
    rounded_box(root, 1241, 268, 58, 66, "state")
    text(root, 1270, 296, "Xᵣ", text_anchor="middle", css_class="formula")
    text(root, 1270, 317, "= Y", text_anchor="middle", css_class="small")

    line(root, 170, 382, 1185, 382, "guide", arrow=True)
    text(root, 677, 405,
         "shift distances double by stage:  Δₜ  →  2Δₜ  →  4Δₜ  →  ⋯  →  2^(r−1)Δₜ",
         text_anchor="middle", css_class="body")
    text(root, 677, 428,
         "Every shifted copy in one box reads the same immutable old state Xₖ.",
         text_anchor="middle", css_class="small")

    text(root, 42, 468, "Worked schedule: m = 16, T₊ = {3,11,15}, Δ = {13,5,1}",
         css_class="section")
    example_stage(root, 42, "k = 0", "active shifts {1,5,13}", "X₁ = (I + U)X₀")
    line(root, 247, 540, 277, 540, arrow=True)
    example_stage(root, 277, "k = 1", "active shifts {2,10}", "26 ≥ 16 is pruned")
    line(root, 482, 540, 512, 540, arrow=True)
    example_stage(root, 512, "k = 2", "active shift {4}", "20,52 ≥ 16 are pruned")
    line(root, 717, 540, 747, 540, arrow=True)
    example_stage(root, 747, "k = 3", "active shift {8}", "then U¹⁶ = 0")

    rounded_box(root, 982, 488, 317, 104, "note")
    text(root, 1000, 515, "Composition, not expansion", css_class="stage-title")
    text(root, 1000, 542, "Mixed feedback paths arise as stages compose.", css_class="small")
    text(root, 1000, 565, "No pairwise tap-sum schedule is materialized.", css_class="small")

    rounded_box(root, 350, 628, 620, 55, "identity")
    text(root, 660, 651, "Final reduction assembly", text_anchor="middle", css_class="stage-title")
    text(root, 660, 674, "red_g(A) = L ⊕ V(Y),    where A = L + xᵐH",
         text_anchor="middle", css_class="formula")

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("operator schematic output must use the .svg extension")
    render(args.output)
    print(f"operator construction schematic: {args.output}")


if __name__ == "__main__":
    main()
