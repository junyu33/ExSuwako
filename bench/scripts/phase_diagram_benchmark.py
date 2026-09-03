"""Collect exact or random per-support reduction points for a phase diagram."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
from pathlib import Path
from typing import Any


CURRENT_INPUT_DISTRIBUTION = "uniform-full-range:v1"
CURRENT_TIMING_SCOPE = "reduction-steady-state:v1"
CURRENT_SETUP_SCOPE = "modulus-plan:v1"
CURRENT_TIMING_ORDER = "cyclic-method-rotation:v1"
CURRENT_AGGREGATION = "median-of-trial-medians:no-outlier-removal:v1"
CURRENT_GS_SOURCE_COST_MODEL = "scalar-source-v1"
CURRENT_PLAN_STORAGE_MODEL = "requested-owned-bytes:v1"


def validate_manifest_entry(value: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"manifest line {line_number}: expected a JSON object")
    sample_id = value.get("sample_id")
    provenance = value.get("provenance")
    m = value.get("m")
    taps = value.get("taps")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError(f"manifest line {line_number}: invalid sample_id")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError(f"manifest line {line_number}: invalid provenance")
    if isinstance(m, bool) or not isinstance(m, int) or m <= 0:
        raise ValueError(f"manifest line {line_number}: m must be positive")
    if not isinstance(taps, list):
        raise ValueError(f"manifest line {line_number}: taps must be a list")
    previous = -1
    for tap in taps:
        if isinstance(tap, bool) or not isinstance(tap, int):
            raise ValueError(
                f"manifest line {line_number}: tap exponents must be integers"
            )
        if tap < 0 or tap >= m:
            raise ValueError(
                f"manifest line {line_number}: tap {tap} is outside [0, {m})"
            )
        if tap <= previous:
            raise ValueError(
                f"manifest line {line_number}: taps must be strictly increasing"
            )
        previous = tap
    return value


def load_manifest(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"manifest line {line_number}: invalid JSON: {error.msg}"
                ) from error
            entry = validate_manifest_entry(value, line_number)
            sample_id = entry["sample_id"]
            if sample_id in sample_ids:
                raise ValueError(
                    f"manifest line {line_number}: duplicate sample_id {sample_id!r}"
                )
            sample_ids.add(sample_id)
            entries.append(entry)
    if not entries:
        raise ValueError("manifest contains no entries")
    return entries


def exact_tap_argument(taps: list[int]) -> str:
    return ",".join(str(tap) for tap in taps) if taps else "-"


def serialized_taps(taps: list[int]) -> str:
    return ";".join(str(tap) for tap in taps) if taps else "-"


def parse_serialized_taps(value: str, m: int) -> list[int]:
    if value == "-":
        return []
    try:
        taps = [int(tap) for tap in value.split(";")]
    except ValueError as error:
        raise RuntimeError(f"benchmark emitted invalid taps: {value!r}") from error
    previous = -1
    for tap in taps:
        if tap < 0 or tap >= m or tap <= previous:
            raise RuntimeError(
                f"benchmark emitted noncanonical taps for m={m}: {value!r}"
            )
        previous = tap
    return taps


def derive_geometry(m: int, taps: list[int]) -> dict[str, object]:
    if not taps:
        delta_min: int | None = None
    else:
        delta_min = min(m - tap for tap in taps)

    active_counts: list[int] = []
    scheduled_work = 0
    scale = 1
    while True:
        active = [m - tap for tap in taps if scale * (m - tap) < m]
        if not active:
            break
        active_counts.append(len(active))
        scheduled_work += sum(m - scale * distance for distance in active)
        scale *= 2

    return {
        "s": len(taps),
        "h": len(taps) + 1,
        "Delta_min": "NA" if delta_min is None else delta_min,
        "log2_m_over_delta": (
            "" if delta_min is None else math.log2(m / delta_min)
        ),
        "feedback_stages": len(active_counts),
        "active_tap_counts": (
            ";".join(str(count) for count in active_counts)
            if active_counts
            else "-"
        ),
        "feedback_active_tap_sum": sum(active_counts),
        "W_fb": scheduled_work,
    }


def derive_gs_source_cost(
    m: int, taps: list[int], word_bits: int
) -> dict[str, object]:
    """Independently emulate the documented scalar-source-v1 loop model."""
    state_words = (m + word_bits - 1) // word_bits
    input_words = (2 * m + word_bits - 1) // word_bits
    cost = {
        "GS_source_aligned_word_contributions": 0,
        "GS_source_cross_word_contributions": 0,
        "GS_source_word_shifts": 0,
        "GS_source_word_xors": 0,
        "GS_source_logical_word_reads": 0,
        "GS_source_logical_word_writes": 0,
        "GS_source_scratch_words": state_words + 1,
    }

    extract_word_offset, extract_bit_offset = divmod(m, word_bits)
    for dst in range(state_words):
        source = dst + extract_word_offset
        if source < input_words:
            cost["GS_source_logical_word_reads"] += 1
            cost["GS_source_word_shifts"] += extract_bit_offset != 0
        if extract_bit_offset != 0 and source + 1 < input_words:
            cost["GS_source_logical_word_reads"] += 1
            cost["GS_source_word_shifts"] += 1
            cost["GS_source_word_xors"] += 1
        cost["GS_source_logical_word_writes"] += 1
    cost["GS_source_logical_word_writes"] += 1

    factor = 1
    while True:
        shifts = sorted(
            factor * (m - tap)
            for tap in taps
            if tap != 0 and factor * (m - tap) < m
        )
        if not shifts:
            break
        descriptors = [divmod(shift, word_bits) for shift in shifts]
        affected_words = (m - shifts[0] + word_bits - 1) // word_bits
        all_aligned = all(bit_offset == 0 for _, bit_offset in descriptors)
        for dst in range(affected_words):
            cost["GS_source_logical_word_reads"] += 1
            cost["GS_source_logical_word_writes"] += 1
            if all_aligned:
                for word_offset, _ in descriptors:
                    if word_offset >= state_words - dst:
                        break
                    cost["GS_source_aligned_word_contributions"] += 1
                    cost["GS_source_logical_word_reads"] += 1
                    cost["GS_source_word_xors"] += 1
                continue

            index = 0
            while index < len(descriptors):
                word_offset = descriptors[index][0]
                if word_offset >= state_words - dst:
                    break
                cost["GS_source_logical_word_reads"] += 2
                while (
                    index < len(descriptors)
                    and descriptors[index][0] == word_offset
                ):
                    bit_offset = descriptors[index][1]
                    if bit_offset == 0:
                        cost["GS_source_aligned_word_contributions"] += 1
                    else:
                        cost["GS_source_cross_word_contributions"] += 1
                        cost["GS_source_word_shifts"] += 2
                    cost["GS_source_word_xors"] += 2
                    index += 1
        factor *= 2

    descriptors = sorted(divmod(tap, word_bits) for tap in taps)
    all_aligned = all(bit_offset == 0 for _, bit_offset in descriptors)
    for dst in range(state_words):
        cost["GS_source_logical_word_reads"] += 1
        cost["GS_source_logical_word_writes"] += 1
        if all_aligned:
            for word_offset, _ in descriptors:
                if word_offset > dst:
                    break
                src = dst - word_offset
                if src < state_words:
                    cost["GS_source_aligned_word_contributions"] += 1
                    cost["GS_source_logical_word_reads"] += 1
                    cost["GS_source_word_xors"] += 1
            continue

        index = 0
        while index < len(descriptors):
            word_offset = descriptors[index][0]
            if word_offset > dst:
                break
            src = dst - word_offset
            if src >= state_words:
                index += 1
                continue
            cost["GS_source_logical_word_reads"] += 1 + (src > 0)
            while (
                index < len(descriptors)
                and descriptors[index][0] == word_offset
            ):
                bit_offset = descriptors[index][1]
                if bit_offset == 0:
                    cost["GS_source_aligned_word_contributions"] += 1
                    cost["GS_source_word_xors"] += 1
                else:
                    cost["GS_source_cross_word_contributions"] += 1
                    cost["GS_source_word_shifts"] += 2
                    cost["GS_source_word_xors"] += 2
                index += 1

    if m % word_bits != 0:
        cost["GS_source_logical_word_reads"] += 1
        cost["GS_source_logical_word_writes"] += 1
    return {"GS_source_cost_model": CURRENT_GS_SOURCE_COST_MODEL, **cost}


def validate_benchmark_geometry(
    row: dict[str, object], m: int, taps: list[int]
) -> None:
    geometry = derive_geometry(m, taps)
    try:
        word_bits = int(str(row.get("word_bits")))
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            f"benchmark emitted invalid word_bits: {row.get('word_bits')!r}"
        ) from error
    if word_bits <= 0:
        raise RuntimeError(f"benchmark emitted invalid word_bits: {word_bits}")
    source_cost = derive_gs_source_cost(m, taps, word_bits)
    expected = {
        "m": str(m),
        "s": str(geometry["s"]),
        "h": str(geometry["h"]),
        "taps": serialized_taps(taps),
        "Delta_min": str(geometry["Delta_min"]),
        "feedback_stages": str(geometry["feedback_stages"]),
        "active_tap_counts": str(geometry["active_tap_counts"]),
        "feedback_active_tap_sum": str(geometry["feedback_active_tap_sum"]),
        "W_fb": str(geometry["W_fb"]),
        **{field: str(value) for field, value in source_cost.items()},
    }
    for field, value in expected.items():
        if str(row.get(field)) != value:
            raise RuntimeError(
                f"benchmark geometry mismatch for {field}: "
                f"expected {value!r}, got {row.get(field)!r}"
            )
    if row.get("input_distribution") != CURRENT_INPUT_DISTRIBUTION:
        raise RuntimeError(
            "benchmark emitted an unexpected input distribution: "
            f"{row.get('input_distribution')!r}"
        )
    if row.get("timing_scope") != CURRENT_TIMING_SCOPE:
        raise RuntimeError(
            "benchmark emitted an unexpected timing scope: "
            f"{row.get('timing_scope')!r}"
        )
    if row.get("setup_scope") != CURRENT_SETUP_SCOPE:
        raise RuntimeError(
            "benchmark emitted an unexpected setup scope: "
            f"{row.get('setup_scope')!r}"
        )
    if row.get("plan_storage_model") != CURRENT_PLAN_STORAGE_MODEL:
        raise RuntimeError(
            "benchmark emitted an unexpected plan-storage model: "
            f"{row.get('plan_storage_model')!r}"
        )
    if row.get("timing_order") != CURRENT_TIMING_ORDER:
        raise RuntimeError(
            "benchmark emitted an unexpected timing order: "
            f"{row.get('timing_order')!r}"
        )
    for field in [
        "GS_setup_ns", "Serial_setup_ns", "Naive_setup_ns",
        "BarrettGF2X_setup_ns", "Dense_setup_ns",
        "LopezDahabLoop_setup_ns",
    ]:
        try:
            value = float(str(row.get(field)))
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"benchmark emitted invalid setup timing for {field}: "
                f"{row.get(field)!r}"
            ) from error
        if value < 0:
            raise RuntimeError(
                f"benchmark emitted negative setup timing for {field}: {value}"
            )
    for field in [
        "GS_plan_bytes", "Serial_plan_bytes", "BarrettGF2X_plan_bytes"
    ]:
        try:
            value = int(str(row.get(field)))
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"benchmark emitted invalid plan storage for {field}: "
                f"{row.get(field)!r}"
            ) from error
        if value <= 0:
            raise RuntimeError(
                f"benchmark emitted nonpositive plan storage for {field}: {value}"
            )
    try:
        naive_bytes = int(str(row.get("Naive_plan_bytes")))
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "benchmark emitted invalid plan storage for Naive_plan_bytes: "
            f"{row.get('Naive_plan_bytes')!r}"
        ) from error
    if naive_bytes < 0:
        raise RuntimeError(
            f"benchmark emitted negative Naive plan storage: {naive_bytes}"
        )
    try:
        dense_enabled = int(str(row.get("Dense_enabled")))
        dense_limit = int(str(row.get("Dense_matrix_limit_bytes")))
        dense_bytes = int(str(row.get("Dense_plan_bytes")))
        dense_setup = float(str(row.get("Dense_setup_ns")))
        dense_ns = float(str(row.get("Dense_ns")))
        dense_ratio = float(str(row.get("Dense/GS")))
    except (TypeError, ValueError) as error:
        raise RuntimeError("benchmark emitted invalid dense-baseline fields") from error
    if dense_enabled not in (0, 1) or dense_limit <= 0:
        raise RuntimeError("benchmark emitted invalid dense-baseline metadata")
    if dense_enabled:
        if (
            dense_bytes <= 0
            or dense_setup < 0
            or dense_ns <= 0
            or dense_ratio <= 0
        ):
            raise RuntimeError("enabled dense baseline emitted invalid measurements")
    elif any(
        value != 0
        for value in (dense_bytes, dense_setup, dense_ns, dense_ratio)
    ):
        raise RuntimeError("disabled dense baseline emitted nonzero measurements")
    try:
        generated_enabled = int(str(row.get("Generated_enabled")))
        generated_bytes = int(str(row.get("Generated_plan_bytes")))
        generated_setup = float(str(row.get("Generated_setup_ns")))
        generated_ns = float(str(row.get("Generated_ns")))
        generated_ratio = float(str(row.get("Generated/GS")))
    except (TypeError, ValueError) as error:
        raise RuntimeError("benchmark emitted invalid generated fields") from error
    if generated_enabled != 0:
        raise RuntimeError("phase driver does not accept generated plugins")
    if any(
        value != 0
        for value in (
            generated_bytes, generated_setup, generated_ns, generated_ratio
        )
    ):
        raise RuntimeError("disabled generated reducer emitted nonzero fields")
    try:
        ld_enabled = int(str(row.get("LopezDahabLoop_enabled")))
        ld_bytes = int(str(row.get("LopezDahabLoop_plan_bytes")))
        ld_setup = float(str(row.get("LopezDahabLoop_setup_ns")))
        ld_ns = float(str(row.get("LopezDahabLoop_ns")))
        ld_ratio = float(str(row.get("LopezDahabLoop/GS")))
    except (TypeError, ValueError) as error:
        raise RuntimeError("benchmark emitted invalid loop Lopez-Dahab fields") from error
    if ld_enabled != 0:
        raise RuntimeError("phase driver does not enable loop Lopez-Dahab")
    if any(value != 0 for value in (ld_bytes, ld_setup, ld_ns, ld_ratio)):
        raise RuntimeError("disabled loop Lopez-Dahab emitted nonzero fields")


def add_derived_fields(
    row: dict[str, object], sample_id: str, provenance: str,
    m: int, taps: list[int]
) -> None:
    validate_benchmark_geometry(row, m, taps)
    row["sample_id"] = sample_id
    row["provenance"] = provenance
    row.update(derive_geometry(m, taps))
    row.update(derive_gs_source_cost(m, taps, int(str(row["word_bits"]))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--m", type=int, default=1 << 20)
    parser.add_argument(
        "--s",
        type=int,
        nargs="+",
        default=[8, 16, 32, 64, 96, 128, 160, 192, 256, 320, 384, 448, 512],
    )
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--inputs", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup-runs", type=int, default=0)
    parser.add_argument("--measurement-trials", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-naive", action="store_true")
    parser.add_argument("--with-dense", action="store_true")
    args = parser.parse_args()

    if args.inputs <= 0 or args.repeats <= 0:
        raise ValueError("inputs and repeats must be positive")
    if args.warmup_runs < 0 or args.measurement_trials <= 0:
        raise ValueError(
            "warmup-runs must be nonnegative and measurement-trials positive"
        )
    if args.with_dense and not args.no_naive:
        raise ValueError("--with-dense requires --no-naive")

    rng = random.Random(args.seed)
    rows: list[dict[str, object]] = []
    fields = [
        "sample_id",
        "provenance",
        "m",
        "word_bits",
        "s",
        "h",
        "taps",
        "Delta_min",
        "log2_m_over_delta",
        "feedback_stages",
        "active_tap_counts",
        "feedback_active_tap_sum",
        "W_fb",
        "GS_source_cost_model",
        "GS_source_aligned_word_contributions",
        "GS_source_cross_word_contributions",
        "GS_source_word_shifts",
        "GS_source_word_xors",
        "GS_source_logical_word_reads",
        "GS_source_logical_word_writes",
        "GS_source_scratch_words",
        "plan_storage_model",
        "GS_plan_bytes",
        "Serial_plan_bytes",
        "Naive_plan_bytes",
        "BarrettGF2X_plan_bytes",
        "Dense_plan_bytes",
        "Dense_enabled",
        "Dense_matrix_limit_bytes",
        "Generated_plan_bytes",
        "Generated_enabled",
        "LopezDahabLoop_plan_bytes",
        "LopezDahabLoop_enabled",
        "input_distribution",
        "timing_scope",
        "setup_scope",
        "timing_order",
        "aggregation",
        "inputs",
        "batch_repeats",
        "warmup_runs",
        "measurement_trials",
        "measurement_trial",
        "GS_setup_ns",
        "Serial_setup_ns",
        "Naive_setup_ns",
        "BarrettGF2X_setup_ns",
        "Dense_setup_ns",
        "Generated_setup_ns",
        "LopezDahabLoop_setup_ns",
        "GS_ns",
        "Serial_ns",
        "Naive_ns",
        "BarrettGF2X_ns",
        "Dense_ns",
        "Generated_ns",
        "LopezDahabLoop_ns",
        "Serial/GS",
        "Naive/GS",
        "BarrettGF2X/GS",
        "Dense/GS",
        "Generated/GS",
        "LopezDahabLoop/GS",
        "sample",
        "seed",
    ]

    def save_rows() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def run(command: list[str]) -> list[dict[str, str]]:
        if args.no_naive:
            command.append("no-naive")
        if args.with_dense:
            command.append("with-dense")
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        return list(csv.DictReader(completed.stdout.splitlines()))

    def measured_runs(command: list[str]) -> list[tuple[int, dict[str, str]]]:
        for _ in range(args.warmup_runs):
            run(list(command))
        result: list[tuple[int, dict[str, str]]] = []
        for trial in range(args.measurement_trials):
            for row in run(list(command)):
                result.append((trial, row))
        return result

    def add_measurement_fields(row: dict[str, object], trial: int) -> None:
        row["aggregation"] = CURRENT_AGGREGATION
        row["inputs"] = args.inputs
        row["batch_repeats"] = args.repeats
        row["warmup_runs"] = args.warmup_runs
        row["measurement_trials"] = args.measurement_trials
        row["measurement_trial"] = trial

    if args.manifest is not None:
        for entry in load_manifest(args.manifest):
            c_seed = rng.getrandbits(64) or 1
            taps = entry["taps"]
            command = [
                str(args.binary),
                "--taps",
                exact_tap_argument(taps),
                str(args.inputs),
                str(args.repeats),
                str(entry["m"]),
                hex(c_seed),
            ]
            measured = measured_runs(command)
            if len(measured) != args.measurement_trials:
                raise RuntimeError(
                    f"expected {args.measurement_trials} rows for sample "
                    f"{entry['sample_id']!r}"
                )
            for trial, parsed_row in measured:
                row: dict[str, object] = dict(parsed_row)
                row["seed"] = c_seed
                add_derived_fields(
                    row, entry["sample_id"], entry["provenance"],
                    entry["m"], taps
                )
                add_measurement_fields(row, trial)
                rows.append(row)
                print(
                    f"sample={entry['sample_id']} trial={trial} m={row['m']} "
                    f"taps={row['taps']} serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
                    flush=True,
                )
                save_rows()
    else:
        for s in args.s:
            if not 0 <= s <= args.m:
                raise ValueError(f"invalid support size {s} for m={args.m}")
            c_seed = rng.getrandbits(64) or 1
            command = [
                str(args.binary),
                str(args.samples),
                str(args.inputs),
                str(args.repeats),
                str(args.m),
                str(s),
                hex(c_seed),
            ]
            measured = measured_runs(command)
            if len(measured) != args.samples * args.measurement_trials:
                raise RuntimeError(
                    f"expected {args.samples * args.measurement_trials} "
                    f"rows for s={s}"
                )
            for trial, parsed_row in measured:
                row = dict(parsed_row)
                row["seed"] = c_seed
                taps = parse_serialized_taps(str(row["taps"]), args.m)
                sample_id = (
                    f"random-m{args.m}-s{s}-seed{c_seed:016x}-"
                    f"sample{row['sample']}"
                )
                add_derived_fields(
                    row, sample_id, "synthetic-fixed-weight-uniform:v1",
                    args.m, taps
                )
                add_measurement_fields(row, trial)
                rows.append(row)
                print(
                    f"sample={sample_id} trial={trial} "
                    f"delta={row['Delta_min']} "
                    f"serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
                    flush=True,
                )
            save_rows()


if __name__ == "__main__":
    main()
