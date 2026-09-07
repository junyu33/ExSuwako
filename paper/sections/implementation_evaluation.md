# Implementation and Evaluation Draft

This document defines the paper-facing implementation model, research
questions, parameter grid, metrics, and figures. Execution order, checkbox
status, and artifact requirements are maintained only in
[the experimental TODO](../exp_todo.md).

## 8. Implementations

### 8.1 Reference Implementation

- naive long division;
- Python/Sage Frobenius-factorized reduction (FFR);
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
- immutable synchronous-stage semantics, with a proved low-to-high in-place
  scalar realization;
- no undefined shifts;
- constant-time field-element handling.

The implemented scalar FFR and Serial reducers share the word/bit shift
descriptors, high-part extraction, and low/carry right-shift components in
`sparse_shift.h`.  FFR retains its destination-oriented gather traversal and
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
The native `LopezDahabLoop` mode uses ordinary tap and high-word loops. In
addition to the paper's strict domain, it supports the word-aligned boundary
$\deg q=m-W$: dedicated differential tests cover 1,536 such cases because no
feedback returns to the source word at equality. It is compared with the ordinary-loop FFR
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
   word-level reduction algorithm when its $\deg q<m-W$ assumption holds,
   together with the tested ordinary-loop boundary $\deg q=m-W$;
3. Barrett;
4. Montgomery only in a separately frozen Montgomery-domain multiplication
   workload, not in the current direct $A\mapsto A\bmod g$ microbenchmark;
5. the implemented opt-in row-major dense linear map for
   $H\mapsto x^mH\bmod g$, evaluated by packed row parity;
6. the existing `Naive` ordinary polynomial long division as the generic
   correctness/portability reference, not a tuned performance competitor.

The implemented exact-manifest phase path admits either Dense or ordinary-loop
López--Dahab as the fourth method beside FFR, Serial, and Barrett. Dense retains
its explicit matrix-size ceiling; ordinary-loop López--Dahab retains $m>W$ and
$\deg q\le m-W$. The two modes are mutually exclusive and neither is promoted to
a final winner panel unless the formal sweep shows that it is a credible
strong baseline in the corresponding region.

### 8.6 Optional RTL Prototype

No RTL prototype is planned for the current software-reduction study. A future
hardware study would compare serial sparse folding, FFR, and a
fixed dense XOR network, and would report latency, frequency, area/LUTs,
registers, throughput, and pipeline depth under one frozen synthesis flow.

## 9. Evaluation

### 9.1 Research Questions

**RQ1: Correctness.** Does FFR agree with independent reducers
for arbitrary tap sets?

The current validation record establishes agreement for the binary core by
randomized and exhaustive tests, and separately tests the coefficient-algebra
identity over GF(4) and \(\mathbb F_2[\varepsilon]/(\varepsilon^2)\).  These
tests can falsify an implementation or a stated identity; they do not replace
the correctness proof. The portable-C differential suite additionally checks
FFR, serial folding, naive long division, and gf2x-backed Barrett on 1,400
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
constructed FFR plan.  The phase-diagram driver derives these quantities
independently from the complete tap set and rejects any row whose schedule
metadata disagrees with the predicted geometry.  This checks the structural
predictor before it is correlated with timing data; it does not by itself
establish the latency-scaling claim or an instruction-count model.
The retained six-panel data collapse to 72 distinct
$(m,\Delta_{\min})$ coordinates. A two-panel depth figure plots the six
fixed-$m$ gap sweeps and the $\Delta_{\min}=1$ scaling slice; every emitted
native stage count agrees exactly with
$D_{\rm fb}=\lceil\log_2(m/\Delta_{\min})\rceil$, and the six power-of-two
gap-one points lie on $D_{\rm fb}=\log_2m$. This is an implementation-level
check of schedule depth, not evidence that wall-clock latency equals the
stage count or that one software stage is one circuit layer.
The separate `scalar-source-v1` profile models the complete portable FFR data
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
The implemented primary path materializes one input batch per support, checks
FFR, Serial, and gf2x-backed Barrett on that batch, and then times all three on
the same immutable inputs under cyclic method-order rotation.
Controlled phase samples are generated as a complete feasible Cartesian grid
of explicitly selected $(m,h,\Delta_{\min})$ values. The highest tap is fixed
to $m-\Delta_{\min}$ and the remaining taps are deterministically spread, so
weight and feedback gap can be swept independently. Constant-free and
constant-present grids have distinct provenance labels, and infeasible cells
are rejected rather than omitted. These controlled points isolate the two
axes; fixed-weight random-support quantiles remain a separate experiment.

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
serial folding, FFR, and multiplication-based reduction be
organized by support size and feedback difficulty, while preserving the
dependence on modulus degree, word size, and implementation platform?

