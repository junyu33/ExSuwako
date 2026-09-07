#!/usr/bin/env python3
"""Contract and differential smoke checks for the Rabin E2E driver."""

from __future__ import annotations

import argparse
import csv
import io
import math
import subprocess


def run(binary: str, *args: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([binary, *args], capture_output=True, text=True)
    if expect_success and result.returncode:
        raise AssertionError(result.stderr)
    if not expect_success and result.returncode == 0:
        raise AssertionError("invalid Rabin invocation unexpectedly succeeded")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()

    # x^8+x^4+x^3+x+1 is irreducible over GF(2).
    result = run(
        args.binary,
        "--m", "8",
        "--taps", "0,1,3,4",
        "--trials", "2",
        "--warmups", "1",
        "--sample-id", "aes-polynomial",
    )
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    required = {
        "schema", "sample_id", "m", "h", "delta_min", "taps", "trial",
        "order", "method", "e2e_ns", "setup_ns", "chain_ns", "check_ns",
        "result",
    }
    if not rows or set(rows[0]) != required:
        raise AssertionError("unexpected Rabin CSV schema")
    methods = {"FFR", "BarrettGF2X", "Serial", "NTL-IterIrredTest"}
    if len(rows) != 2 * len(methods):
        raise AssertionError("unexpected Rabin row count")
    for trial in range(2):
        selected = [row for row in rows if int(row["trial"]) == trial]
        if {row["method"] for row in selected} != methods:
            raise AssertionError("incomplete method rotation")
        if {int(row["order"]) for row in selected} != set(range(len(methods))):
            raise AssertionError("invalid timing positions")
    for row in rows:
        if row["schema"] != "rabin-power-of-two-irred:v1":
            raise AssertionError("wrong workload schema")
        if row["result"] != "irreducible" or float(row["e2e_ns"]) <= 0:
            raise AssertionError("invalid Rabin result")
        if row["method"] != "NTL-IterIrredTest":
            parts = [float(row[name]) for name in ("setup_ns", "chain_ns", "check_ns")]
            if not all(value >= 0 and math.isfinite(value) for value in parts):
                raise AssertionError("invalid matched-driver component")
            if abs(sum(parts) - float(row["e2e_ns"])) > 1e-6 * float(row["e2e_ns"]):
                raise AssertionError("E2E components do not sum to total")

    # x^8+x+1 is reducible, so timing must be refused.
    run(
        args.binary,
        "--m", "8",
        "--taps", "0,1",
        "--trials", "1",
        expect_success=False,
    )
    print("Rabin benchmark contract checks passed")


if __name__ == "__main__":
    main()
