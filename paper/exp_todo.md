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
3. matched reduction-only microbenchmarks;
4. complete arithmetic operations;
5. end-to-end application workloads;
6. reproducible artifact validation.

## Source Coverage and Provenance

This checklist consolidates executable experimental work; it does not replace
the mathematical arguments, literature judgments, or conversation records in
the source notes. In particular, files under `raw/` remain research
provenance rather than paper evidence. The following map records how their
actionable experimental content is covered:

| Source | Experimental content retained here | Non-experimental content remains in |
|---|---|---|
| [README.md](../README.md) and [native_benchmark.md](../bench/native_benchmark.md) | Current inventory, benchmark contract, gf2x provenance, and artifact rules in Current Inventory, P0, and Gate 6 | The source files as implementation documentation |
| [writing_guide.md](writing_guide.md) | Evidence levels and completion criteria in all gates | Paper structure, claim status, and submission gates |
| [implementation_evaluation.md](sections/implementation_evaluation.md) | Implementations, baselines, RQ1--RQ7, parameter sweeps, metrics, figures, tables, and negative results in Gates 1--4 and 6 | Paper-facing evaluation design |
| [extensions_appendices.md](sections/extensions_appendices.md) | Claim-to-evidence experiments and former implementation/evaluation TODOs in Gates 1--6 | Mathematical, prior-art, appendix, and submission planning |
| [application.md](notes/application.md) | Repeated squaring and modulus selection in Gates 4A and 4B | Application motivation and evidence ledger |
| [math_1.md](raw/math_1.md) and [math_2.md](raw/math_2.md) | Optional coefficient-algebra checks in Gates 1 and 2 | General algebraic derivations, proofs, and open problems |
| [related_1.md](raw/related_1.md), [related_2.md](raw/related_2.md), and [related_3.md](raw/related_3.md) | Their demands for matched classical comparisons enter Gate 3 | Hostile-search records summarized in [related_work.md](sections/related_work.md) and tracked in [prior_art_plan.md](notes/prior_art_plan.md) |
| [math_comp.md](notes/math_comp.md), [technical_body.md](sections/technical_body.md), [intro_draft.md](sections/intro_draft.md), and [venue_choice.md](notes/venue_choice.md) | Any evidence requirements are represented by Gates 1--6; these files define no independent experiment queue | Mathematical synthesis, manuscript prose, and venue strategy |
| [experiment-planning skill](../skills/exsuwako-experiment-planning/SKILL.md) and [paper-writing skill](../skills/exsuwako-paper-writing/SKILL.md) | Both skills route experimental work to this file and deliberately contain no duplicate checklist | Workflow instructions in the skill files |

When a source note gains a new executable experiment, add it to the relevant
gate here and update this map. Do not mark a source as covered merely because
it uses the word "experiment"; preserve proof obligations and prior-art work
in their own documents.

## Current Inventory

The following items describe code that exists, not completed paper evidence.

- [x] A unified native reduction API exposes generalized Suwako, serial sparse
      folding, naive long division, and gf2x-backed Barrett reduction.
- [x] The native correctness check compares the four reducers across
      representative aligned and non-aligned degrees.
- [x] Reduction-only benchmark and phase-diagram drivers exist under
      bench/scripts/.
- [x] Local exploratory CSV files are separated under bench/data/ and are
      ignored by Git.
- [ ] Rerun every claimed correctness and timing result from the eventual
      experiment commit and record the command, seed, compiler, gf2x path,
      machine, CPU-affinity policy, and raw output.
- [ ] Promote the temporary square-input diagnostic into a versioned benchmark
      before citing any modular-squaring timing.

The current reduction benchmark samples a random low half and only one set bit
in the high half. This is a valid named input distribution, but it is not a
model for modular squaring, a dense product, or a generic degree-below-$2m$
input. Keep its results separate from the application experiments below.

## P0: Freeze the Experimental Contract

- [ ] Freeze the tap convention, including whether the constant tap is listed
      explicitly and whether $h$ includes the leading term.
