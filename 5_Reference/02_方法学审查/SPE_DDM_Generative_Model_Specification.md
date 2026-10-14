# SPE–DDM 生成模型与设计空间建模：理论基础和实施规格（工作稿）

**版本：** v0.1  
**日期：** 2026-10-11  
**用途：** 作为完善 Self-Matching Task（SMT）生成模型、模拟数据生成、参数恢复、模型恢复和实验设计空间优化的理论与技术依据；可交由后续 AI 或研究者据此实现。  
**状态：** 核心方向已初步确定；文末列出仍需在实现前显式处理的技术问题。本文不是已验证的最终心理理论，也不应把文中的候选函数描述为人类行为的普遍定律。

---

## 1. 研究目标与总体原则

本项目拟研究实验设计空间

\[
\Omega=(P,T,W,M)
\]

如何影响 Self-Matching Task 中的潜在决策过程及外显行为。当前可将变量暂时区分为：

- **P — Practice:** 先前对形状—社会标签联结的练习/学习量。
- **T — Stimulus presentation duration:** 视觉刺激的计划呈现时长。
- **W — Response deadline:** 从刺激呈现开始计时，到允许有效反应的最晚时间。
- **M / association condition:** 原项目中用于表示匹配或联结条件的变量。为避免歧义，代码和数据中应分开记录 `association_type`（Self/Other 等联结类别）与 `match_status`（Match/Nonmatch）。不要在同一个字段里混用这两个因素。

总体建模链条为：

\[
(P,T,W,\text{association},\text{match status})
\rightarrow (v,a,z,t_0)
\rightarrow (RT,\text{choice},\text{accuracy},\text{timeout})
\]

基本原则：

1. 先建立参数少、心理解释明确的基线模型，再增加交互项、延迟参数或额外随机效应。
2. P、T、W 对 DDM 参数的作用属于待检验的生成假设，而不是已被证明的心理定律。
3. 生成器、拟合器和模型比较必须使用一致的选择编码、时间单位、deadline 规则与边界定义。
4. 不应为了得到有效 RT 而反复重抽超时试次；超时本身是 deadline 条件下的重要观测结果。
5. 拟合优劣不能单独证明心理机制正确。必须同时检验参数恢复、模型恢复、收敛和后验预测检查（Wilson & Collins, 2019）。

## 2. DDM 的基本定义及符号约定

### 2.1 漂移扩散过程

采用标准 Wiener diffusion decision process 作为基本过程：

\[
 dX_s=v\,ds+\sigma\,dB_s,
\]

其中：

- \(X_s\)：潜在决策变量；
- \(v\)：有符号的 drift rate；
- \(\sigma\)：扩散噪声尺度；
- \(B_s\)：标准 Wiener 过程；
- \(s\)：决策过程经过时间。

**尺度识别约定：** 第一版固定 \(\sigma=1\)，不与 \(v\) 或 \(a\) 一起自由估计。若同时任意改变漂移、边界和扩散噪声的尺度，参数可能无法单独识别。

### 2.2 v 的含义

\(v\) 是潜在决策变量沿决策轴的**有符号平均漂移率**，不是物理空间里的速度矢量。其符号取决于边界和反应如何编码：正值使过程平均朝上边界移动，负值使其平均朝下边界移动；绝对值通常反映平均证据积累强度/效率。

在一般 DDM 中，更大的证据积累幅度通常会使选择更可靠，并改变 RT 分布，但 RT 和准确率仍然共同依赖边界间距、起点和非决策时间等参数（Ratcliff & McKoon, 2008; Wiecki et al., 2013）。

### 2.3 a、z、t0 的约定

- \(a\)：边界间距，反映需要积累多少证据才作出选择；不是时间单位。
- \(z\)：标准 DDM 中通常是相对起点比例，\(z\in(0,1)\)。当 \(z=0.5\) 时，起点位于两边界中点。
- \(x_0\)：以证据轴单位表示的绝对起点。若边界为 \([0,a]\)，则 \(x_0=za\)，因此 \(z=0.5\) 等价于 \(x_0=a/2\)。旧 Notebook 中的 `evidence = a / 2` 是把绝对起点放在中点，并非把 HDDM 的比例参数 `z` 设置成数值 `a/2`。
- \(t_0\)：非决策时间的总合参数，涵盖 DDM 外部的编码/执行等过程；观测反应时为 \(RT=t_0+s\)。第一版固定为一个合理的正值，待基础恢复成功后再评估是否需要估计或加入个体差异。

