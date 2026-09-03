# Experimental TODO

This file is the authoritative execution checklist for ExSuwako experiments.
The paper structure and claim status remain in
[writing_guide.md](writing_guide.md); the paper-facing research questions,
parameter model, metrics, and planned figures remain in
[sections/implementation_evaluation.md](sections/implementation_evaluation.md).

Do not infer a paper claim from a checked implementation task. Advance
evidence through the following levels:

1. correctness;
2. operation-count and cost-model validation;
3. matched reduction microbenchmarks;
4. reproducible artifact validation.

Checkbox notation is `[x]` for completed work, `[ ]` for open work, and `[-]`
for an item that was reviewed and found not applicable to the frozen
experiment contract.  A `[-]` item must retain the reason rather than silently
disappearing from the checklist.

## Source Coverage and Provenance

This checklist consolidates executable experimental work; it does not replace
the mathematical arguments, literature judgments, or conversation records in
the source notes. In particular, files under `raw/` remain research
provenance rather than paper evidence. The following map records how their
actionable experimental content is covered:

| Source | Experimental content retained here | Non-experimental content remains in |
|---|---|---|
| [README.md](../README.md) and [native_benchmark.md](../bench/native_benchmark.md) | Current inventory, benchmark contract, gf2x provenance, and artifact rules in Current Inventory, P0, and Gate 4 | The source files as implementation documentation |
| [writing_guide.md](writing_guide.md) | Evidence levels and completion criteria in all gates | Paper structure, claim status, and submission gates |
| [implementation_evaluation.md](sections/implementation_evaluation.md) | Implementations, baselines, RQ1--RQ7, parameter sweeps, metrics, figures, tables, and negative results in Gates 1--4 | Paper-facing evaluation design |
| [extensions_appendices.md](sections/extensions_appendices.md) | Claim-to-evidence experiments and former implementation/evaluation TODOs in Gates 1--4 | Mathematical, prior-art, appendix, and submission planning |
| [application.md](notes/application.md) | No executable gate: application material is motivation and possible future work, not part of the reduction experiment contract | Application motivation and provenance |
| [math_1.md](raw/math_1.md) and [math_2.md](raw/math_2.md) | Optional coefficient-algebra checks in Gates 1 and 2 | General algebraic derivations, proofs, and open problems |
| [related_1.md](raw/related_1.md), [related_2.md](raw/related_2.md), and [related_3.md](raw/related_3.md) | Their demands for matched classical comparisons enter Gate 3 | Hostile-search records summarized in [related_work.md](sections/related_work.md) and tracked in [prior_art_plan.md](notes/prior_art_plan.md) |
| [math_comp.md](notes/math_comp.md), [technical_body.md](sections/technical_body.md), [intro_draft.md](sections/intro_draft.md), and [venue_choice.md](notes/venue_choice.md) | Any evidence requirements are represented by Gates 1--4; these files define no independent experiment queue | Mathematical synthesis, manuscript prose, and venue strategy |
| [experiment-planning skill](../skills/exsuwako-experiment-planning/SKILL.md) and [paper-writing skill](../skills/exsuwako-paper-writing/SKILL.md) | Both skills route experimental work to this file and deliberately contain no duplicate checklist | Workflow instructions in the skill files |

When a source note gains a new executable experiment, add it to the relevant
gate here and update this map. Do not mark a source as covered merely because
it uses the word "experiment"; preserve proof obligations and prior-art work
in their own documents.

## Current Inventory

The following items describe code that exists, not completed paper evidence.

- [x] A unified native reduction API exposes generalized Suwako, serial sparse
      folding, naive long division, gf2x-backed Barrett, ordinary-loop
      López--Dahab Algorithm 2, and dense linear-map reduction.
- [x] The native correctness checks compare the four unrestricted native
      reducers plus ordinary-loop López--Dahab wherever its stated degree
      assumption holds across representative aligned and non-aligned degrees,
      and separately verify opt-in Dense against long division.
- [x] Reduction-only benchmark and phase-diagram drivers exist under
      bench/scripts/.
