# Related Work and Novelty Boundary

This note records the current prior-art boundary for generalized Suwako
reduction.  It is a working draft derived from a hostile search, rather than a
claim that the search is exhaustive.  In particular, each cited primary source
must still be checked for its precise model, assumptions, and terminology
before this text is incorporated into a submission.

The relevant object is reduction modulo a binary monic polynomial

$$
g(x)=x^m+\bigoplus_{t\in T}x^t,
\qquad T\subseteq\{0,\ldots,m-1\}.
$$

Generalized Suwako views the high part of an input through a nilpotent sparse
feedback operator.  Its proposed distinction is not the abstract existence of
an inverse or of a logarithmic-depth division algorithm.  Rather, it is the
following combination: for this feedback operator in characteristic two, the
binary inverse factorization can be applied as sparse shift/XOR stages because
Frobenius powers double the original tap distances without increasing the
number of taps in an individual factor.  This gives a schedule derived directly
from the modulus support, with stage count controlled by the tap geometry and
without materializing a dense reciprocal or reduction matrix.

The word “proposed” is important here.  The comparison below identifies the
closest known families and the obligations for a complete audit; it does not
yet establish a priority claim.

## Generic Parallel Polynomial Division and Toeplitz Inversion

Classical work on fast parallel polynomial division reduces division to
triangular Toeplitz inversion and polynomial reciprocal computation modulo a
power of the indeterminate.  These results already give logarithmic parallel
depth for general polynomial division, and subsequent work studies
work--depth tradeoffs for reciprocal computation.  Consequently, generalized
Suwako must not be presented as the first logarithmic-depth algorithm for
polynomial modular reduction.

The intended distinction is structural.  Generic reciprocal and Toeplitz
methods solve a broader problem and may use dense linear algebra, FFT-based
polynomial arithmetic, or general multiplication.  Generalized Suwako instead
uses the sparse reduction feedback induced by a fixed binary modulus.  For the
operator \(U\), its factors have the form

$$
I+U^{2^k},
\qquad
U^{2^k}=
\bigoplus_{t\in T} S_{2^k(m-t)},
$$

so each factor retains the original support cardinality while its shifts are
simply doubled.  Mixed tap combinations are produced by composing factors;
they are not stored as a reciprocal polynomial.  The audit question is thus
whether prior parallel-division work gives this same sparse, support-preserving
realization and a corresponding \(\Delta_{\min}\)-sensitive bound, not merely
whether it gives a parallel inverse.

## Sparse Binary-Field Reduction

Niehues, Custódio, and Panario study modular reduction and squaring in
\(\operatorname{GF}(2^m)\) for arbitrary low-weight moduli.  Their general
reduction procedure eliminates high coefficients from top degree to bottom
degree by folding each coefficient through the non-leading terms of the
modulus.  The paper explicitly treats circuit delay as sensitive to the
modulus and reports that taps near the leading term can yield a long critical
path.

This work is the most direct algorithmic baseline for generalized Suwako.  It
shares the sparse-modulus setting but retains the serial feedback traversal.
Generalized Suwako aims to replace that traversal by a doubling sequence of
sparse feedback stages.  A careful final comparison should use the same
representation and count separately: sparse shift/XOR work, sequential
feedback depth, parallel or gate depth, modulus setup, and storage.  It should
not infer a speedup from asymptotic depth alone.

## Barrett and Montgomery Families

Barrett- and Montgomery-style reductions over binary polynomial rings provide
well-established alternatives for general moduli.  They normally trade sparse
folding for multiplication-based operations and modulus-dependent constants,
such as a reciprocal or an inverse.  Earlier work also considers
precomputation-free variants by choosing special modulus families whose
required constants can be recovered from the modulus itself.

Accordingly, “without precomputation” is not a suitable novelty claim on its
own.  The relevant boundary is narrower: generalized Suwako seeks to avoid
materializing a dense reciprocal while remaining applicable to arbitrary binary
monic moduli, with favorable work only when the non-leading support is sparse.
The final comparison must state the allowed modulus family, the required
partial products, which constants are precomputed, and whether such setup is
amortized.

