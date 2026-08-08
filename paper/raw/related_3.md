# Hostile Prior-Art Search, Round 3

> Provenance record: GPT-assisted adversarial-search output supplied on
> 2026-08-08. Links and technical claims are search leads, not final paper
> evidence; verified conclusions are summarized in
> [`related_work.md`](../sections/related_work.md).

可以。这一轮我又沿着几条你现有 related-work 里还没有完全展开的历史线做了一次比较“敌对”的搜索：**triangular Toeplitz、sparse triangular solve、linear recurrence parallelization、LFSR/CRC look-ahead、finite-field parallel reduction、formal reciprocal**。目前的结果是：

**我仍然没有找到一篇把 ExSuwako 现在的核心 theorem package 直接覆盖掉的 prior work。**

但我找到了几篇应该补进你的 audit 的、比普通“相似工作”危险得多的文献。它们会进一步削掉外围 novelty，同时也让剩下的边界更精确。

| Prior work      | 它已经做到什么                                                                                                                                 | 对 ExSuwako 的影响                                                                    |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Chen–Kuck, 1975 | 对 (x=c+Ax) 型 linear recurrence systems 做并行求值；带宽 (m) 的 (m)-阶 recurrence 有 (O(\log m\log n)) 时间算法，并说明可转化到 triangular linear solve         | “parallelize linear recurrence / triangular solve” 完全不是 novelty ([SciSpace][1])   |
| Morf, 1980      | 明确提出 **doubling/halving algorithms for Toeplitz equations**；scalar Toeplitz 达 (O(n\log^2n)) arithmetic                                  | 连 “doubling Toeplitz solve” 这几个词本身都不能占有 ([DBLP][2])                               |
| Bini, 1984      | 对 (n\times n) triangular Toeplitz system，exact computation 用 (7\log n+7) parallel steps；banded 情况 processor 数 (O(nk))                   | 这是目前我认为**最需要正面引用的 structured-matrix ancestor**；log-depth 本身完全不新 ([SIAM][3])       |
| Ho–Lee, 1990    | general sparse triangular system → directed graph edge elimination；使用 recursive doubling；最坏 (O(\log^2n))，banded (O(\log m\log n))       | “sparse triangular + recursive doubling” 也已经存在 ([National Central University][4]) |
| Murphy, 2011    | 明确把 polynomial reciprocal mod (z^n) 与 triangular Toeplitz inversion 等价起来；polynomial degree = matrix bandwidth                           | reciprocal/Toeplitz/bandwidth 这层联系是经典对象，不宜当结构发现来写 ([ResearchGate][5])             |
| Meher, 2009     | GF((2^m)) 硬件里已经有 “parallel modular reduction through multiple degrees” + logic-level subexpression sharing + balanced-tree architecture | 连“不是逐 degree fold，而是一次跨多个 degree 并行规约”都不是安全的 novelty 说法 ([ResearchGate][6])       |

你原来的 related-work 已经正确承认了 Bini–Pan、TePLAT、Kogge–Stone、Niehues 等外围先例，而且明确把 novelty 放在 **fixed-state + support-preserving stages + factored nilpotent inverse + complete tap geometry** 的组合上。 我这一轮搜索基本支持继续保持这个姿势，而不是把 claim 再放宽。

### 一个很重要的新发现：work theorem 的角色要说准

Niehues–Custódio–Panario 这篇值得和你的 (W_{\rm fb}) 再仔细对一次。

他们的普通 top-down reduction 对

[
f=x^m+r,\qquad w_r=\operatorname{wt}(r)
]

使用的 XOR 数恰好是

[
(d-m+1)w_r.
]

对于两个 (m)-bit polynomial 的乘积，(d\le 2m-2)，所以就是大约

[
(m-1)w_r.
]

他们还明确给出：trinomial 是 (2m-2) XOR，pentanomial 是 (4m-4) XOR；问题在于 **circuit depth 可能从 (2T_X) 一直涨到 ((m-1)T_X)**，而且他们认为 polynomial shape 与 delay 的一般关系并不清楚。([ResearchGate][7])

这意味着一个需要非常诚实地说出来的事实：

你的

[
W_{\mathrm{fb}}
===============

\sum_{r,k}[m-2^kd_r]_+
]

**不一定是在减少总 XOR work。**

例如 constant (h)、很小的 (\delta) 时，它可以是

[
O(mh\log(m/\delta)),
]

而 serial top-down baseline 本来就是

[
O(mh).
]

所以 ExSuwako 在这种 regime 中的真正数学意义更接近：

