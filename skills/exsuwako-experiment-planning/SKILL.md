---
name: exsuwako-experiment-planning
description: Plan, execute, and review ExSuwako correctness, cost-model, baseline, implementation, and cryptographic-parameter experiments using the paper outline and explicit evidence gates.
---

# ExSuwako Experiments

Use this skill when planning experiments, implementing baselines, reviewing
benchmark evidence, or updating the experimental TODO list for ExSuwako.
Ground the work in:

- `paper/writing_guide.md`, especially Sections 8-9, the Immediate TODO List,
  and Submission Gates;
- `README.md`, for notation and current evidence boundaries;
- `src/reference/generalized_suwako_poc.py`, for the existing independent
  reducer and test behavior.

Do not call a Python correctness PoC a performance implementation. Keep
correctness, operation-count validation, microbenchmarking, and end-to-end
cryptographic impact as separate evidence layers.

## Repository Layout

Keep algorithm and reusable native implementation code in `src/`, public
interfaces in `include/`, and correctness-only test programs in `tests/`.
Put experiment code in the experiment directory `bench/`: this includes
benchmark C entrypoints, Python experiment drivers, manifests, and raw
measurement outputs. Do not place benchmark entrypoints such as
`*_exp.c` in `src/`; `src/` is reserved for code that implements a reusable
algorithm or library API. Keep each experiment's code and result artifact
clearly named so a result can be traced back to its driver and command.

## Current Baseline

Treat the following as already available only after rerunning them from the
current checkout:

- naive bit-level sparse long division;
- generalized Suwako reduction over `GF(2)`, with synchronous per-round reads;
- hand-picked edge cases;
- randomized differential tests;
- exact integer round-count calculation.

Record command, commit, seed, machine, Python version, parameter range, and
result for every run. A passing test establishes agreement with the reference
reducer; it does not establish novelty, optimality, or speed.

## Evidence Gates

Advance experiments in this order:

1. **Correctness gate:** independent reducers agree for all tested cases.
2. **Model gate:** measured operation counts match the stated work and depth
   formulas.
3. **Baseline gate:** every claimed win has a fair serial, dense, and
   multiplication-based comparison.
4. **Implementation gate:** native code measures the same operation and output
   contract as the reference implementation.
5. **Relevance gate:** parameters and workloads connect to real cryptographic
   finite-field arithmetic.
6. **Artifact gate:** another checkout can reproduce tables, figures, and test
   results from documented commands.

Do not make a later claim while an earlier gate is open.

## Experiment TODO List

### Phase 0: Freeze Definitions and Interfaces

- [ ] Freeze the modulus family and tap convention.
- [ ] Freeze input range: degree less than `2m` for a product input.
- [ ] Freeze `Delta_t = m - t`, `Delta_min`, exact `r`, and active-tap counts.
- [ ] Freeze the word model: word size, limb order, masking, and shift rules.
- [ ] Specify whether measurements include input/output packing and reduction
      setup.
- [ ] Define reduction-only and end-to-end multiplication APIs.
- [ ] Record all public parameters and avoid data-dependent control-flow claims
      unless separately verified.

### Phase 1: Correctness and Differential Testing

- [ ] Rerun edge cases including `Delta_min = 1`, taps near both ends, maximum
      supported tap weight, and all-zero/all-one inputs.
- [ ] Exhaust all tap sets and all inputs for small `m` where feasible.
- [ ] Run randomized tests across larger `m`, tap weights, tap spacing, and
      input distributions.
- [ ] Add a slow independent polynomial long-division implementation in a
      separate module or process.
- [ ] Add a direct polynomial-evaluation or library-field check where feasible.
- [ ] Test that each round reads one immutable `old` state across all taps.
- [ ] Test final low-part assembly separately from feedback closure.
- [ ] Test the exact round count against the loop's active-shift condition.
- [ ] Store failing seeds and regression cases permanently.

### Phase 2: Operation-Count and Cost-Model Validation

- [ ] Instrument per-round active taps satisfying `2^k Delta_t < m`.
- [ ] Verify the predicted sum of active taps against instrumentation.
- [ ] Count state updates, shifts, XORs, reads/writes, and temporary words.
- [ ] Separate logical shifts from cross-word and cross-vector shifts.
- [ ] Measure schedule generation, storage, and code-generation time.
- [ ] Check the predicted Pareto coordinates:
      `(work, feedback depth, setup)`.
- [ ] Document which costs are asymptotic, which are machine-model counts, and
      which are wall-clock measurements.

### Phase 3: Parameter Corpus

- [ ] Build synthetic controlled families varying `m`, tap weight, and
      `Delta_min` independently.
- [ ] Include gap-one families with fixed tap count and growing `m`.
- [ ] Include evenly spaced and clustered taps.
- [ ] Include low-weight, medium-weight, and high-weight tap sets.
- [ ] Select real irreducible sparse moduli relevant to cryptographic arithmetic.
- [ ] Include non-irreducible moduli only as structural stress tests and label
      them separately.
- [ ] Record provenance, irreducibility status, degree, tap set, and modulus
      Hamming weight for every real parameter.

### Phase 4: Baselines

Implement or integrate baselines under the same API and input distribution:

