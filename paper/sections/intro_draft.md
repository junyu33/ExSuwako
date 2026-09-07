# Draft: Title, Abstract, and Introduction

## Candidate Titles

1. Sparse Modular Reduction with Logarithmic Feedback Depth
2. Breaking the Feedback Chain in Sparse Binary Polynomial Reduction
3. Sparse Work without Serial Folding over $\mathbb F_2$
4. Sparse, Shallow Modular Reduction without a Materialized Reciprocal

Preferred working title:

> Sparse Modular Reduction with Logarithmic Feedback Depth

Use "feedback depth" instead of unqualified "circuit depth".

## Paper Shape

The structure should combine two styles:

- **Limitation-first introduction:** explain why existing sparse reduction is
  useful, isolate the sequential feedback-chain loss, then present
  contribution, high-level idea, impact, and technical overview.
- **Definition-first technical body:** fix the cost model, prove structural
  lemmas, then translate the structure into complexity and parameter claims.

Write Sections 2, 4, 5, and 6 before the Introduction. The Introduction should
describe only results already established in the technical sections.

## Abstract Draft

Binary polynomial modular reduction is a basic component of arithmetic over
characteristic-two fields. When the modulus is sparse, reduction can be
implemented with shifts and XORs, with work sensitive to the Hamming weight of
the modulus. Conventional sparse folding, however, can have a sequential
feedback chain of length

$$
\Theta(m/\Delta_{\min}),
$$

where $\Delta_{\min}$ is the minimum distance between the leading term and an
internal tap.

Generic parallel polynomial division and fixed-modulus linear networks avoid
this dependency chain, while Barrett- and Montgomery-style methods support
arbitrary moduli. These approaches, however, do not simultaneously preserve
sparse work, logarithmic feedback depth, and lightweight modulus setup.

We present Frobenius-factorized reduction (FFR) for moduli

$$
g(x)=x^m+q(x)
    =x^m+\bigoplus_{t\in T}x^t,
\qquad
T\subseteq\{0,\ldots,m-1\}.
$$

The set $T$ may be empty; no condition is imposed on the constant
coefficient, and irreducibility is not required. Sparsity affects the work but
not correctness.

The construction expresses reduction through the sparse feedback operator

$$
U=\bigoplus_{t\in T}S_{m-t}.
$$

Because the shift operators commute and the coefficient field has
characteristic two,

$$
U^{2^k}
=
\bigoplus_{t\in T}S_{2^k(m-t)}.
$$

Consequently, $(I+U)^{-1}$ admits a product factorization whose individual
factors remain sparse and contain only doubled original tap distances. Mixed
tap combinations are realized implicitly through factor composition and never
need to be materialized. The key algorithmic consequence is that every factor
remains expressible using only shifts at doubled original tap distances.
Those distances may be retained in a compact reusable plan or regenerated
online from the canonical taps. The latter uses no persistent
modulus-specific shift schedule, but still uses an $m$-bit state and
tap-sized descriptor workspace.

The resulting algorithm is correct for arbitrary binary moduli. When $q\ne0$,
it uses

$$
r=
\left\lceil
\log_2\frac{m}{\Delta_{\min}}
\right\rceil
$$

dependent feedback stages. When $q=0$, it uses $r=0$ stages. For fixed $m$ and
$\Delta_{\min}$, the stage count is independent of the number of taps; tap
placement affects the stage count only through $\Delta_{\min}$, whereas active
tap counts control work within each stage. Its word-level
work is

$$
O\left(
n\left(
r+\sum_{k=0}^{r-1}h_k+|T|
\right)
\right),
$$

where $n=\lceil m/W\rceil$ and $h_k$ is the number of active taps in stage
$k$. For constant-weight modulus families this becomes

$$
O\left(n\left(1+\log(m/\Delta_{\min})\right)\right).
$$

The completed native evaluation should be summarized only at its measured
evidence level: the planned FFR phase diagram contains both winning and losing
regions, while a separate 45-point planned/online experiment gives median
steady-state online/planned ratios 1.676, 1.086, 1.006, and 1.002 at
$m=128,2048,32768,131072$. The derived $K=1$ quantity favors online FFR at
all measured points, but is not a directly timed one-shot interval.