- [ ] Add an exact tap-list or manifest input mode; do not rely only on a seed
      to recover the tested modulus.
- [ ] Emit the complete tap set, irreducibility status, provenance, $m$, $h$,
      $\Delta_{\min}$, active-tap profile, and sample identifier.
- [ ] Define and name each input distribution:
      high monomial, random high half, multiplication product, polynomial
      square, and application-generated state.
- [ ] Freeze the timed boundary for reduction-only, square formation,
      modular squaring, multiplication, and end-to-end workloads.
- [ ] Freeze setup accounting: schedule generation, reciprocal generation,
      generated code, dense matrices, allocation, and amortization over $K$.
- [ ] Freeze compiler flags, word width $W$, gf2x build and linkage, CPU
      affinity, frequency policy, warm-up, repetitions, aggregation, and
      outlier treatment.
- [ ] Use deterministic seeds and preserve failing or anomalous cases as
      permanent regression inputs.

## Gate 1: Correctness

- [ ] Run make check from the experiment commit and archive its output.
- [ ] Exhaust all tap sets and all inputs for small $m$ where feasible.
- [ ] Cover $\Delta_{\min}=1$, taps at both ends, mixed aligned and unaligned
      shifts, dense supports, constant-free moduli, reducible moduli, and
      non-word-aligned degrees.
- [ ] Verify that every generalized-Suwako stage reads one immutable old
      state across all active taps.
- [ ] Test feedback closure and final low-part assembly independently.
- [ ] Add differential tests for square-shaped and multiplication-shaped
      inputs.
- [ ] If the coefficient-algebra or positive-characteristic extensions are
      promoted beyond theorem statements, add small exact differential tests
      over at least one non-binary coefficient algebra; do not treat this as
      evidence for the native binary kernel.
- [ ] Verify every new specialized reducer, squarer, or generated circuit
      against an independent long-division or computer-algebra result before
      timing it.
- [ ] Preserve exact irreducibility certificates or reproducible Sage checks
      for every modulus labelled irreducible.

## Gate 2: Cost Model

- [ ] Instrument the active taps satisfying
      $2^k\Delta_t<m$ in every feedback stage.
- [ ] Check the measured stage count against
      $r=\lceil\log_2(m/\Delta_{\min})\rceil$.
- [ ] Validate the predicted sums of active taps, affected coefficients, word
      shifts, XORs, reads, writes, and temporary words.
- [ ] Separate logical shifts from cross-word and cross-vector shifts.
- [ ] Validate setup time and stored schedule size independently of steady
      state reduction time.
- [ ] Correlate predicted word work with measured cycles without relabelling
      either quantity as the other.
- [ ] Record regimes where memory traffic, stage barriers, or instruction
      alignment invalidate a simple operation-count predictor.

## Native Implementation Backlog

- [ ] Audit the portable scalar implementation for arbitrary public taps,
      non-word-aligned $m$, constant-free moduli, top-word masking, and
      undefined shifts.
- [ ] Retain the fair shared word-level shift primitive while keeping the
      distinct GS and serial traversals.
- [ ] Complete a matched Montgomery baseline where its representation and
      setup assumptions are meaningful.
- [ ] Include a generic polynomial-remainder implementation as a correctness
      and portability baseline, without presenting it as a tuned sparse
      competitor.
- [ ] Add a dense linear-map baseline with setup time and storage reported.
- [ ] Add a fixed-modulus code generator for active stages and low-part
      assembly; report generated code size.
- [ ] Add optimized fixed-modulus trinomial and pentanomial reducers needed by
      the strongest-baseline gate, including Lopez--Dahab when its degree
      assumptions hold.
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
- [ ] Add optimized fixed-modulus trinomial/pentanomial folding, generated
      shift/XOR code, and dense linear reduction where they are credible
      strongest baselines.
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

## Gate 4A: Repeated Modular Squaring

