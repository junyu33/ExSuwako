#!/usr/bin/env python3
"""Freeze the separate representative slices for planned versus online FFR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_controlled_supports import spread_support


DEGREES = (128, 2048, 32768, 131072)
WEIGHTS = {
    128: (3, 9, 65),
    2048: (3, 9, 65, 513),
    32768: (3, 9, 65, 513),
    131072: (3, 9, 65, 513),
}


def entries() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for m in DEGREES:
        for h in WEIGHTS[m]:
            for delta_min in (1, 64, m // 4):
                taps = spread_support(m, h, delta_min, "absent")
                result.append(
                    {
                        "sample_id": f"ffr-online-m{m}-h{h}-d{delta_min}",
                        "provenance": "ffr-online-representative-slice:v1",
                        "m": m,
                        "taps": taps,
                    }
                )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = entries()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, separators=(",", ":")) + "\n")
    print(f"points={len(values)} output={args.output}")


if __name__ == "__main__":
    main()
