#!/usr/bin/env python3
"""Generate deterministic sparse irreducible moduli for the Rabin E2E study.

Run this file with ``sage -python``.  The output is JSON Lines so the exact
modulus, search seed, and Sage certificate provenance are fixed before timing.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from sage.all import GF, PolynomialRing  # type: ignore[import-not-found]
from sage.version import banner  # type: ignore[import-not-found]


SCHEMA = "exsuwako-rabin-modulus:v1"
PROVENANCE = "deterministic-fixed-weight-sage-search:v1"


def integer(text: str) -> int:
    return int(text, 0)


def candidate_taps(
    rng: random.Random, m: int, h: int, delta_min: int
) -> tuple[int, ...]:
    highest = m - delta_min
    required = {0, highest}
    population = [tap for tap in range(1, highest) if tap not in required]
    extra = h - 1 - len(required)
    if extra < 0 or extra > len(population):
        raise ValueError("requested (m, h, delta_min) is infeasible")
    return tuple(sorted(required | set(rng.sample(population, extra))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--h", type=int, required=True)
    parser.add_argument("--delta-min", type=int, required=True)
    parser.add_argument("--seed", type=integer, required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.m < 2 or args.m & (args.m - 1):
        raise ValueError("m must be a power of two of at least two")
    if args.h < 3 or args.h % 2 == 0:
        raise ValueError("h must be odd and at least three for irreducibility")
    if not 1 <= args.delta_min < args.m:
        raise ValueError("delta_min must lie in [1, m)")
    if args.count < 1 or args.max_attempts < 1:
        raise ValueError("count and max_attempts must be positive")

    field = GF(2)
    ring = PolynomialRing(field, "x")
    x = ring.gen()
    rng = random.Random(args.seed)
    seen: set[tuple[int, ...]] = set()
    rows: list[dict[str, object]] = []

    for attempt in range(1, args.max_attempts + 1):
        taps = candidate_taps(rng, args.m, args.h, args.delta_min)
        if taps in seen:
            continue
        seen.add(taps)
        modulus = x**args.m + sum(x**tap for tap in taps)
        if not modulus.is_irreducible():
            continue
        rows.append(
            {
                "schema": SCHEMA,
                "sample_id": (
                    f"rabin-m{args.m}-h{args.h}-d{args.delta_min}-"
                    f"i{len(rows)}"
                ),
                "provenance": PROVENANCE,
                "m": args.m,
                "h": args.h,
                "delta_min": args.delta_min,
                "taps": list(taps),
                "search_seed": args.seed,
                "accepted_attempt": attempt,
                "irreducible": True,
                "certificate": "sage-is_irreducible:v1",
                "sage_version": str(banner),
            }
        )
        if len(rows) == args.count:
            break

    if len(rows) != args.count:
        raise RuntimeError(
            f"found {len(rows)} irreducible moduli after {args.max_attempts} attempts"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(
        f"schema={SCHEMA} found={len(rows)} attempts={rows[-1]['accepted_attempt']} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
