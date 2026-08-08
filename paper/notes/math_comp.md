# A Mathematics of Computation Core: Sparse Nilpotent Feedback Inversion

This note distills `raw/math_1.md` and `raw/math_2.md` into a candidate mathematical
core for a *Mathematics of Computation* paper.  It deliberately separates
statements that are ready to formalize from attractive extensions whose proof,
algorithmic model, or prior-art boundary still needs work.

## Relationship Between the Two Raw Notes

`raw/math_2.md` subsumes the central characteristic-two story in `raw/math_1.md`, and
strengthens it substantially.  In particular, it supplies the truncated
reciprocal formulation, a geometry-sensitive work bound, a bounded-fan-in
depth lower bound in a generic-coefficient model, commuting block taps, and
radix tradeoffs in positive characteristic.

It does **not** fully include the following material from `raw/math_1.md`:

| Material | Status in this note |
|---|---|
| Reduction over an arbitrary commutative ring, with alternating signs | A valid algebraic extension, but outside the characteristic-two core. |
| The explicit quotient identity \(qY=S(Y)+x^mT(Y)\) and its direct reduction proof | Restated below; it is the cleanest correctness entry point. |
| The criterion for invertibility of \(H\mapsto x^mH\bmod f\), and the reversible shear lift | A separate reversible-linear-map result; not needed for the core reduction theorem. |
| A \(\gcd(d_1,\ldots,d_h)\)-decomposed prefix scan for bounded normalized order | A promising competing algorithm, but its work, depth, and ancilla bounds require a separate proof. |

Thus the answer to “does 2 include 1?” is: **it includes and improves the
characteristic-two sparse-inversion core, but not all of 1's auxiliary
generalisations and circuit claims.**

## Algebraic Setting

Let \(R\) be a commutative algebra of characteristic two and let

$$
f(x)=x^m+q(x)\in R[x]
$$

be monic, with \(\deg q<m\).  Neither irreducibility of \(f\) nor a field
assumption on \(R\) is required.  For an input of degree below \(2m\), write

$$
A(x)=L(x)+x^mH(x),
\qquad \deg L,\deg H<m.
$$

For any polynomial \(Y\) of degree below \(m\), define \(S(Y)\) and \(T(Y)\)
uniquely by

$$
q(x)Y(x)=S(Y)+x^mT(Y),
\qquad \deg S(Y),\deg T(Y)<m.
$$

Then

$$
A-fY=L+S(Y)+x^m\bigl(H+Y+T(Y)\bigr).
$$

Consequently, if \(Y\) solves \(H=(I+T)Y\), then

$$
A\bmod f=L+S(Y).
$$

This proves reduction once \(I+T\) is inverted.  Monicity is the only
condition needed for the quotient and remainder to be well-defined; the
quotient algebra need not be a field.

## Sparse Feedback and the Factored Reciprocal

Write the positive-degree part of \(q\) as

$$
q_+(x)=\sum_{r=1}^{h}a_rx^{e_r},
\qquad 0<e_r<m,
$$

with distinct feedback distances \(d_r=m-e_r\).  The constant coefficient,
when present, contributes to \(S\) but not to the high-part feedback.  Let
\(N\) be the nilpotent right-shift operator on coefficient vectors of length
\(m\).  Then

$$
T=\rho(N),
\qquad
\rho(z)=\sum_{r=1}^{h}a_rz^{d_r}.
$$

If \(h=0\), then \(T=0\) and no feedback stage is necessary.  Otherwise set

$$
\delta=\min_r d_r=m-\max_r e_r,
\qquad
D=\left\lceil\log_2\frac{m}{\delta}\right\rceil.
$$

Since \(N^m=0\), \(T^{2^D}=0\).  Commutativity and characteristic two give
the Frobenius identity

$$
T^{2^k}
=\sum_{r=1}^{h}a_r^{2^k}N^{2^kd_r}.
$$

Therefore

$$
(I+T)^{-1}
=\prod_{k=0}^{D-1}\bigl(I+T^{2^k}\bigr).
$$

Equivalently, this is a factored application of the truncated reciprocal

$$
(1+\rho(z))^{-1}\bmod z^m,
$$

without forming that generally dense polynomial.  Each stage uses only the
original \(h\) taps whose doubled distance remains below \(m\).  Products of
distinct taps occur implicitly through the composition of stages and need not
be materialized.

## Candidate Main Theorem

> **Theorem (sparse Frobenius feedback inversion).**  Let \(R\) be a
> commutative characteristic-two algebra and let \(f=x^m+q\in R[x]\) be
> monic.  For inputs of degree below \(2m\), reduction modulo \(f\) is
> obtained by solving a nilpotent feedback equation \(H=(I+T)Y\), followed by
> the low-part map \(L+S(Y)\).  If the positive-degree part of \(q\) has
> \(h\) nonzero terms at distances \(d_1,\ldots,d_h\), then the inverse of
> \(I+T\) is applicable in
>
> $$
> D=\left\lceil\log_2\frac{m}{\delta}\right\rceil
> $$
>
> sequential feedback stages, where \(\delta=\min_r d_r\).  At stage \(k\),
> the formal scheduled support is contained in
> \(\{r:2^kd_r<m\}\), and its coefficient at tap \(r\) is
> \(a_r^{2^k}\).  The actual nonzero support is
> \(\{r:2^kd_r<m,\ a_r^{2^k}\ne0\}\).  If \(R\) is reduced (in
> particular, if \(R\) is a field), these two supports coincide for the
> initially nonzero coefficients.

The theorem makes no field or irreducibility claim.  It is stronger and more
accurate to say that characteristic two preserves *per-stage* tap sparsity
than to say that it makes a generic reciprocal sparse.

