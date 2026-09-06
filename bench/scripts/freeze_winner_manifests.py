#!/usr/bin/env python3
"""Materialize the frozen Classical Winner Phase Diagram support suites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_controlled_supports import generate_entries
from generate_fixed_weight_supports import (
    CONSTANT_FREE_PROVENANCE,
    generate_cell,
)


MAIN_DEGREES = (128, 512, 2048, 8192, 32768, 131072)
SUPPLEMENT_DEGREES = (256, 1024, 4096, 16384, 65536)
SCALING_DEGREES = (1 << 16, 1 << 17, 1 << 18, 1 << 19, 1 << 20)
PANEL_WEIGHTS = (2, 3, 5, 9, 17, 33, 65)
SCALING_WEIGHTS = (3, 9, 33, 129)
RANDOM_SEED = 0x4558535557414B4F


def powers_to_half(m: int) -> list[int]:
    values: list[int] = []
    value = 1
    while value <= m // 2:
        values.append(value)
        value *= 2
    return values


HIGH_WEIGHT_GRIDS = {
    128: ((65, 81, 97, 113, 121), powers_to_half(128)),
    512: ((65, 97, 129, 193, 257, 385), powers_to_half(512)),
    2048: (
        (65, 97, 129, 193, 257, 385, 513, 769, 1025),
        powers_to_half(2048),
    ),
    8192: (
        (65, 97, 129, 193, 257, 385, 513, 769, 1025),
        powers_to_half(8192),
    ),
    32768: (
        (97, 129, 161, 193, 225, 257, 321, 385, 513, 769, 1025),
        powers_to_half(32768),
    ),
    131072: (
        (97, 129, 193, 257, 385, 513, 641, 769, 897, 1025),
        powers_to_half(131072),
    ),
}


def write(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(entry, separators=(",", ":")) + "\n" for entry in entries),
        encoding="utf-8",
    )


def write_controlled_pair(
    root: Path, stem: str, m: int, weights: tuple[int, ...], deltas: list[int],
    constant_policy: str = "absent",
) -> int:
    core = [delta for delta in deltas if delta < 64]
    ld = [delta for delta in deltas if delta >= 64]

    def feasible(delta: int, h: int) -> bool:
        required_positive_taps = h - (2 if constant_policy == "present" else 1)
        return required_positive_taps <= m - delta

    def entries_for(selected: list[int]) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for h in weights:
            for delta in selected:
                if feasible(delta, h):
                    entries.extend(
                        generate_entries(
                            [m], [h], [delta], constant_policy
                        )
                    )
        return entries

    count = 0
    if core:
        entries = entries_for(core)
        write(root / f"{stem}-core.jsonl", entries)
        count += len(entries)
    if ld:
        entries = entries_for(ld)
        write(root / f"{stem}-ld.jsonl", entries)
        count += len(entries)
    return count


def random_entries(m: int) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for h in PANEL_WEIGHTS:
        supports, population, sampler = generate_cell(
            m, h, 256, RANDOM_SEED, "absent"
        )
        for index, taps in enumerate(supports):
            entries.append({
                "sample_id": (
                    f"fixed-weight-m{m}-h{h}-sample{index:04d}-constant-absent"
                ),
                "provenance": CONSTANT_FREE_PROVENANCE,
                "m": m,
                "taps": list(taps),
                "support_sampler": sampler,
                "support_seed": RANDOM_SEED,
                "cell_population": str(population),
                "requested_supports": 256,
                "realized_supports": len(supports),
                "constant_policy": "absent",
            })
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("bench/manifests/paper"),
    )
    args = parser.parse_args()
    root = args.output_dir
    points = 0

    for m in (128, 512, 2048):
        entries = generate_entries(
            [m], [3, 17, 65], [1, m // 16, m // 2], "absent"
        )
        write(root / f"dense-screen-m{m}.jsonl", entries)
        points += len(entries)

    for m in MAIN_DEGREES:
        points += write_controlled_pair(
            root, f"main-m{m}", m, PANEL_WEIGHTS, powers_to_half(m)
        )
        entries = random_entries(m)
        write(root / f"random-m{m}.jsonl", entries)
        points += len(entries)

        high_weights, high_deltas = HIGH_WEIGHT_GRIDS[m]
        points += write_controlled_pair(
            root, f"highweight-m{m}", m, high_weights, high_deltas
        )

    for m in SUPPLEMENT_DEGREES:
        points += write_controlled_pair(
            root, f"supplement-m{m}", m, PANEL_WEIGHTS, powers_to_half(m)
        )

    for m in (512, 8192, 131072):
        points += write_controlled_pair(
            root, f"constant-present-m{m}", m, (3, 9, 33, 65),
            [1, 64, m // 4, m // 2], "present",
        )

    for m in SCALING_DEGREES:
        weights = (129,) if m in (1 << 16, 1 << 17) else SCALING_WEIGHTS
        points += write_controlled_pair(
            root, f"scaling-m{m}", m, weights,
            [1, 64, 256, m // 16, m // 4, m // 2],
        )

    print(
        f"suite=classical-winner-phase-diagram:v1 points={points} "
        f"output_dir={root}"
    )


if __name__ == "__main__":
    main()
