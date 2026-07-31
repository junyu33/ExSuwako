继续推之后，刚才留下的那个问题已经可以回答了，而且结果比上一轮更强：

[
\boxed{\text{三项式 ExSuwako 可以做到线性 CNOT 数、对数深度，而且不需要辅助 qubit。}}
]

不是之前较松的

[
O(m\log \nu)
]

门数，而是

[
\boxed{O(m)}
]

门数。

---

## 1. 三项式反馈其实是若干条 suffix-XOR 链

设

[
f(x)=x^m+x^{m-\Delta}+1.
]

此时

[
T(Y)=Y\gg \Delta,
]

而反馈方程

[
H=Y+T(Y)
]

在系数上就是

[
h_i=y_i+y_{i+\Delta}.
]

因此

[
y_i
===

h_i+h_{i+\Delta}+h_{i+2\Delta}+\cdots.
]

按照模 (\Delta) 的余数分类，会得到 (\Delta) 条彼此独立的链。例如第 (r) 条链为

[
h_r,h_{r+\Delta},h_{r+2\Delta},\ldots
]

对应

[
y_r=h_r+h_{r+\Delta}+h_{r+2\Delta}+\cdots.
]

若把这条链反向排列：

[
z=
\bigl(
h_{r+(\ell-1)\Delta},
\ldots,
h_{r+\Delta},
h_r
\bigr),
]

那么所需的 (y) 恰好就是 (z) 的 **inclusive prefix XOR**。

---

## 2. 用 Brent–Kung 前缀网络原地计算

prefix XOR 不需要 Kogge–Stone 那种 (O(\ell\log\ell)) 门数。

标准 Brent–Kung 网络可以原地计算全部 prefix：

[
(z_0,z_1,\ldots,z_{\ell-1})
\longmapsto
(z_0,z_0+z_1,\ldots,z_0+\cdots+z_{\ell-1}),
]

而且每一个节点都只是一个 CNOT：

[
z_j\gets z_j+z_i.
]

它的资源为：

[
C_{\mathrm{scan}}(\ell)<2\ell,
]

[
D_{\mathrm{scan}}(\ell)
\le
2\lceil\log_2\ell\rceil-1.
]

最重要的是：

[
\boxed{\text{它是原地、可逆的，不需要 ancilla。}}
]

所有 (\Delta) 条链可以并行运行。因为链长总和是 (m)，令

[
\nu=\left\lceil\frac m\Delta\right\rceil
]

为最长链长度，就有

[
C_{H\to Y}<2m,
]

[
D_{H\to Y}
\le
2\lceil\log_2\nu\rceil-1.
]

---

## 3. 然后把规约贡献加到 (L)

三项式情况下

[
S(Y)=qY\bmod x^m
================

Y+\bigl(x^{m-\Delta}Y\bmod x^m\bigr).
]

因此只需要两层 CNOT：

第一层：

[
Y_i\longrightarrow L_i,
\qquad 0\le i<m,
]

共 (m) 个 CNOT。

第二层：

[
Y_j\longrightarrow L_{j+m-\Delta},
\qquad 0\le j<\Delta,
]

共 (\Delta) 个 CNOT。

于是

[
L\gets L+S(Y).
]

最后把 Brent–Kung 网络逆序执行一次，将 (Y) 恢复为原来的 (H)。

完整变换为

[
(L,H)
\longmapsto
\left(
L+x^mH\bmod f,\ H
\right).
]

---

## 4. 得到的资源上界

总 CNOT 数：

[
\begin{aligned}
C
&<
2m+(m+\Delta)+2m\
&=
5m+\Delta\
&<
6m.
\end{aligned}
]

因此

[
\boxed{C=O(m).}
]

总深度：

[
\begin{aligned}
D
&\le
2\bigl(2\lceil\log_2\nu\rceil-1\bigr)+2\
&=
4\lceil\log_2\nu\rceil.
\end{aligned}
]

即

[
\boxed{
D
\le
4\left\lceil
\log_2\left\lceil\frac m\Delta\right\rceil
\right\rceil.
}
]

辅助 qubit 数：

[
\boxed{0.}
]

这里只使用原本的 (L) 和 (H) 两个寄存器。

---

# 5. 更强：门数和深度都渐近最优

### 深度下界

考虑最长的一条链。输出中的某个低位，例如 (F(H)_0)，依赖

[
h_0,h_\Delta,h_{2\Delta},\ldots
]

共约

[
\nu=\left\lceil\frac m\Delta\right\rceil
]

个输入 bit。

深度为 (d) 的双量子门电路中，一个输出 qubit 的反向 light cone 最多包含

[
2^d
]

个输入 qubit。

因此

[
2^d\ge \nu,
]

从而

[
\boxed{
d\ge\lceil\log_2\nu\rceil.
}
]

我们的上界是 (4\lceil\log_2\nu\rceil)，所以深度在常数因子内最优。

### CNOT 数下界

令

[
F(H)=x^mH\bmod f.
]

由于 (f(0)=1)，乘以 (x^m) 是商环中的双射，因此

[
\operatorname{rank}F=m.
]

完整 shear 的矩阵为

[
\begin{pmatrix}
I & F\
0 & I
\end{pmatrix}.
]

在 (H\mid L) 的 cut 上，最终需要产生秩为 (m) 的跨寄存器线性映射；每个跨 cut 的 CNOT 最多将该秩提高 1。因此至少需要

