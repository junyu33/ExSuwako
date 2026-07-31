# Related Work and Novelty Boundary

This section records the current prior-art boundary for generalized Suwako
reduction.  It follows a hostile search rather than an exhaustive priority
claim.  The central comparison is with reduction modulo a binary monic
polynomial

$$
g(x)=x^m+\bigoplus_{t\in T}x^t,
\qquad T\subseteq\{0,\ldots,m-1\}.
$$

Generalized Suwako regards the high part of an input as the right-hand side of
a finite, forced, nilpotent feedback recurrence.  Its proposed contribution is
not the existence of a reciprocal, a Frobenius identity, or a generic
logarithmic-depth recurrence solver.  The relevant candidate contribution is
the following specialization: it applies a factored reciprocal to the fixed
length reduction problem as sparse shift/XOR stages, retains the original tap
support in each factor, and exposes work and stage bounds determined by the
complete tap geometry.  All novelty language below remains conditional on a
complete source-level audit.

Correctness applies to every binary monic modulus, including dense moduli.
Sparsity is a performance condition rather than an applicability condition:
it controls the amount of shift/XOR work in the factored schedule.  For dense
moduli, multiplication-based Barrett or Montgomery reductions may be the more
appropriate implementation choice.

## Generic Polynomial Division and Truncated Reciprocals

Classical parallel polynomial division reduces division to triangular Toeplitz
inversion or reciprocal computation modulo a power of the indeterminate.  In
particular, Bini and Pan obtain logarithmic parallel time for general
polynomial division through these reductions [1].  Formal power-series inversion,
Newton/Hensel precision doubling, and finite geometric-series inverses of
nilpotent operators are likewise established tools [6].  More broadly,
randomized polylogarithmic-time parallel algorithms exist for general linear
systems over arbitrary fields [5].  Generalized Suwako must
therefore not be described as the first logarithmic-depth polynomial division
or as a new inverse identity.

The distinction is representational and algorithmic.  General reciprocal and
Toeplitz methods address a broader problem and may materialize a dense
reciprocal or use general polynomial multiplication.  For the sparse feedback
operator \(U\) induced by a fixed modulus, generalized Suwako instead applies

$$
(I+U)^{-1}=\prod_{k\geq 0}(I+U^{2^k})
$$

only up to nilpotence.  In characteristic two, a stage has the form

$$
U^{2^k}=\bigoplus_{t\in T} S_{2^k\Delta_t},
\qquad \Delta_t=m-t,
$$

so it has one shifted contribution per original tap.  The method does not
store the mixed terms arising from the product as a reciprocal polynomial or a
reduction matrix.  The unresolved audit question is whether prior
parallel-division or sparse-reciprocal work gives the same fixed-state,
support-preserving realization together with a tap-geometry-sensitive work
analysis.

## LFSR Look-Ahead and Parallel Recurrences

The closest known local mechanism is the term-preserving look-ahead
transformation (TePLAT) of Lin, Chen, and Hu.  For an LFSR generator
polynomial \(P(x)\), TePLAT replaces it by \(P(x)^2\); in characteristic two,
this doubles every exponent while preserving the number of nonzero terms.  The
construction can be iterated to obtain a bit-parallel recurrence with the
original feedback-term count [2].  This result precludes claims that Frobenius
squaring preserves tap count, or that term-preserving feedback-distance
doubling itself, is new.

TePLAT nevertheless solves a different problem.  It transforms a homogeneous
LFSR recurrence into one of higher order and trades iteration span against the
expanded recurrence state.  Generalized Suwako instead solves the finite
forced triangular system

$$
(I+U)Y=H
$$

within the fixed \(m\)-coefficient reduction state.  Its factors are applied
as an implicit inverse rather than adopted as the generator of a new,
higher-order LFSR.  No source found in the present audit applies TePLAT's
term-preserving doubling to arbitrary binary modular reduction in this
fixed-state form, nor derives the complete tap-geometry work formula used
here.  This distinction should be explained directly rather than left as an
implicit difference of application domains.

More generally, recursive doubling and parallel-prefix algorithms for linear
recurrences are classical.  Kogge and Stone give a parallel algorithm for a
general class of recurrence equations, including higher-order linear
recurrences [3].  Consequently, reducing a bounded-order recurrence through a
state transition and a prefix computation is a standard baseline.  Any
prefix-scan specialization in this work should be presented as a comparison
regime, not as an independent novelty claim.  Its role is to identify the
parameter region in which a bounded normalized feedback order is preferable to
sparse Frobenius stages.

