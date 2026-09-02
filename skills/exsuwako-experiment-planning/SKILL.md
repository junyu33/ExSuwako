---
name: exsuwako-experiment-planning
description: Plan, execute, and review ExSuwako correctness, cost-model, baseline, implementation, classical phase-diagram, modular-squaring, modulus-selection, reversible-circuit, and artifact experiments using explicit evidence gates.
---

# ExSuwako Experiments

## Branch Scope

This workflow applies only on a curated venue branch that contains
`paper/exp_todo.md`.  `main` intentionally has no authoritative manuscript
experiment checklist; record only reusable code, tests, and factual results
there, then plan paper integration on the target venue branch.

Use [paper/exp_todo.md](../../paper/exp_todo.md) as the sole authoritative
experiment checklist. Read it completely before planning or changing an
experiment, then read only the topic documents needed for the current gate:

- [paper/writing_guide.md](../../paper/writing_guide.md) for claim status and
  submission gates;
- [paper/sections/implementation_evaluation.md](../../paper/sections/implementation_evaluation.md)
  for paper-facing research questions, parameter definitions, metrics, and
  figures;
- [paper/notes/application.md](../../paper/notes/application.md) for the
  application hypotheses and their claim boundaries;
- [README.md](../../README.md) for notation and current implementation scope;
- [src/reference/generalized_suwako_poc.py](../../src/reference/generalized_suwako_poc.py)
  for the independent reducer and reference behavior.

Do not maintain another TODO list in this skill. When the experimental plan
changes, update paper/exp_todo.md and keep topic documents linked to it.

## Workflow

1. Identify the exact evidence level requested: correctness, cost model,
   reduction-only microbenchmark, complete arithmetic operation, end-to-end
   application, circuit resource count, or artifact reproduction.
2. Locate the corresponding gate in paper/exp_todo.md and check its
   prerequisites.
3. Freeze the modulus manifest, input distribution, output contract, setup
   policy, timing boundary, seed, compiler, linked libraries, and platform
   before collecting comparative data.
4. Pass correctness and model checks before timing.
5. Compare identical operations and inputs through the same abstraction.
6. Preserve raw rows and metadata; regenerate summaries and figures from those
   rows.
7. Update checkbox status only when the stated evidence is reproducible from
   the current checkout.
8. After completing a gate, propagate its consequence to the paper-facing
   documents using the synchronization rules below. Do not create duplicate
   experiment checkboxes in those documents.

## Completion Synchronization

`paper/exp_todo.md` owns experiment completion state. Topic documents own the
interpretation of that state; they must not maintain shadow copies of its
checkboxes.

When checking an item or completing a gate:

1. Update `paper/notes/application.md` if the result confirms, refutes, or
   leaves unresolved an application hypothesis. Change its evidence ledger and
   surrounding qualification, not merely a status word.
2. Update `paper/sections/implementation_evaluation.md` when planned methods,
   parameters, figures, or tables have become actual evaluated artifacts.
   Preserve the distinction between the evaluation design and reported
   results.
3. Update `paper/writing_guide.md` when the evidence changes a paper claim,
   contribution status, or submission gate.
4. Update `paper/sections/extensions_appendices.md` only when the evidence
   changes its claim-to-evidence matrix, limitations, appendix contents, or
   submission readiness. Its mathematical and prior-art TODOs remain
   independent and are never auto-completed by an experiment.
5. Leave files under `paper/raw/` unchanged. They are provenance records; add
   a new note or link from a paper-facing document if later evidence revises
   their conclusions.

A completed experimental gate therefore triggers a consistency review, not
automatic textual replacement. If the result is negative, record the negative
result and narrow the claim; do not leave the old hypothesis marked as open or
silently treat the gate as a success claim.

## Repository Layout

- Put reusable native algorithms in src/ and public interfaces in include/.
- Put correctness-only native programs in tests/.
- Put benchmark entrypoints, experiment drivers, manifests, and plotting
  scripts in bench/scripts/.
- Put exploratory raw measurements in bench/data/.
- Do not place benchmark entrypoints in src/.
- Do not commit local CSV measurements unless the repository publication
  policy is explicitly changed.

## Evidence Discipline

Advance experiments in this order:

1. independent reducers or circuits agree;
2. measured operation counts match the stated model;
3. all claimed baselines implement the same operation and contract;
4. native measurements use matched inputs and timing boundaries;
5. parameters and workloads connect to real arithmetic;
6. a fresh checkout reproduces the result.

A passing test establishes agreement, not novelty, optimality, or speed. A
reduction-only result is not a modular-square, multiplication, or end-to-end
result. A software feedback stage is not a CNOT layer.

## Current Baseline Cautions

- Treat native implementations as available code, not current evidence, until
  rerun from the experiment commit.
- The reduction-only benchmark uses `uniform-full-range:v1` over the complete
  degree-below-$2m$ domain. Multiplication results, squares, and application
  states are subsets of that domain and become separate corpora only when
  complete formation or workload costs are measured.
- GS versus serial is the primary matched sparse-reduction comparison.
  Barrett, naive, dense, generated, and specialized reducers answer different
  baseline questions and must retain their setup assumptions.
- Use fixed public moduli and deterministic seeds when randomness is involved.
- Keep reduction-only, complete arithmetic, and application measurements in
  separate result sets.

## Reporting Rules

- Label every result as correctness, model validation, microbenchmark,
  complete arithmetic, end-to-end, or circuit-resource evidence.
- Record command, commit, seed, full tap set, input distribution, repetitions,
  compiler, flags, linked gf2x path, machine, CPU affinity, and timing
  boundary. Record irreducibility status and evidence only for field-level
  claims that require them; general reduction does not assume irreducibility.
- Show favorable, losing, and uncertain regimes.
- Separate cycles, wall time, word work, XOR count, instruction count, CNOT
  count, gate depth, and ancilla count.
- Include setup, storage, generated code, and amortization when relevant.
- Do not transfer conclusions across ISAs, circuit models, or modulus
  representations without new evidence.
- Do not call Python timing a native performance result.

## Completion

An experiment is ready for paper integration only when its gate and the
corresponding completion items in paper/exp_todo.md are checked, the raw
artifact is reproducible, and the prose claim does not exceed the measured or
proved evidence.
