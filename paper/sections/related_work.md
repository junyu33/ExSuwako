# Related Work and Novelty Boundary

This section records the current prior-art boundary for Frobenius-factorized reduction (FFR)
reduction.  It follows a hostile search rather than an exhaustive priority
claim.  The central comparison is with reduction modulo a binary monic
polynomial

$$
g(x)=x^m+\bigoplus_{t\in T}x^t,
\qquad T\subseteq\{0,\ldots,m-1\}.
$$

FFR regards the high part of an input as the right-hand side of
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
systems over arbitrary fields [5].  FFR must
therefore not be described as the first logarithmic-depth polynomial division
or as a new inverse identity.

The older structured-linear-system literature makes this boundary still
sharper. Chen and Kuck study time and processor bounds for linear recurrence
systems and relate them to triangular solves [10]. Morf explicitly develops
``doubling algorithms'' for Toeplitz and related equations [11]. Most
directly, Bini solves an \(n\times n\) triangular Toeplitz system in
\(7\log n+7\) parallel steps for exact computation in his arithmetic model;
the processor bound is \(\frac52n^2\), or \(\frac52n(k+1)\) when the matrix
has bandwidth \(k\) [12]. Murphy later restates the equivalence between
reciprocal computation modulo \(z^n\), polynomial division, and triangular
Toeplitz inversion, with polynomial degree corresponding to matrix bandwidth
[14]. Thus neither recursive doubling, logarithmic-depth triangular Toeplitz
inversion, nor the reciprocal--Toeplitz--bandwidth correspondence is a
contribution of this work.

The distinction is representational and algorithmic.  General reciprocal and
Toeplitz methods address a broader problem and may materialize a dense
reciprocal or use general polynomial multiplication.  For the sparse feedback
operator \(U\) induced by a fixed modulus, FFR instead applies

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

Bini's banded bound also clarifies why bandwidth alone does not settle that
question. A feedback operator may contain only a few shifted diagonals while
its largest shift, and hence its ordinary matrix bandwidth, is close to \(m\).
The banded processor bound then remains quadratic even though the discrete
support is sparse. The candidate distinction of FFR is not a
new Toeplitz solver, but the characteristic-two identity

$$
\rho(N)^{2^k}=\bigoplus_{t\in T}N^{2^k\Delta_t},
$$

which exposes the evolution of each occupied diagonal separately and leads to
an exact complete-support cost rather than a bandwidth-only bound.

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
expanded recurrence state.  FFR instead solves the finite
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

Ho and Lee provide an even closer generic sparse baseline. They transform a
sparse triangular system into a directed graph and solve it by edge
elimination and recursive doubling, with reported worst-case
\(O(\log^2 n)\) time on a CREW PRAM and \(O(\log m\log n)\) time for bandwidth
\(m\) [13]. This rules out novelty claims based merely on applying recursive
doubling to a sparse triangular dependency graph. Their bounds are expressed
for general sparsity and bandwidth, however, rather than for the explicit
support evolution available here: Frobenius powering retains one shifted
diagonal per original tap without combinatorial support growth. Whether this
distinction, together with the exact work expression below, is absent from
prior sparse triangular solvers remains a source-level audit obligation.

Parallel LFSR and CRC architectures supply a second relevant baseline.
Ayinala and Parhi construct equivalent state-space formulations for all CRC
and BCH generator polynomials, obtaining a full speed-up over a serial LFSR
at increased hardware cost [9].  Such constructions may materialize or
implicitly implement a general state transition.  They therefore rule out a
claim of first parallelization of arbitrary feedback, but do not by themselves
provide a support-preserving sparse reciprocal realization for fixed-length
polynomial reduction.

## Sparse Binary-Field Reduction