- [x] Local exploratory CSV files are separated under bench/data/ and are
      ignored by Git.
- [ ] Rerun every claimed correctness and timing result from the eventual
      experiment commit and record the command, seed, compiler, gf2x path,
      machine, CPU-affinity policy, and raw output.

The current reduction benchmark samples uniformly from the full
degree-below-$2m$ input domain and measures only reduction modulo the selected
monic polynomial $g$.

## P0: Freeze the Experimental Contract

The frozen binary tap convention is

$$
g(x)=x^m+\sum_{t\in T}x^t,
\qquad
T\subseteq\{0,\ldots,m-1\}.
$$

`taps` is the complete, explicit, ascending list `sort(T)`. It excludes the
leading exponent $m$, contains no duplicates, and may be empty. Set $s=|T|$
and let $h=s+1$ be the Hamming weight of the complete monic modulus. Tap order
has no mathematical meaning; sorting is the canonical serialized form. Native
experiment inputs must already satisfy this convention rather than relying on
silent deduplication or normalization.

- [x] [Q] Freeze the tap convention, including whether the constant tap is
      listed explicitly and whether $h$ includes the leading term. [A]
      `taps=sort(T)` is the complete ascending nonleading support, includes
      exponent 0 exactly when present, excludes $m$, permits the empty set,
      and defines $s=|T|$ and $h=s+1$.
- [x] [Q] Add an exact tap-list or manifest input mode; do not rely only on a
      seed to recover the tested modulus. [A] Use the exact tap-list CLI or a
      JSONL manifest; a seed alone is not the modulus identity.
- [x] [Q] Emit the complete tap set, irreducibility status, provenance, $m$,
      $h$, $\Delta_{\min}$, active-tap profile, and sample identifier. [A]
      General reduction rows preserve `sample_id`, `provenance`, $m$, and
      complete taps, then deterministically derive and emit $s$, $h$,
      $\Delta_{\min}$, feedback stages, active-tap profile, and scheduled
      work; irreducibility is recorded separately only for field-level claims
      that require it, because general reduction does not assume it.
- [x] [Q] Define and name each input distribution: high monomial, random high
      half, multiplication product, polynomial square, and
      application-generated state. [A] The experiment scope was narrowed to
      reduction of arbitrary inputs with degree below $2m$; the sole primary
      distribution is `uniform-full-range:v1`, which samples $A=L+x^mH$ for
      independent uniform $m$-bit $L,H$. Products and squares are subsets of
      this reduction domain and are not separate reduction distributions;
      application workloads are outside the current reduction-only contract.
- [x] [Q] Freeze the timed boundary for reduction-only, square formation,
      modular squaring, multiplication, and end-to-end workloads. [A] The
      experiment scope was narrowed to reduction-only:
      `reduction-steady-state:v1` times batched reduction of materialized
      inputs $A$ with $\deg A<2m$ modulo the selected monic polynomial $g$
      through `reduce_into()`; reusable setup, allocation, validation, and
      reporting remain outside, while square formation, multiplication, and
      end-to-end workloads are not measured.
- [x] [Q] Freeze setup accounting: schedule generation, reciprocal
      generation, dense matrices, allocation, and
      amortization over $K$. [A] `modulus-plan:v1` reports the median time over
      fresh plan constructions from materialized $m$, taps, and $g$, including
      schedules, reciprocals, and plan-owned scratch allocation while
      excluding parsing, shared modulus materialization, benchmark buffers,
      validation, reporting, and teardown; preserve raw
      $T_{\mathrm{setup}}$ and $T_{\mathrm{reduce}}$ and derive
      $T_{\mathrm{setup}}+KT_{\mathrm{reduce}}$ only for an explicitly stated
      $K$; dense-map generation and allocation are included in its setup and
      its stored-map size is reported separately.
