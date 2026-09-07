# Technical Body Draft

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
| Frobenius-factorized reduction (FFR) | yes when $q$ is sparse | yes | yes | yes | yes |

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

For the coefficient-algebra extension, the corresponding stage has formal
support \(\{r:2^kd_r<m\}\), with coefficient \(a_r^{2^k}\).  Its actual
nonzero support additionally requires \(a_r^{2^k}\ne0\).  These agree over a
reduced characteristic-two algebra, including every field; over a general
commutative characteristic-two algebra the geometric schedule remains valid,
but its scheduled work can exceed the work after zero coefficients are
eliminated.

### 4.9 Why Characteristic Two Matters

State:

- commuting operators are required;
- characteristic two cancels cross terms;
- the same sparse factorization does not hold directly in odd characteristic.

## 5. Frobenius-Factorized Reduction

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

**Theorem 4.** If $U\ne0$,

$$
D_{\mathrm{fb}}
=
\left\lceil
\log_2\frac{m}{\Delta_{\min}}
\right\rceil.
$$

If $U=0$ (equivalently, $T\subseteq\{0\}$), then $D_{\mathrm{fb}}=0$.
For fixed $m$ and $\Delta_{\min}$, state separately:

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

The low-to-high right-shift update permits one in-place state.  Excluding
caller-owned input and output, the scalar implementation uses exactly
\(n+1\) plan-owned scratch-array words: \(n=\lceil m/W\rceil\) state words
and one zero sentinel.  The proof is now drafted in the manuscript.

### 6.6 Setup

The explicit feedback schedule has exactly

$$
S_{\rm fb}=\sum_kh_k
=\sum_{t\in T}\left\lceil\log_2\frac m{\Delta_t}\right\rceil
$$

shift records, plus \(r\) stage records and \(|T|\) assembly records.  A
two-pass bucket construction takes \(O(|T|+r+S_{\rm fb})\) word-RAM
operations.  These statements describe reusable schedule setup; the
benchmark continues to time its concrete plan builder separately.

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

FFR has lower asymptotic reduction work when

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

FFR lowers the additional reduction term. It does not
automatically change the asymptotic exponent of complete field multiplication.
