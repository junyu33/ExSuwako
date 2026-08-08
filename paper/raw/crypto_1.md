# Cryptographic Application Search 1: Koblitz Curves and Poseidon2b

> Status: cleaned GPT-assisted research record.  The mathematical reductions,
> standards claims, implementation bottlenecks, and performance thresholds
> below must be checked against primary sources before entering the paper.

## 1. Leading Candidate: Koblitz-Curve Scalar Multiplication

The most direct candidate is $\tau$-adic scalar multiplication for
Koblitz-ECDH or Koblitz-ECDSA.  A binary Koblitz curve has the form

$$
E_a:y^2+xy=x^3+ax^2+1,
\qquad a\in\{0,1\},
$$

over $\mathbb F_{2^m}$.  The curve coefficients lie in the prime field
$\mathbb F_2$.

### 1.1 Changing the polynomial basis preserves the abstract curve

For two irreducible degree-$m$ polynomials $f_0$ and $f_1$, choose a field
isomorphism

$$
\phi:\mathbb F_2[z]/(f_0)\longrightarrow\mathbb F_2[z]/(f_1).
$$

Because $\phi$ fixes $0$ and $1$, applying $\phi$ coordinate-wise preserves
the equation of $E_a$:

$$
(x,y)\longmapsto (\phi(x),\phi(y)).
$$

Thus one may keep the same abstract curve, group order, discrete-log problem,
and high-level ECDH or ECDSA algorithm while changing only the field
representation.  The base point and external coordinates must be converted
through $\phi$.  This is a representation change, not the selection of a
merely similar curve.  Implementation and side-channel properties still have
to be re-evaluated.

### 1.2 Frobenius makes modular squaring central

Koblitz scalar multiplication uses the Frobenius endomorphism

$$
\tau(x,y)=(x^2,y^2).
$$

After a $\tau$-adic expansion of the scalar, many ordinary point doublings are
replaced by applications of $\tau$.  In a polynomial basis, each application
requires two modular squarings:

$$
x\longmapsto x^2\bmod f,
\qquad
y\longmapsto y^2\bmod f.
$$

This directly combines the two existing application hypotheses: repeated
modular squaring and reducer-aware modulus selection.

The motivating implementation claim is that modular reduction can dominate
polynomial-basis squaring for some Koblitz parameters, especially when the
standard pentanomial is awkward for vector registers.  This claim, including
any K-283 operation breakdown, must be recovered from and quoted against the
original implementation literature.

### 1.3 Degree alignment

The current two-cluster search has candidate irreducible pentanomials at

$$
m\in\{163,233,283,409,571\},
$$

which coincides with the traditional Koblitz-curve degree set.  Examples of
standard polynomial-basis moduli to verify from the standards include

$$
\begin{aligned}
K\text{-}233 &: z^{233}+z^{74}+1,\\
K\text{-}283 &: z^{283}+z^{12}+z^7+z^5+1,\\
K\text{-}409 &: z^{409}+z^{87}+1.
\end{aligned}
$$

The coincidence makes K-283 a natural first experiment: it provides a
standard pentanomial, a same-degree two-cluster candidate, and a substantial
optimized-implementation literature.

## 2. Proposed Koblitz Experiment

### 2.1 Representations and reducers

Use at least the following backends:

1. the standard K-283 polynomial basis with the strongest credible
   fixed-modulus unrolled reducer;
2. a verified irreducible two-cluster degree-283 polynomial with generalized
   Suwako and any credible generated specialization;
3. a normal-basis backend, or the strongest reproducible normal-basis result,
   because Frobenius is a cyclic coordinate rotation there;
4. a hybrid or table-based backend when it is a realistic strongest baseline.

Construct and verify

$$
\phi:\mathbb F_2[z]/(f_{\mathrm{NIST}})
\longrightarrow
\mathbb F_2[z]/(f_{\mathrm{GS}}),
$$

then map the standard base point to

$$
G'=(\phi(G_x),\phi(G_y)).
$$

Conversion and isomorphism setup must be reported separately and included in
any workload where representations change online.

### 2.2 Measurement ladder

Measure increasingly complete operations:

1. field squaring, multiplication, and inversion;
2. one Frobenius application $\tau$;
3. $\tau^k$ for small $k$ using repeated squaring;
4. $\tau^k$ for larger $k$ against table-based multi-squaring;
5. random-point and fixed-point $\tau$-adic scalar multiplication;
6. complete ECDH, ECDSA signing, and ECDSA verification, where the chosen
   implementation exposes matched and reproducible entrypoints.