**第一版决定：** 固定无起点偏向，使用相对起点 \(z=0.5\)（或等价的中心起点）。暂不将 Self-specific response bias 作为必须机制；后续若理论和数据支持，再单独研究 \(z\)。

---

## 3. 选择编码：固定实际按键含义，并按正确反应方向确定 v 的符号

SMT 至少包含两个不同维度：

1. `association_type`：Self、Other/Stranger 等联结类别；
2. `match_status`：当前形状—标签组合是否符合学得的联结（Match 或 Nonmatch）。

这两个维度不可合并。Self/Other 并不等于 Match/Nonmatch。

### 3.1 第一版的反应编码约定

建议固定：

- 上边界 = 实际的 **Match response**；
- 下边界 = 实际的 **Nonmatch response**；
- 数据中的 `choice` 记录被试实际选择（Match/Nonmatch），而不是仅记录正确/错误；
- `correct_choice` 根据真实 Match/Nonmatch 状态生成；
- `accuracy` 根据 `choice == correct_choice` 推导。

定义正确反应方向符号：

\[
q_i=\begin{cases}
+1,&\text{Match 是本试次正确反应},\\
-1,&\text{Nonmatch 是本试次正确反应}.
\end{cases}
\]

先定义正值的证据积累幅度 \(d_i>0\)，然后定义有符号漂移率：

\[
\boxed{v_i=q_i d_i.}
\]

因此，正确答案为 Match 的试次，其漂移方向朝 Match 上边界；正确答案为 Nonmatch 的试次，其漂移方向朝 Nonmatch 下边界。SPE 可以先在 \(d\) 层面表达，再由 \(q_i\) 决定当前试次的漂移方向。

这在概念上是“实际反应选项编码 + 根据哪个反应正确而翻转 drift 符号”。某些软件（如 HDDM）把这种实现归在 stimulus-coding / `split_param='v'` 的框架中，因为数据需同时提供实际选择和决定哪个方向为正确方向的刺激/条件列。实现时应遵循所用软件的文档，而不要只凭“Response Coding”或“Stimulus Coding”这个标签判断模型是否一致（HDDM 文档：<https://github.com/hddm-devs/hddm/blob/master/docs/source/howto.rst>；<https://github.com/hddm-devs/hddm/blob/master/docs/source/tutorial_regression_stimcoding.rst>）。

### 3.2 方案 A 与方案 B 是否完全相同？

“实际选择编码”和“正确/错误编码”可以在正确变换 choice 标签、漂移方向与边界定义后，表达同一个潜在决策过程；在固定中点起点、没有反应偏向且所有参数约定一致时，预测的行为分布可以等价或非常接近。

但它们**不能在不进行转换的情况下直接混用**。尤其是，当模型允许固定的实际反应偏向（例如总是更偏向按 Match 键）时，仅用 correct/error 编码通常无法保持这种跨试次恒定的按键偏向。HDDM 文档也区分 accuracy coding 与 stimulus coding，并指出需要建模刺激类别/实际反应偏向时应使用相应的 stimulus-coding 结构。

**第一版实现选择：** 保留实际 choice 的含义（Match/Nonmatch），以 `correct_choice` 或与之等价的试次条件来决定 drift 符号；将起点固定在中点，不估计额外 response bias。生成器须输出全部映射字段，以便后续验证编码转换是否正确。

### 3.3 不将 Self 直接等同于某个边界

Self 相关优势是刺激/联结类别效应，而 Match/Nonmatch 是反应选择维度。不能把“Self”直接编码成上边界、“Other”编码成下边界。Self/Other 的影响首先体现在证据积累幅度 \(d\)（或其后续模型扩展）上；Match/Nonmatch 的正确反应决定 \(v\) 的方向符号。

---

## 4. P：练习次数对证据积累幅度的影响

### 4.1 第一版函数

不在没有理论依据时预先增加延迟参数。先定义标准指数饱和函数：

\[
\boxed{f_P(P)=1-\exp(-P/\tau_P)},\qquad \tau_P>0.
\]

其性质为：

\[
f_P(0)=0,\qquad \lim_{P\to\infty}f_P(P)=1.
\]

\(\tau_P\) 是学习收益趋近饱和的时间尺度，\(P\) 应使用练习次数的同一单位（例如 trial 次数）。

### 4.2 心理解释与限定

候选解释为：练习有助于强化形状—标签联结和提高相关信息提取效率，进而提高 SMT 决策中的证据积累幅度。该函数是用于表示“边际收益递减”的建模假设，并非已被证明的 SPE 普遍学习规律。