### 9.2 Parameter Grid

The six main fixed-degree panels use a $2\times3$ layout and

$$
m\in
\{128,512,2048,8192,32768,131072\}.
$$

Intermediate controlled panels use
$m\in\{256,1024,4096,16384,65536\}$.  The large-degree scaling slice extends
through $m=2^{20}$ without repeating the complete random-support sweep above
$m=131072$.

The controlled high-weight extension samples every feasible power-of-two
$\Delta_{\min}$ on one common logarithmic weight grid, retaining the earlier
crossover-refinement weights. It explicitly disables Serial plan construction and timing after the
primary panels have established that Serial is far outside the competitive
region.  FFR and Barrett remain present at every extension point; ordinary-loop
ordinary-loop López--Dahab is retained for $\Delta_{\min}\ge W$. This is a
separately labelled method set, not missing Serial data silently interpreted as
a loss.

$$
h\in
\{2,3,5,9,17,33,65\},
$$

$$
\Delta_{\min}
\in
\{1,2,4,\ldots,m/2\}.
$$

Include:

- fixed-weight monic binary polynomials with support sampled uniformly from
  $\{0,\ldots,m-1\}$;
- synthetic controlled families for worst-case and friendly tap placement;
- arbitrary monic moduli with irreducibility unclassified as the primary
  ring-level stress tests;
- $0\in T$ and $0\notin T$ cases;
- $T=\varnothing$ and the resulting $q=0$ case;
- constant-free, constant-one, and dense-$q$ cases;
- non-word-aligned degrees.

Here $s=0$ is the separate $q=0$ boundary case. For each $(m,s)$ with
$s\ge1$, sample enough independent supports to report median, p90,
and p99 rather than only the mean. Do not label this model "random
polynomials" without specifying the fixed weight: unconstrained random
polynomials are typically dense.

The formal grid requests 256 distinct exact supports per $(m,h)$ cell.  When
the constant-free population is smaller, it uses the complete population; in
particular, $(m,h)=(128,2)$ contains only 127 supports.  The deterministic manifest
generator records the sampler, master seed, population, requested count, and
realized count before timing.  The implemented fixed-weight summarizer
requires at least 100 distinct exact supports per cell by default and first
takes the median of retained
trial measurements for each support and only then computes the cross-support
median and nearest-rank p90/p99. Thus machine-level timing repetition is not
treated as additional draws from the support distribution. Duplicate tap
sets, incomplete trial sequences, mixed experiment contracts, and provenance
outside the registered fixed-weight families are rejected. The formal panels
use `synthetic-fixed-weight-uniform-constant-free:v1`; the older unrestricted
family remains separately labelled. Both the
support-level medians and the cell summaries are retained, so losing and tail
cases remain auditable rather than being replaced by favorable examples.

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
context structures and lifetime-owned buffers of FFR, Serial, Naive, Barrett,
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
The frozen phase diagram therefore does not include a separate real
irreducible-modulus panel and makes no field-level performance claim;
synthetic rows are identified by provenance but are not called reducible
unless reducibility has actually been established.

