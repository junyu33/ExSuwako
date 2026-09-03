#!/usr/bin/env python3
"""Generate deterministic manifests of distinct fixed-weight supports."""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path


MASK64 = (1 << 64) - 1
PROVENANCE = "synthetic-fixed-weight-uniform:v1"
CONSTANT_FREE_PROVENANCE = "synthetic-fixed-weight-uniform-constant-free:v1"
SAMPLER = "splitmix64-floyd-distinct:v1"


class SplitMix64:
    def __init__(self, seed: int) -> None:
        self.state = seed & MASK64

    def next(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return value ^ (value >> 31)

    def below(self, bound: int) -> int:
        if not 0 < bound <= 1 << 64:
            raise ValueError("random bound must lie in [1,2^64]")
        limit = (1 << 64) - ((1 << 64) % bound)
        while True:
            value = self.next()
            if value < limit:
                return value % bound


def sample_subset(m: int, size: int, rng: SplitMix64) -> tuple[int, ...]:
    """Floyd sampling: one uniform size-subset using O(size) memory."""
    selected: set[int] = set()
    for upper in range(m - size, m):
        candidate = rng.below(upper + 1)
        selected.add(upper if candidate in selected else candidate)
    if len(selected) != size:
        raise AssertionError("internal fixed-weight sampling error")
    return tuple(sorted(selected))


def cell_seed(seed: int, m: int, h: int) -> int:
    value = seed & MASK64
    value ^= (m * 0xD6E8FEB86659FD93) & MASK64
    value ^= (h * 0xA5A3564E27F8862F) & MASK64
    return value


def generate_cell(
    m: int, h: int, requested: int, seed: int, constant_policy: str = "either"
) -> tuple[list[tuple[int, ...]], int, str]:
    domain_start = 1 if constant_policy == "absent" else 0
    domain_size = m - domain_start
    if m <= 0 or not 2 <= h <= domain_size + 1:
        raise ValueError(f"invalid fixed-weight cell m={m}, h={h}")
    size = h - 1
    population = math.comb(domain_size, size)
    count = min(requested, population)
    if population <= requested:
        return (
            list(itertools.combinations(range(domain_start, m), size)),
            population,
            "exhaustive-fixed-weight:v1",
        )

    policy_seed = seed ^ (0x243F6A8885A308D3 if constant_policy == "absent" else 0)
    rng = SplitMix64(cell_seed(policy_seed, m, h))
    supports: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    while len(supports) < count:
        support = tuple(
            tap + domain_start for tap in sample_subset(domain_size, size, rng)
        )
        if support not in seen:
            seen.add(support)
            supports.append(support)
    return supports, population, SAMPLER


def require_distinct(values: list[int], name: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{name} values must be distinct")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--m", type=int, nargs="+", required=True)
    parser.add_argument("--h", type=int, nargs="+", required=True)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--seed", type=lambda value: int(value, 0), required=True)
    parser.add_argument(
        "--constant-policy", choices=["either", "absent"], default="either"
    )
    args = parser.parse_args()
    if args.samples <= 0:
        raise ValueError("samples must be positive")
    require_distinct(args.m, "m")
    require_distinct(args.h, "h")

    entries: list[dict[str, object]] = []
    capped_cells: list[str] = []
    for m in args.m:
        for h in args.h:
            supports, population, sampler = generate_cell(
                m, h, args.samples, args.seed, args.constant_policy
            )
            if len(supports) < args.samples:
                capped_cells.append(f"m{m}-h{h}:{len(supports)}")
            for index, taps in enumerate(supports):
                entries.append({
                    "sample_id": (
                        f"fixed-weight-m{m}-h{h}-sample{index:04d}-"
                        f"constant-{args.constant_policy}"
                    ),
                    "provenance": (
                        CONSTANT_FREE_PROVENANCE
                        if args.constant_policy == "absent" else PROVENANCE
                    ),
                    "m": m,
                    "taps": list(taps),
                    "support_sampler": sampler,
                    "support_seed": args.seed,
                    "cell_population": str(population),
                    "requested_supports": args.samples,
                    "realized_supports": len(supports),
                    "constant_policy": args.constant_policy,
                })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, separators=(",", ":")) + "\n")
    capped = ";".join(capped_cells) if capped_cells else "none"
    print(
        f"points={len(entries)} cells={len(args.m) * len(args.h)} "
        f"requested_per_cell={args.samples} capped_cells={capped} "
        f"sampler={SAMPLER} constant_policy={args.constant_policy} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