Parallel LFSR and CRC architectures supply a second relevant baseline.
Ayinala and Parhi construct equivalent state-space formulations for all CRC
and BCH generator polynomials, obtaining a full speed-up over a serial LFSR
at increased hardware cost [10].  Such constructions may materialize or
implicitly implement a general state transition.  They therefore rule out a
claim of first parallelization of arbitrary feedback, but do not by themselves
provide a support-preserving sparse reciprocal realization for fixed-length
polynomial reduction.

## Sparse Binary-Field Reduction

Sparse polynomial-basis arithmetic has a substantial earlier literature,
including word-oriented reduction, Mastrovito-style constructions, and
bit-parallel polynomial-basis arithmetic [9].  Most directly, Niehues, Custodio, and
Panario give a uniform top-down reduction procedure for arbitrary low-weight
binary moduli.  Their procedure folds high coefficients through the
non-leading support one coefficient at a time.  Their circuit discussion also
identifies that the critical path depends strongly on tap placement, and that
its delay ranges from \(2T_X\) to \((m-1)T_X\).  They report that the general
relationship between modulus shape and delay is not clear, while high taps can
produce long feedback chains [4].

This is the principal classical baseline in the low-weight regime.  Both
methods are correct for arbitrary binary monic moduli, but generalized Suwako
uses sparsity to make its shift/XOR work favorable and preserves the serial
feedback traversal only in the baseline.  Generalized Suwako replaces this
traversal by sparse stages at distances \(2^k\Delta_t\).  A final comparison
must use a common representation and report separately: shift/XOR work,
sequential feedback depth, bounded-fan-in or gate depth where a circuit model
is fixed, schedule setup, and storage.  A logarithmic feedback-stage count by
itself does not establish a wall-clock speedup or an improvement to complete
field multiplication.

The current audit has not found a sparse-reduction result that derives the
full active-tap work expression

$$
W_{\mathrm{fb}}
=\sum_k\sum_{t\in T}[m-2^k\Delta_t]_+,
$$

or an equivalent exact work--depth geometry for a fixed-state, doubling-based
reduction schedule.  This is a candidate theorem, not yet a priority claim.

## Barrett and Montgomery Families

Barrett- and Montgomery-style reductions over binary polynomial rings provide
well-established alternatives for general moduli.  They trade sparse folding
for multiplication-based operations and modulus-dependent constants, such as
a reciprocal or an inverse.  Earlier work also considers variants without a
separate precomputation phase by restricting the modulus family so that the
needed constants can be derived from the modulus itself.  In particular,
Knezevic, Sakiyama, Fan, and Verbauwhede give precomputation-free Barrett or
Montgomery reductions for two specific characteristic-two modulus families [8],
rather than for arbitrary binary moduli.

Thus, ``without precomputation'' is not an appropriate novelty claim.  The
more precise boundary is that generalized Suwako seeks not to materialize a
dense reciprocal or reduction matrix while allowing arbitrary binary monic
moduli.  Sparse support affects the work favorably, but is not a correctness
assumption.  Any comparison must state the modulus class, required partial
products, stored constants, and setup-amortization model.

## Quantum and Reversible Circuits

There is extensive prior work on CNOT realizations of binary-field arithmetic,
including squaring, multiplication, and reduction circuits.  In particular,
Vandaele gives a construction for primitive trinomials in which the reduction
matrix decomposes into CNOT ladders indexed by residue classes modulo the tap
distance.  The ladders admit a logarithmic-depth implementation.  This is
closely aligned with the chain decomposition obtained from a trinomial
\(x^m+x^t+1\), where \(\Delta=m-t\) [7].

Accordingly, this work must not claim the first linear-size or logarithmic
depth CNOT construction for trinomial reduction.  The trinomial upper-bound
construction is prior art.  A reversible-circuit contribution would require a
separate, explicit result beyond that construction, for example a
model-specific lower bound, a sharp \(\Delta\)-parameterized resource bound
not implied by the known ladder construction, or a multi-tap extension with a
clear size--depth--space comparison.  Classical correctness and scalar
software measurements alone do not establish any such circuit claim.
A zero-ancilla shear formulation or exact CNOT constants would likewise
require a direct comparison with the ladder construction before being claimed.

## Current Novelty Boundary

