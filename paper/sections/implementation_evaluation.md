# Implementation and Evaluation Draft

This document defines the paper-facing implementation model, research
questions, parameter grid, metrics, and figures. Execution order, checkbox
status, and artifact requirements are maintained only in
[the experimental TODO](../exp_todo.md).

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

The implemented scalar GS and Serial reducers share the word/bit shift
descriptors, high-part extraction, and low/carry right-shift components in
`sparse_shift.h`.  GS retains its destination-oriented gather traversal and
doubling schedule, while Serial retains its source-oriented scatter traversal
and sequential feedback chain.  Thus the comparison shares the primitive
being measured without collapsing the two algorithms into one loop structure.

### 8.3 Fixed-Modulus Code Generation

The implemented `fixed-unrolled-gs-c:v1` generator expands active tap lists,
feedback stages, destination words, and final low assembly for one exact
$(m,T)$, including $t=0$ only where the uniform formulas require it. It emits
a temporary 64-bit-word shared-object plugin and does not hard-code an extra
XOR for $X$. Report source generation, compilation, loaded-plan setup, source
and shared-object bytes, and the ELF `.text` section separately from
steady-state reduction.

The separate `lopez-dahab-algorithm2-fixed-c:v1` mode unrolls Algorithm 2's
full-word and partial-word cancellation for arbitrary modulus weight. It is
available only when $\deg q<m-W$, exactly the assumption stated by López and
Dahab; unsupported tap placements are rejected rather than silently routed
through a different algorithm. Trinomials and pentanomials remain mandatory
strong-baseline cases, but are not an algorithmic applicability boundary.
The native `LopezDahabLoop` mode implements the same Algorithm 2 domain with
ordinary tap and high-word loops. It is compared with the ordinary-loop GS
kernel under the common plan/setup and steady-state timing contract, while the
two generated modes separately measure fixed-modulus specialization.

### 8.4 SIMD

SIMD is not planned for the current portable-scalar evaluation. Potential
future targets include:

- x86 AVX2;
- x86 AVX-512;
- ARM NEON;
- ARM SVE.

Any future SIMD study must separately freeze cross-limb shifts, cross-vector
shifts, XOR fan-in, memory traffic, and stage barriers. A tap is inactive in a
feedback stage whenever
$2^k(m-t)\ge m$; the same rule applies uniformly to every exponent in $T$.

### 8.5 Baselines

Implement or integrate:

1. serial sparse folding;
2. optimized trinomial/pentanomial folding, including the Lopez--Dahab
   word-level reduction algorithm when its $\deg g<m-W$ assumption holds;
3. Barrett;
4. Montgomery only in a separately frozen Montgomery-domain multiplication
   workload, not in the current direct $A\mapsto A\bmod g$ microbenchmark;
5. the implemented opt-in row-major dense linear map for
   $H\mapsto x^mH\bmod g$, evaluated by packed row parity;
6. the existing `Naive` ordinary polynomial long division as the generic
   correctness/portability reference, not a tuned performance competitor.

### 8.6 Optional RTL Prototype

No RTL prototype is planned for the current software-reduction study. A future
hardware study would compare serial sparse folding, generalized Suwako, and a
fixed dense XOR network, and would report latency, frequency, area/LUTs,
registers, throughput, and pipeline depth under one frozen synthesis flow.

## 9. Evaluation

### 9.1 Research Questions

**RQ1: Correctness.** Does generalized Suwako agree with independent reducers
for arbitrary tap sets?

The current validation record establishes agreement for the binary core by
randomized and exhaustive tests, and separately tests the coefficient-algebra
identity over GF(4) and \(\mathbb F_2[\varepsilon]/(\varepsilon^2)\).  These
tests can falsify an implementation or a stated identity; they do not replace
the correctness proof. The portable-C differential suite additionally checks
GS, serial folding, naive long division, and gf2x-backed Barrett on 1,400
fixed-degree and 10,000 deterministic stratified-random cases with complete
bitwise-random degree-below-$2m$ inputs. Its support profiles include the
empty, sparse, dense, constant-free, endpoint, mixed-alignment, and
unrestricted boundaries for $1\le m\le512$.
The fixed degrees surround the first three machine-word boundaries, and every
reducer receives an oversized, nonzero-prefilled output so top-word masking
and tail clearing are checked independently of remainder equality.  A
dedicated shared-shift suite exhausts small source/destination capacities and
all bit offsets, and the native suites also pass under ASan and UBSan.
The private scalar feedback-stage kernel is additionally tested against an
independent out-of-place, bit-level implementation of the immutable-old stage
semantics for explicit alignment classes and 20,000 deterministic random
stages; this is direct implementation evidence for the synchronous-update
condition, not a replacement for its proof.
The complete feedback closure and final low-part assembly are also isolated
and compared separately against out-of-place bit-level references on five
explicit support classes and 20,000 deterministic random cases. This
distinguishes schedule/closure errors from assembly errors that an end-to-end
remainder comparison would otherwise conflate.

**RQ2: Feedback chain.** Does latency scale with
$1+\log(m/\Delta_{\min})$ rather than $m/\Delta_{\min}$?

