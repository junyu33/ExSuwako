# Generalized Suwako Writing Guide

This file is the single source of truth for the paper's scope, terminology,
section order, claim status, and submission gates. It is deliberately not a
repository for full proofs, prior-art notes, benchmark plans, or application
speculation; those live in the linked topic documents below.

## Central Thesis

Generalized Suwako reduction applies a sparse, factored truncated reciprocal
to the nilpotent feedback operator induced by a monic binary modulus. For a
sparse non-leading part, it retains support-sensitive shift/XOR work while
reducing the sequential feedback chain to logarithmic length.

Keep the following distinct:

- correctness applies to arbitrary monic binary moduli;
- favorable work applies when the non-leading support is sparse;
- feedback depth is not bounded-fan-in gate depth;
- a reduction-only result does not imply an asymptotic improvement to complete
  field multiplication;
- novelty and practical impact remain conditional on the prior-art audit and
  matched experiments.

## Working Title

> Generalized Suwako: Sparse Modular Reduction with Logarithmic Feedback Depth

Use *feedback depth* unless a Boolean or CNOT gate model is explicitly fixed.

## Topic Documents

| Topic | Canonical working document | Role |
|---|---|---|
| Abstract and introduction | [sections/intro_draft.md](sections/intro_draft.md) | Narrative draft; finalize last. |
| Algebra, theorems, and complexity | [notes/math_comp.md](notes/math_comp.md) | Mathematical core and claim ledger. |
| Technical body assembly | [sections/technical_body.md](sections/technical_body.md) | Manuscript section plan and proof interfaces. |
| Prior-art boundary | [sections/related_work.md](sections/related_work.md) | Paper-facing novelty boundary. |
| Prior-art audit plan | [notes/prior_art_plan.md](notes/prior_art_plan.md) | Coverage checklist and provisional comparison matrix. |
| Applications | [notes/application.md](notes/application.md) | Hypotheses and end-to-end validation plans. |
| Implementation and evaluation | [sections/implementation_evaluation.md](sections/implementation_evaluation.md) | Paper-facing research questions, models, metrics, and figures. |
| Experimental execution | [exp_todo.md](exp_todo.md) | Authoritative experiment checklist, evidence gates, priorities, and artifact status. |
| Extensions and appendices | [sections/extensions_appendices.md](sections/extensions_appendices.md) | Extensions, limitations, appendices, and detailed research management. |
| Venue framing | [notes/venue_choice.md](notes/venue_choice.md) | Submission strategy; not manuscript content. |
| Exploratory records | [raw/](raw/) | Preserve reasoning and leads; never cite as final evidence. |

A topic document may refine a claim, but it may not silently alter this guide's
scope or final section order.

## Final Manuscript Shape

1. Introduction
2. Preliminaries and cost models
3. Existing reduction paradigms
4. Sparse feedback operators
5. Generalized Suwako reduction
6. Complexity analysis
7. Prior art and novelty boundary
8. Implementations and evaluation
9. Applications and limitations
10. Conclusion

The technical body follows a definition-first order. The introduction is
limitation-first and is written only after the theorem, prior-art, and evidence
claims it summarizes have stabilized.

## Canonical Terminology and Notation

| Item | Canonical form |
|---|---|
| Contribution | generalized Suwako reduction; a method or algorithm |
| Modulus | \(g(x)=x^m+q(x)=x^m+\bigoplus_{t\in T}x^t\) |
| Tap distance | \(\Delta_t=m-t\) |
| Nearest feedback distance | \(\Delta_{\min}=\min_{t\in T}\Delta_t\), only for \(q\ne0\) |
| Feedback operator | \(U\) in the binary scalar presentation; \(T\) only for the general algebraic presentation |
| Low-part operator | \(V\) |
| Exact stage count | \(r=\lceil\log_2(m/\Delta_{\min})\rceil\), with \(r=0\) for \(q=0\) |
| Per-stage active taps | \(h_k\) |
| Modulus Hamming weight | \(h=1+|T|\) |
| Operation measures | feedback depth, word work, setup, space, gate depth; never conflate them |

Call an ISA an ISA; call a concrete evaluation target a platform or machine.
Do not turn word work into instruction count, XOR count into gate count, or a
CNOT upper bound into hardware depth without fixing the model.