The current evidence supports the following deliberately conditional
formulation:

> To the best of our current knowledge, no prior method has been identified
> that simultaneously treats arbitrary binary monic moduli; realizes the
> resulting fixed-length reduction as support-sensitive sparse shift/XOR
> stages; reduces its sequential feedback chain through a factored nilpotent
> inverse without materializing a dense reciprocal or reduction matrix; and
> gives an exact work--depth characterization in terms of the complete tap
> geometry.

This is not a claim that the Frobenius-doubling observation is new.  TePLAT
already supplies its nearest known recurrence-level antecedent, and generic
parallel division and prefix methods supply broader antecedents.  The central
research question is whether their combination with fixed-state sparse modular
reduction and the associated exact geometry analysis is genuinely absent from
the literature.

## References for the Prior-Art Audit

- [1] D. Bini and V. Pan, ``Fast Parallel Polynomial Division via Reduction to
  Triangular Toeplitz Matrix Inversion and to Polynomial Inversion Modulo a
  Power,'' *Information Processing Letters* 21(2), 1985.
  [Publisher record](https://www.sciencedirect.com/science/article/abs/pii/0020019085900377).
- [2] J.-C. Lin, S.-J. Chen, and Y. H. Hu, ``Cycle-Efficient LFSR
  Implementation on Word-Based Microarchitecture,'' *IEEE Transactions on
  Computers* 62(4), 2013, DOI: 10.1109/TC.2012.14.
  [Institutional record](https://scholars.lib.ntu.edu.tw/entities/publication/cf88d695-1e7d-4867-88bf-5632d1877206).
- [3] P. M. Kogge and H. S. Stone, ``A Parallel Algorithm for the Efficient
  Solution of a General Class of Recurrence Equations,'' *IEEE Transactions
  on Computers* 22(8), 1973, DOI: 10.1109/TC.1973.5009159.
- [4] L. Boppre Niehues, R. Custodio, and D. Panario, ``Fast Modular Reduction
  and Squaring in \(\operatorname{GF}(2^m)\),'' *Information Processing
  Letters* 132, 2018, DOI: 10.1016/j.ipl.2017.12.002.
  [Publisher record](https://www.sciencedirect.com/science/article/abs/pii/S0020019017302168).
- [5] R. Kaltofen and V. Pan, ``Processor-Efficient Parallel Solution of Linear
  Systems II: The Positive Characteristic and Singular Cases,'' *Proceedings
  of the 33rd Annual Symposium on Foundations of Computer Science* (FOCS),
  1992, pp. 714--723.
- [6] K. S. K. Kalorkoti, ``Inverting Polynomials and Formal Power Series,''
  *SIAM Journal on Computing* 22(3), 1993, DOI: 10.1137/0222037.
  [Publisher record](https://epubs.siam.org/doi/10.1137/0222037).
- [7] V. Vandaele, ``Quantum Binary Field Multiplication with Subquadratic
  Toffoli Gate Count and Low Space-Time Cost,'' arXiv:2501.16136, 2025.
  [arXiv record](https://arxiv.org/abs/2501.16136).

The following additional audit entries complete the numbered list.

- [8] M. Knezevic, K. Sakiyama, J. Fan, and I. Verbauwhede, ``Modular Reduction in \(\operatorname{GF}(2^n)\) without Pre-computational Phase,'' *WAIFI 2008*, LNCS 5130, pp. 77--87. [Author-hosted PDF](https://www.esat.kuleuven.be/cosic/publications/article-1115.pdf).

- [9] H. Wu, ``Low Complexity Bit-Parallel Finite Field Arithmetic Using Polynomial Basis,'' *CHES 1999*, pp. 280--291. [Bibliographic record](https://dblp.org/rec/conf/ches/Wu99).

- [10] M. Ayinala and K. K. Parhi, ``High-Speed Parallel Architectures for Linear Feedback Shift Registers,'' *IEEE Transactions on Signal Processing* 59(9), pp. 4459--4469, 2011, DOI: 10.1109/TSP.2011.2159495. [Institutional record](https://experts.umn.edu/en/publications/high-speed-parallel-architectures-for-linear-feedback-shift-regis/).

The bibliography above is a claim ledger rather than a final reference list.
Before submission, verify the exact model and theorem used from each primary
source, replace these records with checked bibliography entries, and add any
older sparse-reciprocal, LFSR, or VLSI result discovered by citation chasing.