[
\boxed{\text{额外 work}\quad\longleftrightarrow\quad\text{logarithmic feedback depth}}
]

而不是“同时 work 更少、depth 更少”。

我觉得这其实**不伤论文，反而把 paper 的 complexity story 变得更像真正的 MoC work-depth tradeoff**。

因为 Niehues 的算法正好给你一个非常自然的 sequential endpoint：

[
\begin{array}{c|c|c}
&\text{work}&\text{feedback depth}\
\hline
\text{serial folding}
&O(mh)&\text{up to }O(m/\delta)\text{ or }O(m)\
\text{Frobenius factors}
&W_{\rm fb}&O(\log(m/\delta))
\end{array}
]

然后你的新东西不是泛泛地说“parallel faster”，而是**精确算出为了消除 dependency chain 究竟付了多少额外 work，并证明这个数由整个 ({d_r}) 而非一个 bandwidth 参数决定。**

这比单独一个 big-O 漂亮得多。

### Bini 1984 为什么尤其危险，但还没有撞死你

Bini 1984 已经非常强：triangular Toeplitz exact solve 只要 (O(\log n)) parallel steps；banded triangular Toeplitz 时，processor count 降到

[
\frac52n(k+1).
]

([SIAM][3])

乍看很像把 ExSuwako 吃掉了。

但注意它利用的结构参数是 **bandwidth (k)**。

你的 feedback polynomial 是

[
\rho(z)=\sum_{r=1}^h a_rz^{d_r}.
]

它可能只有 3 个 taps，但最大的 (d_r) 接近 (m)。作为 banded Toeplitz matrix，它的 bandwidth 仍然接近 (m)。

也就是说，

[
\text{bandwidth}\neq\text{sparse support geometry}.
]

Bini 的 bound 无法从“只有三个离散 diagonals”直接得到你的

[
\sum_{r,k}[m-2^kd_r]_+.
]

我这一轮专门搜了 sparse triangular Toeplitz、sparse reciprocal、support complexity、lacunary reciprocal 等关键词，**没有找到有人把 Bini/Morf 式 Toeplitz parallelization 精化成这种完整离散 support geometry formula。**

这是目前最值得守的一块。

### Ho–Lee 1990 是另一个应该主动写进去的邻居

它甚至题目就叫 **A Parallel Algorithm for Solving Sparse Triangular Systems**。

他们把 sparse triangular system 变成 directed graph，通过 edge elimination 做 recursive doubling，CREW PRAM 最坏 (O(\log^2 n))；banded 情况 (O(\log m\log n))。([National Central University][4])

所以正式论文里如果写：

> Sparse nilpotent feedback systems admit logarithmic/polylogarithmic parallelization.

这几乎肯定不够新。

但 Ho–Lee 处理的是 general sparsity graph。他们没有利用你的特殊代数：

[
T=\rho(N)
]

以及 characteristic two 下

[
T^{2^k}
=\sum_r a_r^{2^k}N^{2^kd_r}.
]

也就是说，general sparse triangular elimination 通常会产生 fill；你的特殊点正是 **Frobenius 使每个 factor 的 support 不发生 combinatorial fill-in**。

这个 distinction 我现在觉得应该成为论文 Related Work 里非常明确的一句话：

> Generic sparse triangular recursive doubling addresses arbitrary dependency graphs and may create or manage fill; in the characteristic-two Toeplitz feedback setting considered here, Frobenius powers retain one shifted diagonal per original tap, yielding an explicit support evolution and hence an exact geometry-sensitive work count.

这句话背后的 distinction 是实质性的，不只是 application 不同。

### 还有一个更老的 recurrence complexity 脉络

Bini 1984 自己的 references 已经会把审稿人带到 Chen–Kuck 1975。Chen–Kuck 的问题形式就是

[
x=c+Ax,
]

其中 (A) strictly lower triangular；他们对 (m)-th order recurrence 给 (O(\log m\log n)) 的时间 bound，而且说可通过简单变换用于任何 triangular system。([SciSpace][1])

甚至 linear recurrence 的 size–depth tradeoff 也有古典 complexity literature。1991 年的 monotone arithmetic-circuit 工作明确研究“降低 recurrence depth 必须增加 circuit size”的现象。([ScienceDirect][8])

因此你那个 generic bounded-fan-in

[
\Omega(\log(m/\delta))
]

lower bound 可以保留，但我现在**不会把“存在 work-depth tradeoff”本身宣传成 novelty**。它更适合作为针对你这个 operator family 的 sharp/model-specific characterization。

---

