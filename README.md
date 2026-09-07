# ExSuwako

**ExSuwako** is the repository name for an early proof-of-concept
implementation of Frobenius-factorized reduction (FFR) for sparse binary
polynomials.

It extends the original trinomial-oriented Suwako idea to monic moduli of the
form

$$
g(x)=x^m+\sum_{t\in T}x^t,
$$

where

$$
T\subseteq\{0,\ldots,m-1\}.
$$

The canonical `taps` list is the complete ascending list of exponents in
$T$; it excludes the leading exponent $m$ and contains no duplicates. Write
$s=|T|$. The Hamming weight of the modulus is therefore

$$
h=s+1.
$$

The current implementation operates over $\mathbb F_2[x]$ and reduces inputs
of degree less than $2m$, which is the usual degree range produced by
multiplying two polynomials of degree less than $m$. The repository now has a
portable C reduction API, a Python reference implementation, correctness tests,
and exploratory benchmark drivers.

## Status

This repository is a research prototype.

The current code is intended to:

- validate the generalized construction against a simple reference reducer;
- expose the operator structure of the algorithm;
- support further correctness, complexity, implementation, and prior-art work;
- serve as a starting point for SIMD and hardware implementations.

It is **not** currently intended to be:

- a production cryptographic library;
- a constant-time Python implementation;
- a formally verified implementation;
- evidence that all relevant prior work has been exhausted;
- a claim that the present formulation is novel in every component.

The repository is private while the result is still being investigated.

## Operator formulation

Write the input as

$$
C=L+x^mH,
$$

where $L$ contains the low $m$ coefficients and $H$ contains the high
coefficients.

For every tap $t\in T$, define

$$
\Delta_t=m-t.
$$

On the truncated $m$-bit coefficient space, define the feedback operator

$$
U(X)=\bigoplus_{t\in T}\left(X\gg\Delta_t\right).
$$

Also define the low-part assembly operator

$$
V(X)
=
\bigoplus_{t\in T}
\left((X\ll t)\bmod x^m\right).
$$

Equivalently, with

$$
q(x)=\sum_{t\in T}x^t,
$$

the product $qX$ splits as

$$
qX=V(X)+x^mU(X).
$$

Since $g=x^m+q$ implies $x^m\equiv q$ modulo $g$, cancelling the high part
requires solving

$$
H=(I+U)X.
$$

The reduction implemented by the PoC can be written as

$$
\operatorname{red}_g(C)
=
L\oplus V\!\left((I+U)^{-1}H\right).
$$

Because the shift operators commute and the coefficient field has
characteristic two,

$$
U^{2^k}(X)
=
\bigoplus_{t\in T}
\left(X\gg 2^k\Delta_t\right).
$$

The operator $U$ is nilpotent on the truncated space. Consequently, for a
sufficient number of rounds,

$$
(I+U)^{-1}
=
\prod_{k\ge 0}\left(I+U^{2^k}\right).
$$

The corresponding iteration is

$$
X_{k+1}
=
X_k
\oplus
\bigoplus_{t\in T}
\left(X_k\gg 2^k\Delta_t\right).
$$

All shifts in a single round must read the same old value $X_k$. They must
not observe partially updated results from other taps in that round.

In a SIMD or hardware implementation, this naturally suggests two
ping-pong buffers. The Python PoC expresses the same dependency rule through
an immutable `old` state within each round.

If $T\ne\varnothing$, let

$$
\Delta_{\min}=\min_{t\in T}(m-t),
$$

the number of dependent feedback rounds used by the implementation is

$$
\left\lceil
\log_2\left(\frac{m}{\Delta_{\min}}\right)
\right\rceil.
$$

For $T=\varnothing$, set $r=0$; reduction modulo $x^m$ has no feedback
rounds.

The exact ceiling is important. When at least one feedback round is active and
the closest tap is a fixed distance from the leading term, the bare expression
$\log(m/\Delta_{\min})$ tends to zero, but the feedback closure still needs one
round. In that regime, asymptotic statements should keep the exact $r$ or use

$$
r=\Theta\left(1+\log\frac{m}{\Delta_{\min}}\right).
$$

## Files

### Source Layout

- `include/`: public C headers and small shared word-level primitives.
- `src/`: reusable native reducer implementations.
- `src/reference/`: independent Python reference code.
- `tests/`: native and Python correctness-only test programs.  `make check`
  runs the native reducer check and the two theorem-falsification suites.
- `bench/scripts/`: benchmark entrypoints and experiment drivers.
- `bench/data/`: local or externally supplied benchmark payloads and generated
  outputs. The complete directory is ignored by Git; the paper artifact keeps
  only its SHA-256 contract, scripts, and deterministic manifests in the
  repository.
