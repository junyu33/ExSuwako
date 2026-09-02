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

- [x] [Q] What is the canonical binary tap convention? [A] `taps=sort(T)` is the complete ascending nonleading support, includes exponent 0 exactly when present, excludes $m$, permits the empty set, and defines $s=|T|$ and $h=s+1$.
- [x] [Q] How is the exact tested modulus recovered? [A] Use the exact tap-list CLI or a JSONL manifest; a seed alone is not the modulus identity.
- [x] [Q] Which modulus identity and geometry fields are preserved? [A] Preserve `sample_id`, `provenance`, $m$, and complete taps, then deterministically derive and emit $s$, $h$, $\Delta_{\min}$, feedback stages, active-tap profile, and scheduled work; record irreducibility separately only for field-level claims that require it.
- [x] [Q] What is the reduction input domain and primary distribution? [A] `uniform-full-range:v1` samples every degree-below-$2m$ input as $A=L+x^mH$ for independent uniform $m$-bit $L,H$.
- [x] [Q] What does the benchmark time? [A] `reduction-steady-state:v1` times only batched reduction of materialized inputs $A$ with $\deg A<2m$ modulo the selected monic polynomial $g$ through `reduce_into()`; reusable setup, allocation, validation, and reporting remain outside.
- [x] [Q] How are setup costs accounted for? [A] `modulus-plan:v1` reports the median time over fresh plan constructions from materialized $m$, taps, and $g$, including schedules, reciprocals, and plan-owned scratch allocation while excluding parsing, shared modulus materialization, benchmark buffers, validation, reporting, and teardown; preserve raw $T_{\mathrm{setup}}$ and $T_{\mathrm{reduce}}$ and derive $T_{\mathrm{setup}}+KT_{\mathrm{reduce}}$ only for an explicitly stated $K$, while future generated-code and dense-map baselines must additionally report generation, compilation, code/storage size, and allocation separately.
- [ ] Freeze compiler flags, word width $W$, gf2x build and linkage, CPU
      affinity, frequency policy, warm-up, repetitions, aggregation, and
      outlier treatment.
- [ ] Use deterministic seeds and preserve failing or anomalous cases as
      permanent regression inputs.

## Gate 1: Correctness

- [ ] At the frozen experiment/artifact commit, run `make check` and archive
      its complete output together with the environment metadata required by
      Gate 4. Ordinary development commits do not independently reset this
      item; rerun it after changes that affect algorithms, tests, toolchains,
      or experimental semantics.
- [x] Exhaust all tap sets and all inputs for small $m$ where feasible. For
      $m\le6$, the GF(2) suite checks every monic binary modulus and every
      input of degree below $2m$ against independent long division: 299,592
      modulus/input pairs in total.
- [x] Run the deterministic theorem-falsification suites through `make check`:
      20,000 GF(2) random trials with $m\le128$, 299,592 exhaustive binary
      modulus/input pairs for $m\le6$, 266,304 exhaustive dual-number cases
      for $m\le3$, and the recorded randomized \(\mathbb F_4\) and
      \(\mathbb F_3\) differential checks.  Sources:
      [round 1](../tests/check_theory_round1_gf2.py),
      [round 2](../tests/check_theory_round2_algebras.py), and
      [validation record](raw/math_3.md).  This is computational
      falsification, not a proof.
- [x] Cover $\Delta_{\min}=1$, taps at both ends, mixed aligned and unaligned
      shifts, dense supports, constant-free moduli, reducible moduli, and
      non-word-aligned degrees. The deterministic native suite runs 10,000
      stratified random full-input cases for $1\le m\le512$ in addition to
      700 fixed-degree cases; failures print a directly reproducible case.
- [ ] Verify that every generalized-Suwako stage reads one immutable old
      state across all active taps.
- [ ] Test feedback closure and final low-part assembly independently.
- [ ] If the coefficient-algebra or positive-characteristic extensions are
      promoted beyond theorem statements, add small exact differential tests
      over at least one non-binary coefficient algebra; do not treat this as
      evidence for the native binary kernel.
- [ ] Verify every new specialized or generated reducer
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
- [x] Validate the formal scheduled coefficient-work sum
      $\sum_{r,k}[m-2^kd_r]_+$ against every generated binary schedule and
      exhaustively enumerate support geometry for $2\le m\le18$; see
      [math_3.md](raw/math_3.md).  This does not validate an instruction-count
      or minimal-circuit model.
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