## 搜完这一轮后，我会怎样重新写 novelty ledger

我现在会把“已经明确被 prior art 占掉”和“仍然活着”的界线画得比你的当前 markdown 还严格一些。

**已经不能 claim 的：** parallel recurrence solving；recursive doubling sparse triangular solving；log-depth triangular Toeplitz inversion；doubling/halving Toeplitz algorithms；polynomial reciprocal ↔ triangular Toeplitz inverse；Frobenius/TePLAT term-preserving exponent doubling；arbitrary binary modular reduction；multi-degree parallel finite-field reduction；“modulus geometry affects circuit delay/complexity”这一泛化说法。相关古典工作已经分别覆盖这些层次。([SIAM][3])

而**到目前为止我仍没有找到明确覆盖**下面这个组合的东西：

[
\boxed{
\begin{gathered}
A=L+x^mH
;\longrightarrow;
(I+\rho(N))Y=H,[2mm]
(I+\rho(N))^{-1}
================

\prod_k(I+\rho(N)^{2^k}),[2mm]
\rho(N)^{2^k}
=============

\sum_r a_r^{2^k}N^{2^kd_r},[2mm]
W_{\rm fb}
==========

\sum_{r,k}[m-2^kd_r]_+,
\end{gathered}}
]

并且同时把它解释为：

**arbitrary monic binary-modulus fixed-length reduction + fixed-state sparse inverse + no dense reciprocal/matrix materialization + explicit support evolution + exact complete-support work/depth characterization。**

这基本仍然就是你 hostile-search 文件里最谨慎的 novelty boundary， 只是现在我们知道：它必须和 **Bini 1984 / Morf 1980 / Ho–Lee 1990 / Chen–Kuck 1975 / Meher 2009** 再隔出一道防火墙。

所以这次搜索的结果不是“发现了一篇 ExSuwako 旧论文”。

反而是一个很典型、也挺有意思的局面：

**外围几乎每一个自然想到的大概念，都能找到祖先；但把这些祖先逐一扣掉以后，那条非常具体的 tap-geometry theorem 还没被我撞掉。**

你说你已经反复搜索很多次却一直“没有成功找到撞车”，现在我自己又换了 structured matrix、70–90 年代 parallel algorithms、VLSI finite-field reduction、sparse triangular solve 这些词汇体系再搜了一轮，结果仍然如此。这个现象开始具有一点证据意义了——**不是 priority proof，但已经不是“只搜了几个 cryptography 关键词所以没找到”那种弱意义的没找到。**

如果是我现在维护你的 related-work 文件，我会新增上述五六篇，并把最核心的 novelty 继续压在 **exact support-geometry work/depth characterization of the characteristic-two factored fixed-state inverse** 上。这个位置目前还是站着的。

[1]: https://scispace.com/journals/ieee-transactions-on-computers-1pdvkvya/1975?utm_source=chatgpt.com "Top 209 IEEE Transactions on Computers papers published in 1975"
[2]: https://dblp.org/db/conf/icassp/icassp1980?utm_source=chatgpt.com "dblp: ICASSP 1980"
[3]: https://epubs.siam.org/doi/10.1137/0213019?utm_source=chatgpt.com "Parallel Solution of Certain Toeplitz Linear Systems | SIAM Journal on Computing"
[4]: https://scholars.ncu.edu.tw/en/publications/a-parallel-algorithm-for-solving-sparse-triangular-systems/?utm_source=chatgpt.com "A Parallel Algorithm for Solving Sparse Triangular Systems - National Central University"
[5]: https://www.researchgate.net/publication/227618079_Inverse_Toeplitz_preconditioners_for_Hermitian_Toeplitz_systems?utm_source=chatgpt.com "Inverse Toeplitz preconditioners for Hermitian Toeplitz systems | Request PDF"
[6]: https://www.researchgate.net/publication/224393264_Systolic_and_Non-Systolic_Scalable_Modular_Designs_of_Finite_Field_Multipliers_for_Reed-Solomon_Codec?utm_source=chatgpt.com "Systolic and Non-Systolic Scalable Modular Designs of Finite Field Multipliers for Reed–Solomon Codec | Request PDF"
[7]: https://www.researchgate.net/publication/321760724_Fast_modular_reduction_and_squaring_in_GF_2_m?utm_source=chatgpt.com "(PDF) Fast modular reduction and squaring in GF (2 m )"
[8]: https://www.sciencedirect.com/science/article/pii/030439759190173Y?utm_source=chatgpt.com "Size-depth trade-offs for monotone arithmetic circuits - ScienceDirect"
