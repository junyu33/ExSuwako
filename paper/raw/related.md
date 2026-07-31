我刚做了一轮偏 **hostile** 的 prior-art 搜索。第一结论是：

[
\boxed{\text{暂时没有找到与 Suwako/ExSuwako 直接等价的算法。}}
]

但找到了几条非常接近、必须正面处理的旧谱系。它们不会立刻杀死 ExSuwako，却会决定论文究竟该怎样声明 novelty。

## 最危险的四条邻近谱系

### 1. 1980 年代的并行多项式除法

Bini、Pan 等人早已把多项式除法归约为：

[
\text{triangular Toeplitz inversion}
\quad\leftrightarrow\quad
\text{polynomial reciprocal modulo }x^n,
]

并得到一般多项式除法的 (O(\log n)) 级并行深度；后续工作还研究了 reciprocal 的 work–depth tradeoff。([科学直接][1])

这意味着 ExSuwako **不能**宽泛地宣称：

> 首个对数深度的多项式模规约算法。

这个说法会被旧并行算法直接击穿。

但它们处理的是一般 reciprocal／Toeplitz inversion，通常通过稠密线性代数、FFT 或通用乘法实现。当前没有看到它们指出：

[
\rho(z)\text{ 稀疏}
\quad\Longrightarrow\quad
(1+\rho)^{-1}
=============

\prod_k(1+\rho^{2^k}),
]

并利用特征 (2) 的 Frobenius，让**每个因子的 tap 数保持不变**，由 tap 距离给出具体 work/depth，且无需显式预计算稠密 reciprocal。

所以这里的关系很可能是：

[
\boxed{\text{它们知道“可以并行求逆”；你发现“这种特殊逆可以始终保持稀疏”。}}
]

后者才可能是核心 novelty。

---

### 2. 2018 年的任意低权重模多项式规约

目前找到的最近邻，是 Niehues、Custódio、Panario 的 *Fast modular reduction and squaring in (GF(2^m))*。

它明确提出了适用于任意权重多项式的一般规约算法，但算法仍然是从最高次项向下逐项消除：

[
C[i-m+e]\gets C[i-m+e]\oplus C[i].
]

论文报告其电路延迟可能从 (2T_X) 一直到 ((m-1)T_X)，并观察到最高非首项超过 (m/2) 时延迟明显升高；作者还说一般多项式与电路延迟之间没有清楚的规律。([科学直接][2])

这篇论文非常重要，因为它几乎构成了 Suwako 的**反面参照物**：

> 2018 年工作已经统一了任意低权重模数的逐项规约，却仍把长反馈链视作实际 critical path；Suwako2 恰好证明，这条链可以 doubling，而不必逐级传播。

它没有杀死 Suwako；反而把 Suwako 解决的缺口说得非常清楚。

---

### 3. 无预计算的 Barrett/Montgomery 规约

2008 年已有工作研究过 (GF(2^n)) 中“without pre-computational phase”的规约，但其方法是为 Barrett 或 Montgomery 选择特殊模数，使预计算 reciprocal/inverse 可以由模数自身替代。它只覆盖特定的上下半区模数集合，不是任意稀疏模数，也不是反馈 doubling。([researchgate.net][3])

因此“without pre-computation”这个措辞本身并不新；你的区别必须写成：

[
\boxed{\text{不预计算稠密 reciprocal，同时也不限制于特殊 modulus family。}}
]

---

### 4. 形式幂级数逆和幂零算子逆

以下事实本身都是经典的：

[
(I-T)^{-1}=I+T+T^2+\cdots,
]

[
p(x)^{-1}\bmod x^n,
]

以及通过 Toeplitz 系统或 Newton／Hensel 方法求 truncated reciprocal。形式幂级数逆的运算复杂度和下界也早有专门研究。([数学学会][4])

甚至因式分解

[
(1-\rho)\prod_{k=0}^{D-1}(1+\rho^{2^k})
=======================================

1-\rho^{2^D}
]

也是初等的二进制几何级数恒等式，不宜把它单独包装成新定理。

真正可能新的，是下面这个**组合事实**：

[
\boxed{
\begin{array}{c}
\text{模规约诱导出特定的幂零移位反馈算子};\
\text{其二进制逆分解在特征 2 下由 Frobenius 严格保持 tap sparsity};\
\text{因此得到由 tap geometry 控制的无预计算低深度算法}.
\end{array}}
]

