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

- Select large, irreducible candidate pentanomials and more general low-weight supports, including cases with \(\Delta_{\min}\) close to one.
- Compare generalized Suwako with serial folding, a specialized reducer when one exists, and an appropriate multiplication-based baseline.
- Measure modular squaring separately from complete DDF, irreducibility, or primitive-polynomial-search workloads.
- Report the reduction/squaring fraction of end-to-end time and the final speedup under fixed machine, compiler, input distribution, and seed.
- Treat a negative result as informative: a specialized formula, reciprocal representation, or multiplication routine may dominate on a given family.

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

- Enumerate or sample irreducible sparse moduli at fixed \(m\) and bounded weight, stratified by \(\Delta_{\min}\) and full tap geometry.
- Define the target operation explicitly: reduction alone, modular squaring, multiplication, inversion, or an application-level workload.
- Measure each stated platform with identical multiplication backends and fixed public moduli; do not transfer conclusions across ISAs.
- Compare against the conventional choice rule and report whether its selected modulus changes.
- Keep irreducibility-search cost separate from steady-state arithmetic unless the intended application changes moduli online.

## High-Risk Direction: Quantum Binary-Field Arithmetic

Binary-field squaring and reduction are linear reversible maps, and Itoh--Tsujii inversion contains many squarings. Structured sparse-feedback CNOT networks are therefore an appealing target. Existing quantum work also uses modulus selection to reduce finite-field resources, so this direction overlaps with the modulus-selection question above.

It is nevertheless a separate circuit problem. Software feedback stages do not directly translate into CNOT count or quantum depth. A quantum claim requires an explicit reversible construction and a comparison under a fixed model for:

- CNOT count and CNOT depth;
- fanout realization;
- clean or dirty ancillae;
- in-place versus out-of-place computation; and
- uncomputation within the enclosing inversion or multiplication circuit.

Until such a construction and comparison exist, quantum arithmetic is a high-upside research branch, not an application claim of the current reducer.

## Deliberately Secondary Direction: CRC and Rabin Fingerprints

CRC and Rabin fingerprinting are genuine polynomial-reduction workloads, but they are unlikely to be decisive first applications. Typical moduli are small, rolling updates and table-based methods are heavily optimized, and the best content-defined chunking implementations may avoid Rabin-style reduction entirely. A table-free programmable reducer could be an interesting case study, but should not drive the main narrative without a clear end-to-end result.

## Current Ranking

| Direction | Real workload | Potentially decisive role | Risk |
|---|---:|---:|---:|
| Repeated modular squaring for sparse factorization and irreducibility testing | High | High | Medium |
| Platform-specific selection of irreducible sparse moduli | High | High | Medium |
| Quantum binary-field squaring and inversion | High | Very high | High |
| CRC and Rabin fingerprinting | High | Limited | Medium |
| Attaching the method directly to an existing PQC or ZK scheme | Unclear | Limited | High |

The first two directions should be pursued together: a cost model and a search over irreducible sparse moduli generate candidates, and repeated modular-squaring workloads decide whether the candidates produce a meaningful end-to-end gain.

## Evidence Ledger

| Statement | Status |
|---|---|
| Repeated modular squaring occurs in factorization and irreducibility workflows | Established background; verify exact workload formulations and citations. |
| Sparse high-tap moduli can be hostile to serial feedback | Proved at the feedback-depth level. |
| Generalized Suwako improves modular squaring for pentanomials | Open experimental hypothesis. |
| The platform-optimal irreducible modulus changes under generalized Suwako | Open experimental hypothesis. |
| A generalized-Suwako CNOT network improves quantum resources | Open circuit-construction and evaluation problem. |
| CRC/Rabin is a compelling primary application | Currently unsupported. |

## Source Ledger to Verify

- R. P. Brent and P. Zimmermann, large sparse-polynomial factorization and trinomial-search work. [arXiv:0710.4410](https://arxiv.org/abs/0710.4410).
- Work on reduction and squaring for special irreducible pentanomials. [arXiv:1806.00432](https://arxiv.org/abs/1806.00432).
- Discussion of platform-dependent choices of irreducible polynomials for \(\operatorname{GF}(2^m)\) arithmetic. [Ask Cryptography pointer](https://askcryp.to/t/resource-topic-2007-192-optimal-irreducible-polynomials-for-gf-2-m-arithmetic/2173).
- High-tap irreducible-pentanomial implementation work. [IET record](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/el.2014.0006).
- Quantum finite-field multiplication/division and modulus selection. [arXiv:2511.20618](https://arxiv.org/abs/2511.20618).
- Rabin-fingerprint content-defined chunking and FastCDC. [USENIX 2004 record](https://www.usenix.org/legacy/publications/library/proceedings/usenix04/tech/general/full_papers/policroniades/policroniades_html/index.html), [FastCDC record](https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia).

This is a search ledger rather than a final bibliography. Before using it in a paper, replace each entry with verified primary-source metadata and check that every performance or resource claim is supported by the cited source.