**P 的操作定义必须固定：** 第一版应明确 P 是测试前完成的联结学习/练习次数，还是测试阶段当前累计 trial 数。若 P 是实验设计因素（例如不同被试/组接受不同数量的前置练习），则同一被试的测试试次使用同一个 P 水平；不要在没有实验依据时把 P 误写成每个测试 trial 都自动增加的计数。

### 4.3 后续竞争模型

只有当理论或数据支持早期存在学习延迟时，才考虑：

\[
f_P(P;P_{\mathrm{delay}},\tau_P)=
1-\exp\left[-\frac{\max(P-P_{\mathrm{delay}},0)}{\tau_P}\right].
\]

标准指数函数作为主基线；延迟指数作为后续候选，而非默认主模型。

---

## 5. T：刺激呈现时间、感觉编码与 drift 的映射

### 5.1 第一层：归一化感觉编码函数

先定义一个随呈现时间增加而渐近的候选编码量：

\[
\boxed{Q_T(T)=1-\exp(-T/\tau_T)},\qquad \tau_T>0.
\]

\(Q_T\) 是潜在的、归一化的编码质量代理变量，范围为 0 到 1；它不是直接观测到的真实神经编码质量。T 应使用一致的时间单位，建议在 DDM 内部统一使用秒，输入的毫秒值在进入模型前转换。

### 5.2 第二层：编码质量映射到漂移幅度

候选映射为：

\[
\boxed{d(P,T)=d_0+\beta_P f_P(P)+\beta_T Q_T(T).}
\]

此式采用加性基线：P 与 T 分别贡献一部分证据积累效率。它并不宣称加法是 DDM 的普遍要求，而是选择一个较简单、可解释、可比较的起点。必须通过参数约束确保所有设计条件下 \(d(P,T)>0\)。

不再将任意常数（例如旧代码中的 `3`）解释为心理机制。除非能够给出明确理论定义，否则这种常数只能被视为数值缩放。由于 DDM 扩散尺度固定为 1，\(d_0,\beta_P,\beta_T\) 的范围应通过先验预测模拟来选择，而不是照搬旧 Notebook 的数值。

### 5.3 一项必须显式记录的近似：允许在呈现期间反应

本项目决定：从刺激出现时开始计时，且刺激呈现期间发生的有效按键也被记录；W 是从刺激 onset 开始到 response deadline 的总时长。

因此，若某个试次在 \(RT<T\) 已经作出反应，被试事实上尚未经历完整的计划呈现时长。简单地对该 trial 从决策开始到结束始终使用完整的 \(Q_T(T)\) 计算常数 drift，等价于假设“完整计划 T 所对应的编码质量可从决策过程开始时就生效”。如果被试事先并不知道该 trial 的 T，这种假设并非完全符合时间顺序。

为保持第一版模型可控，可先把常数 \(d(P,T)\) 作为**设计空间的简化基线模型**，但必须报告每个条件中 \(RT<T\) 的比例，并检查该比例是否足以影响结论。不要把这个简化隐去或描述成完整的在线视觉编码机制。

更具时间一致性的扩展是令编码质量随已经经过的刺激时间增长：

\[
Q(t;T)=1-\exp\left[-\frac{\min(t,T)}{\tau_T}\right],
\]

并使用例如：

\[
d(t;P,T)=d_0+\beta_P f_P(P)+\beta_T Q(t;T).
\]

此扩展假定视觉表征在 stimulus offset 后保持并继续支持决策；如果理论上认为刺激消失后不再提供同样的证据，应另行定义 offset 后的 drift/记忆表征机制。时间变化的 drift 需要匹配的生成与 likelihood 求解方法；不能一方面用该时间变化机制生成数据，另一方面用不匹配的恒定 drift WFPT 直接拟合而不说明近似。

**实现建议：** 在第一版先实现常数 drift 基线及其参数恢复；对 `RT < T` 进行诊断。若比例不小，或研究目标要求严格模拟刺激时程，应把时间变化的编码/drift 作为优先扩展，而不仅是可有可无的细节。

---

## 6. W：从 stimulus onset 起算的 response deadline

### 6.1 操作性定义与时间单位

\[
\boxed{W=\text{从刺激开始呈现到允许有效反应的最晚时间}}
\]

