# Parallel Prefix Circuit for Two-Cluster Reduction

This note fixes the circuit definition behind the logarithmic-depth claim in
[the two-cluster derivation](../raw/cnot_4.md).  It describes the construction
implemented and checked by
[`quantum_reduction_resources.py`](../../bench/scripts/quantum_reduction_resources.py).

## Circuit model

The circuit uses all-to-all CNOT gates.  Within one layer, every qubit occurs
in at most one gate.  The interface is the clean shear

$$
(L,H)\longmapsto(L+F(H),H),
$$

where $L$ and $H$ each contain $m$ qubits.  No qubits beyond these two
registers are used, so the ancilla count is zero.

## In-place suffix scan

Consider one chain of length $\ell$ in reverse coefficient order,

$$
z=(z_0,\ldots,z_{\ell-1}).
$$

The desired map is the inclusive prefix XOR

$$
z_j\longmapsto z_0+\cdots+z_j.
$$

For $\ell=1$ the scan is the identity.  For $\ell\geq2$, let
$q=\lceil\log_2\ell\rceil$.  The in-place Brent--Kung network consists of the
following layers.

**Upsweep.** For $d=0,\ldots,q-1$, apply in parallel

$$
\operatorname{CNOT}(z_{j-2^d},z_j),
\qquad
j=2^{d+1}-1\pmod {2^{d+1}},
\quad j<\ell.
$$

**Downsweep.** For $d=q-2,\ldots,0$, apply in parallel

$$
\operatorname{CNOT}(z_{j-2^d},z_j),
\qquad
j=3\cdot2^d-1\pmod {2^{d+1}},
\quad j<\ell.
$$

In every listed layer, the pairs
$(j-2^d,j)$ are disjoint.  Hence the schedule obeys the layer-conflict rule.

### Correctness

After upsweep level $d$, every endpoint
$j=2^{d+1}-1\pmod {2^{d+1}}$ stores the XOR of the complete length-$2^{d+1}$
block ending at $j$.  This follows by induction: the CNOT combines the two
adjacent length-$2^d$ block totals stored at $j-2^d$ and $j$.

The downsweep visits levels in decreasing order.  At level $d$, the wire
$z_{j-2^d}$ already contains the prefix ending immediately before the
length-$2^d$ right block represented at $z_j$.  Their CNOT therefore turns
$z_j$ into the prefix ending at $j$.  Descending induction fills exactly the
endpoints omitted by the upsweep.  At termination every wire contains its
inclusive prefix XOR.

Reversing a coefficient chain before this network makes the resulting prefix
XOR equal to the required suffix XOR.  For stride $\delta$, the coefficient
indices split into $\delta$ disjoint residue-class chains, whose same-numbered
layers can run concurrently.

### Resources

The network uses no ancillae.  At upsweep level $d$ it has

$$
\left\lfloor\frac{\ell}{2^{d+1}}\right\rfloor
$$

CNOTs.  At downsweep level $d$ it has

$$
\left\lfloor\frac{\ell-2^d}{2^{d+1}}\right\rfloor
$$

CNOTs.  Consequently

$$
C_{\mathrm{scan}}(\ell)<2\ell,
\qquad
D_{\mathrm{scan}}(\ell)
\leq 2\lceil\log_2\ell\rceil-1.
$$

## Two-cluster clean shear

For

$$
f=x^m+x^{m-\delta}+1+\sum_{e\in B}x^e,
\qquad e\leq m/2,
$$

the implementation uses the factorization from the raw derivation:

1. apply one parallel suffix scan on all $m$ high-register wires, split into
   residue classes modulo $\delta$;
2. for every remote tap $e$, scan its disjoint length-$e$ source block, copy
   the parities to its length-$e$ target block in one CNOT layer, and unscan;
3. accumulate the sparse low-part map $V$ into $L$ in $2+|B|$ layers;
4. reverse all transformation layers to restore $H$.

Let $C(a)$ and $D(a)$ denote the total CNOT count and maximum layer count of
the parallel scans on a length-$a$ interval split by stride $\delta$.  The
explicit schedule has

$$
\begin{aligned}
C_{\mathrm{full}}
&=2C(m)+4\sum_{e\in B}C(e)+2\sum_{e\in B}e\\
&\quad{}+m+\delta+\sum_{e\in B}(m-e),\\
D_{\mathrm{full}}
&=2D(m)+4\sum_{e\in B}D(e)+3|B|+2.
\end{aligned}
$$

Here $C(a)<2a$ and

$$
D(a)\leq
2\left\lceil\log_2\left\lceil\frac a\delta\right\rceil\right\rceil-1
$$

when the longest chain has at least two wires, while $D(a)=0$ otherwise.
For a fixed number of taps, the emitted circuit therefore satisfies

$$
C=O(m),
\qquad
D=O\!\left(\log\frac m\delta\right),
\qquad
A=0.
$$

The implementation reports the number of emitted CNOTs and explicit
conflict-free layers, rather than inferring depth by dividing the gate count.
It independently basis-checks every suffix scan and then checks all $m$ basis
vectors of the complete clean shear against polynomial long division.  Since
both maps are linear, agreement on this basis proves equality for all inputs
for each tested modulus.

This is a construction-and-correctness result under the stated all-to-all
CNOT model.  It does not establish superiority to the best circuit for a
different field representation or to connectivity-aware synthesis.
