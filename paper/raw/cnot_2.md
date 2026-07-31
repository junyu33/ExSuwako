可以。继续推下去，会得到一个比“可以做成可逆电路”更强的结论：

[
\boxed{\text{ExSuwako 给出了一个显式的稀疏 CNOT 分解。}}
]

并且对三项式，所得深度在标准双量子门模型下是渐近最优的。

---

## 1. 先把 doubling 轮写成具体移位

仍设

[
f(x)=x^m+q(x),\qquad \deg q=t<m,
]

并定义

[
T(Y)=\left\lfloor\frac{qY}{x^m}\right\rfloor.
]

令

[
q(x)=\sum_{e\in E}x^e,
\qquad E=\operatorname{supp}(q).
]

关键恒等式是：

[
T^r(Y)
======

\left\lfloor
\frac{q(x)^rY}{x^{rm}}
\right\rfloor.
]

特别地，当 (r=2^k) 时，利用 (\mathbb F_2) 上的 Frobenius：

[
q(x)^{2^k}
==========

\sum_{e\in E}x^{2^ke}.
]

所以

[
\boxed{
T^{2^k}(Y)
==========

\bigoplus_{e\in E}
\left(
Y\gg 2^k(m-e)
\right)
}
]

其中移位量大于等于 (m) 的项自动消失。

这正是 ExSuwako 每轮只需要若干固定移位和 XOR 的原因：**doubling 不会让 tap 数爆炸**。因为平方不会产生交叉项，Hamming weight 仍然是 (w(q))。

---

## 2. ExSuwako 的每轮

设

[
\nu=\left\lceil\frac m\Delta\right\rceil,
\qquad
\Delta=m-\deg q,
]

于是

[
T^\nu=0.
]

取

[
D=\lceil\log_2\nu\rceil.
]

ExSuwako 可以写成

[
Y_0=H,
]

[
Y_{k+1}
=======

\left(I+T^{2^k}\right)Y_k,
\qquad 0\le k<D.
]

因此

[
\begin{aligned}
Y_D
&=
\prod_{k=0}^{D-1}
\left(I+T^{2^k}\right)H\
&=
\left(
I+T+T^2+\cdots+T^{2^D-1}
\right)H\
&=
(I+T)^{-1}H.
\end{aligned}
]

---

## 3. 每轮可以用两个寄存器可逆计算

保留 (Y_k)，准备一个全零的 (m)-bit 寄存器 (Y_{k+1})。

先复制：

[
Y_{k+1}\gets Y_k.
]

然后对每个 tap (e\in E)，令

[
d_{e,k}=2^k(m-e),
]

加入 CNOT：

[
Y_k[j]\longrightarrow Y_{k+1}[j-d_{e,k}],
\qquad j\ge d_{e,k}.
]

最后得到：

[
Y_{k+1}
=======

Y_k+
\bigoplus_{e\in E}(Y_k\gg d_{e,k})
==================================

\left(I+T^{2^k}\right)Y_k.
]

注意源寄存器和目标寄存器彼此分离，因此：

* 没有覆盖旧值的问题；
* 所有操作都是 CNOT；
* 反向再执行同一批 CNOT，就能把 (Y_{k+1}) 清零。

---

## 4. 完整 reduction 的干净可逆电路

完整过程是：

[
(L,H,0,\ldots,0)
]

依次计算

[
Y_1,Y_2,\ldots,Y_D,
]

然后把

[
S(Y_D)=qY_D\bmod x^m
]

加到 (L)：

[
L\gets L+S(Y_D).
]

接着逆序撤销所有 doubling stage：

[
Y_D\to0,\quad
Y_{D-1}\to0,\quad\ldots,\quad
Y_1\to0.
]

最终得到

[
\boxed{
(L,H,0,\ldots,0)
\longmapsto
\left(
L+x^mH\bmod f,;
H,;
0,\ldots,0
\right).
}
]

所有辅助寄存器都恢复到零。

这就是量子电路里需要的 clean reversible embedding。

---

# 5. 可以给出精确 CNOT 资源上界

定义第 (k) 轮仍然有效的 tap 数：

[
h_k
===

#\left{
e\in E:
2^k(m-e)<m
\right}.
]

第 (k) 轮需要的 CNOT 数是

[
C_k
===

m+
\sum_{e\in E}
\left[m-2^k(m-e)\right]_+,
]

其中第一项 (m) 是复制 (Y_k)，并记

[
[z]_+=\max(z,0).
]

完整电路需要正向和反向各一次，因此总 CNOT 数为

[
\boxed{
C
=

2\sum_{k=0}^{D-1}
\left(
m+
\sum_{e\in E}
[m-2^k(m-e)]*+
\right)
+
\sum*{e\in E}(m-e).
}
]

最后一项是 (S(Y_D)=qY_D\bmod x^m)。

粗略上界为

[
\boxed{
C=O!\left(w(q)m\log\frac m\Delta\right).
}
]

辅助 qubit 数为

[
\boxed{Dm=O!\left(m\log\frac m\Delta\right).}
]

---

## 6. CNOT depth 也能直接估计

每轮的 CNOT 都从寄存器 (Y_k) 指向另一个寄存器 (Y_{k+1})。