- [ ] Serial sparse folding / bit-level long division.
- [ ] Word-oriented serial sparse reduction.
- [ ] Barrett-style reduction over `GF(2)[x]`.
- [ ] Montgomery-style reduction where the representation is meaningful.
- [ ] Dense linear-map or XOR-network reduction, including setup and storage.
- [ ] Generic polynomial remainder as a correctness and portability baseline.
- [ ] Record whether each baseline is generated, precomputed, or modulus
      independent.
- [ ] Verify every baseline against the independent reducer before timing it.

### Phase 5: Native Implementations

- [ ] Implement portable C with arbitrary `m` and explicit ping-pong buffers.
- [ ] Check all shift counts and limb-boundary cases for undefined behavior.
- [ ] Generate fixed-modulus schedules and unrolled stages.
- [ ] Measure generated code size and schedule storage.
- [ ] Add in-place and out-of-place variants where meaningful.
- [ ] Implement AVX2 or another justified SIMD target.
- [ ] Measure cross-limb/cross-vector shifts, XOR fan-in, memory traffic, and
      stage barriers separately.
- [ ] Keep compiler, flags, CPU model, frequency policy, and thread pinning in
      the artifact record.
- [ ] Treat RTL as optional: compare latency, frequency, area/LUTs, registers,
      throughput, and pipeline depth only if a defensible implementation is
      available.

### Phase 6: Benchmark Protocol

- [ ] Benchmark reduction-only latency and throughput separately.
- [ ] Benchmark complete multiplication including product formation and
      reduction.
- [ ] Measure cold setup, warm setup, and amortized setup over `K` operations.
- [ ] Use warm-up iterations and report repetitions, median, spread, and
      outlier handling.
- [ ] Use identical outputs and correctness checks for all implementations.
- [ ] Report cycles per operation, not only wall-clock time.
- [ ] Measure memory traffic and temporary storage where hardware counters are
      available.
- [ ] Run each relevant parameter at least enough times to support the stated
      precision; record the raw samples.
- [ ] Repeat representative cases on a second machine or architecture when
      making architecture-independent claims.

### Phase 7: Research Questions and Figures

Answer these questions explicitly:

- [ ] RQ1: Does generalized Suwako agree with independent reducers for arbitrary
      tested tap sets?
- [ ] RQ2: Does measured work follow active-tap and round-count predictions?
- [ ] RQ3: When does it beat serial sparse and dense reduction?
- [ ] RQ4: How do setup cost and amortization change the crossover?
- [ ] RQ5: Which conclusions survive across scalar, SIMD, and optional hardware
      targets?
- [ ] Plot work/depth/setup tradeoff maps.
- [ ] Plot stage count versus `Delta_min`.
- [ ] Plot gap-one scaling as `m` grows.
- [ ] Plot predicted active-tap work against measured runtime.
- [ ] Plot setup amortization over `K`.
- [ ] Produce crossover heatmaps, not only favorable examples.
- [ ] Include a table of real moduli and their provenance.
- [ ] Include a table comparing method families and cost assumptions.
- [ ] Include a theorem/complexity summary table.
- [ ] Include scalar and SIMD results separately.

### Phase 8: Negative Results and Boundaries

- [ ] Report high-weight regimes where the method loses.
- [ ] Report small-degree regimes where Barrett or Montgomery wins.
- [ ] Report cases where setup dominates.
- [ ] Report cases where memory traffic or stage barriers erase logical-work
      advantages.
- [ ] State that feedback depth is not automatically bounded-fan-in gate depth.
- [ ] State that the method does not change the asymptotic exponent of complete
      field multiplication by itself.
- [ ] Avoid lower-bound, optimality, constant-time, or universal-speedup claims.

### Phase 9: Artifact and Submission Readiness

- [ ] Add one command for correctness validation.
- [ ] Add one command for operation-count validation.
- [ ] Add one command for the complete benchmark suite.
- [ ] Pin compiler/tool versions and document CPU/OS information.
- [ ] Store seeds, parameter manifests, raw measurements, and plotting scripts.
- [ ] Regenerate every paper figure and table from raw data.
- [ ] Verify a fresh checkout can run the scoped artifact path.
- [ ] Match every abstract and introduction claim to a theorem, table, or
      figure already produced.
- [ ] Mark unresolved prior-art and application questions as open before
      submission.

## Reporting Rules

- Label results as `correctness`, `model validation`, `microbenchmark`, or
  `end-to-end`.
- Never compare Python time with native C time as an algorithmic result.
- Never compare different modulus sets without showing the parameter manifest.
- Show both favorable and losing regimes.
- Separate reduction-only speedup from complete multiplication speedup.
- Include setup and storage when comparing generated or dense methods.
- State whether a result is measured, derived, or projected.
- Preserve the distinction between word work, XOR count, instruction count,
  gate count, latency, and throughput.

## Completion Criteria

Call the experimental package ready for paper integration only when:

1. correctness and cost-model gates pass;
2. all claimed baselines agree with the independent reducer;
3. native measurements cover a non-artificial parameter region;
4. losing regimes and setup costs are reported;
5. at least one result connects to real cryptographic arithmetic;
6. figures and tables are reproducible from a fresh checkout; and
7. the paper's claims do not exceed the evidence.
