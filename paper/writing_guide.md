# Generalized Suwako Writing Guide

Working outline for a CRYPTO / EUROCRYPT-style paper on generalized Suwako
reduction.

Central thesis:

> Binary modular reduction can support arbitrary moduli while preserving
> sparsity-sensitive work, logarithmic feedback depth, and lightweight setup
> when the non-leading part of the modulus is sparse.

Keep the claims separate throughout the paper:

- correctness is claimed for arbitrary degree-$m$ binary moduli;
- sparsity-sensitive work and favorable crossover regimes target sparse or
  moderately sparse non-leading parts.

This document is a writing plan, not a final paper draft. Keep unsupported
novelty, importance, and performance claims behind TODO markers until the
prior-art and native-implementation evidence exists.

## Candidate Titles

1. Generalized Suwako: Sparse Modular Reduction with Logarithmic Feedback Depth
2. Breaking the Feedback Chain in Sparse Binary Polynomial Reduction
3. Sparse Work without Serial Folding over $\mathbb F_2$
4. Sparse, Shallow, and Precomputation-Light Modular Reduction

Preferred working title:

> Generalized Suwako: Sparse Modular Reduction with Logarithmic Feedback Depth

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

We present generalized Suwako reduction for moduli

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

TODO: Add native implementation results and precise crossover claims.

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

Generalized Suwako removes the linear feedback-depth penalty of unfriendly
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

## 2. Preliminaries and Cost Models

### 2.1 Binary Polynomials

Define:

- coefficient-vector representation;
- truncation modulo $x^m$;
- shift operators;
- word width $W$;
- number of words $n=\left\lceil m/W\right\rceil$;
- treatment of a partial top word.

### 2.2 Sparse Moduli

Let

$$
g=x^m+q=x^m+\bigoplus_{t\in T}x^t,
\qquad
T\subseteq\{0,\ldots,m-1\}.
$$

Define

$$
\Delta_t=m-t,
\qquad
h=\operatorname{wt}(g)=1+|T|.
$$

If $q\ne0$, define

$$
\Delta_{\min}=\min_{t\in T}\Delta_t=m-\deg q.
$$

If $q=0$, do not define $\deg q$ or $\Delta_{\min}$ and set the feedback
depth to $0$.

Assumptions:

- $g$ is monic;
- the constant coefficient may be either zero or one;
- taps are distinct;
- $T\subseteq\{0,\ldots,m-1\}$;
- irreducibility is not required for the reduction theorem.

### 2.3 Shift Operators

Define $S_d(X)=X\gg d$ on the truncated $m$-bit space.

State:

$$
S_aS_b=S_{a+b},
\qquad
S_aS_b=S_bS_a,
\qquad
S_d=0\quad\text{for }d\ge m.
$$

### 2.4 Reduction Problem

Input:

$$
C=L+x^mH,
\qquad
\deg L,\deg H<m.
$$

Output:

$$
R=C\bmod g,
\qquad
\deg R<m.
$$

### 2.5 Complexity Metrics

**Feedback-dependency depth.** Define $D_{\mathrm{fb}}$ as the maximum number
of sequential state-transforming feedback stages on a dependency path.

Clarify:

- all operations inside one stage may execute in parallel;
- this is not bounded-fan-in Boolean circuit depth;
- fanout and XOR-tree depth are separate hardware costs.

**Word work.** Count cross-word shifts, XORs, operand reads/writes when
included, and carry-less multiplications in the baselines.

**Space.** Count temporary words beyond input and output.

**Setup.** Count schedule-generation work, stored shift descriptors,
reciprocal constants, dense reduction matrices, and generated code size.

**Optional gate-depth model.** Introduce only for the hardware evaluation.

### 2.6 Multiplication Complexity

Let $M_W(n)$ denote the machine-word work for multiplying two $n$-word binary
polynomials.

Examples:

$$
M_W(n)=\Theta(n^2)
$$

for schoolbook multiplication, and

$$
M_W(n)=\Theta(n^{\log_2 3})
$$

for Karatsuba.

## 3. Existing Reduction Paradigms

### 3.1 Serial Sparse Folding

Give pseudocode and derive