- [x] [Q] Freeze compiler flags, word width $W$, gf2x build and linkage, CPU
      affinity, frequency policy, warm-up, repetitions, aggregation, and
      outlier treatment. [A] On each recorded platform, build with the
      archived compiler and `-O3 -std=c11 -Wall -Wextra`, emit $W$, record the
      resolved gf2x library, pin the complete driver to one documented logical
      CPU, record its governor/EPP/turbo policy, cyclically rotate method
      order, discard one whole-invocation warm-up, and retain at least 31
      independent trial rows, each containing the median of 12 timed batches
      over the same deterministic inputs and balancing every timing position
      in both three- and four-method runs; report the across-trial median and
      a deterministic bootstrap 95% interval, delete no outliers, add retained
      trials or mark the point uncertain when the interval's relative
      half-width exceeds 1%, and never pool rows across different toolchain,
      linkage, affinity, or frequency policies.
- [x] [Q] Use deterministic seeds and preserve failing or anomalous cases as
      permanent regression inputs. [A] Every random path uses a deterministic
      recorded seed, identical phase-driver seeds are regression-tested to
      reproduce support identities and geometry, and native correctness
      failures print seed, suite, degree, trial, complete taps, and exact input
      words; minimized failures are added as word-width-independent
      bit-exponent cases in
      `tests/reduction_regressions.h`, while benchmark-only anomalous supports
      are retained with `sample_id`, provenance, degree, and complete taps in
      `bench/manifests/regression_supports.jsonl` rather than as committed
      exploratory CSV.

## Gate 1: Correctness

- [ ] At the frozen experiment/artifact commit, run `make check` and archive
      its complete output together with the environment metadata required by
      Gate 4. Ordinary development commits do not independently reset this
      item; rerun it after changes that affect algorithms, tests, toolchains,
      or experimental semantics.
- [x] [Q] Exhaust all tap sets and all inputs for small $m$ where feasible.
      [A] [Round 1](../tests/check_theory_round1_gf2.py) checks every monic
      binary modulus and every input of degree below $2m$ for $m\le6$ against
      independent long division, totaling 299,592 exhaustive modulus/input
      pairs, and adds 20,000 random GF(2) cases with $m\le128$, all with no
      mismatch.
- [x] [Q] Cover $\Delta_{\min}=1$, taps at both ends, mixed aligned and
      unaligned shifts, dense supports, constant-free moduli, reducible
      moduli, and non-word-aligned degrees. [A] The deterministic native suite
      runs 10,000 stratified random full-input cases for $1\le m\le512$ plus
      700 fixed-degree cases and prints a directly reproducible case on
      failure.
- [x] [Q] Verify that every generalized-Suwako stage reads one immutable old
      state across all active taps. [A] `tests/check_gs_stage.c` invokes the
      actual private scalar stage kernel without changing the production
      source or API and compares each in-place stage against an independent
      out-of-place, bit-level immutable-old reference for all-aligned,
      all-unaligned, mixed-shift, word-boundary, non-word-aligned-degree, and
      20,000 deterministic random cases.
- [x] [Q] Test feedback closure and final low-part assembly independently.
      [A] `tests/check_gs_components.c` invokes the actual private GS schedule
      and assembly kernels without changing production code or its public API;
      for empty, constant-only, constant-free, dense, mixed-boundary, and
      20,000 deterministic random cases, it separately compares the computed
      closure with a stage-by-stage out-of-place bit reference and assembly
      with $L\mathbin\oplus\sum_{t\in T}(X\ll t)\bmod x^m$ evaluated bitwise.
- [x] [Q] If the coefficient-algebra or positive-characteristic extensions are
      promoted beyond theorem statements, add small exact differential tests
      over at least one non-binary coefficient algebra; do not treat this as
      evidence for the native binary kernel. [A] Round 2 already supplies
      266,304 exhaustive dual-number cases, 20,000 randomized GF(4) cases, and
      10,000 randomized GF(3) cases through `make check`; these validate the
      stated extension identities and sign convention only, not a native
      non-binary implementation or performance claim.