## 1. Introduction

### 1.1 Binary Polynomial Modular Reduction

Let

$$
A(x),B(x)\in\mathbb F_2[x],
\qquad
\deg A,\deg B<m.
$$

Field or quotient-ring multiplication computes

$$
C(x)=A(x)B(x)
$$

followed by

$$
R(x)=C(x)\bmod g(x).
$$

Explain:

- reduction is a distinct arithmetic primitive;
- its implementation depends strongly on the modulus;
- fixed-modulus and changing-modulus settings have different tradeoffs;
- reduction can account for a significant part of field multiplication;
- characteristic-two reduction admits shift/XOR implementations.

Do not open with AES, HQC, Binius, CNOT, or another narrow application.

### 1.2 Sparse Reduction

The construction below is correct for arbitrary binary moduli. We first
motivate it in the sparse setting, where its computational tradeoffs are most
favorable.

Consider

$$
g(x)=x^m+q(x)
    =x^m+\bigoplus_{t\in T}x^t,
\qquad
T\subseteq\{0,\ldots,m-1\}.
$$

From

$$
x^m
\equiv
q(x)
\pmod g,
$$

high coefficients can be folded using shifts and XORs.

Advantages:

- no carry-less multiplication in the reduction step;
- work responds to the sparse representation;
- little modulus-specific state;
- public-parameter control flow can be simple;
- straightforward software and hardware realization.

### 1.3 Limitation of Conventional Sparse Reduction

The central limitation is not Hamming weight alone.

For $q\ne0$ and each $t\in T$, define

$$
\Delta_t=m-t,
\qquad
\Delta_{\min}=\min_{t\in T}\Delta_t=m-\deg q.
$$

The tap $t=0$, when present, has $\Delta_t=m$: it contributes to low-part
assembly but never becomes an active feedback tap. The case $q=0$ is handled
separately with zero feedback depth.

When a tap lies close to the leading term, each fold lowers the relevant degree
by only approximately $\Delta_{\min}$. Conventional folding may therefore
require

$$
\Theta\left(\frac{m}{\Delta_{\min}}\right)
$$

dependent feedback steps.

Central sentence:

> Low Hamming weight does not by itself imply a short dependency chain.

Consequences:

- limited instruction-level parallelism;
- poor latency for hardware;
- repeated full-operand passes;
- difficult SIMD scheduling;
- strong sensitivity to tap placement;
- pressure to select reduction-friendly moduli.

### 1.4 Existing Workarounds

**Friendly modulus selection:** choose taps with sufficiently large gaps. This
preserves sparse shift/XOR reduction but restricts parameter choice.

**Hand-unrolled fixed-modulus reduction:** generate a specialized XOR network
for one modulus. This can perform well but has code-size, synthesis, and
modulus-agility costs.

**Dense reduction matrices:** represent the fixed reduction map as a linear map
over $\mathbb F_2$. This can have low XOR depth but may lose sparse structure
and requires preprocessing/storage.

**Generic parallel polynomial division:** supports arbitrary divisors and
low-depth algorithms, but the work need not remain sensitive to the sparse tap
set.

**Barrett- and Montgomery-style reduction:** mature and general, but the
reduction work is typically of order $M_W(n)$ and uses modulus-dependent
constants.

### 1.5 Main Question

> Can sparse binary modular reduction retain sparsity-sensitive work, reduce
> the sequential feedback chain to logarithmic length, and avoid dense
> modulus-specific preprocessing?

### 1.6 Our Contribution

**Sparse operator formulation.** Write the input as

$$
C=L+x^mH,
\qquad
\deg L,\deg H<m.
$$

Define

$$
U(X)
=
\bigoplus_{t\in T}(X\gg(m-t))
$$

and

$$
V(X)
=
\bigoplus_{t\in T}
\left((X\ll t)\bmod x^m\right).
$$

We prove

$$
\operatorname{red}_g(C)
=
L\oplus V((I+U)^{-1}H).
$$

**Sparse Frobenius factorization.** For every $k\geq0$,

