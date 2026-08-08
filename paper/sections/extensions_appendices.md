# Extensions, Limitations, and Research Management

The mathematical and prior-art TODOs remain in this document.  All
implementation, evaluation, application, circuit-counting, and artifact tasks
are maintained in [the experimental TODO](../exp_todo.md).

## 10. Extensions

### 10.1 Coefficient Algebras

Let $A$ be a commutative $\mathbb F_2$-algebra and

$$
g(Y)=Y^m+\sum_ta_tY^t.
$$

Define

$$
U=\sum_ta_tS_{m-t}.
$$

Then

$$
U^{2^k}
=
\sum_ta_t^{2^k}S_{2^k(m-t)}.
$$

Place the full result in an appendix unless it becomes central.

### 10.2 Tower Fields

State mathematical applicability, but do not claim a strong benefit for
quadratic towers without evidence.

### 10.3 Hardware Interpretation

Discuss balanced XOR trees, fanout, stage pipelining, and area-latency
tradeoffs.

## 11. Limitations

1. Feedback depth is not bounded-fan-in gate depth.
2. Work grows with the number of active taps.
3. Dense moduli may be poor targets.
4. Practical crossover depends on shift throughput and memory traffic.
5. Barrett/Montgomery may win at small degrees.
6. No lower bound or optimality result is currently claimed.
7. The coefficient-algebra extension lacks a compelling direct application.
8. Novelty remains conditional on the LFSR, CRC, and parallel-division audit.

## 12. Conclusion

1. State correctness for arbitrary binary moduli.
2. Restate the sparse-work versus serial-depth constraint.
3. Introduce the sparse feedback operator.
4. State the characteristic-two Frobenius factorization and its classical
   reciprocal-doubling relation.
5. State logarithmic feedback depth.
6. State sparse-sensitive work and lightweight setup.
7. State the experimentally identified useful regimes.
8. Close with:

   > Characteristic-two structure can shorten a feedback chain without first
   > densifying the operator that created it.

## Appendices

- Appendix A: Full correctness proof
- Appendix B: Exact word-operation and memory counts
- Appendix C: Trinomial reduction and parallel prefix
- Appendix D: Coefficient-algebra extension
- Appendix E: Exhaustive and randomized validation
- Appendix F: Native implementation details
- Appendix G: Complete benchmark results
- Appendix H: Prior-art comparison matrix

## Theorem Dependency Graph

1. Lemma 1: one-step low/high decomposition.
2. Lemma 2: reduction recurrence.
3. Lemma 3: nilpotency of $U$.
4. Theorem 1: reduction through $(I+U)^{-1}$.
5. Lemma 4: sparse Frobenius powers.
6. Theorem 2: sparse inverse factorization.
7. Theorem 3: algorithmic correctness.
8. Theorem 4: feedback-depth bound.
9. Theorem 5: active-tap work, space, and setup.
10. Corollary 1: constant-weight complexity.
11. Corollary 2: schoolbook comparison.
12. Corollary 3: Karatsuba comparison.
13. Optional Theorem 6: coefficient-algebra extension.

## Claim-to-Evidence Matrix

| Claim | Formal proof | Experiment | Prior-art audit |
|---|---:|---:|---:|
| Correct for arbitrary binary moduli | required | required | sparse reduction |
| Logarithmic feedback depth | required | scaling test | serial/LFSR |
| Stage count independent of $|T|$ for fixed $\Delta_{\min}$ | required | fixed-gap $|T|$-sweep | multi-tap look-ahead |
| Work sensitive to $h_k$ | required | work/runtime test | dense/generic division |
| Random-support expected work and depth | required | fixed-weight support sweep | sparse reduction / look-ahead |
| Three-regime algorithm-selection phase diagram | no universal boundary | fixed-$m$ sampled winner panels | serial folding / multiplication reduction |
| Lower work than Barrett/Montgomery in sparse regimes | required | heatmap | multiplication reduction |
| Lightweight setup | precise definition | amortization | reciprocal/matrix |
| Useful on real moduli | no | required | parameter sources |
| Coefficient-algebra extension | required | optional | algebra literature |

## Writing Order

### Phase 1: Theorem Skeleton

- [ ] Freeze definitions.
- [ ] Freeze the depth model.
- [ ] Complete proofs.
- [ ] Derive exact complexity formulas.

### Phase 2: Prior-Art Boundary

- [ ] Build the comparison matrix.
- [ ] Identify the closest results.
- [ ] Rewrite the novelty statement.

### Phase 3: Implementation and Evidence

Execute [the experimental TODO](../exp_todo.md) in evidence-gate order.

### Phase 4: Flagship Narrative

Write the Abstract and Introduction last.

The Introduction must describe only results already established in the
technical sections.

## Immediate TODO List

### Mathematics

- [ ] Formalize the truncated shift space.
- [ ] Prove the one-step decomposition.
- [ ] Prove the recurrence.
- [ ] Prove nilpotency with the sharp bound.
- [ ] Prove sparse Frobenius powers.
- [ ] Prove inverse factorization.
- [ ] Derive exact active-tap work.
- [ ] Prove the random-support active-work and feedback-depth bounds.
- [ ] Derive exact space and setup.
- [ ] Formalize the Barrett/Montgomery comparison.

### Prior Art

- [ ] Parallel polynomial division.
- [ ] Reciprocal and Toeplitz inversion.
- [ ] LFSR look-ahead.
- [ ] Parallel CRC.
- [ ] Parallel prefix.
- [ ] Newton/Hensel power-series inversion in characteristic two.
- [ ] Factored reciprocal representations.
- [ ] Sparse application of reciprocal-doubling factors.
- [ ] Nilpotent-operator inversion over $\mathbb F_2$.
- [ ] Sparse finite-field reduction.
- [ ] Barrett/Montgomery over $\mathbb F_2[x]$.
- [ ] Dense XOR-network synthesis.

### Experimental Work

Implementation, classical evaluation, repeated modular squaring, modulus
selection, and artifact packaging are tracked only in
[exp_todo.md](../exp_todo.md).

## Submission Gates

### Gate 1: Novelty

No prior method found that simultaneously gives:

- correctness for arbitrary binary moduli;
- sparsity-sensitive work when the non-leading part is sparse;
- logarithmic feedback depth;
- lightweight setup without materializing a dense reciprocal polynomial or
  reduction matrix.

### Gate 2: Theorems

Exact and model-consistent results for:

- correctness;
- depth;
- work;
- space;
- setup;
- multiplication-based comparison.

### Gate 3: Evidence

A broad, non-artificial parameter region is a genuine Pareto improvement in

$$
(\text{work},\text{feedback depth},\text{setup}).
$$

### Gate 4: Cryptographic Relevance

The evaluated degrees and moduli connect to real cryptographic arithmetic,
even if the main contribution remains foundational.