- `bench/*.md`: benchmark notes and command documentation.
- `paper/`: this branch's venue-specific manuscript plan and claim boundaries;
  shared mathematical facts and provenance remain on `main`.

The native reducers share the `reduction_method` wrapper in
`include/reduction.h`. A method owns reducer-specific setup state, exposes its
required output size, and provides the common timed contract

```c
reduce_into(input, context, output)
```

This wrapper is intentionally small: it lets correctness tests and benchmark
drivers call GS, serial sparse folding, naive long division, Barrett,
López--Dahab Algorithm 2, and the opt-in dense and generated fixed-modulus reducers
through the same API without hiding each algorithm's real setup and scratch
requirements.

### Native Reducers

- `src/GS.c`: Frobenius-factorized reduction. It precomputes the sparse doubling
  schedule and computes
  $L+V((I+U)^{-1}H)$ with one reusable state buffer.
- `src/serial.c`: word-oriented serial sparse folding baseline. It propagates
  high-part feedback one round at a time.
- `src/naive.c`: simple long-division reference baseline.
- `src/barrett.c`: Barrett-style GF(2) polynomial reduction using `gf2x_mul`
  through `poly_mul_gf2x`.
- `src/lopez_dahab.c`: ordinary-loop López--Dahab Algorithm 2 with a reusable
  tap-descriptor and scratch plan, available when $m>W$ and
  $\deg q\le m-W$; equality is the tested word-aligned extension of the
  paper's strict assumption.
- `src/dense.c`: fixed-modulus row-major binary linear map, with setup and
  lifetime storage exposed separately from steady-state row-parity reduction.
- `src/generated.c`: ABI-checked loader for temporary fixed-modulus plugins
  emitted by `bench/scripts/generate_fixed_reducer.py`; generated source and
  binaries remain outside `src/`. The generator supports both unrolled GS and
  López--Dahab Algorithm 2 for eligible fixed moduli of arbitrary weight.
- `src/reduction.c`: common wrapper API used by tests and native benchmarks.

### Python Reference

Contains:

- `generalized_suwako`, the generalized reduction prototype;
- `naive_sparse_reduction`, a bit-by-bit reference implementation;
- input and modulus validation;
- hand-picked edge cases;
- randomized differential testing;
- detailed diagnostics on a mismatch.

The implementation uses Python arbitrary-precision integers as coefficient
vectors. Bit $i$ represents the coefficient of $x^i$.

## Requirements

For the Python reference:

- Python 3 and its standard library.

For the native C implementation and benchmarks:

- a C11 compiler;
- `make`;
- a native `gf2x` installation providing `gf2x.h` and `-lgf2x`.

The Makefile defaults to

```make
GF2X_PREFIX=/usr/local
```

and links with

```text
-I$(GF2X_PREFIX)/include -L$(GF2X_PREFIX)/lib -lgf2x
```

On the current development machine, this resolves `-lgf2x` to
`/usr/lib/libgf2x.so`; no `/usr/local/lib/libgf2x.a` is present.

## Running the validation

Run the native correctness suite with:

```bash
make check
```

This builds and runs `tests/check_reduction.c`, which compares GS, serial,
naive, and Barrett through the common `reduction_method` API. It also runs
`tests/check_gs_stage.c`, which compares the actual private in-place GS stage
kernel against an independent out-of-place, bit-level immutable-old reference
for explicit alignment classes and 20,000 deterministic random stages, and
`tests/check_gs_components.c`, which separately checks the complete feedback
closure and final low-part assembly against bit-level references on five
explicit classes and 20,000 deterministic random cases. The production source
and API are unchanged. The deterministic
native suite includes 700 fixed-degree cases and 10,000 stratified random
cases with bitwise-random inputs over the full degree-below-$2m$ range. The
support profiles cover empty, sparse, dense, constant-free, endpoint,
word-aligned/unaligned, and unrestricted tap sets for $1\le m\le512$; they
include reducible moduli and forced $\Delta_{\min}=1$ cases. A mismatch prints
the seed, degree, trial, complete taps, and input words.

The older alias is kept for now:

```bash
make check-serial
```

Run the Python reference validation suite with:

```bash
python3 src/reference/generalized_suwako_poc.py
```

The default suite includes:

- hand-picked trinomial, pentanomial, and higher-weight cases;
- cases with taps close to both ends of the modulus;
- cases with $\Delta_{\min}=1$;
- 10,000 randomized cases;
- degrees up to $m=2048$;
- modulus Hamming weights from 3 through 12.

For a reproducible run with a fixed random seed:

```bash
PYTHONPATH=src/reference python3 -c \
  'from generalized_suwako_poc import run_validation; run_validation(seed=0)'
```

