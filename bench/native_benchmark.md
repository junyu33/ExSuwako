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

## Input Distribution Registry

Every result row carries an `input_distribution` label. The frozen names and
mathematical contracts are:

| Name | Input polynomial $A$ with $\deg A<2m$ | Status |
|---|---|---|
| `uniform-full-range:v1` | $A=L+x^mH$, where $L$ and $H$ are independent uniform $m$-bit polynomials | Implemented; primary reduction-only corpus |

Polynomial multiplication results, polynomial squares, and application states
are subsets of this same degree-below-$2m$ reduction domain; they do not define
different reduction operations. They are introduced only by complete
arithmetic or end-to-end experiments that include formation or workload costs.
All reducers in one reduction-only comparison consume the same materialized
`uniform-full-range:v1` inputs.

## Timed-Boundary Registry

Every timing row carries a `timing_scope` label. The frozen operation
boundaries are:

| Name | Included inside the timed operation | Excluded from the timed operation | Status |
|---|---|---|---|
| `reduction-steady-state:v1` | Calls to `reduce_into(input, plan, output)` over a materialized input batch | Plan/setup construction, input generation, allocation, correctness checks, checksum consumption, and reporting | Implemented |
| `square-formation:v1` | Formation of the unreduced polynomial square into a preallocated $2m$-bit buffer | Reduction, reusable setup, input generation, allocation, validation, and reporting | Defined; pending |
| `modular-square-steady-state:v1` | Square formation followed by reduction to an $m$-bit output, including any intermediate-buffer traffic | Reusable setup, input generation, allocation, validation, and reporting | Defined; pending |
| `multiplication-formation:v1` | Polynomial multiplication into a preallocated $2m$-bit buffer | Reduction, reusable setup, input generation, allocation, validation, and reporting | Defined; pending |
| `modular-multiplication-steady-state:v1` | Polynomial multiplication followed by reduction, including intermediate-buffer traffic | Reusable setup, input generation, allocation, validation, and reporting | Defined; pending |
| `end-to-end:<workload>:vN` | One named workload invocation from materialized public inputs/state to its specified result, including its arithmetic and control flow | Process startup, corpus generation, file I/O, validation, and reporting | Workload-specific |

Microbenchmarks time a batch with one clock interval and divide by the number
of operations; they do not place clock calls around each individual reducer
call. A fused implementation may use its own internal organization, but it
must retain the same mathematical input/output operation and timing-scope
label. Reusable setup is deliberately handled by the separate setup-accounting
contract rather than hidden inside one method's timed operation.

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
{"sample_id":"k283-example","provenance":"hand-constructed-example:v1","m":283,"taps":[0,7,12]}
{"sample_id":"empty-283","provenance":"synthetic-boundary:v1","m":283,"taps":[]}
```

```text
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest supports.jsonl --output bench/data/exact.csv \
  --inputs 8 --repeats 5 --seed 1 --no-naive
```

Manifest taps obey the same canonical contract. `sample_id` must be nonempty
and unique, while `provenance` is a nonempty label for the modulus source or
generation rule. The driver rejects unordered, duplicate, nonintegral, and
out-of-range taps rather than normalizing them silently.

The manifest stores only the source fields `sample_id`, `provenance`, `m`, and
`taps`. The driver deterministically derives and emits `s`, `h`, `Delta_min`,
`feedback_stages`, `active_tap_counts`, and `W_fb`; it also checks the native
driver's `m`, `s`, `h`, taps, and `Delta_min` against those derived values.
Here `active_tap_counts` serializes

\[
h_k=\#\{t\in T:2^k(m-t)<m\}
\]

with semicolons, and `W_fb` is
\(\sum_{t,k}[m-2^k(m-t)]_+\). A zero-stage profile is written as `-`.
Irreducibility is not part of this general reduction contract; field-level
experiments must record it separately when their claims require it.

The current native binary emits
`input_distribution=uniform-full-range:v1`. Future complete-arithmetic or
application drivers must name their own corpus without presenting it as a
different reduction API. It also emits
`timing_scope=reduction-steady-state:v1`; timing results with another scope
must not be merged into the same distribution.

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
rows and now records the exact support, active-tap profile, and
\(W_{\mathrm{fb}}\). Extend its output contract to include setup timings and
\(K\)-amortized quantities before generating this map. No existing CSV is
evidence for the map.
