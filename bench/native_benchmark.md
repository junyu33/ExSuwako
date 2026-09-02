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

All reducers in one comparison consume the same materialized
`uniform-full-range:v1` inputs.

## Timed-Boundary Registry

Every timing row carries a `timing_scope` label. The frozen operation boundary
is:

| Name | Included inside the timed operation | Excluded from the timed operation | Status |
|---|---|---|---|
| `reduction-steady-state:v1` | Calls to `reduce_into(input, plan, output)` over a materialized input batch | Plan/setup construction, input generation, allocation, correctness checks, checksum consumption, and reporting | Implemented |

The benchmark times a batch with one clock interval and divides by the number
of reductions; it does not place clock calls around individual calls. Every
method must retain the same mathematical operation $A\mapsto A\bmod g$ for
$\deg A<2m$. Reusable setup is deliberately handled by the separate
setup-accounting contract rather than hidden inside one method's timed
operation.

The two Barrett products call the upstream `gf2x_mul` API. The reciprocal
polynomial is precomputed outside the timed reduction path.

## Sampling and Stability Protocol

One native invocation reports the median of `batch_repeats` timed batches.
Within each setup and reduction repeat, the first measured method advances
cyclically, so no reducer is permanently assigned to the cold/ramp-up or
late/hot position.
Choose a repeat count divisible by the number of enabled methods to balance
every method across every position exactly; the frozen count of 12 works for
both the three-method (`no-naive`) and four-method configurations. Every row
records `timing_order=cyclic-method-rotation:v1`.
For paper measurements, run one discarded whole-invocation warm-up followed
by 31 independent measurement trials over the same materialized support and
deterministically reproduced input corpus. Preserve all 31 rows, then report
their median. Do not delete or winsorize outliers; report dispersion from the
retained rows. Use a deterministic nonparametric bootstrap over the retained
trial medians and mark a point uncertain when the relative half-width of its
95% median confidence interval exceeds 1%; additional trials may narrow that
interval, but must be retained and reported rather than replacing unfavorable
measurements.

The phase-diagram driver implements this protocol with
`--warmup-runs 1 --measurement-trials 31`. Its default remains one trial so
contract tests and exploratory runs stay short. Every raw row records
`inputs`, `batch_repeats`, `warmup_runs`, `measurement_trials`, and
`measurement_trial`, together with
`aggregation=median-of-trial-medians:no-outlier-removal:v1`. The frozen
paper-facing inner count is twelve batch repeats. A final run must retain the
same input count across compared methods and record that count rather than
hiding it in the aggregation step.

On the primary machine, an exploratory calibration pinned to logical CPU 10
split 310 independent runs into ten disjoint groups of 31. For the tested
representative support under cyclic method rotation and 12 batch repeats, the
group-median CV was 0.802% for GS, 0.148% for Serial, and 0.020% for Barrett.
This calibrates the sampling rule; it is not a paper performance result and
must be rerun on the final artifact commit. Measurements made under the old
fixed GS--Serial--Naive--Barrett order are not comparable to this protocol.

Primary-machine runs use GCC with
`-O3 -std=c11 -Wall -Wextra`, 64-bit `word_t`, and the dynamically resolved
gf2x shared library. Run the driver under `taskset` on one recorded logical
CPU. Record the exact compiler version, linked gf2x path, CPU model and
affinity, governor, energy-performance preference, and turbo state with the
raw run. Do not pool rows collected under different compiler, linkage,
affinity, or frequency policies.

## Setup-Accounting Registry

Every row also carries `setup_scope=modulus-plan:v1`. Starting from already
materialized $m$, taps, and $g$, one setup sample times construction of a fresh
reusable reducer plan. Destruction happens after the clock stops. The
benchmark takes the median of `repeats` fresh constructions, then constructs a
separate plan for correctness checking and steady-state reduction timing.

The included method-specific work is:

| Method | Included in setup |
|---|---|
| GS | feedback-stage schedule, shift descriptors, and plan-owned scratch allocation |
| Serial | tap descriptors, sorting, and plan-owned state allocation |
| Naive | its current lightweight context allocation |
| Barrett | reciprocal $\mu$, Barrett plan construction, and plan-owned scratch allocation |

Argument parsing, shared modulus materialization, input/output benchmark
buffers, correctness checks, reporting, and teardown are excluded uniformly.
The CSV preserves `GS_setup_ns`, `Serial_setup_ns`, `Naive_setup_ns`, and
`BarrettGF2X_setup_ns` separately from the steady-state reduction fields. For
an explicitly stated number $K$ of reductions using one plan, derive

\[
T_{\mathrm{total}}(K)=T_{\mathrm{setup}}+K T_{\mathrm{reduce}},
\qquad
\bar T(K)=T_{\mathrm{reduce}}+\frac{T_{\mathrm{setup}}}{K}.
\]

Do not bake a particular $K$ into the raw CSV. A future generated-code or
dense-map reducer must count method-specific generation and allocation as
setup, while reporting compilation time, generated code size, and stored-map
size as separate quantities. None of those future baselines is currently
measured.

## Seed and Regression Registry

The native xorshift generator is deterministic. Its nonzero C seed controls
random support sampling and `uniform-full-range:v1` inputs and is emitted in
every native CSV row. Artifact commands must pass the seed explicitly even
when a driver has a deterministic default. The phase-diagram driver's Python
seed deterministically generates nonzero per-invocation C seeds; every derived
row preserves the actual C seed, exact taps, stable `sample_id`, and
provenance. Repeating the same driver seed is contract-tested to reproduce all
nontiming identity and geometry fields.

Native correctness testing uses the fixed seed
`0xd1b54a32d192ed03`; the theorem-falsification suites record their own fixed
seeds in source and, where supported, output. A native mismatch prints its
suite, seed, degree, trial, complete taps, compared methods, and exact
little-endian input words.
After minimizing a failure, encode its input as mathematical bit exponents in
`tests/reduction_regressions.h`; `make check` replays that corpus before the
random suites. Bit exponents keep the case independent of machine word width.

Benchmark-only anomalous supports belong in
`bench/manifests/regression_supports.jsonl` with a stable identifier and
provenance. The manifest is replayed by the experiment contract test. Local
timing CSV remains exploratory and ignored; do not promote environmental
jitter into a modulus regression unless the exact support reproducibly
triggers the anomaly under the frozen platform protocol.

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
`input_distribution=uniform-full-range:v1` and
`timing_scope=reduction-steady-state:v1`, together with
`setup_scope=modulus-plan:v1` and the four per-method setup timings.

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
rows and records the exact support, active-tap profile, \(W_{\mathrm{fb}}\),
and raw per-method setup and reduction timings. The plotting step must derive
the amortized quantities for explicitly stated values of $K$; it must not add
a hidden default $K$ to the raw data. No existing CSV is evidence for the map.
