结论先说得尖锐一点：

> 这轮 hostile prior-art 搜索没有找到能够整体击杀 ExSuwako 的工作，但找到了一个“核心机制部分击杀”和一个“量子分支基本击杀”。

因此你确实仍然有理由保持信心，不过论文的新颖性不能再放在“发现 Frobenius doubling”上，而必须放在“如何把它组织成固定长度稀疏模规约，并精确刻画 work–depth 几何”上。

## 1. 最危险的先例：TePLAT

Lin、Chen、Hu 在 2013 年提出了 term-preserving look-ahead transformation：

\[
Q(x)=P(x)^2.
\]

在特征 2 下，

\[
P(x)=\sum_i p_i x^i
\quad\Longrightarrow\quad
P(x)^2=\sum_i p_i x^{2i},
\]

所以反馈项数量不变，而反馈距离全部翻倍。论文进一步反复使用 \(P^{2^k}\)，把逐位 LFSR 递推变成并行递推。[Lin–Chen–Hu 2013](https://scholars.lib.ntu.edu.tw/entities/publication/cf88d695-1e7d-4867-88bf-5632d1877206)；其学位论文给出了更完整的代数推导和例子：[Lin 2015 dissertation](https://asset.library.wisc.edu/1711.dl/7NAJQH3D4DJXJ8S/R/file-3a1bf.pdf)。

这和 GS 的局部机制高度同源：

- 利用特征 2 的 Frobenius；
- 支撑不膨胀；
- 位移距离按 \(2^k\) 翻倍；
- 用若干 doubling level 打破长反馈链。

所以以下表述基本不能再作为新颖性：

- “首次观察到 Frobenius 次幂保持 tap 数量”；
- “首次通过平方把反馈距离翻倍”；
- “首次在不增加反馈项数量的情况下并行化稀疏反馈”。

但 TePLAT 尚未整体覆盖我们的对象。它处理的是齐次 LFSR 递推，通过把生成多项式升到更高次数来改变迭代跨度；反复 doubling 还会增加所需的初始状态或存储范围。GS 处理的是有限截断的受迫三角系统：

\[
(I+T)Y=H,
\qquad
Y=(I+T)^{-1}H,
\]

并在固定的 \(m\)-位状态中依次应用

\[
(I+T)^{-1}
=
\prod_{k\ge 0}(I+T^{2^k}).
\]

目前没有搜到 TePLAT 或其引用工作把这套机制直接用于固定长度的稀疏二元多项式规约，也没有搜到它们给出你现在的完整 tap-geometry 工作量公式。

我的判断是：

> TePLAT 吃掉了“局部 doubling 技巧”的优先权，但没有吃掉“有限稀疏模规约的逆算子分解及其精确几何分析”。

这会成为审稿人最可能提出的挑战，必须在 related work 中主动、详细讨论，不能只放一个引用。

## 2. 量子三项式分支：Vandaele 2025 几乎直接覆盖

Vandaele 在三项式

\[
P(x)=x^n+x^k+1
\]

下研究二元域乘法的量子电路。其规约矩阵被分解为 \(n-k\) 条并行 CNOT ladder，每条链对应模 \(n-k\) 的一个剩余类，再利用已有的并行 ladder 构造得到对数深度。[Vandaele 2025](https://arxiv.org/abs/2501.16136)

这基本就是我们三项式分析中的：

- \(\Delta=n-k\)；
- 按模 \(\Delta\) 分链；
- 每条链做前缀 XOR；
- 总 CNOT 数线性；
- 深度为 \(O(\log(n/\Delta))\) 或粗略的 \(O(\log n)\)。

因此，三项式规约的

\[
O(m)\text{ CNOT size},
\qquad
O(\log(m/\Delta))\text{ depth}
\]

上界构造不能再作为独立的主要新颖性。至多还可能保留：

- 更精确的 \(\Delta\)-参数化深度，而不只是 \(O(\log n)\)；
- 明确的零辅助比特 shear 映射
  \[
  (L,H)\mapsto(L+F(H),H);
  \]
- 精确常数；
- 在明确电路模型中的 matching lower bound；
- 多 tap 模数的推广。

但其中每一点都需要和 Vandaele 的完整电路模型逐项核对。就目前结果而言，我不建议再把“三项式量子规约上界”作为论文旗舰结果。

## 3. Prefix scan 也属于标准背景

Kogge–Stone 早在 1973 年就用 recursive doubling 并行求解线性递推，包括高阶递推，在足够处理器下达到对数时间。[Kogge–Stone 1973](https://doi.org/10.1109/TC.1973.5009159)

因此，对归一化反馈阶数 \(g\) 较小的情况，把递推写成固定维状态转移并做 parallel prefix，本身不能宣称为新算法。你可以贡献的是：

- 如何从稀疏模数导出合适的 \(g\)；
- 与 Frobenius sparse doubling 的分界；
- 精确 size/depth；
- reversible/CNOT 资源；
- 哪些 tap geometry 适合 scan，哪些适合 GS。

换句话说，scan 应该被定位为标准工具在本问题上的一个区域，而不是论文的原创核心。

## 4. 传统稀疏规约没有击杀 GS

Niehues、Custódio、Panario 2018 对任意低权重二元模数给出了统一的逐项规约，并分析了 XOR 数和 critical path。其延迟可能从 \(2T_X\) 一直增长到 \((m-1)T_X\)，且最高非首项接近 \(m\) 时反馈链明显恶化。[Niehues–Custódio–Panario 2018](https://www.sciencedirect.com/science/article/abs/pii/S0020019017302168)

更早的 Mastrovito、Wu、Sunar–Koç 和特定五项式规约工作也会根据 tap 位置分析串行 fold 次数。它们已经认识到

\[
\Delta=m-\max e_i
\]

一类距离控制反馈轮数，但我仍然没有找到它们用

\[
T,\ T^2,\ T^4,\ldots
\]

代替逐级 fold，也没有找到精确的

\[
W_{\mathrm{fb}}
=
\sum_k\sum_r [m-2^k d_r]_+
\]

这种完整 tap-geometry 公式。

这部分目前仍然站得住。

## 5. Hostile claim ledger

| 潜在主张 | 搜索结果 | 状态 |
|---|---|---|
| Frobenius 平方保持反馈项数量 | TePLAT 已明确提出 | 已被覆盖 |
| 通过 \(2^k\) 倍反馈距离打破递推链 | TePLAT 已提出 | 已被部分覆盖 |
| 一般线性递推的 recursive doubling / scan | Kogge–Stone 等经典结果 | 已被覆盖 |
| 三项式按 \(\Delta\) 分成 CNOT ladders | Vandaele 2025 几乎直接给出 | 上界分支基本被覆盖 |
| 有限受迫系统的 \((I+T)^{-1}\) Frobenius 因子化 | 恒等式本身经典；作为规约算法尚无直接命中 | 组合贡献 |
| 任意稀疏模数的固定状态 GS 规约 | 未找到直接先例 | 仍可能新 |
| 精确 nilpotence depth \(D\) | 未找到直接先例 | 仍可能新 |
| 完整 tap geometry 的精确工作量 \(W_{\mathrm{fb}}\) | 未找到直接先例 | 目前最强 |
| work–depth phase diagram／适用边界 | 未找到直接先例 | 很有希望 |
| 与串行规约的公平软件实证 | 属于实现贡献 | 需要正式实验支撑 |

## 最终判断

目前最准确的描述是：

> 一个 partial kill，一个 branch kill，但没有 package kill。

如果论文仍然写成：

> 我们发现 \(P(x)^{2^k}\) 保持稀疏性，因此可以 doubling。

那确实很容易被 TePLAT 打成已知技巧。

但如果写成：

> 我们把稀疏二元模规约识别为有限受迫 LFSR 的 nilpotent triangular solve；利用 Frobenius 因子化在固定状态上求逆，并给出由全部 tap 距离决定的精确 work–depth 几何、适用边界和实证结果。

这个包目前没有被搜到直接先例，而且内容明显不只是一个恒等式。

所以，你的信心不是没有依据。只是现在必须把论文的“灵魂”从 doubling observation 提升到：

\[
\boxed{
\text{finite inverse formulation}
+
\text{exact tap geometry}
+
\text{work–depth characterization}
}
\]

量子三项式上界应该降级；TePLAT 应提升为最接近、必须正面区分的第一相关工作。下一轮最值得做的是沿 TePLAT 的引用链继续搜索，并把每条现有 theorem 与 TePLAT、Vandaele 做逐项 claim mapping。