This is Application 1 in
[application.md](notes/application.md#main-direction-repeated-modular-squaring-in-sparse-polynomial-search).

- [ ] Add a modular-square API mapping one $m$-bit field element to its reduced
      square.
- [ ] Implement and time square formation separately from reduction.
- [ ] Use random field elements and application-generated Frobenius-chain
      states; do not substitute the current high-monomial distribution.
- [ ] Measure reduction-only, square-only, and complete modular-square costs
      for the same inputs.
- [ ] Compare generalized Suwako with serial folding, gf2x-backed Barrett, the
      strongest general low-weight squarer, and applicable family-specific
      trinomial or pentanomial formulae.
- [ ] Include the irreducible two-cluster pentanomials and reciprocal-hostile
      examples, but also include standard and previously optimized moduli.
- [ ] Implement a repeated-Frobenius chain and verify every step against an
      independent implementation.
- [ ] Add a complete Rabin irreducibility test, DDF kernel, or
      primitive-polynomial certification workload.
- [ ] For candidate-search workloads, report early exits and the reducible
      candidate distribution rather than timing only successful candidates.
- [ ] Report the square-formation, reduction, GCD, multiplication, and other
      fractions of end-to-end time.
- [ ] Treat an advantage confined to reduction-only timing as a
      microbenchmark result, not application impact.
- [ ] Preserve negative cases where a specialized squarer, reciprocal
      representation, or multiplication-based method wins.

## Gate 4B: Platform-Specific Modulus Selection

This is Application 2 in
[application.md](notes/application.md#coupled-direction-platform-specific-modulus-selection).

- [ ] Build a versioned candidate generator for irreducible trinomials,
      pentanomials, and selected higher-weight moduli.
- [ ] Stratify candidates at fixed $m$ and $h$ by $\Delta_{\min}$, full tap
      geometry, word alignment, and reciprocal geometry.
- [ ] Include standard moduli, the architecture-specific choices in the
      existing modulus-selection literature, and the two-cluster candidates.
- [ ] Record the exact irreducibility check, seed, search range, candidate
      count, and provenance of every selected modulus.
- [ ] Define the optimization objective before ranking moduli: reduction,
      modular squaring, multiplication, inversion, a weighted arithmetic mix,
      or an application-level workload.
- [ ] Select a best modulus independently for serial folding, generalized
      Suwako, specialized fixed reduction, and multiplication-based reduction.
- [ ] Test whether generalized Suwako changes the selected modulus, rather
      than merely timing a hand-picked hostile example.
- [ ] Re-evaluate the selected modulus on every stated platform; do not
      transfer a ranking across ISAs.
- [ ] Include generated-code size, setup, storage, and amortization in the
      objective where applicable.
- [ ] State when a protocol or standard fixes the polynomial and therefore
      does not permit modulus selection without a basis conversion.
- [ ] Keep offline irreducibility-search cost separate from steady-state field
      arithmetic unless online modulus search is itself the application.
- [ ] Couple the final selection experiment to Gate 4A so that the chosen
      moduli are tested in repeated modular squaring and at least one
      end-to-end workload.

## Gate 6: Reproducibility and Artifact

- [ ] Keep benchmark entrypoints and drivers under bench/scripts/.
- [ ] Keep exploratory raw CSV files under bench/data/; promote only
      documented manifests and final evidence artifacts according to the
      repository publication policy.
- [ ] Emit commit, command, seed, modulus manifest, compiler, linked gf2x
      library, machine, affinity, and timing metadata with every run.
- [ ] Provide one command for correctness, one for cost-model validation, one
      for reduction microbenchmarks, and one for each end-to-end application.
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
- [ ] Repeated modular squaring passes a specialized-baseline comparison.
- [ ] Any modulus-selection claim demonstrates a changed winner under a fixed
      objective, or is reported as a negative result.
- [ ] At least one end-to-end workload connects the result to real
      cryptographic or computational arithmetic.
- [ ] A fresh checkout reproduces every result used by the paper.
