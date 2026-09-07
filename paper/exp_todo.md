# Experimental TODO

This file is the authoritative execution checklist for ExSuwako experiments.
The paper structure and claim status remain in
[writing_guide.md](writing_guide.md); the paper-facing research questions,
parameter model, metrics, and planned figures remain in
[sections/implementation_evaluation.md](sections/implementation_evaluation.md).

The paper-facing method name is Frobenius-factorized reduction (FFR).  The
frozen native API, source filenames, CSV fields, and artifact method keys keep
the historical identifier `GS`; occurrences of `GS` below refer to that
internal identifier rather than a second algorithm.

Do not infer a paper claim from a checked implementation task. Advance
evidence through the following levels:

1. correctness;
2. operation-count and cost-model validation;
3. matched reduction microbenchmarks;
4. reproducible artifact validation;
5. end-to-end workload validation.

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
| [implementation_evaluation.md](sections/implementation_evaluation.md) | Implementations, baselines, RQ1--RQ7, parameter sweeps, metrics, figures, tables, negative results, and the Gate 5 E2E workload | Paper-facing evaluation design |
| [extensions_appendices.md](sections/extensions_appendices.md) | Claim-to-evidence experiments and former implementation/evaluation TODOs in Gates 1--4 | Mathematical, prior-art, appendix, and submission planning |
| [application.md](notes/application.md) | Repeated modular squaring and Rabin irreducibility testing in Gate 5 | Application motivation, alternatives, and claim boundaries |
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

- [x] A unified native reduction API exposes FFR (internal key `GS`), serial sparse
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
- [-] Rerun every claimed correctness and timing result from the eventual
      experiment commit and record the command, seed, compiler, gf2x path,
      machine, CPU-affinity policy, and raw output. [A] Superseded by the
      frozen multi-cohort artifact: the reported timing rows were already
      collected at three clean experiment commits necessitated by the
      no-Serial high-weight and $\Delta_{\min}=W$ López--Dahab contract
      changes. Recollecting them at a later manuscript commit would create a
      different experiment rather than validate the retained one. The
      canonical 67,576-row dataset preserves all required metadata and is
      hash-locked; its complete analysis was reproduced from a fresh checkout.
      Correctness and a short metadata-complete timing smoke run were rerun at
      the frozen artifact commit.

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

- [x] At the frozen experiment/artifact commit, run `make check` and archive
      its complete output together with the environment metadata required by
      Gate 4. Ordinary development commits do not independently reset this
      item; rerun it after changes that affect algorithms, tests, toolchains,
      or experimental semantics. [A] A detached fresh worktree at
      `68af03679c8114e691c0b0cee45fe2904a083ffa` completed `make check` with
      exit status zero. The 109-line external log has SHA-256
      `6ef8b4ca51d84358933baa7a842a5e79fc2c4006e9f26d927afe3add025ee83a`;
      the tracked validation record binds it to the compiler, gf2x library,
      platform, affinity, and frequency metadata.
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
- [x] [Q] Verify that every FFR stage reads one immutable old
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
      arbitrary modulus weight under $\deg q\le m-W$; equality is a tested
      ordinary-loop extension of the paper's strict assumption. It uses the same unified API
      and balanced timing rotation as GS, and reports reusable plan setup,
      storage, and steady-state reduction. The native differential suite
      checks it against independent long division before timing.
- [-] Add justified SIMD implementations, beginning with one frozen ISA, and
      measure cross-vector shifts and stage barriers separately. [A] Not
      applicable to the frozen portable-scalar experiment contract: no vector
      ISA is selected or implemented, and cross-vector costs require a
      separately frozen ISA-specific model.
- [-] Treat AVX-512, NEON, SVE, and RTL as optional extensions until the scalar
      evidence gates are complete. [A] These targets remain future extensions
      rather than planned evidence for the current Math. Comp. study; no
      cross-vector or hardware result is claimed.
- [-] If an RTL prototype is built, report latency, frequency, area/LUTs,
      registers, throughput, and pipeline depth under one synthesis flow. [A]
      No RTL prototype is planned under the current software-reduction
      contract, so no synthesis flow or hardware metric is claimed.

## Gate 3: Classical Reduction Phase Diagram

