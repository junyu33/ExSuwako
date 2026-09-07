# Mathematics of Computation Writing Guide

This file is the single source of truth for the `math-comp` manuscript's
scope, terminology, section order, claim status, and submission gates. It is
deliberately not a repository for full proofs, prior-art notes, benchmark
plans, or application speculation; those live in the linked topic documents
below.

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

## Branch Boundary

This manuscript is theorem-first.  Its relevance claim is to finite-field and
computational-algebra workloads, especially repeated modular squaring,
irreducibility testing, and sparse-polynomial search.  It does not require a
protocol deployment, a constant-time claim, a Koblitz-curve case study, or a
reversible-circuit result.  Those cryptographic and circuit directions belong
to the `eurocrypt` branch and must not be imported as contributions here.

## Working Title

> Generalized Suwako: Sparse Modular Reduction with Logarithmic Feedback Depth

Use *feedback depth* unless a Boolean gate model is explicitly fixed.

## Topic Documents

| Topic | Canonical working document | Role |
|---|---|---|
| Full manuscript skeleton | [骨架.md](骨架.md) | Expandable Math. Comp. section scaffold; subordinate to this guide. |
| Abstract and introduction | [sections/intro_draft.md](sections/intro_draft.md) | Narrative draft; finalize last. |
| Algebra, theorems, and complexity | [notes/math_comp.md](notes/math_comp.md) | Mathematical core and claim ledger. |
| Technical body assembly | [sections/technical_body.md](sections/technical_body.md) | Manuscript section plan and proof interfaces. |
| Prior-art boundary | [sections/related_work.md](sections/related_work.md) | Paper-facing novelty boundary. |
| Prior-art audit plan | [notes/prior_art_plan.md](notes/prior_art_plan.md) | Coverage checklist and provisional comparison matrix. |
| Applications | [notes/application.md](notes/application.md) | Computational-algebra workload hypotheses and validation plans. |
| Implementation and evaluation | [sections/implementation_evaluation.md](sections/implementation_evaluation.md) | Paper-facing research questions, models, metrics, and figures. |
| Experimental execution | [exp_todo.md](exp_todo.md) | Authoritative experiment checklist, evidence gates, priorities, and artifact status. |
| Extensions and appendices | [sections/extensions_appendices.md](sections/extensions_appendices.md) | Extensions, limitations, appendices, and detailed research management. |
| Venue framing | [notes/venue_choice.md](notes/venue_choice.md) | Private submission strategy; not manuscript content. |
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
9. Computational-algebra consequences and limitations
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
| Exact stage count | \(r=\lceil\log_2(m/\Delta_{\min})\rceil\) when \(U\ne0\), and \(r=0\) when \(U=0\) |
| Per-stage active taps | \(h_k\) |
| Modulus Hamming weight | \(h=1+|T|\) |
| Operation measures | feedback depth, word work, setup, space, gate depth; never conflate them |

Call an ISA an ISA; call a concrete evaluation target a platform or machine.
Do not turn word work into instruction count, XOR count into gate count, or a
Boolean-circuit upper bound into hardware depth without fixing the model.

## Claim Ledger

| Claim | Required evidence | Current status |
|---|---|---|
| Reduction through a nilpotent feedback inverse | Formal proof | Proof drafted in the manuscript; independent audit pending |
| Frobenius preserves formal per-stage sparsity; actual support is exact over reduced algebras | Formal proof | Binary proof drafted in the manuscript; coefficient-algebra extension remains separate |
| Scheduled geometry-sensitive work bound | Formal proof with operation model | Proof drafted in the manuscript; independent audit pending |
| Exact schedule size, scalar temporary space, and setup bound | Formal proof with implementation boundary | Proof drafted in the manuscript; independent audit pending |
| Random-support work and depth laws | Formal distributional proof | Proof drafted; geometry agrees on 10,623 frozen supports |
| Algebraic computational falsification | Reproducible independent tests | Measured over GF(2), GF(4), dual numbers, and F3; not a proof |
| Generic bounded-fan-in depth lower bound | Formal model and proof | Candidate theorem |
| Native scalar speed regions and setup amortization | Reproducible matched experiments | Fresh-checkout artifact reproduced from the hash-locked 67,576-row primary-platform dataset; no cross-platform claim |
| Platform-optimal modulus changes | Search plus end-to-end measurements | Open hypothesis |
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
8. Treat coefficient-algebra and prefix-scan statements as extensions with
   their own hypotheses.

## Writing and Validation Order

1. Complete the scalar theorem skeleton and cost model.
2. Close the prior-art boundary for reciprocal, Toeplitz, LFSR, CRC, parallel
   prefix, sparse reduction, Barrett/Montgomery, and linear-circuit synthesis.
3. Stabilize the portable implementation and correctness checks.
4. Run matched reduction-only experiments, then repeated-squaring and
   irreducibility-testing workloads.
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
The hostile prior-art audit is closed for this claim boundary; reopen it only
if this boundary changes or a direct counterexample is identified.

### Gate 2: Theorems

The paper has exact, model-consistent results for correctness, feedback depth,
work, space, setup, and all claimed comparisons.

### Gate 3: Evidence

The evaluation identifies winning and losing regions under fixed platform,
compiler, modulus, input distribution, and timing boundary. The reduction-only
artifact gate is complete: a fresh checkout rebuilds all 24 current figures
and table sources from the externally supplied, hash-locked canonical dataset.
This is single-platform evidence and does not discharge relevance or theorem
proof obligations.

### Gate 4: Relevance

At least one repeated-squaring, irreducibility-testing, factorization, or
sparse-polynomial-search workload demonstrates the computational consequence
of the result.  A reduction-only speedup is not presented as workload impact.