$$
U^{2^k}(X)
=
\bigoplus_{t\in T}
(X\gg 2^k(m-t)).
$$

Thus repeated squaring doubles the original shift distances. Mixed tap
combinations are realized implicitly by factor composition and never need to
be materialized.

Moreover,

$$
(I+U)^{-1}
=
\prod_{k=0}^{r-1}(I+U^{2^k}),
$$

where

$$
r=
\left\lceil
\log_2\frac{m}{\Delta_{\min}}
\right\rceil.
$$

For $q=0$, use $r=0$ and omit $\Delta_{\min}$.

**Complexity guarantees.** Establish:

1. correctness for arbitrary binary moduli;
2. logarithmic feedback-dependency depth;
3. stage count determined by $\Delta_{\min}$, not directly by Hamming weight;
4. work sensitive to the active tap set;
5. linear working space;
6. sparse schedule generation without materializing a dense reciprocal
   polynomial or reduction matrix;
7. lower asymptotic reduction work than multiplication-based methods in
   specified sparse regimes.

**Relation to reciprocal doubling.** The inverse identity is classical
truncated reciprocal doubling in characteristic two. The contribution claimed
here is its sparsity-preserving realization: each factor remains directly
executable from the original modulus support.

**Implementations and evaluation.** Provide:

- reference implementation;
- portable word-oriented C;
- fixed-modulus generated code;
- SIMD implementations;
- serial sparse, dense-matrix, Barrett, and Montgomery baselines;
- parameter-space and setup-amortization experiments.

### 1.7 High-Level Idea

Consider two feedback shifts:

$$
U=S_a+S_b.
$$

Naively,

$$
U^2
=
S_a^2+S_aS_b+S_bS_a+S_b^2.
$$

The shifts commute, so $S_aS_b=S_bS_a$. Over characteristic two,

$$
S_aS_b+S_bS_a=0.
$$

Hence

$$
U^2=S_{2a}+S_{2b}.
$$

More generally,

$$
U^{2^k}
=
\bigoplus_{t\in T}S_{2^k\Delta_t}.
$$

The Frobenius identity itself is standard. Its consequence here is that
repeated inverse-doubling stages do not require the explicit construction of
mixed tap combinations. The geometric inverse can therefore be factorized as

$$
(I+U)^{-1}
=
(I+U)(I+U^2)(I+U^4)\cdots,
$$

truncated once every shift distance is at least $m$. The telescoping identity
is

$$
(I+U)
\prod_{k=0}^{r-1}(I+U^{2^k})
=
I+U^{2^r}
=
I.
$$

### 1.8 Impact

FFR removes the linear feedback-depth penalty of unfriendly
sparse moduli without replacing sparse reduction by a dense linear map or a
multiplication-based reducer. Correctness is arbitrary in the modulus, while
the work advantage is sparsity-sensitive.

It separates two effects of the modulus:

$$
\Delta_{\min}
\quad\text{controls the number of feedback stages,}
$$

while

$$
h_k
\quad\text{determines the work in stage }k.
$$

The total modulus Hamming weight is

$$
h=\operatorname{wt}(g)=1+|T|,
$$

and gives only a coarse work parameter; the accurate schedule cost uses
$\sum_k h_k$.

The result changes the traditional parameter-selection tradeoff: efficient
sparse reduction no longer inherently requires friendly tap placement.

### 1.9 Technical Overview

1. Split the input as $C=L+x^mH$.
2. Let $q(x)=\bigoplus_{t\in T}x^t$.
3. Prove $qX=V(X)+x^mU(X)$.
4. Define $\rho(H)=x^mH\bmod g$ and derive $\rho(H)=V(H)+\rho(UH)$.
5. Iterate the recurrence:

   $$
   \rho(H)
   =
   V(H)+V(UH)+V(U^2H)+\cdots.
   $$

6. Use nilpotency to obtain $\rho(H)=V((I+U)^{-1}H)$.
7. Apply the characteristic-two factorization.
8. Translate the factors into immutable-state feedback stages.
9. Derive exact work, depth, space, and setup bounds.
10. Compare with serial folding and multiplication-based reduction.
