# Computational Falsification Record: Coefficient Algebras and Support Geometry

Status: reproducible validation record, not a formal proof.

The executable sources are
[`tests/check_theory_round1_gf2.py`](../../tests/check_theory_round1_gf2.py)
and
[`tests/check_theory_round2_algebras.py`](../../tests/check_theory_round2_algebras.py).
Run both with `make check-theory` (or run the complete repository gate with
`make check`).  The tests use deterministic seeds recorded in the sources.

## Round 1: Binary Core

- 20,000 randomized instances over \(\mathbb F_2\), with
  \(1\le m\le128\), seed `20260808`;
- exhaustive enumeration of every monic binary modulus and every input of
  degree below \(2m\), for \(1\le m\le6\): 299,592 modulus/input pairs.

Each instance independently checks the feedback equation
\(H=(I+T)Y\), agreement between feedback reduction and ordinary monic long
division, and equality of scheduled coefficient work with
\(\sum_{r,k}[m-2^kd_r]_+\).

## Round 2: Algebraic Scope and Geometry

- \(\mathbb F_2[\varepsilon]/(\varepsilon^2)\): 20,000 randomized tests
  for \(m\le24\), plus 266,304 exhaustive modulus/input cases for
  \(m\le3\).  In 13,573 randomized instances, at least one initially
  nonzero scheduled coefficient vanished under Frobenius.
- \(\mathbb F_4\): 20,000 randomized tests for \(m\le32\), comparing the
  factorized inverse, an independent finite geometric inverse, and direct
  monic long division.
- Support geometry: exhaustive enumeration of all 262,125 nonempty supports
  for \(2\le m\le18\).  The scheduled work was always strictly below the
  coarse sum bound; at each fixed \((m,h)\), the maximum occurred at
  distances \(\{1,\ldots,h\}\).
- \(\mathbb F_3\): 10,000 randomized tests for \(m\le12\), checking the
  radix-three inverse identity, the alternating finite geometric inverse, and
  direct monic reduction.  The remainder uses \(L-S(Y)\), not the
  characteristic-two expression \(L+S(Y)\).

The dual-number cases locate a theorem-statement boundary: correctness holds
over arbitrary commutative characteristic-two algebras, but a nonzero initial
coefficient need not remain nonzero under Frobenius.  Consequently the
geometry formula is exact scheduled work in general and exact nonzero-tap work
over a reduced characteristic-two algebra, including every field.