把这些 CNOT 看成一个二分图：

* 左边是 (Y_k) 的 qubit；
* 右边是 (Y_{k+1}) 的 qubit；
* 每个 qubit 的度最多为 (1+h_k)。

二分图边可以用至多最大度个 matching 着色，所以每轮深度至多

[
1+h_k.
]

因此完整 reduction 电路深度满足：

[
\boxed{
\operatorname{depth}
\le
2\sum_{k=0}^{D-1}(1+h_k)+w(q).
}
]

粗略地：

[
\boxed{
\operatorname{depth}
====================

O!\left(
w(q)\log\frac m\Delta
\right).
}
]

这里假设：

* 全连接 qubit；
* 每个 qubit 每层至多参与一个双量子门；
* 不计真实芯片上的 routing。

---

# 7. 三项式情形异常干净

考虑

[
f(x)=x^m+x^t+1,
\qquad
\Delta=m-t.
]

这里

[
q(x)=x^t+1.
]

在 (T^{2^k}) 中，常数 tap 对应右移 (2^km)，始终消失；只剩：

[
T^{2^k}(Y)
==========

Y\gg 2^k\Delta.
]

于是每轮只是：

[
\boxed{
Y_{k+1}
=======

Y_k\oplus
\left(Y_k\gg2^k\Delta\right).
}
]

每轮二分图最大度为 2，所以：

* 每轮深度至多 2；
* 正向加反向总深度至多 (4D)；
* 最后的 (qY\bmod x^m) 深度至多 2。

因此：

[
\boxed{
\operatorname{depth}
\le
4\left\lceil
\log_2\left\lceil\frac m\Delta\right\rceil
\right\rceil+2.
}
]

---

## 8. 而且这个对数深度是渐近最优的

对三项式，

[
T(Y)=Y\gg\Delta.
]

所以

[
Y=(I+T)^{-1}H
=============

H\oplus(H\gg\Delta)
\oplus(H\gg2\Delta)
\oplus\cdots.
]

特别地，

[
Y_0
===

H_0\oplus H_\Delta\oplus H_{2\Delta}
\oplus\cdots.
]

这个输出 bit 依赖大约

[
\nu=\left\lceil\frac m\Delta\right\rceil
]

个独立输入 bit。

在只允许双量子门的深度 (d) 电路中，一个输出 qubit 的反向 light cone 最多覆盖

[
2^d
]

个输入 qubit。因此必有

[
2^d\ge\nu,
]

也就是

[
\boxed{
d\ge
\left\lceil\log_2\nu\right\rceil.
}
]

所以在全连接、双量子门模型中：

[
\boxed{
\text{ExSuwako 对三项式达到了渐近最优 CNOT depth。}
}
]

上界是 (O(\log\nu))，下界也是 (\Omega(\log\nu))。

这已经不是单纯“能不能可逆”的观察，而是一个真正的复杂度结果。

---

# 9. 平方 oracle 也可以直接做成 CNOT-only

令

[
a(x)=\sum_{i=0}^{m-1}a_ix^i.
]

在 (\mathbb F_2) 上：

[
a(x)^2=\sum_i a_i x^{2i}.
]

平方本身只是在偶数位置放置输入 bit，不需要 Toffoli。

把高低部分直接从 (a) 中抽出来：

[
L=\sum_{2i<m}a_ix^{2i},
]

[
H=\sum_{2i\ge m}a_ix^{2i-m}.
]

然后应用上面的 ExSuwako reduction network，就得到：

[
\boxed{
|a\rangle|z\rangle
\longmapsto
|a\rangle
\left|z+a^2\bmod f\right\rangle.
}
]

整个 oracle：

* 只有 CNOT；
* 所有 ancilla 最终归零；
* 不需要先构造一个完整的 (2m)-bit 乘积；
* 深度为
  [
  O!\left(w(q)\log\frac m\Delta\right).
  ]

这就可以直接嵌入 Itoh–Tsujii inversion 一类反复调用 squaring 的量子有限域算法中。

---

## 目前推导出的最强表述

可以暂时写成下面这个命题：

> For (f(x)=x^m+q(x)), ExSuwako induces a clean reversible CNOT circuit for modular reduction with depth
> [
> O!\left(w(q)\log\frac{m}{m-\deg q}\right)
> ]
> and CNOT count
> [
> O!\left(w(q)m\log\frac{m}{m-\deg q}\right).
> ]
> For trinomials, the logarithmic depth is asymptotically optimal in the all-to-all two-qubit gate model.

真正还没解决的是 **CNOT count 和 ancilla 是否最优**。尤其三项式实际上接近一个 parallel suffix-XOR / prefix-scan 问题，可能用更精细的 scan network 把：

[
O(m\log\nu)
]

门数进一步压到：

[
O(m)
]

同时保持 (O(\log\nu)) 深度和 (O(m)) ancilla。

所以现在已经出现一个很清晰的新研究问题：

[
\boxed{
\text{ExSuwako 给出深度最优结构；还能否进一步做到 work-efficient reversible scan？}
}
]

这比最开始的“是否可逆”已经向前走了相当远。