Paper-grade rows use `exsuwako-native-platform:v1`. A reviewable JSON snapshot
records the clean commit, benchmark binary SHA-256, compiler and flags,
resolved gf2x library, platform, hostname, selected logical CPU,
governor/EPP/turbo observations, portable implementation registry, and
multiplication backend. The driver enforces the recorded CPU affinity and
adds its own command plus the exact native command to every row. Paper-grade
mode rejects absent metadata, dirty or mismatched commits, and a binary digest
mismatch; exploratory rows cannot pass the paper-grade winner analyzer. A
direct audit of the 67,576 retained formal trial rows found every required
field present and every one of the 1,096 sample trial sequences complete and
internally consistent. All rows use the same compiler, flags, gf2x library,
platform, affinity, frequency policy, word width, input distribution, timing
scope, setup scope, implementation, and multiplication backend. Collection
spans three clean commits only to introduce the explicit no-Serial
high-weight method set and then the tested López--Dahab boundary
$\Delta_{\min}=W$; no sample pools trials across commits.

### 9.4 Planned Figures

The implemented geometry-only SVG path validates $h$ and
$m/\Delta_{\min}$ and emits one panel per fixed $m$ before any method winner
is assigned. Repeated timing trials collapse to one support point only after
their coordinates agree; the $T=\varnothing$ boundary is reported separately
because $\Delta_{\min}$ is undefined.
The implemented winner analyzer uses a deterministic 10,000-resample
bootstrap for each method median and for trial-paired runtime ratios. A point
receives a unique winner only when every method's relative interval half-width
is at most 1%, the median advantage over every competitor is at least 1%, and
every paired-ratio interval lies strictly below one. Otherwise the point is
retained as a timing, operational, or statistical uncertainty. The SVG path
colors one equal-area block per measured support, marks uncertainty in gray,
and never interpolates an unmeasured cell. The retained paper-grade rows
produce 1,096 cells across the six fixed-$m$ panels: 983 unique winners, 103
timing-unstable cells, 10 operational ties, and no statistical ties. The
renderer can overlay pair-labelled winner boundaries from a separate
prediction table.  The reproducible fitting script alternates sorted points
between calibration and holdout sets at each fixed $m$, fits affine runtime
models to the portable scalar FFR and López--Dahab word-work formulas, and uses
the fixed-$m$ calibration median for Barrett.  Its interfaces are descriptive
model predictions: they do not recolor measured cells, interpolate missing
coordinates, or constitute a crossover theorem.

The measured persistent Barrett crossover is defined slice by slice as the
first stable Barrett winner after which all later stable sampled weights also
select Barrett; uncertain cells never manufacture a crossover. The resulting
onset ranges are:

| $m$ | $\Delta_{\min}<64$ | $\Delta_{\min}\ge64$ |
|---:|---:|---:|
| 128 | $33$--$65$ | $65$ |
| 512 | $97$ | $129$ |
| 2048 | $65$--$97$ | $129$--$193$ |
| 8192 | $129$ | $257$--$385$ |
| 32768 | $225$--$257$ | $513$--$769$ |
| 131072 | $641$ | not observed through $1025$ |

The first column shows FFR losing to multiplication-based reduction as weight
increases in the difficult-feedback regime. In the second, ordinary-loop
López--Dahab increasingly replaces FFR and delays the Barrett crossover. The
smallest degree is visibly overhead-sensitive: at $m=128$ Barrett takes over
by $h=33$--$65$, while López--Dahab wins only two friendly cells. The measured
low-feedback FFR/LD pockets are not monotone, so the exact per-slice runs and
uncertain cells are retained alongside this aggregate table.

Two complementary six-panel slice figures prevent the phase coordinates from
being read as a single undifferentiated notion of sparsity. At fixed
$\Delta_{\min}\in\{1,64\}$, the horizontal coordinate is $\log_2(h-1)$; at
fixed $h\in\{9,65\}$, it is $\log_2(m/\Delta_{\min})$. Both figures report
$\log_2(T_{\rm method}/T_{\rm FFR})$, so the zero line is the empirical
crossover, positive values favor FFR, and negative values favor the competing
method. The fixed-gap slices expose the weight-driven FFR--Barrett crossover,
whereas the fixed-weight slices show how feedback geometry changes the
comparison without changing tap count. L\'opez--Dahab is drawn only on its
measured applicability domain, and non-unique winner classifications remain
visible as hollow markers. The plots use controlled supports and therefore
do not substitute for the separate random-support quantiles.

