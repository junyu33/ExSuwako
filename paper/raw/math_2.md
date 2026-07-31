继续推下去后，最自然的对象已经不是“二元域中的模规约”，而是：

[
\boxed{\text{截断幂级数环中稀疏幂零反馈的快速求逆}}
]

而且现在可以得到一个相当完整的推广框架。不可约性、具体有限域、甚至标量系数都不是核心条件。

---

## 先看一个扩域五项式例子

设系数属于任意特征 (2) 的交换代数 (R)，例如

[
R=\mathbb F_{2^s},
\qquad
R=\mathbb F_2[u]/(g(u)),
]

并取

[
f(x)=x^m+a x^{m-1}+b x^{m-r}+c x+e.
]

它可以可约，(R) 甚至不必是域。

对反馈部分而言，定义右移算子 (N)：

[
(NY)*i=Y*{i+1},\qquad N^m=0.
]

那么只有正次数项参与高位反馈：

[
T=aN+bN^r+cN^{m-1}.
]

在特征 (2) 中：

[
T^{2^k}
=======

a^{2^k}N^{2^k}
+
b^{2^k}N^{2^kr}
+
c^{2^k}N^{2^k(m-1)}.
]

没有任何交叉项。因此无论迭代多少轮，每轮仍然最多是原来的三个 tap，只是：

* 移位距离乘以 (2^k)；
* 系数经过 Frobenius：
  [
  a\mapsto a^{2^k}.
  ]

这已经说明扩域和任意 (w) 项式并不会破坏 ExSuwako 的核心结构。

---

# 1. 真正的统一形式：反转多项式的截断求逆

设

[
f(x)=x^m+q(x),
\qquad
q(x)=\sum_{e=0}^{m-1}a_ex^e.
]

对每个正次数 tap 定义反馈距离：

[
d_e=m-e.
]

再定义反馈多项式

[
\rho(z)
=======

\sum_{\substack{e>0\a_e\ne0}}
a_ez^{m-e}.
]

注意：

[
\operatorname{ord}_z\rho
========================

# \delta

m-\deg q.
]

在系数向量上，反馈算子就是

[
T=\rho(N).
]

于是反馈方程

[
H=(I+T)Y
]

等价于：

[
Y=(I+T)^{-1}H.
]

而它又等价于计算截断幂级数逆：

[
\boxed{
B(z)
====

(1+\rho(z))^{-1}
\bmod z^m.
}
]

最终：

[
Y=B(N)H.
]

因此 ExSuwako 本质上是在不显式构造稠密 reciprocal (B) 的情况下，把它以稀疏因子形式作用到 (H) 上。

---

# 2. 特征 2 中的精确 Frobenius 分解

取

[
D=
\left\lceil
\log_2\frac m\delta
\right\rceil.
]

由于

[
\operatorname{ord}_z \rho^{2^D}
===============================

2^D\delta
\ge m,
]

所以

[
\rho^{2^D}=0\pmod {z^m}.
]

在特征 (2) 中：

[
\boxed{
(1+\rho)^{-1}
=============

\prod_{k=0}^{D-1}
\left(1+\rho^{2^k}\right)
\pmod {z^m}.
}
]

因为：

[
(1+\rho)
\prod_{k=0}^{D-1}(1+\rho^{2^k})
===============================

1+\rho^{2^D}
\equiv1\pmod {z^m}.
]

同时：

[
\rho(z)^{2^k}
=============

\sum_e
a_e^{2^k}z^{2^k(m-e)}.
]

因此每个因子仍然只有原来的 tap 数。

这甚至可以写成一个误差平方过程。令

[
B_k=
\prod_{j=0}^{k-1}(1+\rho^{2^j}),
]

则：

[
(1+\rho)B_k
===========

1+\rho^{2^k}.
]

所以每一轮把正确位数从大约 (2^k\delta) 翻倍到 (2^{k+1}\delta)。