- [x] Verify every native reducer used in reported timing against an
      independent long-division or computer-algebra result before timing it.
      [A] The native differential suite compares ordinary-loop GS, Serial,
      Naive, Barrett, and López--Dahab wherever its degree assumption holds;
      invalid López--Dahab parameters are rejected before timing.
- [-] Preserve exact irreducibility certificates or reproducible Sage checks
      for every modulus labelled irreducible. [A] Not applicable to the
      frozen general-reduction correctness contract: every reducer is tested
      on arbitrary monic binary moduli, and neither correctness nor
      reduction-only timing depends on irreducibility.  Any later field-level
      claim that labels a modulus irreducible must carry its own certificate
      or reproducible Sage check.

## Gate 2: Cost Model

- [x] [Q] Instrument the active taps satisfying $2^k\Delta_t<m$ in every
      feedback stage. [A] The native benchmark obtains
      `active_tap_counts` from the actual GS plan through read-only schedule
      accessors, while the phase-diagram driver independently derives the
      expected profile from $m$ and the complete taps and rejects a mismatch.
- [x] [Q] Check the measured stage count against
      $r=\lceil\log_2(m/\Delta_{\min})\rceil$. [A] The same native plan emits
      `feedback_stages`, including the zero-feedback boundary, and the driver
      checks it against the independently derived exact count before retaining
      a row.
- [x] [Q] Validate the predicted sums of active taps and scheduled coefficient
      applications. [A] The native benchmark obtains
      `feedback_active_tap_sum` and `W_fb` from the actual GS plan, while the
      phase-diagram driver independently checks them against
      $\sum_k h_k$ and $\sum_{t,k}[m-2^k\Delta_t]_+$ before accepting a row.
- [x] [Q] Define and validate source-level word shifts, XORs, reads, writes,
      and temporary words without treating them as compiler instructions or
      hardware memory transactions. [A] `scalar-source-v1` counts the complete
      portable GS data path from the actual plan, while the phase-diagram
      driver independently reconstructs its aligned/cross-word contributions,
      nonzero word shifts, word XORs, logical array accesses, and plan-owned
      scratch words from $m$, taps, and $W$ before accepting a row.
- [x] Validate the formal scheduled coefficient-work sum
      $\sum_{r,k}[m-2^kd_r]_+$ against every generated binary schedule and
      exhaustively enumerate support geometry for $2\le m\le18$; see
      [math_3.md](raw/math_3.md).  This does not validate an instruction-count
      or minimal-circuit model.
- [x] [Q] Separate logical shifts from cross-word and cross-vector shifts.
      [A] `scalar-source-v1` reports zero-bit-offset aligned contributions and
      nonzero-bit-offset cross-word contributions separately. Cross-vector
      shifts are explicitly not applicable to the scalar kernel and require a
      separately named SIMD model if that optional implementation is added.
- [x] [Q] Validate setup time and stored schedule size independently of steady
      state reduction time. [A] `modulus-plan:v1` times fresh plan construction
      and stops before destruction, while `requested-owned-bytes:v1` obtains
      each reducer's context-and-owned-buffer bytes from the separate plan used
      for correctness and steady-state timing only after setup sampling has
      finished. Contract tests preserve every enabled setup and plan-storage field;
      shared modulus, benchmark buffers, allocator overhead, and transient
      library workspace remain excluded.
- [x] Correlate predicted word work with measured reduction runtime without
      relabelling either quantity as the other. [A]
      `analyze_gs_cost_model.py` aggregates retained trials by exact support,
      collapses duplicate tap sets to avoid accidental weighting, and
      computes fixed-$m$ Spearman correlations between `GS_ns` and each
      formal/source predictor separately.  A deterministic bootstrap marks
      supports whose median-runtime interval has relative half-width above 1%
      as uncertain without deleting them.  It explicitly reports nanoseconds,
      not cycles, because the current benchmark has no frozen portable PMU
      contract, and it never calls source-model counts instructions or
      hardware events.
