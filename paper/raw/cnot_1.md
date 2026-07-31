可以，而且结论很漂亮，但必须区分三个不同的“变换”：

[
\boxed{
\begin{array}{l}
H\mapsto Y\text{ 的反馈求解：可逆};\
(L,H)\mapsto R\text{ 的最终规约：不可逆};\
(L,H)\mapsto(R,H)\text{ 的保留高位版本：可逆且自逆}.
\end{array}}
]

## 1. 写出 ExSuwako 的算子形式

设模多项式

[
f(x)=x^m+q(x),\qquad \deg q<m,
]

输入拆成

[
A(x)=L(x)+x^mH(x),
\qquad \deg L,\deg H<m.
]

对任意 (Y)，把 (qY) 拆成高低两部分：

[
qY=S(Y)+x^mT(Y),
]

其中

[
S(Y)=qY\bmod x^m,\qquad
T(Y)=\left\lfloor\frac{qY}{x^m}\right\rfloor.
]

ExSuwako 求出满足

[
H=Y+T(Y)
]

的 (Y)，也就是

[
Y=(I+T)^{-1}H.
]

随后输出

[
R=L+S(Y).
]

因为

[
\begin{aligned}
fY
&=(x^m+q)Y\
&=x^mY+S(Y)+x^mT(Y)\
&=x^m\bigl(Y+T(Y)\bigr)+S(Y)\
&=x^mH+S(Y),
\end{aligned}
]

所以

[
x^mH\equiv S(Y)\pmod f.
]

这就是算法正确性的核心等式。

---

## 2. (H\mapsto Y) 本身确实可逆

因为 (T) 每作用一次，次数至少下降

[
\Delta=m-\deg q>0,
]

所以 (T) 是 nilpotent：

[
T^r=0
]

对充分大的 (r) 成立。因此

[
I+T
]

一定可逆，而且

[
(I+T)^{-1}
==========

I+T+T^2+\cdots+T^{r-1}.
]

ExSuwako 的 doubling 本质上就是快速计算这个逆：

[
(I+T)^{-1}
==========

\prod_{k=0}^{D-1}
\left(I+T^{2^k}\right),
]

其中 (2^D) 足够大，使得 (T^{2^D}=0)。

更直接的是，既然

[
Y=(I+T)^{-1}H,
]

那么逆变换极其简单：

[
\boxed{H=Y+T(Y).}
]

所以反馈传播部分不是信息压缩，而是一个真正的线性双射。

---

## 3. (H\mapsto S(Y)) 在域模数下也可逆

令

[
F(H)=S\bigl((I+T)^{-1}H\bigr).
]

从上面的证明可知：

[
F(H)=x^mH\bmod f.
]

这就是商环中“乘以 (x^m)”的线性变换。

当

[
f(0)=1
]

时，(x) 在 (\mathbb F_2[x]/(f)) 中可逆，因此乘以 (x^m) 也可逆。

特别地，若 (f) 是定义 (\mathbb F_{2^m}) 的不可约多项式，那么其常数项必为 1，于是：

[
\boxed{H\longmapsto x^mH\bmod f}
]

是一个 (m)-bit 到 (m)-bit 的线性双射。

也就是说，在通常的有限域语境下，ExSuwako 从高半部 (H) 生成规约贡献的映射本身也是可逆的。

---

## 4. 但完整规约 ((L,H)\mapsto R) 不可逆

最终结果是

[
R=L+F(H).
]

输入有 (2m) bit，输出只有 (m) bit，所以显然不可能单射：

[
\mathbb F_2^{2m}\longrightarrow\mathbb F_2^m.
]

例如对任意 (H)，选择

[
L=F(H)
]

都会得到 (R=0)。因此普通 reduction 会丢掉商的信息。

---

## 5. 量子电路需要的是这个可逆提升

保留高半部：

[
U:(L,H)\longmapsto \bigl(L+F(H),H\bigr).
]

这个映射一定可逆，甚至是**自逆的**：

[
\begin{aligned}
U^2(L,H)
&=U(L+F(H),H)\
&=(L+F(H)+F(H),H)\
&=(L,H).
\end{aligned}
]

因为在 (\mathbb F_2) 上：

[
F(H)+F(H)=0.
]

因此：

[
\boxed{
(L,H)\mapsto
\left(L+\left(x^mH\bmod f\right),H\right)
}
]

天然就是一个 reversible linear circuit，可以完全由 CNOT 门实现。

这甚至不要求 (F) 自身可逆：任何形式

[
(a,b)\mapsto(a+F(b),b)
]

都是可逆 shear。只是对不可约模数而言，(F) 碰巧自身也可逆。

## 对量子应用的准确结论

ExSuwako 的代数结构**没有可逆性障碍**：

* 内部反馈求解 (H\mapsto Y) 可逆；
* 域语境下的高位规约贡献 (H\mapsto F(H)) 可逆；
* 保留输入的 reduction embedding 可逆且自逆；
* 有限域平方
  [
  a\mapsto a^2\bmod f
  ]
  本身又是 Frobenius 自同构，当然可逆。

真正尚未自动得到的是：

[
\boxed{\text{ExSuwako 的 }O(\log m)\text{ 算法轮数，是否也能转化为低 CNOT depth。}}
]

量子电路里还要单独处理 fan-out、同一 wire 的并发访问、ancilla 数量以及 uncomputation。但“它是否能够成为可逆电路”这一关，答案已经明确是：

[
\boxed{\text{能，而且其可逆提升具有非常干净的自逆结构。}}
]