Setup is analyzed from the same 1,096 exact supports rather than folded into
steady-state reduction. For mandatory, explicitly listed reuse counts $K$, the
derived table retains each method's component medians and computes

$$
T_{\rm total}(K)=T_{\rm setup}+K T_{\rm reduce},\qquad
\bar T(K)=T_{\rm reduce}+T_{\rm setup}/K.
$$

Six amortization panels plot the median competitor/FFR ratio and the p10--p90
range across measured controlled cells. They show that setup can change the
descriptive grid-median ordering at small $K$: the Barrett/FFR curve changes
sign with reuse at $m=128$ and $m=2048$, while L\'opez--Dahab's lightweight
plan is already favorable over most of its measured applicability domain.
The breadth of the bands also rules out a single support-independent
break-even count. A companion six-panel map plots every support at
$(\log_2(W_{\rm fb}+1),D_{\rm fb})$ and encodes measured FFR setup by color.
It is a source-geometry and scalar-setup visualization, not a minimal-work,
instruction-count, or circuit-depth claim. Because the quantiles summarize a
designed Cartesian grid, they are not estimates over a random modulus
population.

The formal scheduled coefficient work is also compared directly with native
FFR time without identifying the two quantities. Within each fixed-$m$ panel,
the scatter of $\log_2W_{\rm fb}$ against the median
$\log_2(\mathrm{FFR\ ns})$ has Spearman coefficient between $0.987$ and
$0.993$ across the six degrees. This is strong monotone predictive evidence
on the controlled grid, while the visible residual structure and the separate
source-word analysis prevent it from being presented as an instruction-count
or exact runtime model.

The random-support geometry experiment is deliberately timing-free. The six
frozen constant-free fixed-weight manifests contain 10,623 distinct supports:
256 for every $(m,s)$ cell with
$s\in\{1,2,4,8,16,32,64\}$ except the exhaustive 127-support population for
$(m,s)=(128,1)$. Exact reconstruction from each tap list shows median feedback
depth growing approximately as $1+\log_2s$ and median normalized work
$W_{\rm fb}/m$ growing approximately linearly with $s$; nearest-rank p90 and
p99 curves retain the upper tail. These observations are computational
support-geometry evidence for the random-support theorem targets, not a proof
and not a measurement of random-support reduction speed.

The operator schematic is generated independently of all benchmark data. It
shows the state chain

$$
X_{k+1}=(I+U^{2^k})X_k
$$

with one immutable old state per stage, the doubling of every active shift
distance, and termination at $U^{2^r}=0$. A concrete $m=16$ example with
$T_+=\{3,11,15\}$ shows the active shift sets
$\{1,5,13\},\{2,10\},\{4\},\{8\}$ and the pruning of shifts reaching $m$.
It also states that mixed feedback paths arise through factor composition,
not through a materialized pairwise-sum schedule. This is a construction
diagram only; it is not included among measured performance or circuit-depth
evidence.

1. **Schematic classical algorithm-selection phase diagram.** For a fixed
   $m$, show modulus Hamming weight $h$ horizontally and
   $m/\Delta_{\min}$ vertically on a logarithmic scale. Label the three
   conceptual regions: serial sparse folding (shift/XOR) for friendly sparse
   supports, FFR for sparse supports with difficult feedback,
   and Barrett/multiplication-based reduction at higher support sizes.
2. **Empirical phase-diagram panels.** For several fixed values of $m$, plot
   sampled supports and color each point by the measured winner among serial,
   FFR, and Barrett. Use the same coordinates as the schematic
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
FFR depends on the full active-tap profile
$r+\sum_k h_k+s$, not only on $s$ and $\Delta_{\min}$. The caption should
state that exact region boundaries are implementation- and
platform-dependent. Cells with close timings or inconsistent winners should
be marked as uncertain rather than forced into a clean region.

### 9.5 Evidence Tables

The tables below contain only completed-gate evidence. In particular, they do
not turn the open proof audit into a proved theorem, call synthetic moduli
irreducible, or substitute the single-machine portable-C run for a
cross-platform experiment.