$$
D_{\mathrm{serial}}
=
\Theta\left(\frac{m}{\Delta_{\min}}\right)
$$

for the difficult family. Also derive total word work in the common model.

### 3.2 Fixed Unrolled Reduction

Separate the abstract reduction algorithm, code generation, XOR-network
synthesis, code size, and fixed-modulus assumptions.

### 3.3 Dense Linear Reduction

Represent reduction by

$$
R_g\in\mathbb F_2^{m\times 2m}.
$$

Discuss low XOR-tree depth, matrix density, storage, preprocessing, and modulus
agility.

### 3.4 Barrett and Montgomery Reduction

Describe their characteristic-two forms at the abstraction level needed for
comparison. Target model:

$$
T_{\mathrm{BM}}(n)=\Theta(M_W(n)).
$$

Do not claim that reciprocal storage is quadratic.

### 3.5 Generic Parallel Polynomial Division

Discuss arbitrary divisors, arithmetic versus Boolean circuit models, depth,
circuit size/work, and whether sparse divisor descriptions remain sparse.

### 3.6 Missing Combination

| Method | Sparse-sensitive work | Short feedback chain | Lightweight setup | Arbitrary modulus | Modulus agility / lightweight setup |
|---|---:|---:|---:|---:|---:|
| Serial sparse folding | yes | no | yes | yes | yes |
| Fixed unrolled reducer | sometimes | yes | no | yes | no, regenerated per modulus |
| Dense matrix | no | yes | no | yes | no |
| Barrett/Montgomery | not generally | multiplication-dependent | moderate | yes | reciprocal-dependent |
| Generic parallel division | not necessarily | yes | not sparse-specific | yes | divisor-dependent |
| Reciprocal/Newton division | not generally | yes | reciprocal-dependent | yes | reciprocal-dependent |
| Generalized Suwako | yes when $q$ is sparse | yes | yes | yes | yes |

TODO: attach primary citations and precise assumptions to every row.

The comparison must distinguish arbitrary-modulus correctness from
sparsity-sensitive efficiency. The method is not limited to arbitrary sparse
moduli; it is correct for arbitrary binary moduli and exploits sparsity when
the non-leading support is sparse.

## 4. Sparse Feedback Operators

### 4.1 Definition of $U$ and $V$

For $X$ in the truncated $m$-bit coefficient space, define

$$
U(X)
=
\bigoplus_{t\in T}
\left(X\gg(m-t)\right)
$$

and

$$
V(X)
=
q(x)X(x)\bmod x^m
=
\bigoplus_{t\in T}
\left((X\ll t)\bmod x^m\right).
$$

When $0\in T$, the corresponding term in $V$ is exactly $X$. No separate
constant-term XOR is present.

### 4.2 One-Step Decomposition

**Lemma 1.** For every $X$ with $\deg X<m$,

$$
q(x)X(x)
=
V(X)+x^mU(X).
$$

The identity holds with no assumption on $q(0)$, irreducibility, or sparsity.

Give a coefficient proof and an operator proof.

### 4.3 Reduction Recurrence

Define

$$
\rho(H)=x^mH\bmod g.
$$

**Lemma 2.**

$$
\rho(H)=V(H)+\rho(UH).
$$

Here $x^m\equiv q(x)\pmod g$ in $\mathbb F_2[x]$. The recurrence uses neither
$q(0)=1$ nor irreducibility; sparsity affects only how cheaply $U$ and $V$ are
applied.

Iterating gives

$$
\rho(H)
=
V(H)+V(UH)+V(U^2H)+\cdots.
$$

### 4.4 Nilpotency

**Lemma 3.** The operator $U$ is nilpotent.

Give a bound using $\Delta_{\min}$.

### 4.5 Reduction Through an Inverse

**Theorem 1.**

$$
\rho(H)=V((I+U)^{-1}H).
$$

Therefore,

$$
\operatorname{red}_g(L+x^mH)
=
L\oplus V((I+U)^{-1}H).
$$

### 4.6 Sparse Frobenius Powers

**Lemma 4.** For every $k\ge0$,

$$
U^{2^k}
=
\bigoplus_{t\in T}S_{2^k\Delta_t}.
$$