Sparse polynomial-basis arithmetic has a substantial earlier literature,
including word-oriented reduction, Mastrovito-style constructions, and
bit-parallel polynomial-basis arithmetic [8].  Most directly, Niehues, Custodio, and
Panario give a uniform top-down reduction procedure for arbitrary low-weight
binary moduli.  Their procedure folds high coefficients through the
non-leading support one coefficient at a time.  Their circuit discussion also
identifies that the critical path depends strongly on tap placement, and that
its delay ranges from \(2T_X\) to \((m-1)T_X\).  They report that the general
relationship between modulus shape and delay is not clear, while high taps can
produce long feedback chains [4].

This is the principal classical baseline in the low-weight regime.  Both
methods are correct for arbitrary binary monic moduli, but FFR
uses sparse, support-sensitive shift/XOR stages and preserves the serial
feedback traversal only in the baseline.  FFR replaces this
traversal by sparse stages at distances \(2^k\Delta_t\).  A final comparison
must use a common representation and report separately: shift/XOR work,
sequential feedback depth, bounded-fan-in or gate depth where a circuit model
is fixed, schedule setup, and storage.  A logarithmic feedback-stage count by
itself does not establish a wall-clock speedup or an improvement to complete
field multiplication.

The work comparison must also be stated as a tradeoff rather than a universal
improvement. In the top-down procedure, reducing an input of degree \(d\)
applies one XOR for every non-leading tap at each of the \(d-m+1\) eliminated
positions, giving the fixed circuit count

$$
(d-m+1)|T|.
$$

For a product of two degree-below-\(m\) polynomials this is at most
\((m-1)|T|\), specializing to \(2m-2\) XORs for a trinomial and \(4m-4\) for a
pentanomial. By contrast, the FFR feedback stages cost

$$
W_{\mathrm{fb}}
=\sum_k\sum_{t\in T}[m-2^k\Delta_t]_+,
$$

before the final low-part assembly is counted. This quantity is not uniformly
smaller and can incur a logarithmic work factor in hostile small-gap regimes.
The defensible claim is therefore an explicit work--feedback-depth tradeoff:
the method pays a geometry-quantified amount of work to replace a potentially
long serial dependency chain by
\(\lceil\log_2(m/\Delta_{\min})\rceil\) sparse stages. Evaluation must report
the regimes in which that exchange helps and the regimes in which ordinary
top-down folding remains preferable.

The current audit has not found a sparse-reduction result that derives the
full active-tap work expression

$$
W_{\mathrm{fb}}
=\sum_k\sum_{t\in T}[m-2^k\Delta_t]_+,
$$

or an equivalent exact work--depth geometry for a fixed-state, doubling-based
reduction schedule.  This is a candidate theorem, not yet a priority claim.

Parallel finite-field hardware also predates this work. Meher derives
systolic and non-systolic polynomial-basis multipliers using modular reduction
across multiple degrees, logic-level subexpression sharing, and balanced-tree
organization [15]. This rules out broad claims of first multi-degree parallel
reduction or first balanced XOR realization. The comparison still has to
separate a fixed multiplier architecture and its logic synthesis from the
uniform arbitrary-modulus schedule and complete tap-geometry analysis claimed
here.

## Barrett and Montgomery Families

Barrett- and Montgomery-style reductions over binary polynomial rings provide
well-established alternatives for general moduli.  They trade sparse folding
for multiplication-based operations and modulus-dependent constants, such as
a reciprocal or an inverse.  Earlier work also considers variants without a
separate precomputation phase by restricting the modulus family so that the
needed constants can be derived from the modulus itself.  In particular,
Knezevic, Sakiyama, Fan, and Verbauwhede give precomputation-free Barrett or
Montgomery reductions for two specific characteristic-two modulus families [7],
rather than for arbitrary binary moduli.

Thus, ``without precomputation'' is not an appropriate novelty claim.  The
more precise boundary is that FFR seeks not to materialize a
dense reciprocal or reduction matrix while allowing arbitrary binary monic
moduli.  Sparse support affects the work favorably, but is not a correctness
assumption.  Any comparison must state the modulus class, required partial
products, stored constants, and setup-amortization model.

## Current Novelty Boundary

The current evidence supports the following deliberately conditional
formulation:

> To the best of our current knowledge, no prior method has been identified
> that simultaneously treats arbitrary binary monic moduli; realizes the
> resulting fixed-length reduction as support-sensitive sparse shift/XOR
> stages; reduces its sequential feedback chain through a factored nilpotent
> inverse without materializing a dense reciprocal or reduction matrix;
> exposes the characteristic-two evolution of every occupied feedback
> diagonal without combinatorial support growth; and gives an exact
> work--depth characterization in terms of the complete tap geometry.

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
The following additional audit entries complete the numbered list.

- [7] M. Knezevic, K. Sakiyama, J. Fan, and I. Verbauwhede, ``Modular Reduction in \(\operatorname{GF}(2^n)\) without Pre-computational Phase,'' *WAIFI 2008*, LNCS 5130, pp. 77--87. [Author-hosted PDF](https://www.esat.kuleuven.be/cosic/publications/article-1115.pdf).

- [8] H. Wu, ``Low Complexity Bit-Parallel Finite Field Arithmetic Using Polynomial Basis,'' *CHES 1999*, pp. 280--291. [Bibliographic record](https://dblp.org/rec/conf/ches/Wu99).

- [9] M. Ayinala and K. K. Parhi, ``High-Speed Parallel Architectures for Linear Feedback Shift Registers,'' *IEEE Transactions on Signal Processing* 59(9), pp. 4459--4469, 2011, DOI: 10.1109/TSP.2011.2159495. [Institutional record](https://experts.umn.edu/en/publications/high-speed-parallel-architectures-for-linear-feedback-shift-regis/).

- [10] S.-C. Chen and D. J. Kuck, ``Time and Parallel Processor Bounds for
  Linear Recurrence Systems,'' *IEEE Transactions on Computers* C-24(7),
  pp. 701--717, 1975, DOI: 10.1109/T-C.1975.224291.
  [DBLP record](https://dblp.org/rec/journals/tc/ChenK75).

- [11] M. Morf, ``Doubling Algorithms for Toeplitz and Related Equations,''
  *Proceedings of ICASSP 1980*, pp. 954--959, DOI:
  10.1109/ICASSP.1980.1171074.
  [DBLP record](https://dblp.org/rec/conf/icassp/Morf80).

- [12] D. Bini, ``Parallel Solution of Certain Toeplitz Linear Systems,''
  *SIAM Journal on Computing* 13(2), pp. 268--276, 1984, DOI:
  10.1137/0213019.
  [Publisher record](https://epubs.siam.org/doi/10.1137/0213019).

- [13] C.-W. Ho and R. C. T. Lee, ``A Parallel Algorithm for Solving Sparse
  Triangular Systems,'' *IEEE Transactions on Computers* 39(6), pp. 848--852,
  1990, DOI: 10.1109/12.53610.
  [Institutional record](https://scholars.ncu.edu.tw/en/publications/a-parallel-algorithm-for-solving-sparse-triangular-systems/).

- [14] B. J. Murphy, ``Acceleration of the Inversion of Triangular Toeplitz
  Matrices and Polynomial Division,'' in *Computer Algebra in Scientific
  Computing*, LNCS 6885, pp. 321--332, 2011, DOI:
  10.1007/978-3-642-23568-9_25.
  [DBLP record](https://dblp.org/rec/conf/casc/Murphy11).

- [15] P. K. Meher, ``Systolic and Non-Systolic Scalable Modular Designs of
  Finite Field Multipliers for Reed--Solomon Codec,'' *IEEE Transactions on
  Very Large Scale Integration (VLSI) Systems* 17(6), pp. 747--757, 2009,
  DOI: 10.1109/TVLSI.2008.2006080.
  [Author manuscript](https://citeseerx.ist.psu.edu/document?doi=4c7d167f77e07c620d7b1f7c550e6f635277afc4).

The bibliography above is a claim ledger rather than a final reference list.
Before submission, verify the exact model and theorem used from each primary
source, replace these records with checked bibliography entries, and add any
older sparse-reciprocal, LFSR, or VLSI result discovered by citation chasing.