The generalized result is compared against the bit-by-bit reference reducer
for every test case.

## Building and Benchmarking

Build the native benchmark with:

```bash
make
```

or with an explicit gf2x prefix:

```bash
make GF2X_PREFIX=/path/to/gf2x
```

The benchmark binary is:

```bash
build/reduction_benchmark
```

Its arguments are:

```text
supports inputs repeats m s seed [no-naive]
--taps LIST inputs repeats m seed [no-naive]
```

The first form samples random supports. The second benchmarks exactly one
canonical support; `LIST` is an ascending, duplicate-free comma-separated tap
list, or `-` for the empty support.

Example:

```bash
build/reduction_benchmark 4 16 3 1024 8 0x9e3779b97f4a7c15
build/reduction_benchmark --taps 0,7,12 16 3 283 0x1
```

The output is CSV with setup time per fresh plan and steady-state reduction
time in nanoseconds:

```text
m,word_bits,s,h,taps,Delta_min,feedback_stages,active_tap_counts,feedback_active_tap_sum,W_fb,GS_source_cost_model,GS_source_...,plan_storage_model,GS_plan_bytes,...,input_distribution,timing_scope,setup_scope,timing_order,GS_setup_ns,...,GS_ns,...
```

The current reduction-only corpus is `uniform-full-range:v1`: it samples
$A=L+x^mH$ with independent uniform $m$-bit $L,H$. The contract is documented in
[bench/native_benchmark.md](bench/native_benchmark.md#input-distribution-registry).

The current timing scope is `reduction-steady-state:v1`: only batched
`reduce_into()` calls are timed. Reducer setup, input generation, allocation,
correctness checks, checksum consumption, and reporting remain outside.

Paper-facing runs cyclically rotate method order within each native trial,
using 12 batch repeats so three- and four-method runs are exactly balanced
across timing positions. They preserve 31 independent native trial rows after one
discarded warm-up and aggregate them by the median without outlier removal.
Use `--warmup-runs 1 --measurement-trials 31`; the CSV records those counts,
the inner batch-repeat count, input count, trial index, and aggregation
contract. The native output also records the machine-word width.

The setup scope is `modulus-plan:v1`. It separately measures fresh reusable
plan construction from materialized $m$, taps, and $g$, including schedules,
reciprocals, and plan-owned scratch allocation. Raw per-method setup and
reduction times are retained so amortized costs can be derived for an explicit
number $K$ of reductions per plan. See
[bench/native_benchmark.md](bench/native_benchmark.md#setup-accounting-registry).

For repeatable support suites, `phase_diagram_benchmark.py --manifest FILE`
accepts JSON Lines records containing `sample_id`, `provenance`, `m`, and
`taps`. The driver retains the source fields and deterministically derives
`s`, `h`, `Delta_min`, `feedback_stages`, `active_tap_counts`,
`feedback_active_tap_sum`, and `W_fb` in its output CSV, after checking the
four schedule quantities against the actual GS plan. It likewise checks the
`scalar-source-v1` GS word-operation fields through an independent Python
derivation. Random-mode rows use provenance
`synthetic-fixed-weight-uniform:v1` and seed-qualified sample identifiers.
Each row also reports every enabled reducer's plan-owned requested bytes under
`requested-owned-bytes:v1`, separately from setup and reduction timing.

Deterministic failures and anomalous supports are promoted into versioned
regression inputs rather than left only in console output or local CSV. Native
exact inputs live in `tests/reduction_regressions.h`; benchmark support cases
live in `bench/manifests/regression_supports.jsonl`. Both are replayed by
`make check`.

Setup remains outside the steady-state reduction region and is reported in
separate columns. Input generation, output allocation, correctness checks, and
checksum consumption are outside both operation timings.

Experiment drivers live in `bench/scripts/`. Local CSV and generated analysis
outputs belong under `bench/data/` and remain outside Git. The Math. Comp.
artifact contract under `bench/artifact/` identifies an externally supplied
canonical dataset by row count and SHA-256 and rebuilds the paper outputs from
it without weakening the no-CSV-in-Git policy.

## Scope and assumptions

The current PoC assumes:

1. coefficients are in $\mathbb F_2$;
2. the modulus is monic and has degree $m$;
3. `taps` contains the complete support of the nonleading part;
4. tap exponents are distinct and satisfy $0\le t<m$;
5. the input has degree less than $2m$.

The implementation does not construct a dense reciprocal polynomial or a dense
reduction matrix. It computes the feedback schedule directly from the sparse
tap positions.

This is best viewed as a matrix-free sparse reciprocal application. It does
not deny the reciprocal structure; rather, it avoids explicitly materializing
the usually dense feedback reciprocal $p(z)^{-1}\bmod z^m$, where

$$
p(z)=1+\bigoplus_{t\in T}z^{\Delta_t},
$$

and applies it through sparse Frobenius factors:

$$
p(z)^{-1}
\equiv
\prod_{k=0}^{r-1}
\left(
1+\bigoplus_{t\in T}z^{2^k\Delta_t}
\right)
\pmod{z^m}.
$$

## Comparison with multiplication-based reduction

Let

$$
n=\left\lceil\frac{m}{W}\right\rceil
$$

be the number of $W$-bit machine words used to represent an $m$-bit
polynomial, and let

$$
r=
\left\lceil
\log_2\left(\frac{m}{\Delta_{\min}}\right)
\right\rceil.
$$

For an individual tap, define

$$
r_t=
\left\lceil
\log_2\left(\frac{m}{\Delta_t}\right)
\right\rceil.
$$

The coarse machine-word work bound for FFR is

$$
T_{\mathrm{FFR}}(m,h,W)
=
O(hnr).
$$

A more precise schedule-sensitive bound, counting only active tap shifts in
rounds where $2^k\Delta_t<m$, is

$$
O\left(n\left(r+\sum_{t\in T}r_t+|T|\right)\right).
$$

The $r$ term accounts for the per-round state update, the sum accounts for
active feedback shifts, and the $|T|$ term accounts for the final low-part
assembly.

Let $M_W(n)$ denote the machine-word complexity of multiplying two
$n$-word binary polynomials. A Barrett- or Montgomery-style reduction
dominated by a constant number of polynomial multiplications has work

$$
\Theta(M_W(n)).
$$

Thus FFR has asymptotically lower machine-word work whenever

$$
hnr=o(M_W(n)),
$$

or equivalently,

$$
h
=
o\left(
\frac{M_W(n)}
     {nr}
\right).
$$

Using $r=\Theta(1+\log(m/\Delta_{\min}))$, this may be written as

$$
h
=
o\left(
\frac{M_W(n)}
     {n\left(1+\log(m/\Delta_{\min})\right)}
\right).
$$

For schoolbook word multiplication,

$$
M_W(n)=\Theta(n^2),
$$

which gives

$$
h
=
o\left(
\frac{m}
     {W\left(1+\log(m/\Delta_{\min})\right)}
\right).
$$

For Karatsuba word multiplication,

$$
M_W(n)=\Theta\left(n^{\log_2 3}\right),
$$

which gives

$$
h
=
o\left(
\frac{(m/W)^{\log_2 3-1}}
     {1+\log(m/\Delta_{\min})}
\right)
=
o\left(
\frac{(m/W)^{0.585\ldots}}
     {1+\log(m/\Delta_{\min})}
\right).
$$

These bounds compare asymptotic machine-word work. They do not by themselves
determine the practical crossover point, which also depends on shift/XOR
throughput, carryless-multiplication instructions, vector width, memory
traffic, tap placement, and implementation constants.

## Research directions

The present prototype is intended to support work on:

- a complete formal derivation of the reduction map;
- precise work, depth, and space bounds;
- comparison with serial sparse folding;
- comparison with multiplication-based reduction methods;
- comparison with LFSR look-ahead, CRC unfolding, parallel polynomial
  division, and related hardware techniques;
- SIMD implementations with explicit ping-pong buffers;
- RTL implementations and area/depth tradeoffs;
- code generation for compile-time modulus parameters;
- evaluation on cryptographically relevant sparse moduli;
- characterization of the regimes in which the generalized method is useful.

## Current triage status

The algebraic core has passed the current first-round correctness checks:
manual derivation, comparison against a bit-by-bit reference reducer, and an
independent reimplementation-based differential check. The in-place scalar
stage kernel is also checked directly against immutable-old stage semantics.
The feedback closure and final low-part assembly are each checked separately
against bit-level references. These checks are useful evidence against
off-by-one, synchronous-update, tap-interaction, final assembly, and
round-count mistakes. The native differential suite additionally surrounds
the first three machine-word boundaries, checks canonical top padding and
oversized-output tails, and exercises the shared scalar right-shift primitive
at every bit offset. The same native paths pass the repository's ASan/UBSan
target.

This does not yet establish novelty, importance, or a compelling application.
The next kill steps are prior-art search around reciprocal methods, sparse
operator factorization, LFSR and CRC unfolding, and concrete C/SIMD/RTL
performance measurements on relevant sparse moduli.

## Repository name

`ExSuwako` remains the repository name.  The paper-facing algorithmic term is
**Frobenius-factorized reduction (FFR)**.  Existing `GS`, `gs_*`, and
GS-named paths are retained as historical implementation and data-schema
identifiers so that frozen benchmark provenance remains stable.