- 刺激呈现期间的有效按键必须记录。
- 有效响应条件为实际 RT 不晚于 W（例如定义为 \(RT\le W\)）。
- 必须满足实验设计的可行约束，例如 \(T<W\)，若计划刺激呈现必须在 deadline 前结束。
- RT、T、W 在模拟与拟合内部应统一换算为秒。
- 在标准 DDM 记法中，观测反应时 \(RT=s+t_0\)。因此决策过程的 deadline 为 \(W-t_0\)，须保证 \(W>t_0\)。动态边界的时间归一化应使用决策过程时间与有效决策时限，而不是机械地用观察 RT 与 W 混算。

### 6.2 W 的三个候选模型

为公平比较，所有候选模型均使用相同的 W 操作定义，并把 deadline 到期作为真实的反应截止事件处理。

#### W0：仅有外部 deadline 的固定边界对照（建议保留作诊断模型）

\[
a(W)=a_0.
\]

边界不随 W 改变，但试次在 W 到期时终止。因此 W 仍然通过响应截断/未响应概率影响观测结果。此模型可帮助区分“deadline 机械截断”与“被试策略随 W 改变”。

#### W1：静态指数边界（本项目的静态基线模型）

\[
\boxed{a_{\mathrm{stat}}(W)=A_{\min}
+(A_{\max}-A_{\min})[1-\exp(-W/\tau_a)]}
\]

其中 \(A_{\max}>A_{\min}>0\)，\(\tau_a>0\)。这表示被试在试次开始时根据已知/预期的整体期限采取不同程度的谨慎策略；试次内边界保持固定。

此模型将包括两个作用：W 决定静态决策谨慎程度，同时硬性 deadline 决定最迟允许的响应时间。两者分别表示适应性 response policy 与客观时间限制，并非同一个机制；通过 W0 对照可以检查是否需要额外的策略假设。

#### W2：动态、对称收缩边界（机制性竞争模型）

为避免只移动一个边界而无意中同时引入决策轴中心位移，第一版动态模型采用对称边界。定义有效决策时限 \(W_d=W-t_0>0\)，决策过程时间为 \(s\)：

\[
\boxed{
a_{\mathrm{dyn}}(s;W)=a_{\mathrm{floor}}+
(a_{\mathrm{start}}-a_{\mathrm{floor}})
\left[1-\left(\frac{s}{W_d}\right)^\Gamma\right]
}
\]

其中 \(0\le s\le W_d\)，\(a_{\mathrm{start}}>a_{\mathrm{floor}}>0\)，\(\Gamma>0\)。于是边界间距从 \(a_{\mathrm{start}}\) 逐渐下降至 deadline 附近的 \(a_{\mathrm{floor}}\)。

在中心化决策坐标中：

\[
L(s)=-a_{\mathrm{dyn}}(s;W)/2,\qquad
U(s)=+a_{\mathrm{dyn}}(s;W)/2.
\]

若无起点偏向，令初始位置为中心 0（等价于相对起点比例 z=0.5）。这一形式是一个候选的 deadline-related urgency/collapsing-boundary 模型，不是已证实的人类最优策略。时变边界可用数值方法处理；相关方法见 Zhang et al. (2014)。

**重要：** W2 的主要机制是 trial 内边界随剩余时间变化；W1 的主要机制是不同 deadline 条件决定 trial 开始时的静态边界。第一版不要同时给 W2 添加任意的 \(a_{\mathrm{start}}(W)\) 函数，否则可能同时拟合两种机制，使模型过于复杂、难以区分。

### 6.3 Deadline 与 timeout / omission 的处理

如果在截止时限内没有触及边界，应输出 `timeout = 1`，并记录 `choice = NA`、`accuracy = NA`、`RT = NA`（同时单独保存 deadline 信息）。不可重抽样直到得到有效反应，也不可把 timeout 自动视为错误选择。

对于固定边界模型，响应试次采用相应的 WFPT 选择条件密度；未响应试次的 likelihood 应包含截止时间之前未触及边界的概率（survival/no-response probability）。动态边界模型则需要对应的时变边界首次通过密度与 deadline survival probability。

这里所说的 timeout 处理是响应时限的统计处理，不等同于引入一个额外的、独立的心理 omission 生成机制。若未来导师要求独立建模 omissions，需要再增加明确的心理机制与竞争模型。

---

## 7. Self-Prioritization Effect 的模型化

### 7.1 不预先规定 SPE 必然来自单一参数

本项目先将 Self/Other 的加工优势作为待区分机制，而不是事先断言它只来自 \(v\)。SMT 的已有研究通过 DDM 分析发现，Self-prioritization 可表现为信息摄取/漂移率上的 stimulus bias；理论上也必须区分 stimulus bias（如何把刺激信息转化为证据）与 response bias（如何准备某种反应）。Golubickis et al. (2017) 是相关 SMT + HDDM 的直接参考。

