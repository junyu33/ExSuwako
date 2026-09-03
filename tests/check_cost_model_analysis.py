#!/usr/bin/env python3
"""Contract test for the GS cost-model correlation analysis."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


FIELDS = [
    "sample_id", "m", "word_bits", "taps", "feedback_stages", "W_fb",
    "GS_source_cost_model", "GS_source_aligned_word_contributions",
    "GS_source_cross_word_contributions", "GS_source_word_shifts",
    "GS_source_word_xors", "GS_source_logical_word_reads",
    "GS_source_logical_word_writes", "GS_source_scratch_words",
    "input_distribution", "timing_scope", "timing_order", "aggregation",
    "inputs", "batch_repeats", "warmup_runs", "measurement_trials",
    "measurement_trial", "seed", "GS_ns",
]


def main() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "bench" / "scripts" / "analyze_gs_cost_model.py"
    )
    with tempfile.TemporaryDirectory(prefix="exsuwako-cost-model-") as directory:
        root = Path(directory)
        source = root / "raw.csv"
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            for sample, xors, runtime, stages, aligned, cross in [
                ("aligned", 10, 20, 0, 10, 0),
                ("aligned-repeat", 10, 22, 0, 10, 0),
                ("mixed-low", 20, 31, 1, 5, 5),
                ("mixed-high", 30, 39, 3, 4, 12),
                ("cross", 40, 55, 6, 0, 20),
            ]:
                for trial in range(3):
                    writer.writerow(
                        {
                            "sample_id": sample,
                            "m": 256,
                            "word_bits": 64,
                            "taps": str(xors),
                            "feedback_stages": stages,
                            "W_fb": xors * 8,
                            "GS_source_cost_model": "scalar-source-v1",
                            "GS_source_aligned_word_contributions": aligned,
                            "GS_source_cross_word_contributions": cross,
                            "GS_source_word_shifts": cross * 2,
                            "GS_source_word_xors": xors,
                            "GS_source_logical_word_reads": xors + 4,
                            "GS_source_logical_word_writes": xors // 2 + 4,
                            "GS_source_scratch_words": 5,
                            "input_distribution": "uniform-full-range:v1",
                            "timing_scope": "reduction-steady-state:v1",
                            "timing_order": "cyclic-method-rotation:v1",
                            "aggregation": "median-of-trial-medians:no-outlier-removal:v1",
                            "inputs": 4,
                            "batch_repeats": 1,
                            "warmup_runs": 1,
                            "measurement_trials": 3,
                            "measurement_trial": trial,
                            "seed": 7,
                            "GS_ns": runtime + trial - 1,
                        }
                    )
        correlations = root / "correlations.csv"
        residuals = root / "residuals.csv"
        diagnostics = root / "diagnostics.csv"
        command = [
            sys.executable, str(script), "--input", str(source),
            "--correlations", str(correlations), "--residuals", str(residuals),
            "--diagnostics", str(diagnostics), "--min-trials", "3",
            "--min-batch-repeats", "1",
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        with correlations.open(newline="", encoding="utf-8") as stream:
            correlation_rows = list(csv.DictReader(stream))
        if len(correlation_rows) != 5:
            raise AssertionError("expected one fixed-m row per predictor")
        xor_row = next(
            row for row in correlation_rows
            if row["predictor"] == "GS_source_word_xors"
        )
        if xor_row["response"] != "GS_ns" or xor_row["spearman_rho"] != "1":
            raise AssertionError(f"unexpected XOR correlation row: {xor_row}")
        with residuals.open(newline="", encoding="utf-8") as stream:
            residual_rows = list(csv.DictReader(stream))
        if len(residual_rows) != 4:
            raise AssertionError("trial aggregation or residual output is incorrect")
        aligned_row = next(row for row in residual_rows if row["taps"] == "10")
        if (
            aligned_row["sample_instances"], aligned_row["trial_count"]
        ) != ("2", "6"):
            raise AssertionError("duplicate exact supports were not collapsed")
        if not all(
            row["timing_status"] in {"stable", "uncertain"}
            and float(row["GS_ns_ci95_low"]) <= float(row["GS_ns"])
            <= float(row["GS_ns_ci95_high"])
            for row in residual_rows
        ):
            raise AssertionError("bootstrap interval or uncertainty status is invalid")
        with diagnostics.open(newline="", encoding="utf-8") as stream:
            diagnostic_rows = list(csv.DictReader(stream))
        if {row["factor"] for row in diagnostic_rows} != {
            "logical-access-proxy", "feedback-stage-barriers", "word-alignment"
        }:
            raise AssertionError("diagnostic factors are incomplete")
        if any(row["causal_claim"] != "none-source-proxy-only" for row in diagnostic_rows):
            raise AssertionError("source proxies must not be reported as causal evidence")
    print("GS cost-model analysis contract checks passed")


if __name__ == "__main__":
    main()
