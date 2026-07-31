# 任意权重的二簇模多项式：线性 CNOT、对数深度与零辅助位

这份笔记继续推广 `cnot_3.md` 中的三项式 suffix-scan 构造。核心结论不是“所有固定权重模多项式都已经解决”，而是存在一个任意权重、包含不可约实例、且对 reciprocal 也可能保持困难的自然多项式族。在标准 all-to-all CNOT 模型中，该族具有线性 size、对数 depth 和零 ancilla 的显式可逆规约电路。

## 1. 二簇多项式族

考虑

$$
f(x)
=x^m+x^{m-\delta}+1+\sum_{e\in B}x^e,
$$

其中

$$
1\leq \delta<\frac m2,
\qquad
B\subseteq\left\{1,\ldots,\left\lfloor\frac m2\right\rfloor\right\}.
$$

其总权重为

$$
w=3+|B|.
$$

这里的 tap 分成两簇：

- 一个靠近最高项的 tap $m-\delta$；
- 任意多个位于低半区的 tap $e\in B$；
- 常数项 $1$ 保证低部乘法算子可逆，并用于 size 下界。

在截断空间 $\mathbb F_2[x]/(x^m)$ 上令

$$
S_d(X)=X\gg d.
$$

常数 tap 的反馈距离为 $m$，故其右移算子为零。有效反馈算子为

$$
U=S_\delta+Q,
\qquad
Q=\sum_{e\in B}S_{m-e}.
$$

## 2. 平方零修正分解

令

$$
P=I+S_\delta.
$$

由于所有截断移位彼此交换，

$$
I+U=P+Q=P\left(I+P^{-1}Q\right).
$$

而

$$
P^{-1}
=I+S_\delta+S_{2\delta}+S_{3\delta}+\cdots
$$

在移位达到 $m$ 时自然截断。记

$$
R=P^{-1}Q.
$$

对每个 $e\in B$，

$$
P^{-1}S_{m-e}
=\sum_{j=0}^{\lfloor(e-1)/\delta\rfloor}
S_{m-e+j\delta}.
$$

其中每个非零移位距离都至少是

$$
m-e\geq \frac m2.
$$

任意两个这样的移位复合后距离至少为 $m$，因而在截断空间上为零。因此

$$
R^2=0.
$$

在特征二中，

$$
(I+R)^{-1}=I+R.
$$

于是得到显式分解

$$
\boxed{
(I+U)^{-1}=(I+R)P^{-1}.
}
$$

这一步是整个构造的关键：近反馈项由一次 suffix scan 解决，所有低半区 tap 在 scan 后退化成一个平方零的跨半区修正。

## 3. 零 ancilla 的 CNOT 实现

### 3.1 实现 $P^{-1}$

$P^{-1}$ 按下标模 $\delta$ 分成 $\delta$ 条独立 suffix-XOR 链。每条链可用 in-place parallel-prefix 网络实现。合计资源为

$$
C_P=O(m),
\qquad
D_P=O\!\left(\log\left\lceil\frac m\delta\right\rceil\right),
$$

且不需要辅助 qubit。

### 3.2 实现单个远 tap

令

$$
T_e=P^{-1}S_{m-e}.
$$

$T_e$ 只把最高的 $e$ 个输入位映到最低的 $e$ 个目标位。由于 $e\leq m/2$，source block 与 target block 不相交。

沿模 $\delta$ 的每条剩余类：

1. 在 source block 上临时执行 suffix scan；
2. 将所得 suffix parity CNOT 到对应 target；
3. 逆向执行 scan，恢复 source block。

因此 $I+T_e$ 可用

$$
C_e=O(e),
\qquad
D_e=O\!\left(\log\left\lceil\frac e\delta\right\rceil+1\right)
$$

实现，且仍然不需要辅助位。

对任意 $e,e'\in B$ 都有 $T_eT_{e'}=0$，所以

$$
\prod_{e\in B}(I+T_e)
=I+\sum_{e\in B}T_e
=I+R.
$$