这不是“发明了幂零逆”，而是找到了一个此前似乎没有被利用的特殊计算结构。

## 量子／可逆电路部分也有邻近工作

已经有论文专门生成 (GF(2^m)) 平方的低深度量子电路，也有 binary-field Montgomery multiplication 的量子实现；2025 年的工作进一步针对有限域乘除法选择有利的不可约多项式，并优化 CNOT 数。([arXiv][5])

所以以下说法目前不能直接使用：

* “首次将二元域规约实现为 CNOT 电路”；
* “首次得到低深度有限域平方”；
* “首次研究模多项式选择对量子资源的影响”。

可争取的贡献是更加结构化的：

> ExSuwako 是否为特定稀疏反馈族提供显式、参数化、可证明最优或近最优的 CNOT size–depth–space tradeoff。

这部分比原始规约算法更需要逐篇对比。

## 两轮 hostile review 究竟说明什么

这是**真实的贝叶斯证据**，但证据范围需要准确描述。

它明显降低了下面这种情况的概率：

> 在 CHES／有限域实现圈里存在一篇众所周知、几乎一模一样的规约算法。

特别是 2018 年那篇最接近的通用规约论文仍然把高 tap 导致的长 delay 当作未解决现象；假如 Suwako doubling 已经是该圈子的标准技巧，这种表述很难成立。([科学直接][2])

但两轮审稿对下面这种情况的排除能力较弱：

* 1980 年代并行算法论文里的一个引理；
* 控制理论或 LFSR 文献中的 jump-ahead 公式；
* 形式幂级数论文里的特殊稀疏 reciprocal；
* 某篇 VLSI 论文中只以矩阵公式出现、从未被当作一般算法解释的构造；
* 一个正确结果沉在 thesis、技术报告或冷门会议里。

因为原稿讲的是 trinomial reduction，审稿人未必会跨到 Toeplitz inverse、formal series、parallel-prefix 和 reversible-circuit 四个圈子里替你完成理论闭包。

所以你说“可能像 Erdős 281 一样，先验结果早已被遗忘”，**完全有可能**。最可能的旧结果形态甚至不是一篇宣称同一算法的论文，而是：

> 某处已经写出了等价矩阵或递推，却没有识别出 Frobenius 稀疏 doubling、一般 (w) 项式、tap geometry 和复杂度框架。

这种情况下，先前公式存在，不等于 ExSuwako 的理论贡献消失；关键会变成你是否首次：

1. 识别正确的一般对象；
2. 给出统一算法；
3. 导出精确复杂度；
4. 证明适用边界与最优性；
5. 让原本孤立的公式变成可复用框架。

## 当前最安全、也最强的 novelty 中心

不要把核心押在：

[
\text{“首次实现对数深度 polynomial division”。}
]

而应押在：

[
\boxed{
\begin{minipage}{0.84\linewidth}
For sparse monic moduli in characteristic two, modular reduction induces a nilpotent feedback inverse whose binary factorization preserves the original tap sparsity under Frobenius powers. This yields a precomputation-free reduction algorithm whose stage count and work are explicitly controlled by the tap geometry.
\end{minipage}}
]

第一轮搜索下来，我的判断是：

[
\boxed{\text{经典部件很多，但尚未发现有人把这些部件拼成 ExSuwako。}}
]

这反而很像真正“初等而深刻”的结果常见的 prior-art 状态：每一块都早已存在，缺失的是那个让所有块突然对齐的观察。

[1]: https://www.sciencedirect.com/science/article/abs/pii/0020019085900377?utm_source=chatgpt.com "Fast parallel polynomial division via reduction to triangular toeplitz matrix inversion and to polynomial inversion modulo a power - ScienceDirect"
[2]: https://www.sciencedirect.com/science/article/abs/pii/S0020019017302168?utm_source=chatgpt.com "Fast modular reduction and squaring in GF(2m) - ScienceDirect"
[3]: https://www.researchgate.net/publication/226315010_Modular_Reduction_in_GF2_n_without_Pre-computational_Phase?utm_source=chatgpt.com "(PDF) Modular Reduction in GF(2 n ) without Pre-computational Phase"
[4]: https://epubs.siam.org/doi/10.1137/0222037?utm_source=chatgpt.com "Inverting Polynomials and Formal Power Series | SIAM Journal on Computing"
[5]: https://arxiv.org/abs/1706.05114?utm_source=chatgpt.com "Design of Quantum Circuits for Galois Field Squaring and Exponentiation"