- [x] Record regimes where memory traffic, stage barriers, or instruction
      alignment invalidate a simple operation-count predictor. [A] The same
      analysis uses leave-one-support-out affine prediction from source word
      XORs, preserves per-support residuals, and reports thresholded residual
      diagnostics by logical-access-pressure proxy, feedback-stage band, and
      alignment class.  These source-level partitions identify model-mismatch
      candidates without claiming hardware-level causation; PMU evidence must
      be added under a separately frozen contract before attributing a
      residual to cache traffic or executed instructions.

## Native Implementation Backlog

- [x] Audit the portable scalar implementation for arbitrary public taps,
      non-word-aligned $m$, constant-free moduli, top-word masking, and
      undefined shifts. [A] GS and Serial now reject zero degree, missing tap
      arrays, and taps outside $[0,m)$; Naive and Barrett validate a monic
      degree-$m$ modulus.  GS and Barrett canonicalize oversized output
      buffers, and GS masks the actual degree-$m$ word rather than the final
      capacity word.  The native differential suite checks top padding and
      output tails around $W$, $2W$, and $3W$ boundaries, while the dedicated
      shared-shift test exhausts offsets across zero, aligned, unaligned, and
      beyond-source shifts.  Both `make check` and `make check-sanitize` pass;
      the latter runs the reducer, GS component/stage, and shared-shift suites
      under ASan and UBSan, and GCC `-fanalyzer` reports no scalar-source
      diagnostic.
- [x] Retain the fair shared word-level shift primitive while keeping the
      distinct GS and serial traversals. [A] Both plans use the descriptors
      and right-shift operations in `include/sparse_shift.h`: high-part
      extraction shares `sparse_assign_right_shift`, GS gathers adjacent
      source words through `sparse_right_shift_word`, and Serial scatters one
      loaded source word through the same `sparse_right_shift_low` and
      `sparse_right_shift_carry` components.  Their schedule and traversal
      structures remain intentionally distinct, and the common primitive is
      exercised at every bit offset by `check_sparse_shift.c` under ordinary,
      ASan, and UBSan builds.
- [-] Complete a matched Montgomery baseline where its representation and
      setup assumptions are meaningful. [A] Not applicable to the frozen
      direct-reduction contract: GS, Serial, Naive, and Barrett all compute
      $A\mapsto A\bmod g$ for a materialized $A$ with $\deg A<2m$, whereas
      Montgomery REDC computes $A\mapsto AR^{-1}\bmod g$ between Montgomery
      representations.  Omitting conversion would compare different
      operations; including conversion multiplication and extra REDC calls
      would no longer measure the same reduction-only primitive.  Montgomery
      remains meaningful only in a separately frozen Montgomery-domain
      multiplication workload and is therefore not a Gate 3 curve.
- [x] Include a generic polynomial-remainder implementation as a correctness
      and portability baseline, without presenting it as a tuned sparse
      competitor. [A] The existing `Naive` reducer performs ordinary
      polynomial long division for any monic degree-$m$ binary modulus and
      shares neither the sparse feedback schedule nor the GS factorization.
      It remains in the unified API and differential tests as the independent
      correctness/portability reference; `Naive_ns` may be retained as
      contextual data but is not described as a tuned or strongest
      performance baseline.
- [x] Add a dense linear-map baseline with setup time and storage reported.
      [A] `dense-row-parity:v1` materializes the fixed-modulus $m\times m$
      binary map $H\mapsto x^mH\bmod g$ in row-major packed words, keeps the
      low-part identity implicit, and evaluates every output row by a
      constant-trip-count parity loop.  It is opt-in through `--with-dense`
      together with `--no-naive`, so four-method timing rotation remains
      balanced and default large-$m$ runs allocate no matrix.  Setup includes
      map construction and plan allocation; `Dense_setup_ns`,
      `Dense_plan_bytes`, `Dense_ns`, and `Dense/GS` are emitted separately.
      The native benchmark refuses matrices above 64 MiB, and `make check`
      differentially validates boundary, dense, sparse, constant-free, and
      random moduli against independent long division.