The paper-facing definition of this experiment is in
[Implementation and Evaluation, Section 9.4](sections/implementation_evaluation.md#94-planned-figures).

- [x] For each fixed $m$, place modulus Hamming weight $h$ on the horizontal
      axis and $m/\Delta_{\min}$ on a base-two logarithmic vertical axis. [A]
      `plot_phase_geometry.py` validates the emitted coordinate against
      $m$ and $\Delta_{\min}$, collapses repeated trials to one support point,
      and emits one dependency-free SVG panel per fixed $m$.  The undefined
      $T=\varnothing$ coordinate is counted and annotated separately rather
      than placed on the logarithmic axis; winner assignment remains a later
      Gate 3 item.
- [x] Compare serial sparse folding (shift/XOR), FFR, and
      gf2x-backed Barrett under the same reduction contract and input corpus.
      [A] For each support, the native benchmark materializes one
      `uniform-full-range:v1` input array, differentially checks all enabled
      plans on that array, and then passes the same immutable array to the
      cyclically rotated `reduction-steady-state:v1` timer.  The phase driver
      retains positive `GS_ns`, `Serial_ns`, `BarrettGF2X_ns`, `Serial/GS`,
      and `BarrettGF2X/GS` fields under the common timing metadata, and its
      contract test rejects a missing primary comparison.
- [x] Add optimized ordinary-loop trinomial/pentanomial folding and dense
      linear reduction where they are credible strongest baselines. [A]
      The exact-manifest phase path can opt into ordinary-loop López--Dahab
      Algorithm 2 for every support satisfying $m>W$ and $\deg q\le m-W$, or
      into the row-parity Dense map below its 64 MiB matrix limit.  Each mode
      replaces Naive to retain a balanced GS/Serial/Barrett/fourth-method
      rotation, and the driver rejects random-mode López--Dahab runs,
      incompatible options, applicability violations, or missing method
      measurements.  Dense is retained as a diagnostic baseline; promotion
      of either method into final winner panels remains conditional on the
      formal sweep rather than an exploratory timing.
- [x] Sweep controlled synthetic supports so that $h$ and
      $\Delta_{\min}$ vary independently. [A]
      `generate_controlled_supports.py` emits the complete feasible Cartesian
      product of explicitly requested $m$, $h$, and $\Delta_{\min}$ values.
      It fixes the highest tap to $m-\Delta_{\min}$ and deterministically
      spreads the remaining taps, with separately labelled constant-free and
      constant-present policies; it rejects any infeasible cell rather than
      silently dropping it. The resulting exact JSONL manifest is consumed
      unchanged by the phase driver, and its contract test checks axis
      coverage, canonical taps, provenance, uniqueness, and determinism.
- [x] Sample fixed-weight supports and report median, p90, and p99 rather than
      only favorable examples. [A] `generate_fixed_weight_supports.py`
      materializes deterministic exact-support manifests before timing, using
      256 distinct supports per requested $(m,h)$ cell or the complete
      constant-free $\binom{m-1}{h-1}$ population when it is smaller. The
      explicit constant policy, sampler, seed,
      population, and realized count remain in the manifest.
      `summarize_fixed_weight.py` first takes the median across retained
      timing trials for each support, then reports the median and nearest-rank
      p90/p99 across distinct supports. It emits both support-level and cell
      tables and rejects duplicates, incomplete trials, mixed contracts, and
      non-random provenance rather than selecting favorable examples.
- [-] Include real irreducible moduli and label reducible ring-level stress
      tests separately. [A] Not planned for the frozen reduction-only phase
      diagram: correctness and timing apply to arbitrary monic binary moduli,
      and this study makes no field-level performance claim. Controlled and
      fixed-weight synthetic samples retain explicit ring-level provenance
      with irreducibility unclassified; they are not labelled reducible
      without a test. Any future field/application experiment must introduce
      a separate manifest with reproducible irreducibility evidence.
- [x] Produce fixed-$m$ winner panels and mark statistically or operationally
      uncertain cells instead of forcing a clean boundary. [A] Retained
      paper-grade rows reconstruct the six $m\in\{128,512,2048,8192,32768,
      131072\}$ panels and 1,096 measured cells. The paired-bootstrap analyzer
      assigns 983 unique winners and preserves 113 uncertain cells: 103
      timing-unstable, 10 operational ties, and no statistical ties. The
      renderer emits equal-area measured blocks in a $2\times3$ SVG/PNG layout
      without interpolating missing cells.  A reproducible repository script
      now fits fixed-$m$ affine runtime models to the GS and López--Dahab
      portable scalar word-work formulas, uses the fixed-$m$ Barrett median,
      preserves a deterministic calibration/holdout split, and overlays only
      adjacent predicted-class interfaces.  The predicted lines do not alter
      measured fills or extrapolate into unmeasured cells.
- [x] Record $W$, full tap placement, input distribution, implementation,
      platform, setup policy, and multiplication backend for every panel. [A]
      A direct audit of all 67,576 retained paper-grade trial rows underlying
      the 1,096 panel cells found no missing metadata, duplicate trial index,
      incomplete trial sequence, or within-sample contract change. Every row
      records $W=64$, complete taps, `uniform-full-range:v1`,
      `portable-scalar-c:v1`, `reduction-steady-state:v1`,
      `modulus-plan:v1`, `gf2x:v1`, the compiler and flags, resolved gf2x
      library, clean commit and binary digest, host/platform, CPU 0 affinity,
      frequency policy, seed, and exact driver/native commands. The three
      clean collection commits preserve the GS, Barrett, and LD reduction
      bodies: the intermediate commit adds the explicit no-Serial high-weight
      method set, and the final commit admits and remeasures the independently
      tested LD boundary $\Delta_{\min}=W$ rather than pooling old trials.
- [x] Report friendly sparse regions, high-weight losses, small-degree
      overhead, and Barrett crossovers. [A]
      `summarize_winner_regions.py` preserves every exact
      $(m,\Delta_{\min})$ winner run and defines the crossover as the earliest
      stable Barrett point after which every later stable sampled point is
      also Barrett. Across the hard-feedback rows $\Delta_{\min}<64$, the
      persistent onset ranges for $m=128,512,2048,8192,32768,131072$ are
      respectively $h=33$--$65$, $97$, $65$--$97$, $129$, $225$--$257$, and
      $641$. Where López--Dahab applies, the corresponding onsets are $65$,
      $129$, $129$--$193$, $257$--$385$, $513$--$769$, and beyond the sampled
      $h=1025$. Thus GS owns the difficult-feedback sparse region but loses at
      high weight; López--Dahab increasingly dominates friendly feedback as
      $m$ grows. At $m=128$, Barrett already takes over by $h=33$--$65$ and
      López--Dahab wins only two cells, marking an implementation-overhead-
      sensitive small-degree regime without assigning a hardware cause;
      low-feedback GS/LD pockets and all uncertain cells remain recorded
      rather than being forced into a monotone boundary.
- [x] Plot feedback-stage count versus $\Delta_{\min}$ and gap-one scaling
      versus $m$ to test the predicted depth law. [A]
      `plot_feedback_depth.py` collapses repeated trials to 72 distinct
      $(m,\Delta_{\min})$ coordinates, rejects any native stage count unequal
      to $\lceil\log_2(m/\Delta_{\min})\rceil$, and emits a two-panel SVG: six
      fixed-$m$ gap sweeps and the $\Delta_{\min}=1$ scaling line. All retained
      coordinates pass exactly; in particular the six gap-one points satisfy
      $D_{\rm fb}=\log_2m$ for the sampled power-of-two degrees. This validates
      the native schedule depth against the structural formula, not wall-clock
      latency, instruction depth, or circuit gate depth.
- [x] Plot fixed-gap weight sweeps and fixed-weight gap sweeps so that tap
      count and feedback difficulty are not conflated. [A]
      `plot_phase_slices.py` emits complementary $2\times3$ figures from the
      retained winner-point medians. The fixed-gap figure varies
      $\log_2(h-1)$ at $\Delta_{\min}=1,64$; the fixed-weight figure varies
      $\log_2(m/\Delta_{\min})$ at $h=9,65$. Both plot
      $\log_2(T_{\rm method}/T_{\rm GS})$ around an explicit zero crossover,
      omit L\'opez--Dahab outside measured applicability, preserve uncertain
      points as hollow markers, and perform no interpolation.
- [x] Plot setup amortization over $K$ and a work--feedback-depth--setup
      tradeoff map. [A] `plot_setup_tradeoff.py` validates complete trial
      sequences and the frozen timing/setup scopes, takes per-support medians
      of the separately measured setup and reduction components, and derives
      $T_{\rm setup}+K T_{\rm reduce}$ only for mandatory explicit $K$ values.
      Its provenance-preserving CSV contains every enabled method for all
      1,096 supports. One $2\times3$ figure reports competitor/GS amortized
      ratios over $K$ as the median and p10--p90 range across measured
      controlled cells; a second plots every support by
      $(\log_2(W_{\rm fb}+1),D_{\rm fb})$ and colors it by GS setup time.
      These are measured scalar setup and grid summaries, not instruction
      counts, minimal circuits, or a random-modulus distribution.
- [x] Plot predicted active-tap work against runtime and random-support depth
      and work against $s$. [A] `plot_work_random_geometry.py` validates and
      collapses the 1,096 controlled timing points, then plots
      $\log_2W_{\rm fb}$ against median $\log_2(\mathrm{GS\ ns})$ separately
      for each $m$; the fixed-$m$ Spearman coefficients range from 0.987 to
      0.993. From the six frozen fixed-weight manifests it independently
      reconstructs exact depth and work for 10,623 supports and reports
      median, p90, and p99 against $\log_2s$. Median depth grows approximately
      as $1+\log_2s$, while median $W_{\rm fb}/m$ grows approximately linearly
      with $s$. The first result is a native reduction microbenchmark
      correlation; the second is deterministic random-support geometry, not
      random-support timing or a proof of the distributional bounds.
- [x] Produce the operator schematic $U,U^2,U^4,\ldots$ as an explanatory
      figure, clearly labelled as a construction diagram rather than measured
      evidence. [A] `draw_operator_schematic.py` generates a data-free SVG
      showing the factorized inverse, synchronous immutable-old updates,
      doubled shift distances, active-tap pruning, nilpotent termination, and
      final assembly. Its $m=16$, $T_+=\{3,11,15\}$ worked schedule has active
      shifts $\{1,5,13\}$, $\{2,10\}$, $\{4\}$, and $\{8\}$, and explicitly
      states that mixed paths arise through stage composition rather than a
      materialized pairwise-sum schedule. The figure itself is marked as
      algebraic construction, not measured timing or circuit depth.
- [x] Populate the planned method, theorem, real-modulus, portable-C, and
      setup/storage tables only from completed gates. [A]
      `summarize_paper_tables.py` deterministically extracts the six-degree
      portable-C anchor/crossover rows and the matched setup/storage medians
      from retained paper-grade data. The paper-facing tables separate method
      applicability, candidate-theorem status, modulus provenance, reduction
      timing, and plan cost. They explicitly leave named irreducible-modulus
      timing and scalar cross-platform results unpopulated, and label passing
      computational checks as falsification evidence rather than proof.

## Gate 4: Reproducibility and Artifact

- [x] Keep benchmark entrypoints and drivers under bench/scripts/. [A] All
      benchmark C entrypoints and Python collection/analysis drivers are under
      `bench/scripts/`; reusable reducers remain under `src/` and correctness
      programs under `tests/`.
- [x] Keep exploratory raw CSV files under bench/data/; promote only
      documented manifests and final evidence artifacts according to the
      repository publication policy. [A] `.gitignore` excludes the complete
      `bench/data/` payload. Git tracks deterministic JSONL manifests, scripts,
      the canonical raw-data hash/row-count contract, and validation hashes;
      no CSV is tracked. Selected PDF renderings used by the LaTeX manuscript
      are retained under `paper/ExSuwako/figures/`, with their canonical SVG
      hashes and conversion command recorded beside them; the complete
      generated artifact remains outside Git.
- [x] Emit commit, command, seed, modulus manifest, compiler, linked gf2x
      library, machine, affinity, and timing metadata with every run. [A] All
      67,576 canonical rows pass the paper-grade metadata audit. Three clean
      commits map one-to-one to three binary digests while all other frozen
      environment fields agree; the fresh smoke run independently exercises
      the same metadata path.
- [x] Provide one command for correctness, one for cost-model validation, and
      one for reduction microbenchmarks. [A] The documented entrypoints are
      `make check`, `make artifact-cost-model`, and
      `make artifact-microbenchmark ARTIFACT_CPU=N`; `make artifact-paper`
      rebuilds the complete paper analysis.
- [x] Regenerate every paper figure and table from recorded raw data. [A]
      `make artifact-paper` reconstructs winner classifications, fitted
      cost-model boundary predictions and diagnostics, winner regions,
      phase/depth/slice/setup/work figures, random-support geometry,
      cost-model summaries, and paper table sources. The declared outputs and
      SHA-256 values are frozen in `bench/artifact/paper-v1.json`.
- [ ] Verify the scoped artifact path from a fresh checkout. [A] A detached
      checkout of artifact commit `68af036` verified the external raw-data
      hash, regenerated all 24 outputs with exact hash agreement, reran the
      cost-model command, and completed a 124-row metadata-complete native
      timing smoke run. See `bench/artifact/validation-68af036.json`.  The
      subsequent fitted-boundary extension adds two CSV outputs and changes
      the winner SVG without changing timing data; record a new detached
      fresh-checkout validation after this extension is committed.
- [-] Repeat representative classical cases on a second machine or ISA before
      making architecture-independent claims. [A] Not applicable to the
      frozen paper claim: every timing result is explicitly scoped to the
      recorded primary portable-scalar platform, and the manuscript makes no
      architecture-independent ordering or speed claim. A second-platform
      table requires a future separately frozen experiment.
- [x] Record all losing regions and failed hypotheses. [A] The retained
      1,096-cell winner data includes GS's high-weight losses, friendly
      López--Dahab regions, small-degree overhead, 103 timing-unstable cells,
      10 operational ties, and the Dense diagnostic result; uncertain cells
      are never converted into wins.

## Reduction-Only Completion Gates

- [x] Every claimed reducer passes an independent correctness check. [A] The
      fresh `make check` run covers unrestricted reducers, the López--Dahab
      applicability boundary, Dense, and generated fixed reducers against
      independent long division before any retained timing is interpreted.
- [x] Every complexity claim is tied to a stated operation or gate model. [A]
      Scheduled coefficient work, scalar source-word counts, feedback depth,
      setup, storage, and any future gate depth remain separately named; none
      is relabelled as instructions, memory traffic, latency, or circuit depth.
- [x] Every speed claim uses matched inputs, outputs, setup policy, and timing
      boundaries. [A] The canonical paper-grade rows enforce one direct-
      reduction operation, immutable shared inputs, cyclic method rotation,
      separate setup, and the frozen timing/aggregation contracts.
- [x] The classical phase diagram contains both winning and losing regions.
      [A] Its 983 unique winners include GS, BarrettGF2X, and López--Dahab
      regions, while all 113 non-unique cells remain explicitly uncertain.
- [ ] A fresh checkout reproduces every result used by the paper. [A] The
      hash-locked external dataset plus tracked manifests and scripts rebuild
      the 24-output predecessor artifact byte-for-byte at commit `68af036`;
      the new 26-output fitted-boundary artifact must receive its own detached
      post-commit audit before this gate is closed again.

## Gate 5: End-to-End Rabin Irreducibility Test

This gate is a new workload contract and does not alter the frozen
reduction-only measurements above.  Its single paper-facing application is a
complete Rabin irreducibility test for sparse binary polynomials of
power-of-two degree.  For such a degree $m$, the test computes the modular
squaring chain through $x^{2^m}$, evaluates
$\gcd(x^{2^{m/2}}-x,g)$, and checks $x^{2^m}=x\pmod g$.

- [x] Freeze deterministic manifests of sparse irreducible moduli, including
      the complete taps, $m$, $h$, $\Delta_{\min}$, generator seed, and a
      reproducible Sage irreducibility check.  The pilot is
      $(m,h,\Delta_{\min})=(512,9,1)$; the paper study will decide expansion
      only after the pilot. [A] The committed pilot manifest fixes
      $T=\{0,54,96,156,271,346,476,511\}$, search seed
      `0x524142494e5031`, accepted attempt 221, and Sage 10.9 certificate
      provenance; `check_rabin_manifest.py` reconstructs the polynomial,
      verifies irreducibility, and reproduces the manifest byte-for-byte.  The
      positive pilot freezes the main $h=9$, $\Delta_{\min}=1$ scaling
      manifest at $m\in\{128,512,2048,8192\}$ by the same rule.
- [x] Implement one shared scalar polynomial squarer and a matched Rabin
      driver that changes only the reducer among FFR, BarrettGF2X, Serial, and
      L\'opez--Dahab where applicable.  The shared GCD/check path must not
      depend on the selected reducer. [A] `gf2_square_to_2m()` supplies the
      shared bit-dilation squarer; the C++ driver invokes the unified reduction
      API and automatically admits L\'opez--Dahab exactly when
      $\Delta_{\min}\ge W$.
- [x] Compare every matched-driver result and checkpoint with NTL, and include
      NTL `IterIrredTest` as a separate optimized end-to-end baseline rather
      than as another reducer inside the matched driver. [A] Before timing,
      every matched reducer's $m/2$ and $m$ checkpoints are compared with an
      NTL `SqrMod` chain; NTL `GCD` is shared by the matched paths, while
      `IterIrredTest` remains an independently timed whole-library baseline.
- [x] Freeze `rabin-power-of-two-irred:v1`: the primary wall-clock interval
      starts from reducer-plan construction and includes all modular squares,
      the GCD, and the final equality test; modulus parsing, manifest I/O,
      result validation, and reporting remain outside.  Also report setup,
      squaring-chain, and GCD/check components without substituting their sum
      for the primary end-to-end measurement. [A] The native CSV records the
      primary interval and its contiguous setup, chain, and check segments;
      the NTL row reports only its independently measured complete interval.
- [x] Run at least one discarded complete warm-up and 31 cyclically ordered
      complete trials per method, retain every observation, and use paired
      deterministic bootstrap intervals for method ratios.  Preserve the
      compiler, flags, gf2x and NTL paths, CPU affinity, frequency policy,
      command, commit, and binary digest with every retained run. [A] The
      collector attaches all required fields, and the analyzer rejects
      incomplete paired trials before producing deterministic 10,000-resample
      median and ratio intervals. Pipeline regression tests exercise this
      contract. The 465-row scaling dataset was collected paper-grade from
      clean commit `5d91ddc`; every row records that commit and a common
      binary digest. Serial is
      retained through $m=2048$ but omitted at $m=8192$, where a measured
      smoke trial takes about 47.5 seconds; that threshold is explicit in the
      command and every output row rather than treating Serial as a loser.
- [x] Run the $m=512$ pilot.  Expand the corpus only if the implementation is
      correct, the end-to-end interval is stable, and reduction remains a
      material fraction of total time; otherwise record the negative result
      and do not manufacture a broader application claim. [A] In the pinned
      31-trial exploratory pilot, median complete times were 0.154 ms for FFR,
      0.359 ms for NTL, 0.588 ms for BarrettGF2X, and 13.06 ms for Serial.
      Paired competitor/FFR median ratios were respectively 2.35, 3.80, and
      84.4, with all 95\% intervals strictly above one. The matched FFR
      squaring chain occupied about 95\% of its total time. This clears
      expansion; a clean-commit repeat gives the same ordering and replaces
      the exploratory values in paper claims.
- [x] Integrate the result into the manuscript only if a complete Rabin test,
      not merely its reduction or modular-squaring component, shows the stated
      effect.  A win over matched reducers but not over NTL must be reported
      with that distinction. [A] At $m=128,512,2048,8192$, all paired 95\%
      intervals place both complete NTL and matched Barrett above FFR. Their
      median ratios span 1.35--8.04 and 1.60--6.81, respectively. The
      manuscript reports one bounded Rabin result and retains polynomial
      factorization, candidate search, and modulus-distribution claims as
      limitations. `bench/artifact/rabin-v1.json` hash-locks the 465 raw rows,
      four-modulus manifest, summary, and figure.