Explain that mixed terms such as $S_{\Delta_i+\Delta_j}$ are not absent from
the fully expanded product; they are realized implicitly through factor
composition and never need to be materialized in the schedule.

### 4.7 Sparse Inverse Factorization

**Theorem 2.** If $q\ne0$, let

$$
r=
\left\lceil
\log_2\frac{m}{\Delta_{\min}}
\right\rceil.
$$

Then $U^{2^r}=0$ and

$$
(I+U)^{-1}
=
\prod_{k=0}^{r-1}(I+U^{2^k}).
$$

If $q=0$, then $U=0$, $V=0$, $r=0$, and $C\bmod x^m=L$.

### 4.8 Relation to Truncated Reciprocal Doubling

The identity

$$
(I+U)^{-1}
=
\prod_{k=0}^{r-1}(I+U^{2^k})
$$

is a characteristic-two instance of truncated reciprocal doubling for a
nilpotent perturbation of the identity. We do not claim the inverse identity
itself as new.

The relevant property for binary modular reduction is that the feedback
operator induced by the modulus satisfies

$$
U^{2^k}
=
\bigoplus_{t\in T}S_{2^k(m-t)}.
$$

Thus every factor remains directly applicable from the original tap
description. No dense reciprocal polynomial or reduction matrix needs to be
materialized.

### 4.9 Why Characteristic Two Matters

State:

- commuting operators are required;
- characteristic two cancels cross terms;
- the same sparse factorization does not hold directly in odd characteristic.

## 5. Generalized Suwako Reduction

### 5.1 Algorithm

```text
Input:
    C = L + x^m H
    taps T
    modulus degree m

X <- H

for k = 0, ..., r - 1:
    old <- X

    for t in T:
        d <- 2^k (m - t)

        if d < m:
            X <- X XOR (old >> d)

R <- L XOR V(X)

return R
```

Mandatory implementation condition:

> Every shift in stage $k$ reads the same immutable value `old`.

### 5.2 Correctness

**Theorem 3.** The algorithm returns $C\bmod g$.

The proof should cite the operator theorems rather than repeat all coefficient
manipulations.

### 5.3 Public Schedule

Define

$$
T_k=\{t\in T:2^k\Delta_t<m\}.
$$

The schedule is

$$
\mathcal S(g)
=
\{(k,2^k\Delta_t):t\in T_k\}.
$$

The definition automatically excludes $t=0$, since
$2^k(m-0)\ge m$. The total modulus weight $h=1+|T|$ and the active-tap count
$h_k=|T_k|$ are distinct quantities.

Discuss runtime generation, compile-time generation, storage, and public
control flow.

### 5.4 Trinomial Specialization

For

$$
g=x^m+x^t+1,
\qquad
T=\{0,t\},
\qquad
\Delta=m-t,
$$

the tap $t=0$ contributes $X$ to $V$ and has feedback distance $m$, so it
never enters a feedback stage. The internal tap $t$ contributes the shifted
low assembly term and the feedback distance $\Delta$. Thus the iteration
becomes

$$
X\leftarrow X\oplus(X\gg\Delta),
$$

$$
X\leftarrow X\oplus(X\gg2\Delta),
$$

$$
X\leftarrow X\oplus(X\gg4\Delta),
$$

and so on.

Explain its relation to suffix XOR and parallel prefix. Do not claim that
prefix scan itself is new.

### 5.5 Multi-Tap Example

Give a complete pentanomial example. Show:

- original tap distances;
- doubled distances in each stage;
- taps becoming inactive;
- no pairwise tap-sum expansion.

### 5.6 Constant-Time Properties

For public $(m,T)$:

- stage count is public;
- shifts are public;
- memory positions are public;
- no field-element-dependent branches are needed.

State that native code still requires a standard constant-time audit.

## 6. Complexity Analysis

### 6.1 Feedback Depth

**Theorem 4.** If $q\ne0$,

$$
D_{\mathrm{fb}}
=
\left\lceil
\log_2\frac{m}{\Delta_{\min}}
\right\rceil.
$$

If $q=0$, then $D_{\mathrm{fb}}=0$. For fixed $m$ and $\Delta_{\min}$, state
separately:

$$
D_{\mathrm{fb}}
\text{ is independent of }|T|.
$$

Tap placement affects the stage count only through $\Delta_{\min}$, whereas
the number of active taps controls the work within each stage.

### 6.2 Active-Tap Work

Let $h_k=|T_k|$. The modulus Hamming weight is $h=\operatorname{wt}(g)=1+|T|$;
do not use $h$ for the per-stage active-tap count.

Target exact bound:

$$
W_{\mathrm{Ex}}
\le
c_1nr
+
c_2n\sum_{k=0}^{r-1}h_k
+
c_3n|T|
+
O(r+|T|).
$$

Hence,

$$
W_{\mathrm{Ex}}
=
O\left(
n\left(
r+\sum_kh_k+|T|
\right)
\right).
$$

Coarse bound, using $h=1+|T|$, is:

$$
W_{\mathrm{Ex}}=O(nhr).
$$

### 6.3 Constant-Weight Families

For constant-weight families with $h=\operatorname{wt}(g)=O(1)$,

$$
W_{\mathrm{Ex}}
=
O\left(
n\left(1+\log\frac{m}{\Delta_{\min}}\right)
\right).
$$

Worst tap placement:

$$
\Delta_{\min}=1
\quad\Longrightarrow\quad
W_{\mathrm{Ex}}=O(n\log m).
$$

Friendly tap placement:

$$
\Delta_{\min}=\Theta(m)
\quad\Longrightarrow\quad
W_{\mathrm{Ex}}=O(n).
$$

### 6.4 Random-Support Analysis

This analysis uses a broad ring setting rather than a finite-field-only
setting. Fix $m$ and $s\ge1$, choose $T$ uniformly from the $s$-subsets of
$\{0,\ldots,m-1\}$, and define

$$
g(x)=x^m+\bigoplus_{t\in T}x^t.
$$

The polynomial is monic and binary, but it may be reducible and its constant
coefficient may be zero or one. This is the primary random-support model. It
should not be described as an unconstrained random polynomial, since such a
polynomial is usually dense and does not target the sparse-sensitive regime.

Equivalently, the distances $\Delta_t=m-t$ form a uniformly random
$s$-subset of $\{1,\ldots,m\}$. Let

$$
h_k=\left|\{t\in T:2^k\Delta_t<m\}\right|.
$$

Then

$$
\mathbb E[h_k]
=
\frac{s}{m}
\left|\{\delta\in\{1,\ldots,m\}:2^k\delta<m\}\right|
\le \frac{s}{2^k},
$$

and therefore

$$
\mathbb E\left[\sum_k h_k\right]
<
\sum_{k\ge0}\frac{s}{2^k}
=2s.
$$

Thus the expected schedule size is $O(s)$, even though a worst-case schedule
can have $O(s\log m)$ entries.

For $s\ge1$, let $\Delta_{\min}=\min_{t\in T}\Delta_t$. Since

$$
D_{\mathrm{fb}}
=
\sum_{k\ge0}\mathbf 1\{2^k\Delta_{\min}<m\},
$$

a union bound gives

$$
\Pr[2^k\Delta_{\min}<m]
\le
\min\left(1,\frac{s}{2^k}\right).
$$

Consequently,

$$
\mathbb E[D_{\mathrm{fb}}]
=O(\log(s+1)).
$$

The order-statistic identity

$$
\mathbb E[\Delta_{\min}]=\frac{m+1}{s+1}
$$

provides intuition for this logarithmic depth, but the depth bound should be
derived from the tail probability above rather than by substituting an
expectation into a logarithm.

Combining the active-tap work bound with the random-support estimates gives

$$
\mathbb E[W_{\mathrm{Ex}}]
=
O\bigl(n(s+\log(s+1))\bigr)
=
O(ns)
\qquad(s\ge1).
$$

Compared with a multiplication-based reducer of cost $\Theta(M_W(n))$, the
random-support asymptotic condition is

$$
s=o\left(\frac{M_W(n)}{n}\right).
$$

This gives $s=o(n)$ for schoolbook multiplication,
$s=o(n^{\log_2 3-1})$ for Karatsuba, and $s=o(\log n)$ for quasi-linear
multiplication. These are asymptotic work comparisons; native experiments
must determine the practical crossover.

