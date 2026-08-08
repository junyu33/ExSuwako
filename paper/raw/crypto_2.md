# Cryptographic Application Search 2: Quantum Binary-ECDLP Resources

> Status: primary-source-backed experiment design plus an exploratory local
> kernel result.  The complete Shor-resource substitution has not yet been
> implemented, and no attack-level improvement is currently claimed.

## 1. Concrete Target

The most executable version of EUROCRYPT route B is not a generic statement
about quantum finite-field arithmetic.  It is a re-estimation of Shor's
algorithm for binary elliptic-curve discrete logarithms after optimizing the
attacker's field representation and reduction circuit.

Garn and Kan give a recent complete target model: exact binary-curve point
addition including exceptional cases, windowed phase estimation, exact
logical resource counts, and physical extrapolations for baseline and
active-volume surface-code architectures at

$$
n\in\{163,233,283,571\}.
$$

Their arithmetic uses polynomial-basis fields with the standardized
irreducible polynomials.  The paper counts both Clifford and non-Clifford
resources for active volume, rather than reporting only Toffoli count.

Primary source:

- M. Garn and A. Kan, "Quantum Resource Estimates for Computing Binary
  Elliptic Curve Discrete Logarithms," *IEEE Transactions on Quantum
  Engineering*, 2025. [arXiv:2503.02984](https://arxiv.org/abs/2503.02984),
  [DOI](https://doi.org/10.1109/TQE.2025.3586541).

This model is unusually well matched to ExSuwako because its authors identify
the large CNOT population of binary-field multiplication as the reason their
active-volume-to-Toffoli ratio is high.  They report that their selected
CRT-based multiplier uses fewer Toffolis than a close Karatsuba alternative
but roughly two to four times as many CNOTs, and leave more active-volume-
efficient multiplication circuits as an open direction.

## 2. Why Representation Choice Is Legitimate for the Attacker

Let the standardized curve be represented over
$\mathbb F_2[z]/(f_0)$.  For any irreducible degree-$n$ polynomial $f_1$, a
field isomorphism

$$
\phi:\mathbb F_2[z]/(f_0)\longrightarrow\mathbb F_2[z]/(f_1)
$$

maps the curve coefficients, base point, and public point into an isomorphic
curve group.  These values are classical attack inputs and can be transformed
before compiling the quantum circuit.  Thus a quantum attacker is not obliged
to retain the defender's polynomial basis.

The appropriate question is consequently adversarial:

> After optimizing over irreducible polynomial representations and credible
> reversible arithmetic circuits, does an ExSuwako-structured reduction lower
> the best known resource estimate for binary ECDLP?

This is stronger and harder than comparing against the standardized modulus.
The baseline must itself choose the best representation available to the
attacker.

## 3. Published Degree-283 Baseline

For $n=283$, Garn--Kan report the following resource scales:

| Component | CNOTs | Swaps | Toffolis | Active volume |
|---|---:|---:|---:|---:|
| One CRT modular multiplication | 325,206 | 618 | 1,776 | $1.38\times10^6$ |
| FLT inversion | 6,254,129 | 47,997 | 31,968 | $2.65\times10^7$ |
| Complete ECPointAdd | not isolated in the summary table | not isolated | $1.55\times10^5$ | $1.18\times10^8$ |
| Windowed phase estimation | not isolated in the summary table | not isolated | $7.09\times10^6$ | $5.30\times10^9$ |

Their ECPointAdd invokes eight multiplications, four inversions, and two
squarings, in addition to linear and controlled logic.  Their FLT inversion
contains repeated modular multiplications and sequences of consecutive
squarings.  For each consecutive-squaring block they compare repeated
squaring with a synthesized matrix for the combined power and choose the
smaller CNOT count.

The published physical extrapolation at $n=283$ includes approximately
13.7 minutes on the stated baseline architecture with a $1\,\mu$s code cycle,
and 36.7 seconds for the stated active-volume architecture with a
$1\,\mu$s delay.  These numbers are reproduction targets, not values that may
be adjusted independently of the paper's architecture assumptions.

## 4. Required Circuit Baselines

The experiment needs at least four circuit families:

1. the Garn--Kan CRT/PLU construction under its standardized moduli and exact
   active-volume cost model;
2. direct dense high-to-low reduction shear and PLU synthesis;
3. Vandaele's subquadratic-Toffoli multiplication and its specialized
   trinomial/equally-spaced reduction circuits;
4. the two-cluster clean shear, first with an executable sequential scan and
   then with the formally verified parallel-prefix construction.

Vandaele's construction is a mandatory baseline because it already provides
subquadratic Toffoli multiplication and logarithmic-depth reductions for
particular primitive-polynomial families:

- V. Vandaele, "Quantum Binary Field Multiplication with Subquadratic
  Toffoli Gate Count and Low Space-Time Cost," 2025.
  [arXiv:2501.16136](https://arxiv.org/abs/2501.16136).

Comparisons must preserve the reversible interface.  A clean shear

$$
(L,H)\longmapsto(L+F(H),H)
$$

cannot be compared directly with an in-place $n$-qubit squaring matrix without
accounting for the registers used to form and retain the polynomial square.

## 5. Executable Kernel Experiment

The first experiment is implemented by
`bench/scripts/quantum_reduction_resources.py`.  It:

- constructs the exact high-to-low reduction matrix for each modulus;
- counts the direct dense shear and its optimal all-to-all bipartite depth;
- emits the explicit zero-ancilla two-cluster shear using sequential in-place
  suffix scans;
- schedules the emitted CNOT list under one two-qubit gate per qubit per
  layer; and
- verifies the circuit on every high-register basis vector against independent
  polynomial long division.

Run:

```text
make check-quantum-resources
python3 bench/scripts/quantum_reduction_resources.py --preset 283
```

The initial degree-283 output is:

| Modulus/backend | CNOTs | CNOT depth | Ancilla |
|---|---:|---:|---:|
| NIST pentanomial, direct dense shear | 1,166 | 8 | 0 |
| Two-cluster pentanomial, direct dense shear | 39,342 | 249 | 0 |
| Two-cluster pentanomial, structured sequential scan | 1,741 | 702 | 0 |

This establishes a large structural improvement for the hostile two-cluster
modulus, but it is a negative signal for attacker-optimal representation
selection: the standard low-tap pentanomial remains smaller and dramatically
shallower in this first reduction-only comparison.  The sequential depth is
not the candidate logarithmic-depth bound, but even an improved depth does not
remove the current CNOT-count disadvantage of 1,741 versus 1,166.

## 6. Full Experiment Ladder

### Stage B0: Reproduce the published baseline

Reproduce Garn--Kan's arithmetic tables, ECPointAdd totals, window-size
optimization, active volume, code distance, and physical-runtime projections
from one fixed paper version.  No ExSuwako substitution is meaningful until
these values agree.

### Stage B1: Attacker-optimal reduction circuits

For each target degree, enumerate or sample irreducible trinomials,
pentanomials, two-cluster polynomials, and literature-selected moduli.  For
every modulus, synthesize the strongest applicable direct, PLU, Vandaele, and
structured scan circuits.  Optimize CNOT count, CNOT depth, swaps, ancilla,
and active volume separately; there is no representation-independent winner.

### Stage B2: Complete field arithmetic

Embed the reduction circuit into matched reversible squaring and
multiplication interfaces.  Recompute consecutive $2^k$-power maps and FLT
inversion addition chains.  Report Toffoli/CCZ resources even if ExSuwako does
not change them, because CNOT savings alone may not alter fault-tolerant cost.

### Stage B3: Point addition and Shor phase estimation

Substitute the new arithmetic resources into the exact ECPointAdd circuit.
Re-optimize the phase-estimation window size rather than holding the published
choice fixed.  Then recompute logical qubits, CNOTs, swaps, Toffolis, active
volume, code distance, hardware footprint, and runtime under both published
architectures.

### Stage B4: Connectivity and sensitivity

Evaluate all-to-all logical CNOT depth and a routed nearest-neighbor model.
Sweep the relative costs assigned to Clifford operations, swaps, magic-state
production, delay length, and workspace.  A result that appears only under one
unstated CNOT pricing assumption is not an attack-resource conclusion.

## 7. Kill and Success Criteria

Route B fails as a central EUROCRYPT result if any of the following holds:

- the attacker-optimal standard/low-tap representation dominates every
  ExSuwako-oriented modulus;
- CNOT savings disappear after complete multiplication or inversion;
- Toffoli production remains the sole bottleneck, leaving physical runtime
  unchanged within modelling uncertainty;
- routing destroys the candidate depth advantage; or
- the final ECDLP active-volume or runtime change is negligible.

Route B becomes credible only if the optimized representation/circuit changes
at least one complete attack resource materially: active volume, logical
depth, logical qubits, physical footprint, or projected runtime.  The result
must be reported against the globally best baseline found in Stage B1, not
only against a dense implementation of the same hostile modulus.

## 8. Current Verdict

The experiment is executable and tied to a current, complete quantum
cryptanalysis model.  It is also substantially less promising at the kernel
level than route A+C: the first exact reduction comparison favors the standard
modulus.  Its immediate value is therefore as a sharp falsification path.  A
positive full-attack result would be very strong, while a negative result
would cleanly bound the cryptographic relevance of the two-cluster CNOT
theorem.
