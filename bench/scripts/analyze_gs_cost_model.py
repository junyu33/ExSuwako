#!/usr/bin/env python3
"""Relate the scalar GS source model to measured reduction runtime.

The input is raw output from phase_diagram_benchmark.py.  Analysis is
stratified by m so that degree scaling is not mistaken for support-geometry
prediction.  No source-model quantity is labelled as an instruction, hardware
memory transaction, cycle count, or measured runtime.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


RESPONSE = "GS_ns"
TIMING_SCOPE = "reduction-steady-state:v1"
COST_MODEL = "scalar-source-v1"
PREDICTORS = (
    "W_fb",
    "GS_source_word_xors",
    "GS_source_word_shifts",
    "GS_source_logical_word_reads",
    "GS_source_logical_word_writes",
)
BOOTSTRAP_RESAMPLES = 10_000
INVARIANT_FIELDS = (
    "m",
    "word_bits",
    "taps",
    "feedback_stages",
    "W_fb",
    "GS_source_cost_model",
    "GS_source_aligned_word_contributions",
    "GS_source_cross_word_contributions",
    "GS_source_word_shifts",
    "GS_source_word_xors",
    "GS_source_logical_word_reads",
    "GS_source_logical_word_writes",
    "GS_source_scratch_words",
    "input_distribution",
    "timing_scope",
    "timing_order",
    "aggregation",
    "inputs",
    "batch_repeats",
    "warmup_runs",
    "measurement_trials",
    "seed",
)


def ranks(values: list[float]) -> list[float]:
    """Return average ranks, including deterministic handling of ties."""
    result = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=values.__getitem__)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index in ordered[start:end]:
            result[index] = rank
        start = end
    return result


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right)
    )
    left_norm = sum((x - left_mean) ** 2 for x in left)
    right_norm = sum((y - right_mean) ** 2 for y in right)
    if left_norm == 0 or right_norm == 0:
        return None
    return numerator / math.sqrt(left_norm * right_norm)


def spearman(left: list[float], right: list[float]) -> float | None:
    return pearson(ranks(left), ranks(right))


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    if len(xs) < 2:
        return None
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return None
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator
    return y_mean - slope * x_mean, slope


def bootstrap_median_interval(
    values: list[float], identity: str
) -> tuple[float, float]:
    seed = int.from_bytes(
        hashlib.sha256(identity.encode("utf-8")).digest()[:8], "little"
    )
    rng = random.Random(seed)
    count = len(values)
    estimates = sorted(
        statistics.median(values[rng.randrange(count)] for _ in range(count))
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return estimates[249], estimates[9749]


def alignment_regime(row: dict[str, object]) -> str:
    aligned = int(row["GS_source_aligned_word_contributions"])
    cross = int(row["GS_source_cross_word_contributions"])
    if cross == 0:
        return "aligned-only"
    if aligned == 0:
        return "cross-word-only"
    return "mixed-alignment"


def stage_regime(row: dict[str, object]) -> str:
    stages = int(row["feedback_stages"])
    if stages == 0:
        return "zero-stage"
    if stages == 1:
        return "one-stage"
    if stages <= 4:
        return "two-to-four-stages"
    return "five-or-more-stages"


def access_regime(row: dict[str, object]) -> str:
    accesses = int(row["GS_source_logical_word_reads"]) + int(
        row["GS_source_logical_word_writes"]
    )
    arithmetic = int(row["GS_source_word_xors"]) + int(
        row["GS_source_word_shifts"]
    )
    fraction = accesses / max(1, accesses + arithmetic)
    if fraction < 0.5:
        return "arithmetic-heavy"
    if fraction < 0.75:
        return "mixed-access-arithmetic"
    return "logical-access-heavy"


def load_samples(
    path: Path, min_trials: int, min_batch_repeats: int,
    min_warmup_runs: int
) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as stream:
        raw_rows = list(csv.DictReader(stream))
    if not raw_rows:
        raise ValueError("input contains no rows")
    required = {
        "sample_id", "measurement_trial", RESPONSE,
        *INVARIANT_FIELDS, *PREDICTORS,
    }
    missing = required.difference(raw_rows[0])
    if missing:
        raise ValueError(f"input is missing fields: {', '.join(sorted(missing))}")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        if row["timing_scope"] != TIMING_SCOPE:
            raise ValueError(f"unexpected timing scope {row['timing_scope']!r}")
        if row["GS_source_cost_model"] != COST_MODEL:
            raise ValueError(f"unexpected GS source model {row['GS_source_cost_model']!r}")
        grouped[row["sample_id"]].append(row)

    sampled_instances: list[dict[str, object]] = []
    for sample_id, rows in grouped.items():
        if len(rows) < min_trials:
            raise ValueError(
                f"sample {sample_id!r} has {len(rows)} trials; need {min_trials}"
            )
        first = rows[0]
        declared_trials = int(first["measurement_trials"])
        trial_indices = [int(row["measurement_trial"]) for row in rows]
        if declared_trials != len(rows) or sorted(trial_indices) != list(
            range(declared_trials)
        ):
            raise ValueError(
                f"sample {sample_id!r} does not contain exactly the declared "
                "measurement-trial indices"
            )
        if int(first["batch_repeats"]) < min_batch_repeats:
            raise ValueError(
                f"sample {sample_id!r} has only {first['batch_repeats']} batch "
                f"repeats; need {min_batch_repeats}"
            )
        if int(first["warmup_runs"]) < min_warmup_runs:
            raise ValueError(
                f"sample {sample_id!r} has only {first['warmup_runs']} warm-up "
                f"runs; need {min_warmup_runs}"
            )
        for row in rows[1:]:
            for field in INVARIANT_FIELDS:
                if row[field] != first[field]:
                    raise ValueError(
                        f"sample {sample_id!r} changes invariant field {field}"
                    )
        sample: dict[str, object] = {
            "sample_id": sample_id,
            "trial_count": len(rows),
            RESPONSE: statistics.median(float(row[RESPONSE]) for row in rows),
            "_measurements": [float(row[RESPONSE]) for row in rows],
        }
        for field in INVARIANT_FIELDS:
            sample[field] = first[field]
        for field in PREDICTORS:
            sample[field] = float(first[field])
        sample["GS_source_logical_word_accesses"] = int(
            first["GS_source_logical_word_reads"]
        ) + int(first["GS_source_logical_word_writes"])
        sample["alignment_regime"] = alignment_regime(sample)
        sample["stage_regime"] = stage_regime(sample)
        sample["access_regime"] = access_regime(sample)
        sampled_instances.append(sample)

    by_support: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for sample in sampled_instances:
        by_support[(str(sample["m"]), str(sample["taps"]))].append(sample)
    samples: list[dict[str, object]] = []
    for (m, taps), instances in by_support.items():
        first = dict(instances[0])
        for instance in instances[1:]:
            for field in INVARIANT_FIELDS:
                if field != "seed" and instance[field] != first[field]:
                    raise ValueError(
                        f"support (m={m}, taps={taps}) changes field {field} "
                        "between sampled instances"
                    )
        first["support_id"] = f"m{m}:taps={taps}"
        first["source_sample_ids"] = ";".join(
            str(instance["sample_id"]) for instance in instances
        )
        first["sample_instances"] = len(instances)
        first["trial_count"] = sum(int(instance["trial_count"]) for instance in instances)
        measurements = [
            value
            for instance in instances
            for value in instance["_measurements"]  # type: ignore[union-attr]
        ]
        first[RESPONSE] = statistics.median(measurements)
        ci_low, ci_high = bootstrap_median_interval(
            measurements, str(first["support_id"])
        )
        half_width = (ci_high - ci_low) / 2.0
        first["GS_ns_ci95_low"] = ci_low
        first["GS_ns_ci95_high"] = ci_high
        first["GS_ns_relative_half_width"] = half_width / float(first[RESPONSE])
        first["timing_status"] = (
            "stable" if float(first["GS_ns_relative_half_width"]) <= 0.01
            else "uncertain"
        )
        del first["_measurements"]
        samples.append(first)
    return sorted(samples, key=lambda row: (int(row["m"]), str(row["taps"])))


def leave_one_out_residuals(samples: list[dict[str, object]]) -> None:
    """Fit runtime = a + b * source-word-XORs within each fixed-m panel."""
    by_m: dict[int, list[dict[str, object]]] = defaultdict(list)
    for sample in samples:
        by_m[int(sample["m"])].append(sample)
    predictor = "GS_source_word_xors"
    for rows in by_m.values():
        if len(rows) < 4:
            raise ValueError(
                "each fixed-m panel needs at least four distinct supports for "
                "leave-one-support-out residual analysis"
            )
        for held_out in rows:
            training = [row for row in rows if row is not held_out]
            fit = linear_fit(
                [float(row[predictor]) for row in training],
                [float(row[RESPONSE]) for row in training],
            )
            if fit is None:
                raise ValueError(
                    f"fixed-m panel {held_out['m']} has no predictor variation"
                )
            intercept, slope = fit
            predicted = intercept + slope * float(held_out[predictor])
            measured = float(held_out[RESPONSE])
            held_out["predictor"] = predictor
            held_out["predicted_GS_ns"] = predicted
            held_out["residual_ns"] = measured - predicted
            held_out["relative_residual"] = (measured - predicted) / measured


def correlation_rows(samples: list[dict[str, object]]) -> list[dict[str, object]]:
    by_m: dict[int, list[dict[str, object]]] = defaultdict(list)
    for sample in samples:
        by_m[int(sample["m"])].append(sample)
    output: list[dict[str, object]] = []
    for m, rows in sorted(by_m.items()):
        measured = [float(row[RESPONSE]) for row in rows]
        for predictor in PREDICTORS:
            rho = spearman([float(row[predictor]) for row in rows], measured)
            output.append(
                {
                    "m": m,
                    "samples": len(rows),
                    "uncertain_samples": sum(
                        row["timing_status"] == "uncertain" for row in rows
                    ),
                    "response": RESPONSE,
                    "response_unit": "nanoseconds-per-reduction",
                    "predictor": predictor,
                    "predictor_kind": "source-model" if predictor != "W_fb" else "formal-coefficient-work",
                    "spearman_rho": "NA" if rho is None else f"{rho:.9g}",
                }
            )
    return output


def diagnostic_rows(
    samples: list[dict[str, object]], threshold: float
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    factors = (
        ("logical-access-proxy", "access_regime"),
        ("feedback-stage-barriers", "stage_regime"),
        ("word-alignment", "alignment_regime"),
    )
    by_m: dict[int, list[dict[str, object]]] = defaultdict(list)
    for sample in samples:
        by_m[int(sample["m"])].append(sample)
    for m, m_rows in sorted(by_m.items()):
        for factor, field in factors:
            regimes: dict[str, list[dict[str, object]]] = defaultdict(list)
            for row in m_rows:
                regimes[str(row[field])].append(row)
            for regime, rows in sorted(regimes.items()):
                residuals = [float(row["relative_residual"]) for row in rows]
                median_bias = statistics.median(residuals)
                median_absolute = statistics.median(abs(value) for value in residuals)
                if len(rows) < 3:
                    status = "insufficient-samples"
                elif abs(median_bias) > threshold or median_absolute > threshold:
                    status = "simple-xor-model-mismatch"
                else:
                    status = "no-large-mismatch-detected"
                output.append(
                    {
                        "m": m,
                        "factor": factor,
                        "regime": regime,
                        "samples": len(rows),
                        "uncertain_samples": sum(
                            row["timing_status"] == "uncertain" for row in rows
                        ),
                        "residual_definition": "LOSO-affine-GS_source_word_xors",
                        "median_relative_residual": f"{median_bias:.9g}",
                        "median_absolute_relative_residual": f"{median_absolute:.9g}",
                        "diagnostic_threshold": f"{threshold:.9g}",
                        "status": status,
                        "causal_claim": "none-source-proxy-only",
                    }
                )
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--correlations", type=Path, required=True)
    parser.add_argument("--residuals", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--min-trials", type=int, default=31)
    parser.add_argument("--min-batch-repeats", type=int, default=12)
    parser.add_argument("--min-warmup-runs", type=int, default=1)
    parser.add_argument("--mismatch-threshold", type=float, default=0.10)
    args = parser.parse_args()
    if (
        args.min_trials <= 0 or args.min_batch_repeats <= 0
        or args.min_warmup_runs < 0
    ):
        raise ValueError(
            "trial/batch minima must be positive and warm-up nonnegative"
        )
    if not 0 < args.mismatch_threshold < 1:
        raise ValueError("mismatch-threshold must lie strictly between zero and one")

    samples = load_samples(
        args.input, args.min_trials, args.min_batch_repeats,
        args.min_warmup_runs
    )
    leave_one_out_residuals(samples)
    correlations = correlation_rows(samples)
    diagnostics = diagnostic_rows(samples, args.mismatch_threshold)
    residual_fields = [
        "support_id", "source_sample_ids", "sample_instances", "m",
        "word_bits", "taps", "trial_count", RESPONSE,
        "GS_ns_ci95_low", "GS_ns_ci95_high", "GS_ns_relative_half_width",
        "timing_status",
        "predictor", "GS_source_word_xors", "predicted_GS_ns", "residual_ns",
        "relative_residual", "feedback_stages",
        "GS_source_logical_word_accesses", "GS_source_scratch_words",
        "GS_source_aligned_word_contributions",
        "GS_source_cross_word_contributions", "access_regime", "stage_regime",
        "alignment_regime",
    ]
    write_csv(args.correlations, correlations)
    write_csv(
        args.residuals,
        [{field: row[field] for field in residual_fields} for row in samples],
    )
    write_csv(args.diagnostics, diagnostics)
    print(
        f"analyzed {len(samples)} supports across "
        f"{len({int(row['m']) for row in samples})} fixed-m panels; "
        f"response={RESPONSE}, source model={COST_MODEL}"
    )


if __name__ == "__main__":
    main()