换句话说：

[
\boxed{\text{ExSuwako 是特征 2 中保持稀疏性的 Newton–Hensel 求逆。}}
]

这可能是比“反馈 doubling”更标准、更容易进入计算数学语境的表述。

---

# 3. 任意 (w) 项式的精确工作量

设反馈中有 (h) 个正次数 tap：

[
1\le h\le w-1,
]

距离为：

[
1\le d_1<d_2<\cdots<d_h<m.
]

第 (k) 轮中，第 (r) 个 tap 需要执行：

[
[m-2^kd_r]_+
]

次系数乘加，其中

[
[z]_+=\max(z,0).
]

所以反馈求逆的精确符号工作量是：

[
\boxed{
W_{\mathrm{fb}}
===============

\sum_{r=1}^{h}
\sum_{k\ge0}
[m-2^kd_r]_+.
}
]

对每个 tap：

[
\sum_{k\ge0}[m-2^kd_r]_+
<
m\left\lceil
\log_2\frac m{d_r}
\right\rceil.
]

从而：

[
\boxed{
W_{\mathrm{fb}}
<
m\sum_{r=1}^{h}
\left\lceil\log_2\frac m{d_r}\right\rceil.
}
]

这比粗糙的

[
O\left(hm\log\frac m\delta\right)
]

强得多，因为它考虑了所有 tap 的几何位置，而不只看最高 tap。

由于距离彼此不同，有 (d_r\ge r)，于是：

[
\sum_{r=1}^{h}\log\frac m{d_r}
\le
\log\frac{m^h}{h!}
==================

O\left(
h\left(1+\log\frac mh\right)
\right).
]

因此对任意 (w) 项式：

[
\boxed{
W_{\mathrm{fb}}
===============

O\left(
mh\left(1+\log\frac mh\right)
\right).
}
]

这个界有几个很漂亮的端点：

[
\begin{array}{c|c}
h & W_{\mathrm{fb}}\
\hline
O(1) & O(m\log m)\
\Theta(\sqrt m) & O(m^{3/2}\log m)\
\Theta(m) & O(m^2)
\end{array}
]

特别是即使 (q) 是稠密的，界也是：

[
O(m^2),
]

而不是粗略估计得到的 (O(m^2\log m))。原因是大多数低 tap 在很早的 doubling 轮次中就移出范围了。

---

# 4. 任意 (w) 的并行深度

第 (k) 轮最多需要把

[
1+h_k
]

个值相加，其中：

[
h_k
===

#{r:2^kd_r<m}.
]

用二元加法树，每轮代数深度为：

[
O(\log(1+h_k)).
]

因此：

[
\operatorname{depth}
\le
\sum_{k=0}^{D-1}
O(\log(1+h_k))
\le
O(D\log(1+h)).
]

即：

[
\boxed{
\operatorname{depth}
====================

O\left(
\log\frac m\delta\cdot\log w
\right).
}
]

对于固定 (w)：

[
\boxed{
\operatorname{depth}
====================

O\left(\log\frac m\delta\right).
}
]

而且这个对数深度在一般意义下不能再消失。

取系数为代数独立元：

[
R=\mathbb F_2[u_1,\ldots,u_h],
]

并令 (u_1) 对应最短距离 (\delta)。在

[
(1+\rho)^{-1}
=============

1+\rho+\rho^2+\cdots
]

中，(z^{j\delta}) 的系数包含唯一单项式：

[
u_1^j.
]

因此一个输出符号会依赖：

[
H_0,H_\delta,H_{2\delta},\ldots
]

共约

[
\nu=\left\lceil\frac m\delta\right\rceil
]

个独立输入。

任何 fan-in 2 的电路深度至少为：

[
\boxed{
\Omega\left(\log\frac m\delta\right).
}
]

所以对固定 (w)，ExSuwako 的代数深度在通用／generic 系数模型中已经渐近最优。