## Claim Ledger

| Claim | Required evidence | Current status |
|---|---|---|
| Reduction through a nilpotent feedback inverse | Formal proof | Candidate theorem |
| Frobenius preserves formal per-stage sparsity; actual support is exact over reduced algebras | Formal proof | Candidate theorem |
| Scheduled geometry-sensitive work bound | Formal proof with operation model | Candidate theorem |
| Algebraic computational falsification | Reproducible independent tests | Measured over GF(2), GF(4), dual numbers, and F3; not a proof |
| Generic bounded-fan-in depth lower bound | Formal model and proof | Candidate theorem |
| Native scalar speed regions | Reproducible matched experiments | Exploratory |
| Platform-optimal modulus changes | Search plus end-to-end measurements | Open hypothesis |
| Koblitz representation/reducer co-design changes complete scalar multiplication | Field-isomorphism implementation, strongest polynomial/normal-basis and multi-squaring baselines, matched end-to-end measurements | Open EUROCRYPT hypothesis; K-283 first |
| CNOT size-depth-space tradeoff | Circuit construction, model, and prior-art audit | Zero-ancilla linear-size/log-depth two-cluster construction implemented and basis-verified; matching lower bounds and prior-art boundary remain open |
| Cluster-separation $\kappa$ partition | Recursive circuit theorem and matching constructions or lower bounds | Open; the two-cluster family is the $\kappa=2$ endpoint |
| Classical and quantum algorithm-selection diagrams | Fixed-$m$ measurements or exact circuit-resource counts under stated models | Planned; classical winner panels and quantum Pareto panels must remain separate |
| Best binary-ECDLP quantum attack resources decrease | Reproduced Garn--Kan baseline, attacker-optimal representation/circuit search, complete active-volume and physical propagation | Open and currently adverse at the degree-283 reduction kernel |
| Novelty | Hostile primary-source audit | Provisional |

Never use “first,” “optimal,” “practical,” “constant-time,” or “significant
speedup” unless the matching row is discharged.

## Theorem Dependency Graph

1. Define the truncated coefficient space and low/high decomposition.
2. Derive the reduction recurrence and feedback nilpotency.
3. Express reduction through \((I+U)^{-1}\).
4. Prove sparse Frobenius powers and the factored inverse.
5. State algorithmic correctness and exact feedback depth.
6. Derive active-tap work, space, and setup.
7. Add random-support and multiplication-based corollaries only under their
   stated models.
8. Treat coefficient-algebra, prefix-scan, and reversible-CNOT statements as
   extensions with their own hypotheses.  In particular, keep the two-cluster
   CNOT theorem separate from claims about arbitrary tap geometry.
9. Develop a cluster-separation parameter $\kappa$ and a size--depth--space
   partition theorem, using the two-cluster family as the exact $\kappa=2$
   endpoint rather than extrapolating it to arbitrary tap sets.

## Writing and Validation Order

1. Complete the scalar theorem skeleton and cost model.
2. Close the prior-art boundary for reciprocal, Toeplitz, LFSR, CRC, parallel
   prefix, sparse reduction, Barrett/Montgomery, and linear-circuit synthesis.
3. Stabilize the portable implementation and correctness checks.
4. Run matched reduction-only experiments, then end-to-end application tests.
5. Draft the introduction, abstract, and conclusion from discharged claims.

Use [exp_todo.md](exp_todo.md) as the sole execution checklist for Steps 3--4.
Topic documents define why an experiment is needed, but they do not maintain
independent copies of its task list.

Run git diff --check after every paper edit. Preserve the separation between
correctness checks, reduction microbenchmarks, and end-to-end workloads.

## Submission Gates

### Gate 1: Novelty

No prior method has been found that simultaneously gives arbitrary-modulus
correctness, sparse-support-sensitive work, logarithmic feedback depth, and a
schedule derived without materializing a dense reciprocal or reduction matrix.

### Gate 2: Theorems

The paper has exact, model-consistent results for correctness, feedback depth,
work, space, setup, and all claimed comparisons.

### Gate 3: Evidence

The evaluation identifies winning and losing regions under fixed platform,
compiler, modulus, input distribution, and timing boundary.

### Gate 4: Relevance

At least one application direction has a defensible connection to a real
workload. A reduction-only speedup is not presented as application impact.
