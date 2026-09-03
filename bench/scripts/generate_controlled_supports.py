#!/usr/bin/env python3
"""Generate a Cartesian support grid with independent h and Delta_min axes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def require_distinct_positive(values: list[int], name: str) -> None:
    if any(value <= 0 for value in values):
        raise ValueError(f"{name} values must be positive")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} values must be distinct")


def spread_support(
    m: int, h: int, delta_min: int, constant_policy: str
) -> list[int]:
    """Construct one deterministic, approximately evenly spaced support."""
    if h < 2:
        raise ValueError("controlled feedback points require h >= 2")
    if not 1 <= delta_min <= m:
        raise ValueError(f"Delta_min={delta_min} is outside [1,{m}]")

    support_size = h - 1
    highest = m - delta_min
    if constant_policy == "absent":
        if highest < support_size:
            raise ValueError(
                f"infeasible cell m={m}, h={h}, Delta_min={delta_min}: "
                "constant-free support has too few available exponents"
            )
        taps = [
            (index * highest) // support_size
            for index in range(1, support_size)
        ]
        taps.append(highest)
    else:
        if highest == 0:
            if support_size != 1:
                raise ValueError(
                    f"infeasible cell m={m}, h={h}, Delta_min={delta_min}: "
                    "tap 0 cannot be counted twice"
                )
            taps = [0]
        else:
            if support_size < 2 or highest < support_size - 1:
                raise ValueError(
                    f"infeasible cell m={m}, h={h}, Delta_min={delta_min}: "
                    "constant-present support has too few available exponents"
                )
            taps = [0]
            taps.extend(
                (index * highest) // (support_size - 1)
                for index in range(1, support_size - 1)
            )
            taps.append(highest)

    if (
        len(taps) != support_size
        or taps != sorted(set(taps))
        or taps[-1] != highest
        or any(tap < 0 or tap >= m for tap in taps)
    ):
        raise AssertionError("internal controlled-support construction error")
    return taps


def generate_entries(
    degrees: list[int], weights: list[int], deltas: list[int],
    constant_policy: str,
) -> list[dict[str, object]]:
    require_distinct_positive(degrees, "m")
    require_distinct_positive(weights, "h")
    require_distinct_positive(deltas, "Delta_min")
    label = "constant-free" if constant_policy == "absent" else "constant-present"
    provenance = f"synthetic-controlled-cartesian-spread-{label}:v1"
    entries: list[dict[str, object]] = []
    for m in degrees:
        for h in weights:
            for delta_min in deltas:
                taps = spread_support(m, h, delta_min, constant_policy)
                entries.append({
                    "sample_id": f"controlled-m{m}-h{h}-d{delta_min}-{label}",
                    "provenance": provenance,
                    "m": m,
                    "taps": taps,
                })
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--m", type=int, nargs="+", required=True)
    parser.add_argument("--h", type=int, nargs="+", required=True)
    parser.add_argument("--delta-min", type=int, nargs="+", required=True)
    parser.add_argument(
        "--constant-policy", choices=["absent", "present"], default="absent"
    )
    args = parser.parse_args()

    entries = generate_entries(
        args.m, args.h, args.delta_min, args.constant_policy
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, separators=(",", ":")) + "\n")
    print(
        f"points={len(entries)} degrees={len(args.m)} weights={len(args.h)} "
        f"deltas={len(args.delta_min)} constant_policy={args.constant_policy} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