| Method | Direct-reduction applicability | Role in retained evidence | Reusable setup object | Boundary |
|---|---|---|---|---|
| Frobenius-factorized reduction (FFR; internal key `GS`) | Any monic binary modulus | Primary portable-C method | doubled-shift schedule and one state plus a sentinel | full tap geometry controls work and traffic |
| Serial folding | Any monic binary modulus | Matched sparse baseline on the original grid; omitted from the high-weight extension after screening | sorted tap descriptors and state buffers | long dependency chain for small $\Delta_{\min}$ |
| BarrettGF2X | Any monic binary modulus | Primary multiplication-based baseline | reciprocal $\mu$ and reusable product buffers | depends on gf2x multiplication thresholds |
| L\'opez--Dahab loop | $\deg q\le m-W$, equivalently $\Delta_{\min}\ge W$ | Matched ordinary-loop baseline only where applicable | tap descriptors and a reusable $2m$-bit work buffer | not applicable outside its degree assumption |
| Dense row-parity map | Any fixed monic modulus while the packed map is at most 64 MiB | Diagnostic screen, not a retained winner method | packed $m\times m$ binary map and high-part scratch | quadratic storage; diagnostic evidence only |
| Naive long division | Any monic binary modulus | Independent correctness and portability reference | lightweight context | not presented as a tuned performance competitor |
| Generated reducer | Fixed modulus | Implementation exists, but excluded from the general-code MoC winner contract | generated/compiled code | code generation is a different specialization contract |
| Montgomery | Montgomery-domain operands | Not a matched direct-reduction baseline | Montgomery constants and representation | REDC computes $AR^{-1}\bmod g$, not $A\bmod g$ |

| Candidate statement | Current status | Completed computational evidence | Remaining boundary |
|---|---|---|---|
| Low/high feedback decomposition and reduction correctness | first internal hostile audit passed | 20,000 random GF(2) trials and 299,592 exhaustive binary modulus/input pairs; native reducers are differentially checked against long division | external review |
| Sparse Frobenius powers and factored inverse | first internal hostile audit passed for the binary theorem | independent agreement over GF(2), $\mathbb F_4$, dual numbers, and $\mathbb F_3$ sign/radix checks | coefficient-algebra extension remains separate |
| Exact feedback-stage count | first internal hostile audit passed | exhaustive native schedule checks at all 72 tested $(m,\Delta_{\min})$ coordinates | feedback depth must not be called bounded-fan-in gate depth |
| Geometry-sensitive scheduled work $W_{\rm fb}$ and its coarse upper bound | first internal hostile audit passed | all 262,125 nonempty supports for $2\le m\le18$ pass the formula/bound checks; fixed-$m$ runtime correlation is $0.987$--$0.993$ | external review of the coefficient- and packed-word models |
| Random-support depth/work laws | first internal hostile audit passed | exact reconstruction for 10,623 frozen supports; reported median, p90, and p99 trends | the theorem applies only to the stated uniform fixed-weight model |

| Modulus corpus | Irreducibility status | Evidence currently supported | Claim boundary |
|---|---|---|---|
| Controlled fixed-weight Cartesian supports | deliberately unclassified | 1,096 paper-grade reduction-only timing cells | implementation/platform phase diagram, not field performance |
| Frozen random fixed-weight supports | deliberately unclassified | geometry for 10,623 distinct supports | no random-support timing claim |
| Arbitrary monic correctness corpus | may include reducible moduli | differential and theorem-falsification checks | correctness does not require irreducibility |
| Real named irreducible moduli | certificate required | not yet timed | real-modulus and field-level performance are deferred |

The portable-C summary uses the controlled constant-free slice
$(h,\Delta_{\min})=(9,1)$. The crossover column is the first stable Barrett
winner on the $\Delta_{\min}=1$ slice after which every later stable sampled
weight is also Barrett; uncertain cells do not create a crossover.

| $m$ | FFR at $(9,1)$ (ns) | Barrett/FFR at $(9,1)$ | persistent Barrett $h$ | Barrett/FFR at onset |
|---:|---:|---:|---:|---:|
| 128 | 64.1 | 2.164 | 33 | 0.881 |
| 512 | 272.9 | 3.807 | 97 | 0.718 |
| 2048 | 1079.2 | 4.247 | 97 | 0.664 |
| 8192 | 4390.2 | 8.654 | 129 | 0.819 |
| 32768 | 17008.4 | 16.768 | 257 | 0.881 |
| 131072 | 68167.1 | 37.712 | 641 | 0.886 |