## Formal Power-Series and Nilpotent Inversion

The identities underlying the construction are classical.  Inverting a
truncated polynomial or formal power series, solving triangular Toeplitz
systems, and Newton/Hensel precision doubling are established techniques.
Likewise, for a nilpotent operator \(U\), the finite geometric-series inverse
and its binary factorization are elementary consequences of the nilpotence and
of characteristic two.  These identities should therefore be used as tools in
the proof, not advertised as independent new theorems.

The possible contribution lies in their specialization to the feedback
operator induced by sparse binary modular reduction.  The audit must determine
whether existing work already combines all of the following features:

- a modulus-induced nilpotent shift-feedback operator;
- a binary factorization applied without materializing the reciprocal;
- Frobenius preservation of the per-factor tap sparsity;
- a work and stage analysis governed by the original tap distances, in
  particular \(\Delta_{\min}\).

An earlier formula that is algebraically equivalent to one factorization would
not by itself settle this question.  It would, however, affect the priority and
must be cited and compared directly.

## Quantum and Reversible-Circuit Work

There is prior work on low-depth quantum circuits for binary-field squaring,
binary-field Montgomery multiplication, and modulus selection for finite-field
arithmetic with CNOT-oriented resource metrics.  Generalized Suwako should not
claim the first CNOT realization of binary-field reduction, the first
low-depth binary-field squaring circuit, or the first study of modulus choice
for quantum resources.

A quantum contribution, if pursued, needs a separate theorem and a
source-by-source comparison.  The defensible target would be an explicit
size--depth--space tradeoff for the particular sparse-feedback family, ideally
with an appropriate optimality or approximation statement.  Classical
reduction correctness and a scalar software benchmark do not establish such a
claim.

## Current Novelty Statement

The present evidence supports only the following conditional formulation:

> To the best of our current knowledge, no prior method has been identified
> that simultaneously treats arbitrary binary monic moduli, retains
> support-sensitive sparse shift/XOR stages for sparse non-leading parts,
> reduces the sequential feedback chain by a Frobenius-sparse binary inverse
> factorization, and generates that schedule without materializing a dense
> reciprocal polynomial or reduction matrix.

This statement must remain provisional until the audit covers parallel
polynomial division, reciprocal and Toeplitz inversion, LFSR jump-ahead and
look-ahead constructions, parallel CRC generation, sparse finite-field
reduction, Barrett/Montgomery variants, and dense XOR-network synthesis.  In
particular, a relevant older result may appear as a matrix recurrence, an LFSR
formula, a thesis, or a VLSI construction rather than as a paper titled
“modular reduction.”

## Sources to Verify Against Primary Versions

- D. Bini and V. Pan, “Fast Parallel Polynomial Division via Reduction to
  Triangular Toeplitz Matrix Inversion and to Polynomial Inversion Modulo a
  Power,” *Information and Computation* (1985).
  [ScienceDirect record](https://www.sciencedirect.com/science/article/abs/pii/0020019085900377).
- P. Niehues, A. L. Custódio, and D. Panario, “Fast Modular Reduction and
  Squaring in \(\operatorname{GF}(2^m)\),” *Information and Computation*
  (2018). [ScienceDirect record](https://www.sciencedirect.com/science/article/abs/pii/S0020019017302168).
- “Modular Reduction in \(\operatorname{GF}(2^n)\) without
  Pre-computational Phase” (2008). [ResearchGate record](https://www.researchgate.net/publication/226315010_Modular_Reduction_in_GF2_n_without_Pre-computational_Phase).
- “Inverting Polynomials and Formal Power Series,” *SIAM Journal on
  Computing*. [Publisher record](https://epubs.siam.org/doi/10.1137/0222037).
- “Design of Quantum Circuits for Galois Field Squaring and Exponentiation”
  (2017). [arXiv record](https://arxiv.org/abs/1706.05114).

The bibliographic metadata above is a search ledger, not yet a validated
reference list.  Before submission, replace it with checked BibTeX entries and
add primary-source citations for the specific claims used in the paper.
