# Prior-Art Audit Plan

## 7. Prior Art and Novelty Boundary

### 7.1 Sparse Finite-Field Reduction

For each paper, record:

- allowed modulus class;
- Hamming-weight assumptions;
- tap-placement assumptions;
- work;
- depth notion;
- preprocessing.

### 7.2 Parallel Prefix

State clearly:

> The trinomial specialization is closely related to classical XOR scan. The
> general result concerns a multi-tap feedback operator whose Frobenius powers
> remain sparse.

### 7.3 LFSR Look-Ahead

Audit transition-matrix powering, jump-ahead methods, arbitrary taps, sparse
preservation, total work, and circuit size.

### 7.4 Parallel CRC

Audit fixed-width unfolding, generated XOR matrices, depth, area, setup, and
whether the construction is uniform in the modulus.

### 7.5 Generic Polynomial Division

Compare circuit model, depth, work/size, uniformity, fixed or variable divisor,
and preservation of a sparse divisor representation.

### 7.6 Barrett and Montgomery

Record exact partial products, reciprocal/precomputation requirements,
characteristic-two variants, and word-complexity assumptions.

### 7.7 Truncated Reciprocal and Newton/Hensel Doubling

Compare the construction against:

- general reciprocal iteration;
- Newton/Hensel precision doubling;
- characteristic-two specializations;
- whether a reciprocal is materialized or only represented implicitly;
- whether general polynomial multiplication is required;
- whether tap sparsity is preserved under application;
- whether the method gives a $\Delta_{\min}$-sensitive stage bound.

The comparison should distinguish a reciprocal algorithm's algebraic identity
from the sparse shift/XOR realization used here.

### 7.8 Dense Linear-Circuit Synthesis

Compare XOR count, gate depth, storage, matrix synthesis cost, and fixed-modulus
assumptions.

### 7.9 Provisional Novelty Statement

> To our knowledge, prior methods do not simultaneously provide:
>
> - correctness for arbitrary binary moduli;
> - work sensitive to the support of the non-leading part when it is sparse;
> - logarithmic sequential feedback depth; and
> - an execution schedule generated directly from the modulus support,
>   without materializing a dense reciprocal polynomial or reduction matrix.

TODO: revise after completing the audit.