The same abstract points and scalars must be used across representations, and
the outputs must agree after conversion to a common canonical representation.

### 2.3 Strong baselines

#### Normal basis

In a normal basis, Frobenius is close to a cyclic bit rotation.  The complete
comparison is therefore not squaring against squaring, but

$$
\text{cheap normal-basis squaring + costlier multiplication}
$$

against

$$
\text{polynomial-basis squaring + fast carry-less multiplication}.
$$

Point additions, precomputation, inversion, conversion, and memory behavior
must remain inside the relevant end-to-end boundary.

#### Multi-squaring tables

High-performance Koblitz implementations may precompute fixed $2^k$-power
maps.  The reported claim that table-based multi-squaring becomes preferable
around $k\ge6$ is a literature lead, not yet verified evidence.  Experiments
must distinguish one $\tau$, short $\tau^k$, and long $\tau^k$ rather than
assuming one winner for all three regimes.

## 3. Claim Boundary and Narrative Risk

Binary-field curves, including the Koblitz family, are reported as deprecated
in NIST SP 800-186.  The exact status, date, rationale, and implications must
be checked in the standard.  This limits deployment relevance but does not
invalidate Koblitz scalar multiplication as a clean cryptographic case study.

Provisional assessment:

| Dimension | Assessment |
|---|---:|
| Mathematical fit to ExSuwako | 9.5/10 |
| Experimental executability | 9/10 |
| Purity as a cryptographic workload | 9/10 |
| Current deployment relevance | 4/10 |
| Ability to support EUROCRYPT alone | 5.5/10 |

The strongest possible positive result would be:

> The standard polynomial is best under a conventional reducer, but a
> different isomorphic polynomial representation coupled to generalized
> Suwako gives a faster complete $\tau$-NAF scalar multiplication.

That would support a field-representation/reducer co-design claim for
elliptic-curve cryptography.  A reduction-only win, or a polynomial-basis win
that loses to normal basis end to end, would not support this claim.

## 4. Modern Follow-Up Candidate: Poseidon2b

Poseidonb/Poseidon2b-style permutations for binary-field proof systems are a
more modern candidate.  Their nonlinear map

$$
x\longmapsto x^7=x\,x^2\,x^4
$$

contains repeated squaring and multiplication over fields such as
$\mathbb F_{2^{32}}$, $\mathbb F_{2^{64}}$, or $\mathbb F_{2^{128}}$.

Given a field isomorphism $\phi$, one can define a conjugate permutation

$$
P_{f_1}=\phi\circ P_{f_0}\circ\phi^{-1}
$$

while mapping round constants and linear-layer coefficients.  The unresolved
implementation question is whether an ExSuwako-friendly polynomial basis can
beat the binary tower fields used by the relevant proof systems.  This branch
is more current than Koblitz curves but less directly connected to the present
native implementation.

## 5. Candidate Ranking

| Candidate | Representation freedom | Squaring centrality | Fit to current experiments | EUROCRYPT narrative |
|---|---:|---:|---:|---:|
| Koblitz $\tau$-NAF ECC | Very high | Very high | Very high | Medium; deprecated family |
| Poseidon2b | High, with conjugated constants | High | Medium | Strong and current |
| General binary ECC | High | Medium | High | Older |
| Binius PCS directly | Constrained by tower structure | Unclear bottleneck | Medium | Very current |
| Classic McEliece | Internal representation can vary | Degrees 12--13 are too small | Low | Poor fit |

The immediate recommendation is to start with K-283 as the cleanest merger of
repeated-squaring and modulus-selection experiments, then audit Poseidon2b as
a possible modern cryptographic anchor.

## 6. Verification Ledger

- Verify the standard Koblitz equations, parameters, basis representations,
  and polynomial moduli from primary standards.
- Verify the exact deprecation language in NIST SP 800-186.
- Identify the high-performance Koblitz implementation that reports the
  K-283 reduction bottleneck and recover its exact measurement boundary.
- Identify and reproduce the multi-squaring threshold claim.
- Verify the current Poseidonb/Poseidon2b specifications, target fields,
  nonlinear layer, and tower-field implementation assumptions.
- Treat side-channel behavior and constant-time implementation as independent
  evaluation obligations.
