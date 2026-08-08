"""Generate and verify CNOT resource counts for binary reduction shears.

The experiment compares a direct dense high-to-low reduction shear with two
explicit zero-ancilla constructions for the two-cluster family documented in
paper/raw/cnot_4.md: a sequential suffix scan and an in-place Brent--Kung
parallel-prefix scan.  Every reported structured circuit is checked both at
the scan level and on a basis of the complete clean reduction shear.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, TextIO


Gate = tuple[int, int]
Layer = list[Gate]


@dataclass(frozen=True)
class Modulus:
    name: str
    m: int
    taps: tuple[int, ...]
    delta: int | None = None
    remote_taps: tuple[int, ...] = ()

    @property
    def polynomial(self) -> int:
        value = 1 << self.m
        for tap in self.taps:
            value |= 1 << tap
        return value


MODULI = (
    Modulus("nist_163", 163, (7, 6, 3, 0)),
    Modulus("cluster_163", 163, (162, 25, 1, 0), 1, (25, 1)),
    Modulus("nist_233", 233, (74, 0)),
    Modulus("cluster_233", 233, (232, 15, 1, 0), 1, (15, 1)),
    Modulus("nist_283", 283, (12, 7, 5, 0)),
    Modulus("cluster_283", 283, (282, 66, 1, 0), 1, (66, 1)),
    Modulus("nist_571", 571, (10, 5, 2, 0)),
    Modulus("cluster_571", 571, (570, 9, 1, 0), 1, (9, 1)),
)


def reduce_polynomial(value: int, modulus: Modulus) -> int:
    while value.bit_length() - 1 >= modulus.m:
        shift = value.bit_length() - 1 - modulus.m
        value ^= modulus.polynomial << shift
    return value


def reduction_columns(modulus: Modulus) -> list[int]:
    """Return columns of F where L <- L + F H is modular reduction."""
    return [
        reduce_polynomial(1 << (modulus.m + j), modulus)
        for j in range(modulus.m)
    ]


def dense_resources(columns: Sequence[int], m: int) -> tuple[int, int]:
    """Return exact size and optimal all-to-all depth of direct shear edges."""
    source_degrees = [column.bit_count() for column in columns]
    target_degrees = [0] * m
    for column in columns:
        bits = column
        while bits:
            low = bits & -bits
            target_degrees[low.bit_length() - 1] += 1
            bits ^= low
    count = sum(source_degrees)
    # The gates form a bipartite graph from H to L.  Its edge-chromatic number
    # equals its maximum degree, so this depth is exact in the all-to-all model.
    depth = max((*source_degrees, *target_degrees), default=0)
    return count, depth


def suffix_scan_gates(
    register_offset: int,
    start: int,
    length: int,
    stride: int,
) -> list[Gate]:
    """Sequentially realize suffix XORs on stride-separated in-place chains."""
    gates: list[Gate] = []
    for residue in range(min(stride, length)):
        chain = list(range(start + residue, start + length, stride))
        for index in range(len(chain) - 1, 0, -1):
            gates.append(
                (register_offset + chain[index],
                 register_offset + chain[index - 1])
            )
    return gates


def brent_kung_prefix_layers(wires: Sequence[int]) -> list[Layer]:
    """Return an in-place inclusive-prefix XOR network on ordered wires.

    Each returned layer consists of pairwise-disjoint CNOTs.  The construction
    is the Brent--Kung upsweep followed by its distribution downsweep.
    """
    length = len(wires)
    if length < 2:
        return []

    levels = (length - 1).bit_length()
    layers: list[Layer] = []

    for level in range(levels):
        half = 1 << level
        step = half << 1
        layer = [
            (wires[index - half], wires[index])
            for index in range(step - 1, length, step)
        ]
        if layer:
            layers.append(layer)

    for level in range(levels - 2, -1, -1):
        half = 1 << level
        step = half << 1
        layer = [
            (wires[index - half], wires[index])
            for index in range(3 * half - 1, length, step)
        ]
        if layer:
            layers.append(layer)

    return layers


def suffix_scan_layers(
    register_offset: int,
    start: int,
    length: int,
    stride: int,
) -> list[Layer]:
    """Realize all stride-separated suffix XORs with parallel prefix scans."""
    chains = [
        list(reversed(range(start + residue, start + length, stride)))
        for residue in range(min(stride, length))
    ]
    networks = [
        brent_kung_prefix_layers(
            [register_offset + index for index in chain]
        )
        for chain in chains
    ]

    # The residue-class chains are disjoint, so layers at equal local depth
    # can be merged without introducing a qubit conflict.
    depth = max((len(network) for network in networks), default=0)
    return [
        [gate for network in networks if layer < len(network)
              for gate in network[layer]]
        for layer in range(depth)
    ]


def inverse_layers(layers: Sequence[Sequence[Gate]]) -> list[Layer]:
    """Invert a layered CNOT circuit."""
    return [list(reversed(layer)) for layer in reversed(layers)]


def flatten_layers(layers: Iterable[Iterable[Gate]]) -> list[Gate]:
    return [gate for layer in layers for gate in layer]


def validate_layers(layers: Sequence[Sequence[Gate]], qubits: int) -> None:
    """Check range and one-gate-per-qubit conflicts in every layer."""
    for layer_index, layer in enumerate(layers):
        occupied: set[int] = set()
        for control, target in layer:
            if not 0 <= control < qubits or not 0 <= target < qubits:
                raise AssertionError(
                    f"layer {layer_index}: gate {(control, target)} outside "
                    f"a {qubits}-qubit circuit"
                )
            if control == target:
                raise AssertionError(
                    f"layer {layer_index}: self-targeting CNOT on {control}"
                )
            if control in occupied or target in occupied:
                raise AssertionError(
                    f"layer {layer_index}: qubit conflict in gate "
                    f"{(control, target)}"
                )
            occupied.add(control)
            occupied.add(target)


def two_cluster_manifest(modulus: Modulus) -> tuple[int, int, tuple[int, ...]]:
    if modulus.delta is None:
        raise ValueError(f"{modulus.name} is not a two-cluster manifest")
    m = modulus.m
    delta = modulus.delta
    remote = modulus.remote_taps
    expected = {m - delta, 0, *remote}
    if set(modulus.taps) != expected:
        raise ValueError(
            f"{modulus.name}: taps do not match delta/remote manifest"
        )
    if not 1 <= delta < m / 2:
        raise ValueError(f"{modulus.name}: delta is outside two-cluster range")
    if any(not 1 <= tap <= m // 2 for tap in remote):
        raise ValueError(f"{modulus.name}: remote tap is outside lower half")
    return m, delta, remote


def two_cluster_gates(modulus: Modulus) -> list[Gate]:
    m, delta, remote = two_cluster_manifest(modulus)

    low_offset = 0
    high_offset = m
    transform: list[Gate] = []

    # P^{-1}: suffix XORs on residue classes modulo delta.
    transform.extend(suffix_scan_gates(high_offset, 0, m, delta))

    # I + T_e: scan the disjoint high source block, copy its suffix parities
    # into the low target block of H, then restore the source block.
    for tap in remote:
        scan = suffix_scan_gates(high_offset, m - tap, tap, delta)
        transform.extend(scan)
        transform.extend(
            (high_offset + m - tap + i, high_offset + i)
            for i in range(tap)
        )
        transform.extend(reversed(scan))

    # V(Y): add the high-state contribution into the low product register.
    assembly: list[Gate] = []
    assembly.extend((high_offset + i, low_offset + i) for i in range(m))
    assembly.extend(
        (high_offset + i, low_offset + i + m - delta)
        for i in range(delta)
    )
    for tap in remote:
        assembly.extend(
            (high_offset + i, low_offset + i + tap)
            for i in range(m - tap)
        )

    # Uncompute the transformed H register after accumulating V(Y).
    return [*transform, *assembly, *reversed(transform)]


def two_cluster_parallel_layers(modulus: Modulus) -> list[Layer]:
    """Return the zero-ancilla two-cluster clean shear in explicit layers."""
    m, delta, remote = two_cluster_manifest(modulus)
    low_offset = 0
    high_offset = m

    transform: list[Layer] = []
    transform.extend(suffix_scan_layers(high_offset, 0, m, delta))

    for tap in remote:
        scan = suffix_scan_layers(high_offset, m - tap, tap, delta)
        transform.extend(scan)
        transform.append([
            (high_offset + m - tap + index, high_offset + index)
            for index in range(tap)
        ])
        transform.extend(inverse_layers(scan))

    assembly: list[Layer] = [
        [(high_offset + index, low_offset + index) for index in range(m)],
        [
            (high_offset + index, low_offset + index + m - delta)
            for index in range(delta)
        ],
    ]
    assembly.extend([
        [
            (high_offset + index, low_offset + index + tap)
            for index in range(m - tap)
        ]
        for tap in remote
    ])

    layers = [*transform, *assembly, *inverse_layers(transform)]
    validate_layers(layers, 2 * m)
    return layers


def apply_gates(state: int, gates: Iterable[Gate]) -> int:
    for control, target in gates:
        if state >> control & 1:
            state ^= 1 << target
    return state


def scheduled_depth(gates: Iterable[Gate], qubits: int) -> int:
    """ASAP depth for the emitted gate order under one-gate-per-qubit layers."""
    last_layer = [0] * qubits
    depth = 0
    for control, target in gates:
        layer = max(last_layer[control], last_layer[target]) + 1
        last_layer[control] = layer
        last_layer[target] = layer
        depth = max(depth, layer)
    return depth


def verify_two_cluster(modulus: Modulus, gates: Sequence[Gate]) -> None:
    columns = reduction_columns(modulus)
    m = modulus.m
    mask = (1 << m) - 1
    for index, expected_low in enumerate(columns):
        output = apply_gates(1 << (m + index), gates)
        actual_low = output & mask
        actual_high = output >> m
        if actual_low != expected_low or actual_high != 1 << index:
            raise AssertionError(
                f"{modulus.name}: basis {index} mismatch: "
                f"low={actual_low:#x}/{expected_low:#x}, "
                f"high={actual_high:#x}/{1 << index:#x}"
            )


def verify_suffix_scan(
    register_offset: int,
    start: int,
    length: int,
    stride: int,
    layers: Sequence[Sequence[Gate]],
) -> None:
    """Basis-verify one parallel suffix scan independently of reduction."""
    gates = flatten_layers(layers)
    for source in range(start, start + length):
        output = apply_gates(1 << (register_offset + source), gates)
        expected = 0
        for target in range(start, source + 1):
            if (source - target) % stride == 0:
                expected |= 1 << (register_offset + target)
        if output != expected:
            raise AssertionError(
                f"suffix scan length={length}, stride={stride}, "
                f"basis={source}: {output:#x} != {expected:#x}"
            )


def verify_parallel_scans(modulus: Modulus) -> None:
    m, delta, remote = two_cluster_manifest(modulus)
    high_offset = m
    verify_suffix_scan(
        high_offset,
        0,
        m,
        delta,
        suffix_scan_layers(high_offset, 0, m, delta),
    )
    for tap in remote:
        verify_suffix_scan(
            high_offset,
            m - tap,
            tap,
            delta,
            suffix_scan_layers(high_offset, m - tap, tap, delta),
        )


def run_internal_checks() -> None:
    """Exercise non-unit strides and dense remote-tap sets at small degrees."""
    for length in range(1, 33):
        for stride in range(1, length + 1):
            layers = suffix_scan_layers(0, 0, length, stride)
            validate_layers(layers, length)
            verify_suffix_scan(0, 0, length, stride, layers)
            longest_chain = (length + stride - 1) // stride
            depth_bound = (
                0 if longest_chain < 2
                else 2 * (longest_chain - 1).bit_length() - 1
            )
            if len(layers) > depth_bound:
                raise AssertionError(
                    f"suffix scan length={length}, stride={stride}: "
                    f"depth {len(layers)} exceeds {depth_bound}"
                )
            if len(flatten_layers(layers)) >= 2 * length:
                raise AssertionError(
                    f"suffix scan length={length}, stride={stride}: "
                    "Brent--Kung size bound failed"
                )

    for m in range(3, 19):
        remote = tuple(range(1, m // 2 + 1))
        for delta in range(1, (m - 1) // 2 + 1):
            modulus = Modulus(
                f"selftest_{m}_{delta}",
                m,
                (m - delta, 0, *remote),
                delta,
                remote,
            )
            layers = two_cluster_parallel_layers(modulus)
            verify_parallel_scans(modulus)
            verify_two_cluster(modulus, flatten_layers(layers))


def selected_moduli(preset: str) -> list[Modulus]:
    if preset == "all":
        return list(MODULI)
    degree = int(preset)
    selected = [modulus for modulus in MODULI if modulus.m == degree]
    if not selected:
        raise ValueError(f"no built-in manifests for degree {degree}")
    return selected


def collect_rows(moduli: Sequence[Modulus]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for modulus in moduli:
        columns = reduction_columns(modulus)
        dense_count, dense_depth = dense_resources(columns, modulus.m)
        common = {
            "name": modulus.name,
            "m": modulus.m,
            "taps": ";".join(map(str, modulus.taps)),
        }
        rows.append({
            **common,
            "method": "direct_dense_shear",
            "CNOTs": dense_count,
            "CNOT_depth": dense_depth,
            "ancilla": 0,
            "verified": "basis",
        })
        if modulus.delta is not None:
            gates = two_cluster_gates(modulus)
            verify_two_cluster(modulus, gates)
            rows.append({
                **common,
                "method": "two_cluster_sequential_scan",
                "CNOTs": len(gates),
                "CNOT_depth": scheduled_depth(gates, 2 * modulus.m),
                "ancilla": 0,
                "verified": "basis",
            })
            layers = two_cluster_parallel_layers(modulus)
            parallel_gates = flatten_layers(layers)
            verify_parallel_scans(modulus)
            verify_two_cluster(modulus, parallel_gates)
            rows.append({
                **common,
                "method": "two_cluster_parallel_prefix",
                "CNOTs": len(parallel_gates),
                "CNOT_depth": len(layers),
                "ancilla": 0,
                "verified": "scan+basis",
            })
    return rows


def write_rows(rows: Sequence[dict[str, object]], stream: TextIO) -> None:
    fields = [
        "name", "m", "taps", "method", "CNOTs", "CNOT_depth", "ancilla",
        "verified",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preset", choices=("all", "163", "233", "283", "571"),
        default="283",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    run_internal_checks()
    rows = collect_rows(selected_moduli(args.preset))
    if args.output is None:
        write_rows(rows, sys.stdout)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            write_rows(rows, stream)


if __name__ == "__main__":
    main()