## Work and Depth Statements

In the formal scheduled coefficient-operation model, which retains every
geometrically surviving initial tap whether or not its later Frobenius
coefficient vanishes, applying the feedback factors has exact
position-weighted work

$$
W_{\mathrm{fb}}
=\sum_{r=1}^{h}\sum_{k\geq 0}[m-2^kd_r]_+,
\qquad [u]_+=\max(u,0).
$$

This yields

$$
W_{\mathrm{fb}}
<m\sum_{r=1}^{h}
\left\lceil\log_2\frac{m}{d_r}\right\rceil
=O\!\left(mh\left(1+\log\frac{m}{h}\right)\right),
$$

where the last bound uses distinct integer distances \(d_r\ge r\).  It
includes the dense endpoint \(O(m^2)\), avoiding the artificial extra
\(\log m\) factor caused by the coarser \(O(hm\log(m/\delta))\) bound.
An implementation that eliminates zero Frobenius coefficients can use strictly
less arithmetic work over a non-reduced coefficient algebra.  Over a reduced
characteristic-two algebra, the displayed expression is also the exact
nonzero-tap work.

With bounded-fan-in additions, stage \(k\) has depth
\(O(\log(1+h_k))\), where

$$
h_k=\#\{r:2^kd_r<m\}.
$$

Hence the algebraic circuit depth is

$$
O\!\left(\log\frac{m}{\delta}\cdot\log(1+h)\right).
$$

For constant \(h\), this is \(O(\log(m/\delta))\).  A matching
\(\Omega(\log(m/\delta))\) lower bound can be stated only in an appropriate
generic-coefficient, bounded-fan-in model: choose algebraically independent
coefficients and retain the shortest-distance tap, so that one output depends
on \(\Theta(m/\delta)\) independent inputs.  It is not automatically a lower
bound for every fixed finite-field modulus, where cancellations or specialized
linear circuits may change the dependency structure.

## Extensions Worth Keeping Separate

### Positive Characteristic and Radix

For a nilpotent \(T\) over characteristic \(p\), the algebraic identity

$$
(I+T)^{-1}
=\prod_{k=0}^{D-1}
\left(\sum_{a=0}^{p-1}(-T)^{ap^k}\right)
$$

holds once \(p^D\) reaches the nilpotency index.  A radix \(b=p^\ell\)
version similarly trades fewer sequential stages for denser factors.  For
fixed \(p\) and \(h\), the number of shift terms in a factor is at most

$$
\binom{h+p-1}{p-1}.
$$

This is a sound algebraic extension, but characteristic two is the principal
algorithmic case: each factor is simply \(I+T^{2^k}\), without higher powers
of \(T\) and their cross terms.

For a full reduction statement in odd characteristic, retain the signs in the
quotient identity:

$$
A-fY=L-S(Y)+x^m\bigl(H-Y-T(Y)\bigr).
$$

Thus \(H=(I+T)Y\) gives remainder \(L-S(Y)\); the binary formula
\(L+S(Y)\) is its characteristic-two specialization.

### Commuting Block Taps

The scalar proof extends to

$$
T=\sum_{r=1}^{h}A_rN^{d_r}
$$

on a characteristic-two module when the endomorphisms \(A_r\) commute with
each other and with \(N\).  This includes extension-field coefficients and
commuting block-feedback systems.  It should be presented as a corollary only
after the scalar proof is complete; its implementation cost depends on the
chosen representation of the \(A_r\).

### Prefix-Scan Alternative

The \(\gcd(d_1,\ldots,d_h)\)-based state decomposition from `raw/math_1.md` may
give a linear-work, logarithmic-depth method for bounded normalized feedback
order.  It is a genuinely different algorithmic regime, not a consequence of
the sparse-doubling bound.  Before including it as a theorem, specify the
state-transition representation, parallel composition cost, circuit fanout,
and ancilla model.  Until then, it belongs in an open-problems or future-work
section.

### Reversible Shear

For reversible implementations, the map

$$
(L,H)\longmapsto(L+F(H),H),
\qquad F(H)=x^mH\bmod f,
$$

is always invertible, and in characteristic two is self-inverse.  This does
not require \(F\) itself to be invertible.  The separate statement
\(F\) invertible if and only if \(x\) is a unit in \(R[x]/(f)\) requires its
own ring-level hypotheses; over a field it is equivalent to \(f(0)\ne0\).
This is useful for a reversible-circuit paper but is not required for the
classical reduction theorem.

## Claim Ledger and Paper Boundary

| Statement | Status |
|---|---|
| Monic reduction reduces to nilpotent feedback inversion | Ready to prove formally. |
| Characteristic-two Frobenius factors retain formal per-stage support; the nonzero support is exact over reduced algebras | Ready to prove formally. |
| Scheduled geometry-sensitive work formula and its dense \(O(m^2)\) endpoint | Ready to prove formally after fixing the operation model. |
| Generic bounded-fan-in depth lower bound | Plausible proof target; state only with the generic-coefficient model. |
| Positive-characteristic and commuting-block generalisations | Algebraically plausible; retain as corollaries after full proof checking. |
| Linear-size reversible circuits for all fixed-weight tap geometries | Open; do not claim. |
| Prefix-scan bound for bounded normalized feedback order | Separate proof obligation. |
| “Newton--Hensel” terminology and novelty | Use only after a prior-art comparison; the inverse identity itself is classical. |

The recommended paper focus is therefore narrow but substantial: **a sparse,
factored application of a truncated reciprocal for nilpotent feedback
operators, with work governed by the complete tap geometry rather than only by
tap count or the nearest tap.**  Modular reduction over binary fields is the
main concrete instance, not the assumption on which the algebra depends.