第一版为了控制工作量，固定中心起点 \(z=0.5\)，不估计 Self-specific \(z\)。这样做是一种简化，不代表理论上否认 response bias 的可能性。若未来发现匹配按键本身的反应偏向明显，需重新评估这一限制。

### 7.2 将一般加工效率与 Self–Other 差异分开

令 \(S_i=1\) 表示 Self 联结，\(S_i=0\) 表示 Other/Stranger 联结；令 \(f_P(P)\) 与 \(Q_T(T)\) 如前定义。

建议以以下嵌套机制组织模拟：

**G0：P/T 只影响一般证据积累效率，Self–Other 差异不随 P/T 改变**

\[
d_i=d_0+\beta_Pf_P(P_i)+\beta_TQ_T(T_i)+\beta_SS_i.
\]

该式中的 \(\beta_S\) 形成恒定的 Self–Other 漂移幅度差异；P/T 对两种联结类别的主效应相同。

**G1：练习调节 SPE**

\[
d_i=d_0+\beta_Pf_P(P_i)+\beta_TQ_T(T_i)+\beta_SS_i
+\beta_{SP}S_i f_P(P_i).
\]

**G2：呈现时间调节 SPE**

\[
d_i=d_0+\beta_Pf_P(P_i)+\beta_TQ_T(T_i)+\beta_SS_i
+\beta_{ST}S_i Q_T(T_i).
\]

**G3：P 与 T 都调节 SPE**

\[
d_i=d_0+\beta_Pf_P(P_i)+\beta_TQ_T(T_i)+\beta_SS_i
+\beta_{SP}S_i f_P(P_i)+\beta_{ST}S_iQ_T(T_i).
\]

这些是候选结构，不应一次性默认 G3 正确。需要在所有实际设计条件下保证 \(d_i>0\)。由于 \(v_i=q_i d_i\)，Self/Other 对应的是漂移幅度的变化；Match/Nonmatch 正确反应类别决定漂移的符号。

### 7.3 Match/Nonmatch 也可能调节 SPE

已有 SMT 研究提示 Self-prioritization 的计算表现可能依赖于 Matching 与 Nonmatching 试次类型。因此上述 G0–G3 先视为简化主模型。如果要将论文结论用于完整 SMT，模型恢复阶段应至少评估“Self 效应是否在 Match 与 Nonmatch 试次相同”的可能性；但在基础生成模型阶段可以把它列为次级扩展，避免无必要地增加参数。

---

## 8. 生成算法的目标步骤

最终生成器应模块化，并能由配置切换候选机制。

1. **读取实验设计配置。** 明确 P 是被试间/区组层面条件还是试次层面变量；明确 T、W、Self/Other、Match/Nonmatch 的分配方式、平衡方法及随机化顺序。不要把每个被试随机抽到的固定 P/T/W 默认为正式实验设计。
2. **生成真实试次属性。** 包含 `subject_id`、`trial_id`、P、T、W、`association_type`、`match_status`、`correct_choice` 与实际反应映射。正确答案必须由设计规则确定，而不是根据模拟结果反推。
3. **计算潜在参数。** 根据指定 P/T 模型计算正值漂移幅度 \(d\)，再按正确反应方向生成有符号 \(v=q d\)；根据指定 W 模型设置固定边界或时变边界；将 \(z=0.5\)、\(t_0\) 等记录为真实参数。
4. **模拟首次通过。** 固定边界可使用经验证的 WFPT 采样法或路径模拟；动态边界需路径模拟或匹配的数值首次通过算法。若使用离散路径模拟，进行时间步长敏感性检查，避免遗漏穿越造成反应时偏差。
5. **应用 deadline。** 以 stimulus onset 作为 RT 零点；允许 T 期间按键；凡 RT 在 deadline 内的首次有效反应均记录。超时试次作为 timeout 保存，绝不重抽至有效。
6. **映射实际选择与准确率。** 边界决定选择方向；选择方向映射为 Match/Nonmatch；与 `correct_choice` 比较后得到 accuracy。
7. **输出观测数据和真值分开保存。** 拟合器只能使用观测数据与实验设计变量，不能读取真实参数列。
8. **写出复现信息。** 每次模拟保存随机种子、模型版本、参数配置、软件版本、时间步长/求解精度与生成日期。

---

## 9. 数据输出字段建议

### 9.1 观测试次文件 `simulated_trials.csv`

