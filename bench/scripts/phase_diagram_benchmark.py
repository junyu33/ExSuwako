"""Collect exact or random per-support reduction points for a phase diagram."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


CURRENT_INPUT_DISTRIBUTION = "uniform-full-range:v1"
CURRENT_TIMING_SCOPE = "reduction-steady-state:v1"
CURRENT_SETUP_SCOPE = "modulus-plan:v1"
CURRENT_TIMING_ORDER = "cyclic-method-rotation:v1"
CURRENT_AGGREGATION = "median-of-trial-medians:no-outlier-removal:v1"
CURRENT_GS_SOURCE_COST_MODEL = "scalar-source-v1"
CURRENT_PLAN_STORAGE_MODEL = "requested-owned-bytes:v1"
CURRENT_METADATA_SCHEMA = "exsuwako-native-platform:v1"
METADATA_FIELDS = (
    "git_commit", "git_dirty", "compiler_path", "compiler_version",
    "compiler_flags", "gf2x_library", "binary_sha256", "platform",
    "machine", "hostname", "cpu_affinity", "frequency_policy",
    "implementation", "multiplication_backend",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_run_metadata(
    path: Path | None, paper_grade: bool, binary: Path
) -> dict[str, object]:
    if path is None:
        if paper_grade:
            raise ValueError("--paper-grade requires --metadata")
        return {
            "metadata_status": "exploratory",
            "metadata_schema": "",
            **{field: "" for field in METADATA_FIELDS},
        }
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    if value.get("metadata_schema") != CURRENT_METADATA_SCHEMA:
        raise ValueError("unexpected benchmark metadata schema")
    missing = [field for field in METADATA_FIELDS if field not in value]
    if missing:
        raise ValueError(f"metadata is missing fields: {', '.join(missing)}")
    if not isinstance(value["cpu_affinity"], int) or value["cpu_affinity"] < 0:
        raise ValueError("metadata cpu_affinity must be a nonnegative integer")
    for field in METADATA_FIELDS:
        if field not in ("git_dirty", "cpu_affinity", "frequency_policy"):
            if not isinstance(value[field], str) or not value[field]:
                raise ValueError(f"metadata field {field} must be nonempty")
    if not isinstance(value["git_dirty"], bool):
        raise ValueError("metadata git_dirty must be boolean")
    if not isinstance(value["frequency_policy"], dict) or not value["frequency_policy"]:
        raise ValueError("metadata frequency_policy must be a nonempty object")
    if paper_grade and value["git_dirty"]:
        raise ValueError("paper-grade benchmark requires a clean commit")
    if paper_grade:
        repository = Path(__file__).resolve().parents[2]
        current_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repository, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        if dirty or value["git_commit"] != current_commit:
            raise ValueError(
                "paper-grade metadata does not describe the clean current commit"
            )
        if value["binary_sha256"] != file_sha256(binary):
            raise ValueError("paper-grade metadata does not match the benchmark binary")
    result: dict[str, object] = {
        "metadata_status": "paper-grade" if paper_grade else "recorded-exploratory",
        "metadata_schema": CURRENT_METADATA_SCHEMA,
    }
    for field in METADATA_FIELDS:
        item = value[field]
        result[field] = (
            json.dumps(item, sort_keys=True, separators=(",", ":"))
            if isinstance(item, dict) else int(item) if isinstance(item, bool) else item
        )
    return result


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
    row: dict[str, object], m: int, taps: list[int],
    *, expect_dense: bool, expect_lopez_dahab: bool,
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
    if dense_enabled != int(expect_dense):
        raise RuntimeError("benchmark emitted an unexpected dense-baseline state")
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
    if ld_enabled != int(expect_lopez_dahab):
        raise RuntimeError(
            "benchmark emitted an unexpected loop Lopez-Dahab state"
        )
    if ld_enabled:
        if ld_bytes <= 0 or ld_setup < 0 or ld_ns <= 0 or ld_ratio <= 0:
            raise RuntimeError(
                "enabled loop Lopez-Dahab emitted invalid measurements"
            )
    elif any(value != 0 for value in (ld_bytes, ld_setup, ld_ns, ld_ratio)):
        raise RuntimeError("disabled loop Lopez-Dahab emitted nonzero fields")


def add_derived_fields(
    row: dict[str, object], sample_id: str, provenance: str,
    m: int, taps: list[int], *, with_dense: bool, with_lopez_dahab: bool,
) -> None:
    validate_benchmark_geometry(
        row, m, taps, expect_dense=with_dense,
        expect_lopez_dahab=with_lopez_dahab,
    )
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
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--no-naive", action="store_true")
    parser.add_argument("--with-dense", action="store_true")
    parser.add_argument("--with-lopez-dahab", action="store_true")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--paper-grade", action="store_true")
    parser.add_argument(
        "--resume", action="store_true",
        help="retain complete manifest samples from an existing output",
    )
    args = parser.parse_args()

    if args.inputs <= 0 or args.repeats <= 0:
        raise ValueError("inputs and repeats must be positive")
    if args.warmup_runs < 0 or args.measurement_trials <= 0:
        raise ValueError(
            "warmup-runs must be nonnegative and measurement-trials positive"
        )
    if args.with_dense and not args.no_naive:
        raise ValueError("--with-dense requires --no-naive")
    if args.with_lopez_dahab and not args.no_naive:
        raise ValueError("--with-lopez-dahab requires --no-naive")
    if args.with_lopez_dahab and args.with_dense:
        raise ValueError("--with-lopez-dahab and --with-dense are mutually exclusive")
    if args.with_lopez_dahab and args.manifest is None:
        raise ValueError("--with-lopez-dahab requires an exact-support manifest")
    if args.resume and args.manifest is None:
        raise ValueError("--resume requires an exact-support manifest")

    run_metadata = load_run_metadata(
        args.metadata, args.paper_grade, args.binary.resolve()
    )
    if args.metadata is not None:
        try:
            os.sched_setaffinity(0, {int(run_metadata["cpu_affinity"])})
        except (AttributeError, OSError) as error:
            raise RuntimeError("could not enforce the recorded CPU affinity") from error

    manifest_entries = (
        load_manifest(args.manifest) if args.manifest is not None else None
    )
    rng = random.Random(args.seed)
    rows: list[dict[str, object]] = []
    fields = [
        "sample_id",
        "provenance",
        "metadata_status",
        "metadata_schema",
        *METADATA_FIELDS,
        "driver_command",
        "benchmark_command",
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

    driver_argv = [value for value in sys.argv if value != "--resume"]
    driver_command = shlex.join(driver_argv)

    def save_rows() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def append_rows(new_rows: list[dict[str, object]]) -> None:
        with args.output.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writerows(new_rows)

    def expanded_command(command: list[str]) -> list[str]:
        command = list(command)
        if args.no_naive:
            command.append("no-naive")
        if args.with_dense:
            command.append("with-dense")
        if args.with_lopez_dahab:
            command.append("with-lopez-dahab")
        return command

    def run(command: list[str]) -> list[dict[str, str]]:
        command = expanded_command(command)
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

    def exact_measured_runs(
        command: list[str],
    ) -> tuple[list[tuple[int, dict[str, str]]], list[str]]:
        total_trials = args.warmup_runs + args.measurement_trials
        measured_command = [*command, f"trials={total_trials}"]
        parsed = run(measured_command)
        if len(parsed) != total_trials:
            raise RuntimeError(
                f"expected {total_trials} batched exact-trial rows"
            )
        result: list[tuple[int, dict[str, str]]] = []
        for row in parsed[args.warmup_runs:]:
            try:
                native_trial = int(row["sample"])
            except (KeyError, ValueError) as error:
                raise RuntimeError("exact benchmark emitted an invalid trial index") from error
            trial = native_trial - args.warmup_runs
            row["sample"] = str(trial)
            result.append((trial, row))
        if sorted(trial for trial, _ in result) != list(
            range(args.measurement_trials)
        ):
            raise RuntimeError("exact benchmark emitted incomplete trial indices")
        return result, measured_command

    def add_measurement_fields(
        row: dict[str, object], trial: int, command: list[str]
    ) -> None:
        row.update(run_metadata)
        row["driver_command"] = driver_command
        row["benchmark_command"] = shlex.join(expanded_command(command))
        row["aggregation"] = CURRENT_AGGREGATION
        row["inputs"] = args.inputs
        row["batch_repeats"] = args.repeats
        row["warmup_runs"] = args.warmup_runs
        row["measurement_trials"] = args.measurement_trials
        row["measurement_trial"] = trial

    completed_samples: set[str] = set()
    if args.resume and args.output.exists():
        assert manifest_entries is not None
        with args.output.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != fields:
                raise ValueError("existing output has an incompatible CSV schema")
            existing_rows = list(reader)
        entries_by_id = {entry["sample_id"]: entry for entry in manifest_entries}
        grouped: dict[str, list[dict[str, object]]] = {}
        expected_contract = {
            "metadata_status": run_metadata["metadata_status"],
            "metadata_schema": run_metadata["metadata_schema"],
            **run_metadata,
            "driver_command": driver_command,
            "input_distribution": CURRENT_INPUT_DISTRIBUTION,
            "timing_scope": CURRENT_TIMING_SCOPE,
            "setup_scope": CURRENT_SETUP_SCOPE,
            "timing_order": CURRENT_TIMING_ORDER,
            "aggregation": CURRENT_AGGREGATION,
            "inputs": args.inputs,
            "batch_repeats": args.repeats,
            "warmup_runs": args.warmup_runs,
            "measurement_trials": args.measurement_trials,
            "Dense_enabled": int(args.with_dense),
            "LopezDahabLoop_enabled": int(args.with_lopez_dahab),
        }
        for existing in existing_rows:
            sample_id = existing["sample_id"]
            if sample_id not in entries_by_id:
                raise ValueError(
                    f"existing output contains unknown sample {sample_id!r}"
                )
            entry = entries_by_id[sample_id]
            expected_entry = {
                "provenance": entry["provenance"],
                "m": entry["m"],
                "taps": serialized_taps(entry["taps"]),
            }
            for field, expected in {**expected_contract, **expected_entry}.items():
                if existing[field] != str(expected):
                    raise ValueError(
                        f"existing output has incompatible {field} for "
                        f"sample {sample_id!r}"
                    )
            grouped.setdefault(sample_id, []).append(existing)
        rows = []
        for sample_id, sample_rows in grouped.items():
            try:
                indices = [int(str(row["measurement_trial"])) for row in sample_rows]
            except ValueError as error:
                raise ValueError("existing output has an invalid trial index") from error
            if len(indices) == args.measurement_trials and sorted(indices) == list(
                range(args.measurement_trials)
            ):
                rows.extend(sample_rows)
                completed_samples.add(sample_id)
            elif len(set(indices)) != len(indices) or any(
                index < 0 or index >= args.measurement_trials for index in indices
            ):
                raise ValueError(
                    f"existing output has invalid trials for sample {sample_id!r}"
                )
        save_rows()
        rows = []
    else:
        save_rows()

    if manifest_entries is not None:
        for entry in manifest_entries:
            c_seed = rng.getrandbits(64) or 1
            if entry["sample_id"] in completed_samples:
                continue
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
            measured, measured_command = exact_measured_runs(command)
            support_rows: list[dict[str, object]] = []
            for trial, parsed_row in measured:
                row: dict[str, object] = dict(parsed_row)
                row["seed"] = c_seed
                add_derived_fields(
                    row, entry["sample_id"], entry["provenance"],
                    entry["m"], taps, with_dense=args.with_dense,
                    with_lopez_dahab=args.with_lopez_dahab,
                )
                add_measurement_fields(row, trial, measured_command)
                support_rows.append(row)
                print(
                    f"sample={entry['sample_id']} trial={trial} m={row['m']} "
                    f"taps={row['taps']} serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
                    flush=True,
                )
            append_rows(support_rows)
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
            support_rows = []
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
                    args.m, taps, with_dense=args.with_dense,
                    with_lopez_dahab=args.with_lopez_dahab,
                )
                add_measurement_fields(row, trial, command)
                support_rows.append(row)
                print(
                    f"sample={sample_id} trial={trial} "
                    f"delta={row['Delta_min']} "
                    f"serial/GS={row['Serial/GS']} "
                    f"barrett/GS={row['BarrettGF2X/GS']}",
                    flush=True,
                )
            append_rows(support_rows)


if __name__ == "__main__":
    main()
