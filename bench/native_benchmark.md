# Native gf2x benchmark

This file documents the current native reduction-only benchmark.  Planned
input distributions, application benchmarks, formal evidence gates, and
artifact requirements are tracked in
[the experimental TODO](../paper/exp_todo.md).

The native reducer implementations live in `src/`; public headers are under
`include/`; benchmark scripts and entrypoints live under `bench/scripts/`.

`bench/scripts/reduction_benchmark.c` drives the reduction-only microbenchmark
through the common `reduction_method` API in `include/reduction.h`. GS, serial sparse
folding, naive long division, and Barrett all expose the same timed
`reduce_into(input, context, output)` contract to the benchmark. Method setup,
input generation, output allocation, correctness checks, and checksum
consumption are outside the timed region.

The two Barrett products call the upstream `gf2x_mul` API. The reciprocal
polynomial is precomputed outside the timed reduction path.

The benchmark requires a native gf2x installation. Set `GF2X_PREFIX` to its
installation prefix and build with MinGW or GCC:

```text
make GF2X_PREFIX=/path/to/gf2x
build/reduction_benchmark 12 64 5
```

Arguments are `supports`, `inputs`, `repeats`, `m`, `s`, `seed`, and an
optional `no-naive` flag. The output is reduction-only timing in nanoseconds
per input. Correctness is checked across all enabled reducers before each timed
trial.

For a large `m` run that skips naive long division, pass the `no-naive` flag:

```text
build/reduction_benchmark 6 8 5 1000000 8 0x9e3779b97f4a7c15 no-naive
```

## Shared Work--Feedback-Depth--Setup Tradeoff Map

This is a shared classical experiment for every paper branch.  At fixed
degree, it must report a point for each exact sampled support with:

- scheduled feedback work
  \(W_{\mathrm{fb}}=\sum_{r,k}[m-2^kd_r]_+\);
- feedback depth
  \(D_{\mathrm{fb}}=\lceil\log_2(m/\Delta_{\min})\rceil\), with the
  explicit zero-feedback boundary; and
- per-method setup time and the amortized objective
  \(T_{\mathrm{setup}}+K T_{\mathrm{reduce}}\) for stated values of \(K\).

The plot is a measured work--feedback-depth--setup tradeoff, not an
instruction-count or minimum-XOR-circuit claim.  It must keep support geometry,
input distribution, compiler, machine, seed, timing boundary, and multiplication
backend with every row.  The existing
`bench/scripts/phase_diagram_benchmark.py` supplies matched per-support timing
rows, but currently records only \(\Delta_{\min}\) and runtime ratios.  Extend
its input/output contract (and the C driver if necessary) to record the exact
support or \(W_{\mathrm{fb}}\), setup timings, and \(K\)-amortized quantities
before generating this map.  No existing CSV is evidence for the map.
