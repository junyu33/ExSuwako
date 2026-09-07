# ExSuwako

ExSuwako is a research implementation of **Frobenius-factorized reduction
(FFR)** for monic binary polynomials. It extends the trinomial-oriented
[Suwako](https://eprint.iacr.org/2025/2303) construction to arbitrary
nonleading supports and evaluates when the resulting sparse shift/XOR schedule
is preferable to serial folding or multiplication-based reduction.

The repository separates shared results from venue-specific work:

- [`main`](https://github.com/junyu33/ExSuwako/tree/main) is the factual
  research trunk;
- [`math-comp`](https://github.com/junyu33/ExSuwako/tree/math-comp) contains
  the theorem-first manuscript and computational-algebra evaluation;
- [`eurocrypt`](https://github.com/junyu33/ExSuwako/tree/eurocrypt) contains
  the cryptographic-application and reversible-circuit research tracks.

The current arXiv manuscript snapshot is tagged
[`arxiv-v1`](https://github.com/junyu33/ExSuwako/tree/arxiv-v1). Its datasets
and reproduction assets are frozen in the
[`moc-artifact-v2`](https://github.com/junyu33/ExSuwako/releases/tag/moc-artifact-v2)
release. Moving branches are not substitutes for these immutable versions.

## Core construction

For

$$
g(x)=x^m+\sum_{t\in T}x^t,
\qquad T\subseteq\{0,\ldots,m-1\},
$$

the canonical `taps` representation is the complete, strictly increasing,
duplicate-free list of exponents in $T$. The implementation reduces inputs
of degree below $2m$ over $\mathbb F_2[x]$; irreducibility of $g$ is not
required.

Write $A=L+x^mH$, define $\Delta_t=m-t$, and let

$$
U(X)=\bigoplus_{t\in T}(X\mathbin{\gg}\Delta_t),
\qquad
V(X)=\bigoplus_{t\in T}((X\mathbin{\ll}t)\bmod x^m).
$$

Then

$$
\mathrm{red}_g(A)=L\oplus V((I+U)^{-1}H).
$$

In characteristic two, Frobenius doubles every tap distance without creating
new taps:

$$
(I+U)^{-1}=\prod_{k=0}^{r-1}(I+U^{2^k}),
\qquad
r=\left\lceil\log_2\frac{m}{\Delta_{\min}}\right\rceil
$$

when feedback is nonzero; otherwise $r=0$. Every shift in one factor must
read the same immutable stage input. FFR can retain the doubled descriptors
in a reusable plan or generate them online on every call.

The complete proofs, cost models, and evaluation are available in the tagged
[LaTeX source](https://github.com/junyu33/ExSuwako/blob/arxiv-v1/paper/ExSuwako/main.tex)
and [compiled manuscript](https://github.com/junyu33/ExSuwako/blob/arxiv-v1/paper/ExSuwako/output.pdf).

## Build and validate

Requirements are Python 3, a C11 compiler, GNU Make, and a native `gf2x`
installation. Override `GF2X_PREFIX` when `gf2x` is outside `/usr/local`.

```sh
make GF2X_PREFIX=/path/to/gf2x
make check GF2X_PREFIX=/path/to/gf2x
```

`make check` runs native differential and component tests, boundary checks,
and deterministic algebraic falsification suites. Venue branches may add
further implementation and artifact checks.

The independent Python reference can also be run directly:

```sh
python3 src/reference/generalized_suwako_poc.py
```

## Native reducers and benchmark

All native methods use the common `reduction_method` wrapper in
[`include/reduction.h`](include/reduction.h):

- planned and online FFR (`src/GS.c`);
- serial sparse folding (`src/serial.c`);
- Barrett reduction through `gf2x` (`src/barrett.c`);
- L\'opez--Dahab Algorithm 2 (`src/lopez_dahab.c`);
- naive long division (`src/naive.c`);
- diagnostic dense-map and generated fixed-modulus reducers.

Build the benchmark with `make`, then benchmark an exact support with:

```sh
build/reduction_benchmark --taps 0,7,12 16 3 283 0x1
```

The benchmark records setup and steady-state reduction separately and retains
the complete support, seed, timing order, compiler, linked `gf2x`, platform,
and affinity metadata. Its full CLI, timing contracts, input distributions,
manifests, and analysis pipeline are documented in
[`bench/native_benchmark.md`](bench/native_benchmark.md). The `math-comp`
planned-versus-online experiment has a
[separate frozen contract](https://github.com/junyu33/ExSuwako/blob/arxiv-v1/bench/ffr_online_benchmark.md).

Local CSV files and generated analyses belong under `bench/data/` and are
ignored by Git.

## Paper and artifact

The `arxiv-v1` tag fixes the manuscript source, figures, implementation, and
reproduction scripts. Download the three released CSV payloads from
[`moc-artifact-v2`](https://github.com/junyu33/ExSuwako/releases/tag/moc-artifact-v2)
before running the paper targets. The exact commands, expected row counts,
SHA-256 values, output hashes, dependencies, and clean-checkout audit are in
the tagged
[artifact contract](https://github.com/junyu33/ExSuwako/blob/arxiv-v1/bench/artifact/README.md).

## Repository map

- `include/`: public C interfaces and shared word-level primitives.
- `src/`: reusable native implementations.
- `src/reference/`: independent Python reference reducer.
- `tests/`: native and algebraic correctness suites.
- `bench/scripts/`: benchmark, manifest, analysis, and plotting programs.
- `bench/manifests/`: deterministic experiment supports.
- `paper/`: branch-specific factual records or venue materials; its
  `README.md` states the current branch contract.

## Scope and naming

The implementation is research software, not a production or constant-time
cryptographic library. Correctness applies to every monic binary modulus;
the favorable performance regions depend on degree, support geometry, machine
word width, platform, and setup amortization.

**ExSuwako** remains the repository name. **GS** abbreviates **Generalized
Suwako**, the original implementation name; the paper-facing method name is
**Frobenius-factorized reduction (FFR)**. Existing `GS`, `gs_*`, and GS-named
artifact fields remain unchanged to preserve API and dataset provenance.