这说明可以逐个应用上述 shear，不会产生不需要的交叉项。

### 3.3 完整 clean reduction shear

对输入

$$
C=L+x^mH,
$$

规约的高半部贡献为

$$
F(H)=V(I+U)^{-1}H,
$$

其中

$$
V(X)=X+\bigl((X\ll(m-\delta))\bmod x^m\bigr)
+\sum_{e\in B}\bigl((X\ll e)\bmod x^m\bigr).
$$

完整电路为：

1. 在 $H$ 上执行 $P^{-1}$；
2. 对每个 $e\in B$ 执行 $I+T_e$，得到 $Y=(I+U)^{-1}H$；
3. 用 CNOT 把 $V(Y)$ 累加到 $L$；
4. 逆向执行第 2、1 步，把 $H$ 恢复为输入值。

最终实现

$$
(L,H)\longmapsto(L+F(H),H).
$$

整个过程只使用 $L,H$ 两个已有寄存器：

$$
\boxed{A=0.}
$$

## 4. 资源上界

前向和反向的 $P^{-1}$ scan 共需 $O(m)$ 个 CNOT。每个远 tap 的前向和反向修正共需 $O(e)$ 个 CNOT。低部装配 $V$ 的精确稀疏映射数为

$$
m+\delta+\sum_{e\in B}(m-e).
$$

因此

$$
C
=O\!\left(m+\sum_{e\in B}e
+m+\sum_{e\in B}(m-e)\right)
=O(wm).
$$

逐个执行各 tap 的保守深度上界为

$$
D
=O\!\left(
\log\left\lceil\frac m\delta\right\rceil
+\sum_{e\in B}
\log\left(1+\left\lceil\frac e\delta\right\rceil\right)
+w
\right).
$$

故当 $w$ 固定时，

$$
\boxed{
C=O(m),
\qquad
D=O\!\left(\log\frac m\delta\right),
\qquad
A=0.
}
$$

这里的 depth 是 all-to-all、每个 qubit 每层最多参与一个双 qubit 门的 CNOT depth，而不是软件 feedback depth。

## 5. 匹配下界

### 5.1 Size 下界

因为 $f(0)=1$，低部算子 $V$ 是可逆的单位三角线性映射；$(I+U)^{-1}$ 也可逆。因此

$$
\operatorname{rank}F=m.
$$

在 $H\mid L$ cut 上，每个跨 cut CNOT 最多把跨寄存器映射的秩提高一。因此任何实现 clean shear

$$
(L,H)\mapsto(L+F(H),H)
$$

的 CNOT 电路至少需要 $m$ 个跨 cut CNOT：

$$
C=\Omega(m).
$$

### 5.2 Depth 下界

令

$$
\beta=
\begin{cases}
m-\max B,&B\neq\varnothing,\\
m,&B=\varnothing.
\end{cases}
$$

则 $\beta\geq m/2$。在次数小于 $\beta$ 的范围内，远 tap 尚未影响 reciprocal series，故 $(I+U)^{-1}$ 的第零行至少含有

$$
H_0,H_\delta,H_{2\delta},\ldots,
H_{(s-1)\delta},
\qquad
s=\left\lceil\frac\beta\delta\right\rceil
$$

这些依赖。又因为 $V$ 的常数项为一，最终 $L_0$ 保留这些依赖。

深度为 $D$ 的二输入 CNOT 电路中，一个输出的 backward light cone 最多含 $2^D$ 个输入。因此

$$
D
\geq
\left\lceil\log_2\left\lceil\frac\beta\delta\right\rceil\right\rceil
=\Omega\!\left(\log\frac m\delta\right).
$$

对固定 $w$，上、下界匹配：

$$
\boxed{
C=\Theta(m),
\qquad
D=\Theta\!\left(\log\frac m\delta\right),
\qquad
A=0.
}
$$

“最优”一词只能在上述明确的 CNOT 模型、clean-shear 接口和二簇假设下使用。