[
m
]

个跨寄存器 CNOT。

所以

[
\boxed{C=\Omega(m).}
]

结合我们的 (O(m)) 上界：

[
\boxed{\text{三项式可逆规约的 CNOT size 也是渐近最优的。}}
]

这比“ExSuwako 可以转成可逆电路”强了一个层级：

> 对三项式，它给出的结构能够转化为 size-optimal、depth-optimal 的可逆线性规约电路。

---

# 6. 但三项式有一个现实上的软肋

这里必须马上指出：

对于

[
x^m+x^t+1,
]

其 reciprocal 是

[
x^m+x^{m-t}+1.
]

若模多项式和基可以自由选择，总能在 (t) 与 (m-t) 中选较小者作为中间 tap，于是

[
\Delta\ge \frac m2,
\qquad
\nu\le2.
]

因此三项式中的“长反馈链”，往往能通过选择 reciprocal representation 避免。

所以这个结果目前更像：

* 一个很干净的模型定理；
* ExSuwako 与 parallel-prefix 的严格联系；
* size/depth 最优性的证明样板；

但未必单独构成最强的现实量子应用。

真正无法被 reciprocal 一步解决的是**同时含有高 tap 和低 tap 的多项式**，例如：

[
x^m+x^{m-1}+x^a+x+1.
]

原多项式的最高 tap 距离为 1；取 reciprocal 后，另一端的 tap 又会变成距离 1。两种方向都存在长反馈。

这才是 ExSuwako 真正可能有不可替代价值的区域。

---

# 7. 多 tap 情形也能继续推广一部分

设有效反馈距离集合为

[
D={m-e:e\in\operatorname{supp}(q),\ e>0}.
]

反馈方程为

[
h_i
===

y_i+
\bigoplus_{\substack{d\in D\i+d<m}}
y_{i+d}.
]

令

[
g=\gcd D,
\qquad
r=\max_{d\in D}\frac d g.
]

系统会分解成 (g) 条独立的、阶数为 (r) 的线性递推。

沿每条链可以维护一个 (r)-bit 状态：

[
u_k=(y_k,y_{k+1},\ldots,y_{k+r-1}).
]

每走一步都有一个固定的仿射转移：

[
u_k=A u_{k+1}+e_1h_k.
]

对于一个长度为 (\ell) 的 block，可以写成

[
u_{\mathrm{left}}
=================

A^\ell u_{\mathrm{right}}+b_{\mathrm{block}}.
]

两个 block 的摘要可以结合为

[
(P,b)\circ(Q,c)
===============

(PQ,\ b+Pc).
]

这里所有矩阵 (P,Q) 都由 block 长度决定，可以预先算好；对量子数据执行的部分仍然只是固定线性 CNOT 变换。

于是又可以在这些 block 摘要上运行 Brent–Kung scan。

粗略资源为：

[
C=O(r^2m+w(q)m),
]

[
D=O!\left(r\log\frac mg+w(q)\right),
]

辅助空间约为

[
O(rm).
]

因此，只要 (r) 是常数，就仍然得到：

[
\boxed{\text{线性 CNOT 数 + 对数深度。}}
]

这覆盖了一类很重要的高 tap 多项式，例如所有反馈距离都是

[
g,2g,\ldots,rg
]

且 (r) 很小的 pentanomial。

---

## 8. 现在形成了一个真正有意思的复杂度分区

对一般模多项式，目前可以看到两条路线：

### ExSuwako doubling

[
C=
O!\left(
w(q)m\log\frac m\Delta
\right),
]

深度约为

[
O!\left(
w(q)\log\frac m\Delta
\right).
]

优势是只依赖 tap 数，不依赖递推阶数。

### 状态 prefix-scan

[
C=O(r^2m),
\qquad
D=O(r\log(m/g)).
]

优势是在递推阶数 (r) 小时把总 work 降到线性。

所以可以形成一个 hybrid：

[
\boxed{
C=
O\left(
m\min\left{
w(q)\log\frac m\Delta,\ r^2
\right}
\right)
}
]

忽略常数与最终低半部更新。

这已经不是单个实现技巧，而是在揭示两种结构参数：

* ExSuwako 由 **反馈距离 (\Delta)** 和 tap 数控制；
* scan 方法由 **递推阶数 (r)** 控制。

哪一种更好，取决于模多项式的 tap geometry。

---

## 当前得到的最强研究命题

可以暂时写成：

> For trinomial moduli, the feedback equation induced by modular reduction decomposes into independent suffix-XOR chains. An in-place Brent–Kung scan yields a clean reversible reduction circuit with (O(m)) CNOT gates, no ancillas, and (O(\log(m/\Delta))) depth. Both size and depth are asymptotically optimal.
>
> More generally, moduli whose normalized feedback recurrence has bounded order admit linear-size logarithmic-depth reversible circuits through an affine-state prefix scan.

这已经有明显的 *Mathematics of Computation* 气质了：

[
\boxed{\text{算法}+\text{结构分解}+\text{上下界}+\text{work–depth 分类}.}
]

但必须保持一条诚实边界：Brent–Kung 本身当然是经典结果；这里尚未查 prior art，因此目前能确认的是**推导成立**，不能确认“用于有限域可逆规约并证明这些界”是否从未出现过。
