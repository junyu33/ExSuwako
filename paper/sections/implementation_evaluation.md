# Implementation and Evaluation Draft

This document defines the paper-facing implementation model, research
questions, parameter grid, metrics, and figures.  Execution order, checkbox
status, application experiments, and artifact requirements are maintained only
in [the experimental TODO](../exp_todo.md).

## 8. Implementations

### 8.1 Reference Implementation

- naive long division;
- Python/Sage generalized Suwako;
- exhaustive small-$m$ validation;
- randomized differential tests;
- deterministic theorem-falsification suites covering GF(2), GF(4), dual
  numbers, support geometry, and the positive-characteristic sign check;
- dedicated cases for $q=0$, $q=1$, $q=x^t$, constant coefficient zero,
  constant coefficient one, dense $q$, reducible $g$, and non-word-aligned
  $m$.

### 8.2 Portable C

Requirements:

- arbitrary $m$;
- arbitrary public taps;
- non-word-aligned degrees;
- no assumption that the constant coefficient is present;
- explicit ping-pong buffers;
- no undefined shifts;
- constant-time field-element handling.

### 8.3 Fixed-Modulus Code Generation

Generate active tap lists, unrolled stages, final low assembly, and optional
in-place specializations. Iterate uniformly over $t\in T$; do not hard-code an
extra XOR for $X$. Measure code size.

### 8.4 SIMD

Potential targets:

- x86 AVX2;
- x86 AVX-512;
- ARM NEON;
- ARM SVE.

Discuss cross-limb shifts, cross-vector shifts, XOR fan-in, memory traffic, and
stage barriers. A tap is inactive in a feedback stage whenever
$2^k(m-t)\ge m$; the same rule applies uniformly to every exponent in $T$.

### 8.5 Baselines

Implement or integrate:

1. serial sparse folding;
2. optimized trinomial/pentanomial folding, including the Lopez--Dahab
   word-level reduction algorithm when its $\deg g<m-W$ assumption holds;
3. Barrett;
4. Montgomery;
5. dense linear reduction;
6. generic polynomial remainder.

### 8.6 Optional RTL Prototype

Compare serial sparse folding, generalized Suwako, and fixed dense XOR network.
Report latency, frequency, area/LUTs, registers, throughput, and pipeline
depth.

## 9. Evaluation

### 9.1 Research Questions

**RQ1: Correctness.** Does generalized Suwako agree with independent reducers
for arbitrary tap sets?

The current validation record establishes agreement for the binary core by
randomized and exhaustive tests, and separately tests the coefficient-algebra
identity over GF(4) and \(\mathbb F_2[\varepsilon]/(\varepsilon^2)\).  These
tests can falsify an implementation or a stated identity; they do not replace
the correctness proof. The portable-C differential suite additionally checks
GS, serial folding, naive long division, and gf2x-backed Barrett on 700
fixed-degree and 10,000 deterministic stratified-random cases with complete
bitwise-random degree-below-$2m$ inputs. Its support profiles include the
empty, sparse, dense, constant-free, endpoint, mixed-alignment, and
unrestricted boundaries for $1\le m\le512$.

**RQ2: Feedback chain.** Does latency scale with
$1+\log(m/\Delta_{\min})$ rather than $m/\Delta_{\min}$?

**RQ3: Crossover.** For which triples $(m,s,\Delta_{\min})$ does generalized
Suwako outperform serial folding and Barrett/Montgomery?

**RQ4: Modulus agility.** How does
$T_{\mathrm{setup}}+K T_{\mathrm{reduce}}$ behave as the number $K$ of
reductions per modulus changes?

**RQ5: Architecture dependence.** Do the same parameter regions remain useful
on scalar, SIMD, and hardware platforms?

**RQ6: Random-support behavior.** For fixed non-leading support size $s$ and
uniformly random support, do the measured active-tap work and feedback depth
follow the predicted $O(s)$ and $O(\log(s+1))$ expectations?

**RQ7: Algorithm-selection phase diagram.** Can the observed choices among
serial folding, generalized Suwako, and multiplication-based reduction be
organized by support size and feedback difficulty, while preserving the
dependence on modulus degree, word size, and implementation platform?

### 9.2 Parameter Grid

Suggested:

$$
m\in
\{128,256,512,1024,2048,4096,8192\},
$$

$$
s\in
\{0,1,2,4,8,16,32,64,128,\ldots\},
$$

$$
\Delta_{\min}
\in
\{1,2,4,8,16,64,m/4,m/2\}.
$$

Include:

- fixed-weight monic binary polynomials with support sampled uniformly from
  $\{0,\ldots,m-1\}$;
