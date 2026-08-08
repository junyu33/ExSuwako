# Application Hypotheses: Sparse Polynomial Search and Modulus Selection

This note records candidate application directions for generalized Suwako reduction. It is not evidence that the method accelerates an end-to-end task. Each direction becomes a paper-facing claim only after a matched implementation, a reproducible workload, and comparison against the strongest specialized baseline.

The target regime is a sparse non-leading part with a high internal tap:

$$
\operatorname{wt}(q)\text{ small},
\qquad
\Delta_{\min}=m-\deg q\text{ small}.
$$

Here conventional top-down folding may have a long feedback dependency chain, whereas generalized Suwako uses

$$
D_{\mathrm{fb}}=
\left\lceil\log_2\frac{m}{\Delta_{\min}}\right\rceil
$$

feedback stages. A useful application must expose this difference repeatedly enough that reduction, rather than multiplication or unrelated overhead, remains material in the total running time.

## Main Direction: Repeated Modular Squaring in Sparse-Polynomial Search

Algorithms for distinct-degree factorization, irreducibility testing, and primitive-polynomial search repeatedly compute

$$
x^{2^d}\bmod P(x).
$$

They therefore perform a long sequence of modular squarings. In the large-degree sparse-polynomial setting, modular squaring can be much cheaper than general multiplication, yet still consume a material fraction of an end-to-end factorization or search. The historical large-trinomial work of Brent and Zimmermann is the motivating workload: it uses blocking to exploit fast squaring modulo sparse polynomials, while retaining modular square and multiplication as visible costs.

Trinomials alone are not necessarily a favorable demonstration for generalized Suwako. By using a reciprocal modulus, a trinomial's single internal tap can often be placed in the lower half, where ordinary folding already has shallow feedback. The more discriminating question is whether a uniform reducer for pentanomials or other low-weight polynomials can improve repeated modular squaring when hand-derived, family-specific reduction formulae are unavailable or unattractive.

The end-to-end hypothesis is:

$$
\text{generalized Suwako modular squaring}
\longrightarrow
\text{faster sparse-polynomial factorization or irreducibility testing}
\longrightarrow
\text{faster search or certification of irreducible/primitive polynomials}.
$$

This is credible only if all arrows are measured. The benchmark must include the polynomial-search or factorization driver, not merely a reduction-only microbenchmark.

### Required Validation