The random-support model is separate from a uniformly sampled irreducible
model. Irreducibility is not required by the algorithm and is not imposed in
the primary analysis. A later cryptographic-relevance experiment may sample
irreducible polynomials, but its support distribution must not be assumed to
follow the uniform-support formulas above.

### 6.5 Space

With ping-pong buffers,

$$
S_{\mathrm{Ex}}=O(n).
$$

Give an exact number of temporary words.

### 6.6 Setup

The explicit schedule has size

$$
O\left(\sum_kh_k\right).
$$

Alternatively, it can be generated online from the tap list.

Compare with reciprocal constants, dense matrices, and fixed XOR-network
synthesis.

### 6.7 Serial Sparse Comparison

Compare separately:

1. feedback-depth improvement;
2. word work;
3. number of complete operand passes;
4. friendly versus unfriendly taps.

Do not infer an equal-factor improvement in total work merely from the
stage-count improvement.

### 6.8 Barrett/Montgomery Comparison

Let

$$
T_{\mathrm{BM}}(n)=\Theta(M_W(n)).
$$

Generalized Suwako has lower asymptotic reduction work when

$$
hn\left(1+\log(m/\Delta_{\min})\right)
=
o(M_W(n)).
$$

Equivalently,

$$
h
=
o\left(
\frac{M_W(n)}
{n\left(1+\log(m/\Delta_{\min})\right)}
\right).
$$

For schoolbook multiplication, if $M_W(n)=\Theta(n^2)$, it suffices that

$$
h
=
o\left(
\frac{n}{1+\log(m/\Delta_{\min})}
\right).
$$

For Karatsuba multiplication, if $M_W(n)=\Theta(n^{\log_2 3})$, it suffices
that

$$
h
=
o\left(
\frac{n^{\log_2 3-1}}
{1+\log(m/\Delta_{\min})}
\right).
$$

For quasi-linear multiplication, universal asymptotic dominance can disappear.

### 6.9 Complete Field Multiplication

The complete cost is

$$
T_{\mathrm{field}}
=
M_W(n)+T_{\mathrm{red}}.
$$

Generalized Suwako lowers the additional reduction term. It does not
automatically change the asymptotic exponent of complete field multiplication.

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

## 8. Implementations

### 8.1 Reference Implementation

- naive long division;
- Python/Sage generalized Suwako;
- exhaustive small-$m$ validation;
- randomized differential tests;
- dedicated cases for $q=0$, $q=1$, $q=x^t$, constant coefficient zero,
  constant coefficient one, dense $q$, reducible $g$, and non-word-aligned
  $m$.

### 8.2 Portable C

Requirements:

- arbitrary $m$;
- arbitrary public taps;
- non-word-aligned degrees;
- no assumption that the constant coefficient is present;
- explicit ping-pong buffers;
- no undefined shifts;
- constant-time field-element handling.

### 8.3 Fixed-Modulus Code Generation

Generate active tap lists, unrolled stages, final low assembly, and optional
in-place specializations. Iterate uniformly over $t\in T$; do not hard-code an
extra XOR for $X$. The $t=0$ term is an ordinary low-assembly tap. Measure code
size.

### 8.4 SIMD

Potential targets:

- x86 AVX2;
- x86 AVX-512;
- ARM NEON;
- ARM SVE.

Discuss cross-limb shifts, cross-vector shifts, XOR fan-in, memory traffic, and
stage barriers. Distinguish $t=0$, which participates only in final low
assembly, from $t>0$, which may participate in both feedback and low assembly.
After $2^k(m-t)\ge m$, a tap is inactive in later feedback stages.

### 8.5 Baselines

Implement or integrate:

1. serial sparse folding;
2. optimized trinomial/pentanomial folding;
3. Barrett;
4. Montgomery;
5. dense linear reduction;
6. generic polynomial remainder.

### 8.6 Optional RTL Prototype

Compare serial sparse folding, generalized Suwako, and fixed dense XOR network.
Report latency, frequency, area/LUTs, registers, throughput, and pipeline
depth.

## 9. Evaluation

### 9.1 Research Questions