All times above are medians in nanoseconds under
`portable-scalar-c:v1`, `reduction-steady-state:v1`, and `gf2x:v1` on the
recorded primary machine. They are not cross-platform results.

At the same $(h,\Delta_{\min})=(9,1)$ anchor, setup and requested plan-owned
storage are:

| $m$ | trials | FFR setup ns / bytes | Serial setup ns / bytes | Barrett setup ns / bytes |
|---:|---:|---:|---:|---:|
| 128 | 127 | 596.5 / 744 | 119.5 / 416 | 782.0 / 184 |
| 512 | 127 | 719.5 / 888 | 123.5 / 512 | 4770.5 / 376 |
| 2048 | 127 | 887.5 / 1176 | 137.0 / 896 | 50799.0 / 1144 |
| 8192 | 127 | 1152.0 / 2040 | 149.0 / 2432 | 558369.5 / 4216 |
| 32768 | 127 | 1312.0 / 5208 | 235.0 / 8576 | 7760258.5 / 16504 |
| 131072 | 31 | 2832.5 / 17592 | 856.5 / 33152 | 119030566.0 / 65656 |

Setup uses `modulus-plan:v1`; bytes use
`requested-owned-bytes:v1` and exclude allocator overhead, shared modulus
storage, benchmark buffers, and transient library workspace. A scalar
cross-platform table remains planned and is intentionally absent.

### 9.6 Negative Results

Report openly:

- high-weight regimes where FFR loses;
- friendly moduli where serial folding is already sufficient;
- small degrees dominated by loop overhead;
- architectures with expensive cross-limb shifts;
- quasi-linear multiplication regimes where the asymptotic comparison changes.

### 9.7 Artifact Status

The reduction-only artifact is frozen by
`bench/artifact/paper-v1.json`. The repository retains no CSV payload: the
external canonical dataset is identified by its 67,576-row count and SHA-256,
while tracked JSONL manifests preserve deterministic support generation. The
artifact accepts three explicitly recorded experiment-commit/binary cohorts;
all remaining platform and contract metadata must agree.

At artifact commit `4465388`, a detached fresh worktree completed `make check`,
verified the external datasets, regenerated all 26 reduction products and both
Rabin products with exact hash agreement, reran the measured cost-model
analysis, completed a 124-row metadata-complete reduction smoke test, and
compiled the manuscript. The tracked validation record contains hashes for
the external log, smoke rows, metadata snapshot, and artifact report. Thus the
timing and application artifacts are independently reproduced. This audit
adds no proof or cross-platform evidence beyond the scoped claims of those
artifacts.

### 9.8 Rabin Irreducibility E2E Pilot

The first application experiment uses the complete Rabin irreducibility test
at a power-of-two degree.  The matched paths share one scalar bit-dilation
squarer and NTL GCD/check implementation and differ only in the selected
reducer; NTL `IterIrredTest` is a separate optimized complete-library
baseline.  The primary `rabin-power-of-two-irred:v1` interval includes reducer
setup, all $m$ modular squares, the $m/2$ checkpoint GCD, and the final
$x^{2^m}=x$ test.

The deterministic scaling manifest contains one Sage-certified irreducible
modulus at each $m\in\{128,512,2048,8192\}$, all with
$(h,\Delta_{\min})=(9,1)$.  Across 31 paper-grade trials pinned to CPU 0,
NTL/FFR median complete-time ratios are 1.35, 2.31, 3.64, and 8.04; matched
Barrett/FFR ratios are 1.60, 3.76, 3.27, and 6.81. All paired bootstrap 95%
intervals remain above one.  The FFR squaring chain grows from about 85.5% to
98.9% of its complete time.  Serial is retained through $m=2048$ but omitted
at $m=8192$ after one smoke trial took about 47.5 seconds.  The separate Rabin
artifact hash-locks all 465 raw rows and deterministically reconstructs the
summary and paper figure.