- synthetic controlled families for worst-case and friendly tap placement;
- non-irreducible moduli as the primary ring-level stress tests;
- $0\in T$ and $0\notin T$ cases;
- $T=\varnothing$ and the resulting $q=0$ case;
- constant-free, constant-one, and dense-$q$ cases;
- reducible moduli and non-word-aligned degrees.

Here $s=0$ is the separate $q=0$ boundary case. For each $(m,s)$ with
$s\ge1$, sample enough independent supports to report median, p90,
and p99 rather than only the mean. Do not label this model "random
polynomials" without specifying the fixed weight: unconstrained random
polynomials are typically dense.

The reduction-only input contract is:

| Registry name | Definition | Current status |
|---|---|---|
| `uniform-full-range:v1` | $A=L+x^mH$ with independent uniform $m$-bit $L,H$ | implemented primary corpus |

Multiplication results, polynomial squares, and application states are subsets
of this same reduction domain. They are not distinct reduction operations and
are separated only in complete-arithmetic or end-to-end experiments that also
include formation or workload semantics. Each reduction result row records
the registry name, and every matched reducer comparison uses the same
materialized input corpus.

For the algorithm-selection plots, use the modulus Hamming weight $h=s+1$ as
the primary horizontal coordinate and report $s=|T|$ as the secondary support
coordinate.  Use

$$
\frac{m}{\Delta_{\min}}
$$

as the vertical coordinate for feedback difficulty, plotted on a base-two
logarithmic scale.  This is equivalent to spacing points by
$\log_2(m/\Delta_{\min})$ while keeping the axis label directly interpretable.
Where machine-word effects are being studied, also record
$\Delta_{\min}/W$ (or $\log_2(W/\Delta_{\min})$) rather than treating the
theoretical coordinate as a complete implementation model.

### 9.3 Metrics

- cycles per reduction;
- throughput;
- latency;
- dependent stages;
- word shifts;
- XORs;
- carry-less multiplications;
- memory traffic;
- setup time;
- modulus-specific bytes;
- generated code size;
- temporary memory.
- median, p90, and p99 for runtime, $\Delta_{\min}$, $D_{\mathrm{fb}}$, and
  $\sum_k h_k$.

The modulus manifest preserves only the source fields `sample_id`,
`provenance`, $m$, and the complete tap set. The experiment driver derives
$s$, $h$, $\Delta_{\min}$, $D_{\mathrm{fb}}$, the complete $(h_k)$ profile,
and $W_{\mathrm{fb}}$ from those fields and cross-checks the native output.
Irreducibility metadata is required only for field-level experiments whose
claims depend on it, not for general reduction correctness or timing.

### 9.4 Planned Figures

1. **Schematic classical algorithm-selection phase diagram.** For a fixed
   $m$, show modulus Hamming weight $h$ horizontally and
   $m/\Delta_{\min}$ vertically on a logarithmic scale. Label the three
   conceptual regions: serial sparse folding (shift/XOR) for friendly sparse
   supports, generalized Suwako for sparse supports with difficult feedback,
   and Barrett/multiplication-based reduction at higher support sizes.
2. **Empirical phase-diagram panels.** For several fixed values of $m$, plot
   sampled supports and color each point by the measured winner among serial,
   generalized Suwako, and Barrett. Use the same coordinates as the schematic
   where possible, and retain an auxiliary view using $\Delta_{\min}/W$ when
   word-granularity effects are material.
3. Tradeoff map: work, feedback depth, and setup.
4. Operator diagram: $U,U^2,U^4,\ldots$.
5. Stage count versus $\Delta_{\min}$.
6. Crossover heatmaps over $(h,\Delta_{\min})$.
7. Gap-one scaling as $m$ grows.
8. Setup amortization over $K$.
9. Predicted active-tap work versus measured runtime.
10. Random-support depth and work versus $s$.

The schematic is a conceptual introduction figure, not a theorem giving a
universal boundary. The empirical panels must be separated by fixed $m$ (and
should state $W$, implementation, and platform), because Barrett cost depends
on multiplication-kernel thresholds and memory behavior, while generalized
Suwako depends on the full active-tap profile
$r+\sum_k h_k+s$, not only on $s$ and $\Delta_{\min}$. The caption should
state that exact region boundaries are implementation- and
platform-dependent. Cells with close timings or inconsistent winners should
be marked as uncertain rather than forced into a clean region.

### 9.5 Planned Tables

1. comparison of method families;
2. theorem and complexity summary;
3. real sparse moduli;
4. portable C results;
5. SIMD results;
6. setup and storage;
7. optional hardware results.

### 9.6 Negative Results

Report openly:

- high-weight regimes where generalized Suwako loses;
- friendly moduli where serial folding is already sufficient;
- small degrees dominated by loop overhead;
- architectures with expensive cross-limb shifts;
- quasi-linear multiplication regimes where the asymptotic comparison changes.