最低字段：

| 字段 | 含义 |
|---|---|
| `subject_id` | 被试编号 |
| `trial_id` | 试次编号 |
| `P` | 前置练习/学习次数 |
| `T_ms` | 计划刺激呈现时间，毫秒 |
| `W_ms` | 从刺激出现起算的反应截止时间，毫秒 |
| `association_type` | Self / Other（按实际实验需要细分） |
| `match_status` | Match / Nonmatch |
| `correct_choice` | 该试次正确反应类别 |
| `choice` | 实际选择；超时则缺失 |
| `RT_s` | 从刺激 onset 到反应的观测 RT，秒；超时缺失 |
| `accuracy` | 正确/错误；超时缺失 |
| `timeout` | 是否在 deadline 前未响应 |

按键映射（如 F/J 的左右含义）如有被试间/区组间 counterbalancing，应另外保存 `key_mapping`。即便当前不研究反应偏向，这一字段也有助于验证编码。

### 9.2 真值文件 `simulation_truth.csv` 或 `simulation_truth.json`

至少保存：

- 生成模型 ID 与配置；
- 群体真实参数：\(d_0,\beta_P,\beta_T,\beta_S,\beta_{SP},\beta_{ST},\tau_P,\tau_T\)；
- W 模型及相关参数：静态模型的 \(A_{\min},A_{\max},\tau_a\)，或动态模型的 \(a_{\mathrm{start}},a_{\mathrm{floor}},\Gamma\)；
- \(t_0\)、扩散尺度 \(\sigma\)；
- 若加入个体差异，保存被试层面真值；
- 随机种子与数值求解设置。

**真值文件只能用于参数恢复/模型恢复评分，不得作为拟合输入。**

---

## 10. 参数恢复、模型恢复和模型比较流程

### 10.1 先做先验预测 / 生成检查

在大规模生成前，检查所选参数范围能否产生合理的 RT、准确率和 timeout 比例。排除几乎全部正确/几乎随机作答、RT 大多超出时限或完全没有超时等极端设置，除非这些正是计划研究的边缘情形。

### 10.2 参数恢复（parameter recovery）

对每个候选生成模型：

1. 从一组已知真参数生成数据；
2. 使用将来真正打算采用的拟合器拟合；
3. 比较估计值与真值，报告偏差、RMSE、相关、credible interval coverage 以及收敛诊断；
4. 检查参数间的强相关或互相补偿，尤其包括 \(\tau_P,\tau_T,\tau_a,\Gamma\) 以及 Self-specific 效应。

参数不可恢复时，不应对真实数据拟合值作强机制解释（Wilson & Collins, 2019）。

### 10.3 模型恢复（model recovery）

分别用 G0/G1/G2/G3 和 W0/W1/W2 等候选模型生成模拟数据，再将每套数据拟合全部候选模型。制作 generating-model × selected-model 的 confusion matrix，评估当前 P/T/W 水平与试次数是否足以区分候选机制。

若指数与其他函数、静态与动态边界相互混淆，结论应是当前设计的区分能力不足，而不是强行声称某个模型是真实心理机制。

### 10.4 真实数据拟合

所有候选模型应使用同一清理规则、相同 trials、相同反应编码、相同 deadline 定义与可比的先验设置。优先考虑 trial-level 联合拟合 RT 与 choice，而不是只拟合平均 RT 或先对各条件均值回归再反推 DDM 参数。

### 10.5 绝对拟合检查

通过 posterior predictive checks 检查模型能否重现：

- Self/Other × Match/Nonmatch 条件下的准确率；
- 正确与错误反应的 RT 分布及多个分位数；
- RT 与 accuracy 的联合模式；
- 不同 P、T、W 条件的条件分布；
- timeout 比例；
- 外显 \(SPE_{RT}=RT_{Other}-RT_{Self}\) 与 \(SPE_{ACC}=ACC_{Self}-ACC_{Other}\)（需事先明确使用何种条件平均和符号约定）。

### 10.6 模型比较

在候选模型都通过收敛、恢复与绝对拟合检查后，再比较样本外预测能力，例如 PSIS-LOO / ELPD，并结合差异标准误与 Pareto-k 诊断。若多个模型预测表现差异不足以区分，应报告不确定性、优先简约模型，或采用模型平均；不要仅凭单一信息准则宣布模型为真。

### 10.7 设计空间优化

最终优化目标不应只是在某个最喜欢的生成模型下找一个设计。建议在确认的候选模型集合下，对每个 \(\Omega=(P,T,W,M)\) 评估：