这比之前只对三项式得到的 light-cone 下界更一般。

---

# 5. 完全不要求具体有限域

现在可以把系数环直接取成：

[
R=
\mathbb F_2[y_1,\ldots,y_s]/I.
]

那么 (f(x)\in R[x]) 可以描述：

* 有限域扩张；
* 可约商代数；
* 含幂零元的非约化代数；
* 多变量多项式环中的一次主变量规约；
* tower extension；
* 产品代数。

只要 (f) 关于 (x) 是首一的，除法和余式都是唯一的。

所以：

[
\boxed{\text{不可约性只决定商对象是不是域，不决定算法是否成立。}}
]

例如：

[
R=\mathbb F_{2^s},
\qquad
R[x]/(f)
]

在 (f) 不可约时是 (\mathbb F_{2^{sm}})；在 (f) 可约时只是一个 (m) 维 (R)-代数。ExSuwako 对两者完全相同。

---

# 6. 还能推广到块系数和模块

标量系数甚至也不是必要的。

设 (M) 是一个特征 (2) 的模块，并令：

[
A_1,\ldots,A_h\in\operatorname{End}(M)
]

是两两可交换的线性算子。定义：

[
T=
\sum_{r=1}^{h}A_rN^{d_r}
]

作用在 (M^m) 上。

因为 (A_r) 与移位 (N) 以及彼此可交换：

[
\boxed{
T^{2^k}
=======

\sum_{r=1}^{h}
A_r^{2^k}N^{2^kd_r}.
}
]

因此所有 ExSuwako 分解仍然成立。

标量多项式规约只是取：

[
A_r(v)=a_rv
]

的特例。

这个模块版本覆盖：

* 扩域符号；
* 向量值递推；
* 具有可交换块系数的反馈系统；
* 某些 polynomial-matrix reduction；
* 多通道线性反馈网络。

因此最一般的核心对象可以表述为：

[
\boxed{\text{带可交换块 tap 的有限长度稀疏反馈系统。}}
]

这已经彻底脱离“某个具体 binary field modulus”。

---

# 7. 扩域上的实现代价也可以精确表达

若：

[
R=\mathbb F_{2^s},
]

则每个反馈操作是：

[
y_i
\leftarrow
y_i+a_r^{2^k}y_{i+2^kd_r}.
]

选定一个 (\mathbb F_2)-基后，乘以固定常数 (a) 是一个 (s\times s) 的二元线性变换。

令：

[
C_{\mathcal B}(a)
]

表示在基 (\mathcal B) 下实现常数乘法 (v\mapsto av) 的成本，那么总 bit-level 成本为：

[
\boxed{
W_{\mathrm{bit}}
================

\sum_{k,r}
[m-2^kd_r]*+
,C*{\mathcal B}(a_r^{2^k}).
}
]

这给出了一个比“最小 Hamming weight 模多项式”更准确的选择目标：

[
\boxed{
\text{tap 位置}
+
\text{Frobenius 轨道}
+
\text{固定常数乘法成本}.
}
]

特别地：

### 系数都属于 (\mathbb F_2)

[
a_r^{2^k}=a_r.
]

外层 ExSuwako 只是对整个 (\mathbb F_{2^s}) 符号执行 XOR，相当于 (s) 条完全相同的二元网络并行运行。

### 一般 (\mathbb F_{2^s}) 系数

由于：

[
a^{2^s}=a,
]

各轮系数模式至多每 (s) 轮循环一次。只需保存至多 (s) 组常数乘法结构。

---

# 8. 正特征 (p) 也能推广

再向前一步，设底层特征是任意素数 (p)。

对任意幂零 (T)，有：

[
(I+T)^{-1}
==========

\sum_{j=0}^{\nu-1}(-T)^j.
]

利用 (p) 进制分组：

[
\boxed{
(I+T)^{-1}
==========

\prod_{k=0}^{D-1}
\left(
\sum_{a=0}^{p-1}
(-T)^{ap^k}
\right),
}
]