## 6. Reciprocal 不能自动消除困难

若 $B$ 含有 $1$，例如

$$
f=x^m+x^{m-1}+x^a+x+1,
$$

则原多项式的最近反馈距离为 $1$。其 reciprocal 为

$$
f^*=x^m+x^{m-1}+x^{m-a}+x+1,
$$

最近反馈距离仍为 $1$。

因此该子族不像三项式那样能通过 reciprocal representation 自动把唯一高 tap 移到低半区。它提供了一个更有说服力的 modulus-selection 与可逆规约测试族。

## 7. 已找到的不可约五项式实例

使用 Sage 的精确 `is_irreducible()` 检查，以下二簇五项式均不可约：

| $m$ | 不可约多项式 |
|---:|---|
| 128 | $x^{128}+x^{127}+x^{11}+x+1$ |
| 163 | $x^{163}+x^{162}+x^{25}+x+1$ |
| 233 | $x^{233}+x^{232}+x^{15}+x+1$ |
| 283 | $x^{283}+x^{282}+x^{66}+x+1$ |
| 409 | $x^{409}+x^{408}+x^{24}+x+1$ |
| 571 | $x^{571}+x^{570}+x^9+x+1$ |

这些检查证明的是所列具体实例的不可约性，不证明该族在所有次数都存在不可约成员，也不证明 primitive 性。

此外，针对 $5\leq m\leq18$ 的小规模枚举／抽样 basis test 已检查：

- $R^2=0$；
- $(I+R)P^{-1}$ 与直接三角求逆一致；
- 所得 high-to-low shear 与直接多项式规约一致。

正式 artifact 应把搜索、不可约性检查和 basis test 固化为版本化脚本，而不能只保留交互式输出。

## 8. 能继续推广到哪里

设低 tap 不再限制于 $e\leq m/2$，并令

$$
\beta=m-\max B.
$$

同样有 $R=P^{-1}Q$，而且 $R$ 的每个移位距离至少为 $\beta$，所以

$$
R^\kappa=0,
\qquad
\kappa=\left\lceil\frac m\beta\right\rceil.
$$

代数上仍有

$$
(I+U)^{-1}
=\left(I+R+R^2+\cdots+R^{\kappa-1}\right)P^{-1}.
$$

这给出一个按 tap cluster separation 参数 $\kappa$ 分层的推广方向：

- $\beta\geq m/2$ 时，$\kappa=2$，就是本笔记的平方零、零 ancilla 构造；
- $\beta\geq m/3$ 时，$\kappa\leq3$；
- 一般 $\beta=\Omega(m)$ 时，$\kappa=O(1)$。

但是，当 $\kappa>2$ 时 source/target 区间会重叠，以上简单的 scan-copy-unscan shear 不再直接成立。此时虽然代数分解仍正确，但线性 CNOT size、对数 CNOT depth 和零 ancilla 三者能否同时保持，需要新的 block-triangular circuit construction。

因此当前严谨边界是：

$$
\boxed{
\text{任意权重的二簇半区族已经构造完成；任意 tap 几何仍未解决。}
}
$$

## 9. Claim ledger

| 命题 | 当前状态 |
|---|---|
| 二簇族的算子分解与 $R^2=0$ | 已证明 |
| 固定 $w$ 的 $O(m)$ CNOT、$O(\log(m/\delta))$ depth、零 ancilla 构造 | 候选定理；需整理正式电路定义 |
| 同一模型下的 $\Omega(m)$ size 与 $\Omega(\log(m/\delta))$ depth | 候选定理；需整理 cut-rank 与 light-cone 引理 |
| 表中六个多项式不可约 | Sage 精确检查通过；需固化脚本 |
| 对所有次数都存在该型不可约多项式 | 未证明 |
| 相对现有量子有限域电路具有新颖性 | 未完成 hostile prior-art audit |
| 相对现有电路具有实际 CNOT 优势 | 未比较，仍开放 |