- [x] Add ordinary-loop López--Dahab Algorithm 2 as a matched native baseline
      when its degree assumption holds. [A] The implementation accepts
      arbitrary modulus weight under $\deg q<m-W$, uses the same unified API
      and balanced timing rotation as GS, and reports reusable plan setup,
      storage, and steady-state reduction. The native differential suite
      checks it against independent long division before timing.
- [ ] Add justified SIMD implementations, beginning with one frozen ISA, and
      measure cross-vector shifts and stage barriers separately.
- [ ] Treat AVX-512, NEON, SVE, and RTL as optional extensions until the scalar
      evidence gates are complete.
- [ ] If an RTL prototype is built, report latency, frequency, area/LUTs,
      registers, throughput, and pipeline depth under one synthesis flow.

## Gate 3: Classical Reduction Phase Diagram

The paper-facing definition of this experiment is in
[Implementation and Evaluation, Section 9.4](sections/implementation_evaluation.md#94-planned-figures).

- [ ] For each fixed $m$, place modulus Hamming weight $h$ on the horizontal
      axis and $m/\Delta_{\min}$ on a base-two logarithmic vertical axis.
- [ ] Compare serial sparse folding (shift/XOR), generalized Suwako, and
      gf2x-backed Barrett under the same reduction contract and input corpus.
- [ ] Add optimized ordinary-loop trinomial/pentanomial folding and dense
      linear reduction where they are credible strongest baselines.
- [ ] Sweep controlled synthetic supports so that $h$ and
      $\Delta_{\min}$ vary independently.
- [ ] Sample fixed-weight supports and report median, p90, and p99 rather than
      only favorable examples.
- [ ] Include real irreducible moduli and label reducible ring-level stress
      tests separately.
- [ ] Produce fixed-$m$ winner panels and mark statistically or operationally
      uncertain cells instead of forcing a clean boundary.
- [ ] Record $W$, full tap placement, input distribution, implementation,
      platform, setup policy, and multiplication backend for every panel.
- [ ] Report friendly sparse regions, high-weight losses, small-degree
      overhead, and Barrett crossovers.
- [ ] Plot feedback-stage count versus $\Delta_{\min}$ and gap-one scaling
      versus $m$ to test the predicted depth law.
- [ ] Plot fixed-gap weight sweeps and fixed-weight gap sweeps so that tap
      count and feedback difficulty are not conflated.
- [ ] Plot setup amortization over $K$ and a work--feedback-depth--setup
      tradeoff map.
- [ ] Plot predicted active-tap work against runtime and random-support depth
      and work against $s$.
- [ ] Produce the operator schematic $U,U^2,U^4,\ldots$ as an explanatory
      figure, clearly labelled as a construction diagram rather than measured
      evidence.
- [ ] Populate the planned method, theorem, real-modulus, portable-C, SIMD,
      setup/storage, and optional-hardware tables only from completed gates.

## Gate 4: Reproducibility and Artifact

- [ ] Keep benchmark entrypoints and drivers under bench/scripts/.
- [ ] Keep exploratory raw CSV files under bench/data/; promote only
      documented manifests and final evidence artifacts according to the
      repository publication policy.
- [ ] Emit commit, command, seed, modulus manifest, compiler, linked gf2x
      library, machine, affinity, and timing metadata with every run.
- [ ] Provide one command for correctness, one for cost-model validation, and
      one for reduction microbenchmarks.
- [ ] Regenerate every paper figure and table from recorded raw data.
- [ ] Verify the scoped artifact path from a fresh checkout.
- [ ] Repeat representative classical cases on a second machine or ISA before
      making architecture-independent claims.
- [ ] Record all losing regions and failed hypotheses.

## Completion Gates

- [ ] Every claimed reducer passes an independent correctness check.
- [ ] Every complexity claim is tied to a stated operation or gate model.
- [ ] Every speed claim uses matched inputs, outputs, setup policy, and timing
      boundaries.
- [ ] The classical phase diagram contains both winning and losing regions.
- [ ] A fresh checkout reproduces every result used by the paper.