其中：

[
p^D\ge\nu.
]

因为：

[
T^{p^k}
=======

\sum_{r=1}^{h}
A_r^{p^k}N^{p^kd_r}.
]

每一轮的基础算子仍然保持 (h)-sparse。只是需要它的前 (p-1) 个幂。

每轮展开后的 tap 数最多为：

[
\sum_{a=0}^{p-1}
\binom{h+a-1}{a}
================

\boxed{
\binom{h+p-1}{p-1}.
}
]

所以对于固定 (p) 和固定 (w)，仍然有：

[
O\left(\log_p\frac m\delta\right)
]

轮，每轮保持常数数量的移位项。

而特征 (2) 特别优雅，因为：

[
\binom{h+1}{1}=h+1,
]

即每轮只需要：

[
I+T^{2^k},
]

完全没有高次交叉项。

因此更准确的结论不是“只有 binary 才成立”，而是：

[
\boxed{\text{任意正特征都成立；特征 2 在稀疏性上最优雅。}}
]

---

# 9. 还能得到一个 radix–work–depth tradeoff

甚至不必每次只按 (p) 进制推进。取：

[
b=p^\ell.
]

则：

[
\boxed{
(I+T)^{-1}
==========

\prod_{k=0}^{D_b-1}
\left(
\sum_{a=0}^{b-1}
(-T)^{ab^k}
\right),
}
]

其中：

[
D_b=
\left\lceil\log_b\nu\right\rceil.
]

增大 (b) 会：

* 减少顺序轮数；
* 但增加每轮展开项数：

[
\le
\binom{h+b-1}{b-1}.
]

所以形成一个明确的 work–depth tradeoff：

[
\boxed{
\text{小 radix：更多轮、每轮更稀疏};
\qquad
\text{大 radix：更少轮、每轮更稠密}.
}
]

在特征 (2) 中，原始 ExSuwako 对应：

[
b=2.
]

对于 (h\ge2)，一旦取 (b=4)，每轮最坏项数就从：

[
h+1
]

增长到：

[
\binom{h+3}{3}.
]

所以 binary doubling 不只是“最自然”的选择，它还是**保持 tap 稀疏性最激进的 radix 选择**。

---

# 10. 现在真正没有解决的边界

代数层面，任意 (w)、可约模数、扩域、交换代数、块系数乃至任意正特征都已经可以统一。

但下面这个更强的电路结论尚未自动得到：

[
\boxed{
\text{对任意固定 }w\text{ 和任意 tap 几何，是否总存在}
}
]

[
\boxed{
O(m)\text{ size}
+
O(\log m)\text{ depth}
+
O(1)\text{ 或零 ancilla}
}
]

的可逆实现。

目前可以稳妥区分：

* 三项式：可以退化成 prefix/suffix scan，线性 size 很有希望；
* 有界状态阶数的多 tap：可以用固定维状态 scan；
* 任意 tap 几何：ExSuwako 给出
  [
  O(m\log m)
  ]
  级别的固定-(w) work 和
  [
  O(\log m)
  ]
  depth，但线性 size 尚不能直接声称。

这不是理论缺陷，反而可能形成论文中最重要的分类：

[
\boxed{
\begin{array}{c}
\text{一般稀疏反馈：Frobenius doubling}\
\text{低状态阶数反馈：work-efficient prefix scan}\
\text{两者之间的最优复杂度边界}
\end{array}}
]

所以，继续推广后，ExSuwako 最强的候选身份已经变成：

> **A sparse Frobenius inversion framework for nilpotent feedback operators over positive-characteristic algebras.**

模多项式规约只是它最直接的一个实例。若这些定理逐一形式化并通过 prior-art 检查，确实已经非常接近一篇以结构、算法、复杂度和一般化为主体的 *Mathematics of Computation* 论文。