- 关键参数的恢复误差与区间覆盖率；
- SPE 参数（如 \(\beta_S\)、\(\beta_{SP}\)、\(\beta_{ST}\)）的可识别性；
- 模型恢复正确率；
- timeout 与有效 trial 数量；
- 模型假设变化时最优设计是否稳定。

若合理模型之间不可区分，可考虑 model-averaged / robust design optimization，而不是仅针对一个模型优化。

---

## 11. 旧 Notebook 的继承与必须改变的部分

已上传的 `S2 gen_data_jh.ipynb` 使用 1 ms 步长逐步更新证据并检查固定的上下边界，可作为理解和原型验证的参考。但是正式生成器至少必须修正以下问题：

1. 旧实现对试次层面的 drift 添加了正态随机扰动，并对 boundary 添加噪声；第一版应先清晰区分群体参数、被试参数、试次随机过程噪声，不要在没有理论定义的情况下给每个参数加随机扰动。
2. 旧实现按 \(T+W\) 计算最大时间；新定义是 W 从 stimulus onset 起算，因此截止时间应使用 W，而不是 T+W。
3. 旧实现会丢弃超时试次并继续抽样直到收集够有效 trial；新模型必须保留 timeout。
4. 旧实现中的 `conditions`、`Label`、`response` 方向有不一致/注释混乱风险。新代码应明确分开 association type、match status、correct choice、observed choice。
5. 旧模型只有 Match/Other 相关条件的局部模拟，不足以直接作为完整 SMT 生成器。
6. 固定边界与动态边界必须用各自匹配的生成/拟合方法；不可用普通固定边界 WFPT likelihood 对动态边界数据作未经验证的拟合。

---

## 12. 当前确认内容与剩余技术风险

### 已初步确认

- **P：** 第一版采用标准指数饱和，不默认引入延迟指数。
- **T：** 先定义饱和编码质量函数，再映射到 drift；第一版以简单的常数 trial-level drift 映射作为基线，但必须诊断 RT<T 的比例，并清楚记录其时间顺序近似。
- **P/T → drift：** 第一版采用有解释的加性结构，不使用缺少理论依据的任意乘法放大系数。
- **W：** 定义为 stimulus onset 到 response deadline 的总时限；刺激呈现期间的响应有效。
- **W 模型：** 静态指数边界为主要基线；动态对称收缩边界为机制性竞争模型；建议保留纯固定边界 + deadline 的 W0 诊断模型。
- **起点：** 基础模型固定在中点，即标准相对起点比例 \(z=0.5\)；不先添加 Self-specific z 或独立 omission 机制。
- **SPE：** 把 Self/Other 与 Match/Nonmatch 分成不同因素；先区分一般加工效率与 Self-specific drift-magnitude 差异，不预设 P/T 一定会调节 SPE。

### 仍须在实现时明确

1. P 的实际实验分配层级（被试间、区组层面或 trial-by-trial 累计）必须与真实范式一致。
2. T 是否需要时间变化的 drift：若 RT<T 并不少见，完整的 \(Q_T(T)\) 常数映射只能作为简化基线；需要考虑实际已呈现时长决定的编码 build-up。
3. Deadline 下未响应 trial 的 likelihood 必须实现，不能只生成/拟合有反应的 trial。
4. 动态边界需要采用可验证的时变边界 solver/likelihood。可考察 PyDDM 等支持时变边界、时变 drift 的框架，但必须用模拟数据验证数值精度和参数恢复；工具是否直接支持本项目的所有条件回归与 censoring 需求，需在实现前核查（PyDDM 文档：https://pyddm.readthedocs.io/en/latest/cookbook/bounds.html）。
5. 第一版是否纳入被试间随机效应应作为配置项。最简单的同质被试生成可用于单元测试，但最终参数恢复应包含与真实研究相称的个体差异压力测试。
6. 如果模型比较的目标是 Self advantage 在 Match 与 Nonmatch 试次是否不同，需将该问题加入模型恢复集合；不要仅凭总体 RT 差异判断。

---

## 13. 参考文献与技术资源

1. **Golubickis, M., Falben, J. K., Sahraie, A., Visokomogilski, A., Cunningham, W. A., Sui, J., et al. (2017).** Self-prioritization and perceptual matching: The effects of temporal construal. *Memory & Cognition, 45*, 1223–1239. https://doi.org/10.3758/s13421-017-0722-3  
   与 SMT/shape-label matching + HDDM 直接相关；讨论 stimulus bias / response bias 以及 drift-rate 的含义。