**RQ1: Correctness.** Does generalized Suwako agree with independent reducers
for arbitrary tap sets?

**RQ2: Feedback chain.** Does latency scale with
$1+\log(m/\Delta_{\min})$ rather than $m/\Delta_{\min}$?

**RQ3: Crossover.** For which triples $(m,s,\Delta_{\min})$ does generalized
Suwako outperform serial folding and Barrett/Montgomery?

**RQ4: Modulus agility.** How does
$T_{\mathrm{setup}}+K T_{\mathrm{reduce}}$ behave as the number $K$ of
reductions per modulus changes?

**RQ5: Architecture dependence.** Do the same parameter regions remain useful
on scalar, SIMD, and hardware platforms?

**RQ6: Random-support behavior.** For fixed non-leading support size $s$ and
uniformly random support, do the measured active-tap work and feedback depth
follow the predicted $O(s)$ and $O(\log(s+1))$ expectations?

### 9.2 Parameter Grid

Suggested:

$$
m\in
\{128,256,512,1024,2048,4096,8192\},
$$

$$
s\in
\{0,1,2,4,8,16,32,64,128,\ldots\},
$$

$$
\Delta_{\min}
\in
\{1,2,4,8,16,64,m/4,m/2\}.
$$

Include:

- fixed-weight monic binary polynomials with support sampled uniformly from
  $\{0,\ldots,m-1\}$;
- synthetic controlled families for worst-case and friendly tap placement;
- non-irreducible moduli as the primary ring-level stress tests;
- $0\in T$ and $0\notin T$ cases;
- $T=\varnothing$ and the resulting $q=0$ case;
- constant-free, constant-one, and dense-$q$ cases;
- reducible moduli and non-word-aligned degrees.

Here $s=0$ is the separate $q=0$ boundary case. For each $(m,s)$ with
$s\ge1$, sample enough independent supports to report median, p90,
and p99 rather than only the mean. Do not label this model "random
polynomials" without specifying the fixed weight: unconstrained random
polynomials are typically dense.

### 9.3 Metrics

- cycles per reduction;
- throughput;
- latency;
- dependent stages;
- word shifts;
- XORs;
- carry-less multiplications;
- memory traffic;
- setup time;
- modulus-specific bytes;
- generated code size;
- temporary memory.
- median, p90, and p99 for runtime, $\Delta_{\min}$, $D_{\mathrm{fb}}$, and
  $\sum_k h_k$.

### 9.4 Planned Figures

1. Tradeoff map: work, feedback depth, and setup.
2. Operator diagram: $U,U^2,U^4,\ldots$.
3. Stage count versus $\Delta_{\min}$.
4. Crossover heatmaps over $(h,\Delta_{\min})$.
5. Gap-one scaling as $m$ grows.
6. Setup amortization over $K$.
7. Predicted active-tap work versus measured runtime.
8. Random-support depth and work versus $s$.

### 9.5 Planned Tables

1. comparison of method families;
2. theorem and complexity summary;
3. real sparse moduli;
4. portable C results;
5. SIMD results;
6. setup and storage;
7. optional hardware results.

### 9.6 Negative Results

Report openly:

- high-weight regimes where generalized Suwako loses;
- friendly moduli where serial folding is already sufficient;
- small degrees dominated by loop overhead;
- architectures with expensive cross-limb shifts;
- quasi-linear multiplication regimes where the asymptotic comparison changes.

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

- [ ] Portable C.
- [ ] Baselines.
- [ ] Parameter sweep.
- [ ] Setup amortization.
- [ ] Artifact.

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

### Implementation

- [ ] Portable C.
- [ ] Serial sparse baseline.
- [ ] Barrett baseline.
- [ ] Montgomery baseline.
- [ ] Dense matrix baseline.
- [ ] Code generator.
- [ ] SIMD implementation.
- [ ] Optional RTL.

### Evaluation

- [ ] Select real moduli.
- [ ] Finalize parameter grid.
- [ ] Measure stage scaling.
- [ ] Run fixed-weight uniform-support ring experiments.
- [ ] Produce crossover heatmaps.
- [ ] Measure setup amortization.
- [ ] Document losing regimes.
- [ ] Package the artifact.

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