The native benchmark exports the feedback-stage count, per-stage active-tap
profile, total active-tap count, and scheduled coefficient work read from the
constructed GS plan.  The phase-diagram driver derives these quantities
independently from the complete tap set and rejects any row whose schedule
metadata disagrees with the predicted geometry.  This checks the structural
predictor before it is correlated with timing data; it does not by itself
establish the latency-scaling claim or an instruction-count model.
The separate `scalar-source-v1` profile models the complete portable GS data
path and distinguishes aligned from cross-word contributions, together with
nonzero word shifts, word XORs, logical array reads and writes, and plan-owned
scratch words. The native profile is checked against an independent Python
reconstruction. These are source-model quantities rather than compiler
instructions or hardware memory transactions; cross-vector behavior remains
outside the scalar model.
The cost-model analysis aggregates trial medians by exact support, collapses
duplicate tap sets, and reports Spearman correlation with `GS_ns` only within
fixed-$m$ panels.  It also uses
leave-one-support-out affine prediction from source word XORs and stratifies
the residuals by logical-access fraction, feedback-stage band, and word
alignment.  The resulting flags show where the simple predictor is
insufficient; because these are source-level proxies, they are not causal
cache, barrier, or instruction-counter evidence.  The present response is
nanoseconds per reduction, not cycles; a future cycle claim requires a frozen
PMU and core-type contract.
A deterministic bootstrap interval marks support timings with relative
half-width above 1% as uncertain; these points are retained and counted rather
than removed from the correlation or residual diagnostics.

**RQ3: Crossover.** For which triples $(m,s,\Delta_{\min})$ does generalized
Suwako outperform serial folding and Barrett under the matched direct-
reduction contract? Montgomery is excluded here because REDC returns
$AR^{-1}\bmod g$; it belongs to a distinct Montgomery-domain multiplication
question whose representation conversions and setup must be accounted for.

**RQ4: Modulus agility.** How does
$T_{\mathrm{setup}}+K T_{\mathrm{reduce}}$ behave as the number $K$ of
reductions per modulus changes?

**RQ5: Scalar portability.** Do the same parameter regions remain useful on a
second scalar machine or ISA? SIMD and hardware require separately frozen
future experiments.

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

Each reduction result row records the registry name, and every matched reducer
comparison uses the same materialized input corpus.

The timing scope is explicit:

| Registry name | Timed mathematical operation | Status |
|---|---|---|
| `reduction-steady-state:v1` | reduction of a materialized degree-below-$2m$ input into a preallocated output | implemented |

For steady-state microbenchmarks, reusable plans, materialized inputs,
outputs, and scratch buffers exist before the clock starts. Input generation,
allocation, correctness checks, checksum consumption, and reporting remain
outside. Reusable setup is reported through the separate setup and
amortization contract. The evaluated mathematical operation is only
$A\mapsto A\bmod g$ for $\deg A<2m$.

Setup uses the separate `modulus-plan:v1` scope. From materialized $m$, taps,
and $g$, it includes each reducer's schedule or reciprocal construction and
plan-owned scratch allocation. Parsing, shared modulus materialization,
benchmark input/output buffers, validation, reporting, and teardown are
excluded. Setup is sampled through fresh plan constructions; the plan used for
steady-state timing is constructed separately. Preserve the raw per-method
$T_{\mathrm{setup}}$ and $T_{\mathrm{reduce}}$ values, then derive
$T_{\mathrm{setup}}+KT_{\mathrm{reduce}}$ only for explicitly stated $K$.
The dense-map baseline includes map generation and allocation in setup and
reports map storage separately. The generated-code baseline reports source
generation, compilation, loaded-plan allocation, their summed setup cost, and
three explicit code-size quantities without hiding them inside steady-state
reduction timing.
The implemented `requested-owned-bytes:v1` model separately reports the
context structures and lifetime-owned buffers of GS, Serial, Naive, Barrett,
and the opt-in Dense baseline. Storage is inspected on the plans used for correctness and
steady-state timing only after the independent setup samples have stopped, so
the inspection itself is outside both timed regions. Allocator overhead,
shared modulus storage, benchmark buffers, and transient library workspace are
not estimated.

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

- nanoseconds per reduction under the implemented portable timing contract;
- cycles per reduction only under a future explicitly frozen PMU and
  core-type contract;
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
- temporary memory;
- `scalar-source-v1` aligned/cross-word contributions, nonzero word shifts,
  word XORs, logical array accesses, and scratch words.
- median, p90, and p99 for runtime, $\Delta_{\min}$, $D_{\mathrm{fb}}$, and
  $\sum_k h_k$.

The modulus manifest preserves only the source fields `sample_id`,
`provenance`, $m$, and the complete tap set. The experiment driver derives
$s$, $h$, $\Delta_{\min}$, $D_{\mathrm{fb}}$, the complete $(h_k)$ profile,
and $W_{\mathrm{fb}}$ from those fields and cross-checks the native output.
Irreducibility metadata is required only for field-level experiments whose
claims depend on it, not for general reduction correctness or timing.

### 9.4 Planned Figures

The implemented geometry-only SVG path validates $h$ and
$m/\Delta_{\min}$ and emits one panel per fixed $m$ before any method winner
is assigned. Repeated timing trials collapse to one support point only after
their coordinates agree; the $T=\varnothing$ boundary is reported separately
because $\Delta_{\min}$ is undefined.

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
5. scalar cross-platform results;
6. setup and storage.

### 9.6 Negative Results

Report openly:

- high-weight regimes where generalized Suwako loses;
- friendly moduli where serial folding is already sufficient;
- small degrees dominated by loop overhead;
- architectures with expensive cross-limb shifts;
- quasi-linear multiplication regimes where the asymptotic comparison changes.