2. **Sui, J., He, X., & Humphreys, G. W. (2012).** Perceptual effects of social salience: Evidence from self-prioritization effects on perceptual matching. *Journal of Experimental Psychology: Human Perception and Performance, 38*(5), 1105–1117. https://doi.org/10.1037/a0029792  
   SMT 与 Self-Prioritization Effect 的经典来源。

3. **Ratcliff, R., & McKoon, G. (2008).** The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation, 20*(4), 873–922. https://doi.org/10.1162/neco.2008.12-06-420  
   DDM 的理论、参数含义及 RT/准确率联合建模基础。

4. **Navarro, D. J., & Fuss, I. G. (2009).** Fast and accurate calculations for first-passage times in Wiener diffusion models. *Journal of Mathematical Psychology, 53*(4), 222–230. https://doi.org/10.1016/j.jmp.2009.02.003  
   标准 Wiener diffusion 模型首次通过时间密度的高效计算方法。

5. **Wiecki, T. V., Sofer, I., & Frank, M. J. (2013).** HDDM: Hierarchical Bayesian estimation of the Drift-Diffusion Model in Python. *Frontiers in Neuroinformatics, 7*, 14. https://doi.org/10.3389/fninf.2013.00014  
   HDDM 的层级 Bayesian 估计框架。

6. **Zhang, S., Lee, M. D., Vandekerckhove, J., Maris, G., & Wagenmakers, E.-J. (2014).** Time-varying boundaries for diffusion models of decision making and response time. *Frontiers in Psychology, 5*, 1364. https://doi.org/10.3389/fpsyg.2014.01364  
   时变/收缩边界以及相关数值方法的理论与计算参考。

7. **Wilson, R. C., & Collins, A. G. E. (2019).** Ten simple rules for the computational modeling of behavioral data. *eLife, 8*, e49547. https://doi.org/10.7554/eLife.49547  
   参数恢复、模型恢复、绝对拟合和计算建模工作流。

8. **HDDM documentation — Coding responses / stimulus coding.** https://github.com/hddm-devs/hddm/blob/master/docs/source/howto.rst  
   区分 accuracy coding 与 stimulus coding，说明实际 response、stimulus/correct-response 列和起点偏向如何对应。

9. **HDDM documentation — Regression with stimulus coding.** https://github.com/hddm-devs/hddm/blob/master/docs/source/tutorial_regression_stimcoding.rst  
   `split_param='v'` 与 `split_param='z'` 的实现示例和模型恢复示例。

10. **PyDDM documentation — Recipes for collapsing bounds.** https://pyddm.readthedocs.io/en/latest/cookbook/bounds.html  
    动态边界的可实现形式、边界依赖条件/时间的示例。实际使用前需核对所用版本、solver 与 fitting API。

---

## 14. 交给后续 AI 的执行要求（简版）

请按本文作为理论与初始规格，先完成一版**可测试、可复现、模块化**的模拟代码，而不是直接追求最大复杂度：

1. 先实现固定 \(z=0.5\)、\(\sigma=1\)、固定 \(t_0\) 的二选择 DDM 单元模拟，并验证固定边界生成分布。
2. 实现实际 choice（Match/Nonmatch）与正确反应条件决定 drift 符号的编码；单元测试必须检查两种 correct-choice 试次的正确反应概率与方向。
3. 加入标准指数 \(f_P(P)\) 与 \(Q_T(T)\)，并实现 G0 基础 drift 幅度模型。
4. 实现 W0、W1、W2 中计划用于恢复的模型；所有模型均应用同样的 deadline 与 timeout 规则。
5. 生成器输出观测数据、独立真值文件和模拟 manifest。
6. 先做小样本 smoke test、边界/RT/timeout 诊断与固定边界 WFPT 对照；再做参数恢复、模型恢复；最后才扩大模拟量。
7. 对动态边界和可能的时间变化 drift，不可使用未经验证的固定边界恒定 drift likelihood；应明确选用并验证相匹配的数值求解方法。
8. 用配置文件或函数参数控制样本量、每人试次数、设计因子水平、生成机制、随机种子、时间步长/solver 精度，避免把当前示例水平硬编码为唯一设计。
9. 把无法确定的实现前提记录为 TODO，并说明选择的近似及其后果，绝不默默替研究者决定。

**核心目标不是证明某个函数一定正确，而是建立一套能够生成已知真值数据、检验参数/模型是否可恢复、并最终判断 \(\Omega\) 设计是否足以识别目标心理机制的可验证工作流。**