The authoritative execution checklist is
[Gate 4A of the experimental TODO](../exp_todo.md#gate-4a-repeated-modular-squaring).
It separates reduction-only, complete modular-square, and end-to-end
factorization or irreducibility evidence, and requires the strongest
specialized squaring baseline.

## Coupled Direction: Platform-Specific Modulus Selection

The choice of irreducible polynomial is an implementation decision, not only an algebraic one. A modulus favorable for serial folding need not be best for another reduction algorithm or a different target platform. The candidate research question is:

> Given a degree \(m\), an implementation target, and generalized Suwako as the reducer, which irreducible sparse polynomial minimizes the relevant arithmetic cost?

For example,

$$
f(x)=x^m+x^{m-1}+x^a+x+1
$$

has \(\Delta_{\min}=1\). It is traditionally hostile to serial folding, but generalized Suwako needs only \(\lceil\log_2m\rceil\) feedback stages. This does not establish that such a modulus wins in software or hardware: complete cost also depends on active-tap work, shifts across machine words, multiplication, squaring representation, code generation, and the platform.

The stronger hypothesis is:

$$
\text{modulus search}
+\text{ generalized-Suwako cost model}
+\text{ target-platform measurements}
\quad\text{may change the platform-optimal modulus.}
$$

An affirmative result would expand the practically viable modulus space rather than merely improve a fixed reducer. A negative result would still quantify how much the traditional friendly-modulus heuristic survives under the new method.

### Required Validation

The authoritative execution checklist is
[Gate 4B of the experimental TODO](../exp_todo.md#gate-4b-platform-specific-modulus-selection).
It covers candidate provenance, fixed objectives, architecture-specific
ranking, representation constraints, and coupling to repeated modular
squaring.

## EUROCRYPT Case Study: Koblitz Scalar Multiplication

Koblitz curves provide a direct cryptographic composition of repeated modular
squaring and reducer-aware field representation.  Over $\mathbb F_{2^m}$,
they have the form

$$
E_a:y^2+xy=x^3+ax^2+1,
\qquad a\in\{0,1\},
$$

and their Frobenius endomorphism is

$$
\tau(x,y)=(x^2,y^2).
$$

A $\tau$-adic scalar multiplication therefore invokes field squaring
repeatedly.  In a polynomial basis, each coordinate square requires modular
reduction, so this is a complete cryptographic workload whose hot path may
expose the reduction behavior studied here.

There is also a clean representation argument.  For any two irreducible
degree-$m$ binary polynomials $f_0$ and $f_1$, a field isomorphism

$$
\phi:\mathbb F_2[z]/(f_0)\longrightarrow\mathbb F_2[z]/(f_1)
$$

fixes the prime-field coefficients $a$ and $1$.  Coordinate-wise application
of $\phi$ therefore maps the same abstract Koblitz curve and group into the
new representation.  This permits a comparison between a standard polynomial
basis and an ExSuwako-oriented modulus without changing the abstract group or
ECDLP instance.  Base points, external coordinates, and any precomputed tables
must be converted explicitly, and implementation security must be evaluated
again.

### First Target: K-283

Degree $283$ is the first proposed target because it combines a standard
pentanomial representation, a verified same-degree two-cluster candidate, and
an existing high-performance implementation literature.  The paper-facing
hypothesis is not merely that generalized Suwako reduces one square faster,
but that field-representation/reducer co-design changes the winner for a
complete $\tau$-adic scalar multiplication.

The comparison should use four representation/backend classes:

1. the standard K-283 polynomial with the strongest fixed-modulus unrolled
   reducer;
2. a verified irreducible two-cluster degree-283 polynomial with generalized
   Suwako and any justified generated specialization;
3. a strong normal-basis implementation, for which Frobenius is a coordinate
   rotation but multiplication may be more expensive;
4. table-based or hybrid multi-squaring where it is a credible strongest
   baseline.

The measurement ladder is:

1. field square, multiply, and invert;
2. one $\tau$;
3. short and long $\tau^k$, separating repeated squaring from table-based
   multi-squaring;
4. random-point and fixed-point scalar multiplication;
5. complete ECDH, ECDSA signing, and ECDSA verification when matched
   reproducible entrypoints are available.

All representations must use the same abstract points and scalars.  Results
must agree after conversion to a common representation.  Isomorphism setup,
boundary conversion, precomputation, tables, and memory must be reported under
an explicit amortization policy.

### Claim Boundary

Koblitz curves are an unusually clean case study but have limited modern
deployment relevance because binary-field curves are reported as deprecated
by current NIST guidance.  This status and the historical implementation
claims about reduction-dominated K-283 squaring and multi-squaring thresholds
still require primary-source verification.  Koblitz can establish that the
method changes a complete cryptographic algorithm, but should not be the only
argument for contemporary relevance.

The complete source record and verification leads are preserved in
[crypto_1.md](../raw/crypto_1.md).  The authoritative executable checklist is
[Gate 4C of the experimental TODO](../exp_todo.md#gate-4c-koblitz-scalar-multiplication).

## High-Risk Direction: Quantum Binary-Field Arithmetic

Binary-field squaring and reduction are linear reversible maps, and Itoh--Tsujii inversion contains many squarings. Structured sparse-feedback CNOT networks are therefore an appealing target. Existing quantum work also uses modulus selection to reduce finite-field resources, so this direction overlaps with the modulus-selection question above.

It is nevertheless a separate circuit problem. Software feedback stages do not directly translate into CNOT count or quantum depth. A quantum claim requires an explicit reversible construction and a comparison under a fixed model for:

- CNOT count and CNOT depth;
- fanout realization;
- clean or dirty ancillae;
- in-place versus out-of-place computation; and
- uncomputation within the enclosing inversion or multiplication circuit.

Outside the restricted family below, the explicit circuit problem remains open. Even for that family, a comparison with the strongest existing circuits is still required before quantum arithmetic can become an application claim of the current reducer.

One restricted but nontrivial family now has a candidate clean construction. For

$$
f=x^m+x^{m-\delta}+1+\sum_{e\in B}x^e,
\qquad
B\subseteq\{1,\ldots,\lfloor m/2\rfloor\},
$$

the feedback inverse factors into one in-place suffix scan and a square-zero cross-half correction. This gives, for fixed weight, a candidate zero-ancilla reversible reduction shear with $O(m)$ CNOT count and $O(\log(m/\delta))$ CNOT depth, together with matching asymptotic lower bounds in the all-to-all two-qubit model. The derivation and its precise claim boundary are recorded in [the two-cluster construction note](../raw/cnot_4.md).

This family also contains irreducible pentanomials of the form

$$
x^m+x^{m-1}+x^a+x+1,
$$

for which both the polynomial and its reciprocal have nearest feedback distance one. Exact Sage checks found examples at degrees $128$, $163$, $233$, $283$, $409$, and $571$. These examples make the branch more concrete, but they do not replace comparison with the strongest existing CNOT synthesis or finite-field arithmetic circuits.

The circuit-model and structured-synthesis tasks are maintained in
[Gate 5A of the experimental TODO](../exp_todo.md#gate-5a-reversible-reduction-circuits).

### Executable Route B: Binary-ECDLP Resource Re-estimation

The concrete attack target is the Garn--Kan fault-tolerant implementation of
Shor's algorithm for binary elliptic-curve discrete logarithms.  It provides
exact point addition, windowed phase estimation, logical gate and qubit
counts, active volume, and physical extrapolations for
$m\in\{163,233,283,571\}$.  Its discussion explicitly identifies the large
CNOT population of binary-field multiplication as a source of high active
volume.

The attacker may map the public curve, base point, and public point through a
field isomorphism before compiling the quantum circuit.  Route B must
therefore optimize over field representations rather than compare only with
the standardized polynomial.  The attack-level question is:

> Does a structured ExSuwako reduction survive attacker-optimal modulus and
> circuit selection, complete multiplication and inversion, exact point
> addition, window re-optimization, and the published physical cost model?

The executable kernel test is available as
`bench/scripts/quantum_reduction_resources.py`.  It emits both sequential and
zero-ancilla Brent--Kung parallel-prefix realizations, validates every
conflict-free layer, independently basis-checks each scan, and checks the
complete clean shear against polynomial long division.  At degree 283, the
sequential construction reduces the two-cluster modulus from 39,342
direct-shear CNOTs to 1,741 CNOTs at depth 702.  The parallel-prefix variant
uses 2,513 CNOTs at an explicit conflict-free schedule depth of 82, with zero
ancilla.  This remains an adverse cross-representation result because the
standard NIST pentanomial's direct shear uses 1,166 CNOTs at depth 8.  The
current evidence therefore supports an executable falsification experiment,
not an attack-level improvement claim.  The parallel construction and proof
are recorded in [the circuit note](cnot_parallel_prefix.md).

The next stages are to reproduce the published resource tables, search for the
attacker-optimal irreducible modulus and circuit, embed each winner into
squaring, multiplication and FLT inversion, and then recompute ECPointAdd,
phase estimation, active volume and physical runtime.  CNOT count, CNOT depth,
swaps, Toffolis, ancillae and connectivity must all remain visible.  A change
only to a cheap Clifford subroutine is insufficient unless it affects a
complete attack resource.

The complete reasoning, primary baseline, initial output and kill criteria are
recorded in [crypto_2.md](../raw/crypto_2.md).  The executable attack-resource
checklist is
[Gate 5B of the experimental TODO](../exp_todo.md#gate-5b-binary-ecdlp-quantum-resource-re-estimation).

## Deliberately Secondary Direction: CRC and Rabin Fingerprints

CRC and Rabin fingerprinting are genuine polynomial-reduction workloads, but they are unlikely to be decisive first applications. Typical moduli are small, rolling updates and table-based methods are heavily optimized, and the best content-defined chunking implementations may avoid Rabin-style reduction entirely. A table-free programmable reducer could be an interesting case study, but should not drive the main narrative without a clear end-to-end result.

## Current Ranking

| Direction | Real workload | Potentially decisive role | Risk |
|---|---:|---:|---:|
| Koblitz $\tau$-adic scalar multiplication with reducer-aware representation | Very high | Very high | Medium-high: deprecated family and strong normal-basis baseline |
| Repeated modular squaring for sparse factorization and irreducibility testing | High | High | Medium |
| Platform-specific selection of irreducible sparse moduli | High | High | Medium |
| Binary-ECDLP quantum resource re-estimation | Very high | Very high | Very high: first kernel comparison favors the standard modulus |
| CRC and Rabin fingerprinting | High | Limited | Medium |
| Attaching the method directly to an existing PQC or ZK scheme | Unclear | Limited | High |

K-283 should be the first cryptographic case study.  It composes the first two
general directions: a cost model and a search over irreducible sparse moduli
generate representations, and $\tau$-adic scalar multiplication decides
whether the representation changes an end-to-end cryptographic workload.

## Evidence Ledger

| Statement | Status |
|---|---|
| Repeated modular squaring occurs in factorization and irreducibility workflows | Established background; verify exact workload formulations and citations. |
| Sparse high-tap moduli can be hostile to serial feedback | Proved at the feedback-depth level. |
| Generalized Suwako improves modular squaring for pentanomials | Open experimental hypothesis. |
| The platform-optimal irreducible modulus changes under generalized Suwako | Open experimental hypothesis. |
| A field-isomorphic K-283 representation improves complete $\tau$-adic scalar multiplication | Open experimental hypothesis; normal-basis and multi-squaring comparisons required. |
| Koblitz field-representation changes preserve the abstract curve group | Mathematical claim to formalize; implementation and side-channel properties are not preserved automatically. |
| A generalized-Suwako CNOT network improves quantum resources | Candidate matching asymptotic bounds for the restricted two-cluster family; prior-art and comparative evaluation remain open. |
| ExSuwako lowers the best binary-ECDLP quantum attack estimate | Open and currently adverse at the reduction kernel: structured two-cluster reduction beats its dense realization but not the standard degree-283 modulus. |
| CRC/Rabin is a compelling primary application | Currently unsupported. |

## Source Ledger to Verify

- R. P. Brent and P. Zimmermann, large sparse-polynomial factorization and trinomial-search work. [arXiv:0710.4410](https://arxiv.org/abs/0710.4410).
- Work on reduction and squaring for special irreducible pentanomials. [arXiv:1806.00432](https://arxiv.org/abs/1806.00432).
- Discussion of platform-dependent choices of irreducible polynomials for \(\operatorname{GF}(2^m)\) arithmetic. [Ask Cryptography pointer](https://askcryp.to/t/resource-topic-2007-192-optimal-irreducible-polynomials-for-gf-2-m-arithmetic/2173).
- High-tap irreducible-pentanomial implementation work. [IET record](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/el.2014.0006).
- Quantum finite-field multiplication/division and modulus selection. [arXiv:2511.20618](https://arxiv.org/abs/2511.20618).
- Garn and Kan's exact binary-ECDLP logical and physical resource model.
  [arXiv:2503.02984](https://arxiv.org/abs/2503.02984),
  [IEEE DOI](https://doi.org/10.1109/TQE.2025.3586541).
- Vandaele's subquadratic-Toffoli binary-field multiplication and specialized
  low-depth reduction circuits.
  [arXiv:2501.16136](https://arxiv.org/abs/2501.16136).
- Primary Koblitz-curve standards and $\tau$-adic scalar-multiplication
  specifications; verify the exact equations, parameters, base points, and
  polynomial/normal-basis representations.
- NIST SP 800-186; verify the exact binary-curve deprecation language and its
  scope.
- High-performance Koblitz implementations reporting K-283 field-operation
  costs and table-based multi-squaring thresholds; identify the exact papers
  before citing the bottleneck claims.
- Rabin-fingerprint content-defined chunking and FastCDC. [USENIX 2004 record](https://www.usenix.org/legacy/publications/library/proceedings/usenix04/tech/general/full_papers/policroniades/policroniades_html/index.html), [FastCDC record](https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia).

This is a search ledger rather than a final bibliography. Before using it in a paper, replace each entry with verified primary-source metadata and check that every performance or resource claim is supported by the cited source.
