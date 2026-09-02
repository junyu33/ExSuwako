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

Random-mode arguments are `supports`, `inputs`, `repeats`, `m`, `s`, `seed`,
and an optional `no-naive` flag. The output is reduction-only timing in
nanoseconds per input. Correctness is checked across all enabled reducers
before each timed trial.

For a large `m` run that skips naive long division, pass the `no-naive` flag:

```text
build/reduction_benchmark 6 8 5 1000000 8 0x9e3779b97f4a7c15 no-naive
```

To benchmark one exact modulus support, use the canonical ascending tap list:

```text
build/reduction_benchmark --taps 0,7,12 8 5 283 0x1 no-naive
```

The exact-mode arguments are `--taps LIST`, `inputs`, `repeats`, `m`, `seed`,
and the optional `no-naive` flag. `LIST` is comma-separated, strictly
increasing, duplicate-free, and contains only exponents in `[0,m)`; use `-`
for the empty support. The CSV serializes taps with semicolons so the complete
support occupies one field.

For a versionable suite of exact supports, use a JSON Lines manifest:

```json
{"sample_id":"k283-example","m":283,"taps":[0,7,12]}
{"sample_id":"empty-283","m":283,"taps":[]}
```

```text
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest supports.jsonl --output bench/data/exact.csv \
  --inputs 8 --repeats 5 --seed 1 --no-naive
```

Manifest taps obey the same canonical contract. `sample_id` must be nonempty
and unique; the driver rejects unordered, duplicate, nonintegral, and
out-of-range taps rather than normalizing them silently. Additional manifest
metadata may be recorded in the source manifest, but is not yet propagated to
the benchmark CSV.

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
rows and now records the exact support. Extend its output contract to include
\(W_{\mathrm{fb}}\), setup timings, and \(K\)-amortized quantities before
generating this map. No existing CSV is evidence for the map.
