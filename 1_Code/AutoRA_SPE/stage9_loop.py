#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 9 优化循环：有限候选集 + 共享 CRN 评估缓存 + 四路消融。

设计依据：``5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md``
          §4（设计变量与约束）、§5.3.1(3)（CRN 预计算表）、§6（冻结 Objective）、
          §7（优化器）、§8（四路消融与判据）、§11 第 16 条（**决策 D54**）。

三条不可让渡的性质
------------------
1. **CRN（共同随机数）**：每个候选设计有一个**由设计内容（名字的 sha256 前 12 位）导出**
   的 `inner_eval` 种子（``cell_seed``），与"哪个臂选了它"、与它在候选表的**下标**都无关。
   于是四个臂看到的是同一份噪声实现 ⇒ 臂间比较是**配对**的，不是两次独立抽样之差；
   候选表被截断/过滤/重排也不会让同一设计换种子。
   （依据 `1_Code/AutoRA_SPE/README.md` §6 处方④；200 次重复下覆盖率 SE ≈ 1.5%。）
2. **内环退化为查表**：``Evaluator`` 把每个设计评估一次并缓存；优化器再遇到同一个
   设计时**不再重算**（依据同一处处方⑤）。
3. **优化器看不见噪声**：臂的选择函数只允许读缓存里已有的 `(A, B, J)` 与
   设计的**结构特征**；不允许读 `se`/`n_bad`/`cond` 等内环细节来做选择
   （``features()`` 只返回设计本身的坐标）。否则"消融"会退化成"用真值作弊"。

**D54（本轮）：判据只建立在 (A)/(B) 上，遗漏率罚分改为可行域约束**
--------------------------------------------------------------
标量 `J` 的 MC 噪声有 **95–101%** 来自 (C) 这条二次罚分（D4 附近 `dC/d(omission) ≈ 125`），
而加大 `n_fim` 救不回来（遗漏率不按 `1/sqrt(n_fim)` 收敛）⇒ 用 `J` 给臂排序等于用噪声排序。
因此：``OMISSION_BAND`` 之外的设计**直接移出可行集**（`feasible = False`），
``compare_arms`` 只比较 **(A) 最小点**上的 `(A, B)`，且差异必须超过 `2·sd_A` / `2·sd_B`。
`J` 仍然照算（它冻结在 `SPEC_SHA256` 里），但**只作参考数列出，不进判据**。

⚠️ 本模块**不含任何仿真器**：所有时序与似然都走
   ``1_Code/DDM_Core/{simulate,twophase,likelihood}.py`` 与 ``stage9_inner``。
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
_DDM = _HERE.parent / "DDM_Core"
for _p in (str(_HERE), str(_DDM)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from spe_timing_convention import (MASK_MS, assert_current_design,  # noqa: E402
                                   current_postmask_pressable_ms)
import stage9_inner as S9I                                       # noqa: E402
import stage9_objective as S9O                                   # noqa: E402


# ==================================================================
# 1. 候选设计空间
# ==================================================================
# 总试次固定为 576（D4 定稿值），且程序每轮呈现 4 类刺激（is_self × is_match）
TRIALS_TOTAL = 576
UNIT_PER_CELL = 4
# ⇒ len(T) * len(W) * n_rep 必须等于 144。这是**耦合**：多一个 T 水平就得少重复。
CELL_BUDGET = TRIALS_TOTAL // UNIT_PER_CELL                      # = 144

# 名义水平取自 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` L219–L220 的
# 帧量化口径（T = 2/5/9/15 帧，W = 48/72/108 帧），再各向后延伸两档/一档。
# ⚠️ 必须是**程序能实现的名义值**：程序按 `round(x/FlipIntv)*FlipIntv` 取帧。
T_POOL_MS = (33.33, 83.33, 149.99, 249.98, 349.99, 449.98)      # 2/5/9/15/21/27 帧
W_POOL_MS = (799.98, 1199.9, 1799.9, 2399.8)                     # 48/72/108/144 帧
N_T_CHOICES = (3, 4, 6)
N_W_CHOICES = (2, 3)

# 程序 L250–L256 的两条物理约束（**必须逐格成立**）：
#   C1: W > T + 200 ms         （掩蔽段不能被反应窗口截断）
#   C3: W − T − 200 ms ≥ 300 ms（否则该单元接近全遗漏）
# ⚠️ 掩蔽时长只有一处事实来源：`spe_timing_convention.MASK_MS`
#    （它又转发 `spe_design_model.MASK_MS`），此处**不重新定义一个 200**。
MIN_POSTMASK_MS = 300.0

# ---------------------------------------------------------------- D54
# 「遗漏率罚分」从**加权项**改为**可行域约束**（决策 D54；依据见
# `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §11 第 16 条）：
# 标量 `J` 的 MC 噪声有 95–101% 来自 (C) 这条二次罚分（D4 附近 `dC/d(omission) ≈ 125`），
# 而加大 `n_fim` 救不回来（遗漏率不按 `1/sqrt(n_fim)` 收敛）。
# 带值与**冻结 Objective 同源**（一处事实来源）；改 `FROZEN` 会改哈希，而"重新冻结"
# 必须是一次显式、单独验证的变更 ⇒ 本轮**不重新冻结**，改由**搜索层**把带当约束执行。
OMISSION_BAND = tuple(float(v) for v in S9O.FROZEN["omission_band"])
# 四路消融的判据只建立在 (A)/(B) 上（科学信号，其 MC 噪声比 `J` 小两个数量级）。
CRITERION = ("A", "B")
# 落盘件必须自报「这批裁决文本由哪一版规则生成」。裁决逻辑已经改过三代：
#   D55 之前：`ΔA` 超带却借 `ΔB` 的带子 → 把 BO 差 32% 印成「不可分辨」（洗白）；
#   D55–D58：分「在 (A) 上显著更差」，但 `ΔA` 在带内时仍借 `ΔB` 的带子下结论；
#   D59 起：两根带子**各判各的**，`ΔA` 在带内**不等于**「两者不可分辨」。
# 报告只**逐字转印** payload 里的 `compare[*].verdict`（不重算）⇒ 不记录版本号，
# 读者无法判断手上这份文本该不该信（D59 的第四条同族缺陷）。
VERDICT_LOGIC = ("D60：两根带子各判各的；带宽 = **差**的噪声带 `2·√2·sd`（不是单设计的 `2·sd`）；"
                 "`ΔA` 在带内不得借 `ΔB` 的带子定论")
# ❗ D60：判据带宽是「**两个设计的差**」的噪声带，不是「单个设计读数」的噪声带。
# `measure_noise` 量的是**同一个设计**（锚点）在不同种子下的 `sd`；而 `compare_arms`
# 比的是两条臂各自选中的**不同设计**，它们的 CRN 种子由名字哈希导出 ⇒ **独立** ⇒
# 差的方差 = 2·sd² ⇒ 系数必须是 `2·√2`，用 `2·sd` 会把差的噪声低估 √2 ≈ 1.41 倍
# （偏宽松 ⇒ 更容易宣称「显著 / 最好」，与本文件要防的洗白同族）。
# 附带两条**未解决的**限制（写在这里以免被读者当成已处理）：
#   ① 同方差假设：σ 只在锚点处量过，病态候选（`cond ~ 1e15`、`n_bad = 1`）的
#      `(A)` 波动可能更大 ⇒ `√2·sd_锚点` 仍可能**低估**这些设计的噪声；
#   ② 选择偏差：`A_best` 是「该臂抽到的 N 个点里最小的那个」，是极值统计量
#      （budget 12 时约为 `σ·E[min of 12] ≈ 1.6σ` 的向下偏），而两条臂找到的
#      可行点数不同 ⇒ 偏差不同。带宽挡不住偏，只能靠同时报 `n_feasible` 让读者看见。
DIFF_BAND_FACTOR = 2.0 * float(np.sqrt(2.0))


def check_design(T_ms, W_ms) -> None:
    """逐格检查 C1/C3；不通过抛 ``ValueError``（不静默丢弃，由调用方决定）。

    ⚠️ 桥模块的 `assert_current_design` 收的是**毫秒**（与程序源码一致），
       而内环 `inner_eval` 收的是**秒** —— 单位换算只在这两个入口发生。
    """
    assert_current_design(float(T_ms), float(W_ms))                  # C1（毫秒）
    u_ms = current_postmask_pressable_ms(float(T_ms), float(W_ms))
    if u_ms < MIN_POSTMASK_MS:
        raise ValueError(f"C3 违反：W−T−200 = {u_ms:.2f} ms < {MIN_POSTMASK_MS:.0f} ms"
                         f"（T={T_ms:.2f} ms、W={W_ms:.2f} ms）")


def postmask_s(T_ms, W_ms) -> float:
    """真正可按键时长（**秒**）—— 即方案 §4 改坐标后的 ``u``。"""
    return current_postmask_pressable_ms(float(T_ms), float(W_ms)) / 1000.0


def design_name(T_ms, W_ms, n_rep: int) -> str:
    tf = "/".join(f"{t:.2f}" for t in T_ms)
    wf = "/".join(f"{w:.2f}" for w in W_ms)
    return f"T[{tf}]ms x W[{wf}]ms x r{n_rep}"


def enumerate_designs(verbose: bool = False) -> list[dict]:
    """枚举有限候选集（含可行性过滤）。

    返回按**字典序**排列的列表（顺序是确定的，四路消融共用同一个顺序）。
    """
    out: list[dict] = []
    n_rejected = 0
    for n_t in N_T_CHOICES:
        for n_w in N_W_CHOICES:
            if CELL_BUDGET % (n_t * n_w) != 0:
                continue
            n_rep = CELL_BUDGET // (n_t * n_w)
            for Ts in itertools.combinations(T_POOL_MS, n_t):
                for Ws in itertools.combinations(W_POOL_MS, n_w):
                    try:
                        for T in Ts:
                            for W in Ws:
                                check_design(T, W)
                    except ValueError:
                        n_rejected += 1
                        continue
                    out.append({
                        "name": design_name(Ts, Ws, n_rep),
                        "T_ms": tuple(float(x) for x in Ts),
                        "W_ms": tuple(float(x) for x in Ws),
                        "n_rep": int(n_rep),
                        "n_trials": int(n_t * n_w * UNIT_PER_CELL * n_rep),
                    })
    if verbose:
        print(f"候选设计空间：{len(out)} 个可行设计"
              f"（另有 {n_rejected} 个被 C1/C3 否决）")
    return out


ANCHOR_DESIGN = "T[33.33/83.33/149.99/249.98]ms x W[799.98/1199.90/1799.90]ms x r12"


def cell_seed(name: str, base_seed: int = 0) -> int:
    """候选设计的 CRN 种子。

    ❗ 由**设计本身的名字**（即它的结构）导出，**不是**由它在候选表里的下标导出。
    下标导出有一个隐藏耦合：候选表一改（截断、过滤、重排），同一个设计就换了种子，
    于是"CRN"跨版本失效，而**没有任何报错**。按内容导出则设计↔种子一一对应。
    """
    h = int(hashlib.sha256(str(name).encode("utf-8")).hexdigest()[:12], 16)
    return int((int(base_seed) + h) % (2 ** 32))


def levels_sec(levels_ms) -> tuple:
    """毫秒水平 → 秒水平。

    ❗ **单位只在这一个地方换算**。候选表里的 `T_ms` / `W_ms` 是**毫秒**
    （因为要与 `Exp_Design_Formal.m` 的 `T_nominal`/`W_nominal` 和桥模块的
    `assert_current_design(T_ms, W_ms)` 对齐），而内环 `inner_eval` 收**秒**。
    忘记换一次，内环就会在"T = 33 秒、W = 800 秒"下模拟 —— 遗漏率变成 0、
    信息矩阵变成垃圾，而**没有任何报错**（本文件的第一次冒烟就是这样翻车的）。
    """
    return tuple(float(x) / 1000.0 for x in levels_ms)


# ==================================================================
# 2. 共享 CRN 评估缓存
# ==================================================================
class Evaluator:
    """把 ``inner_eval`` + 冻结 Objective 包成一个**只算一次**的查表器。

    优化器只能通过 ``get()`` / ``value()`` 读结果；``features()`` 只暴露设计坐标。
    """

    def __init__(self, designs: list[dict], *, rho: float | None = None,
                 n_fim: int = 1, n_subjects: int = 40, P: float | None = None,
                 param_set: str = "exp", base_seed: int = 0,
                 anchor_name: str = ANCHOR_DESIGN, verbose: bool = True):
        self.designs = list(designs)
        self.index = {d["name"]: i for i, d in enumerate(self.designs)}
        self.rho = float(S9O.FROZEN["rho_mu"] if rho is None else rho)
        self.n_fim = int(n_fim)
        self.n_subjects = int(n_subjects)
        self.P = P
        self.param_set = param_set
        self.base_seed = int(base_seed)
        self.anchor_name = anchor_name
        self.verbose = verbose
        self.cache: dict[str, dict] = {}
        self.anchor: dict | None = None
        self.seconds = 0.0
        self.n_evals = 0

    # ---- 单个设计的原始内环评估（不含 Objective）----
    def _raw(self, d: dict) -> dict:
        t0 = time.time()
        res = S9I.inner_eval(levels_sec(d["T_ms"]), levels_sec(d["W_ms"]), d["n_rep"],
                             model=S9I.M_T1, rho=self.rho, n_fim=self.n_fim,
                             seed=cell_seed(d["name"], self.base_seed),
                             param_set=self.param_set, P=self.P)
        dt = time.time() - t0
        self.seconds += dt
        self.n_evals += 1
        if self.verbose:
            print(f"  [eval #{self.n_evals}] r{d['n_rep']} "
                  f"T={len(d['T_ms'])}档 W={len(d['W_ms'])}档  {dt:.1f}s", flush=True)
        return res

    def _anchor_of(self) -> dict:
        """锚点设计的 ``(A, B)``。

        ❗ **不能用 `self.get(anchor_name)`** —— `get()` 自己需要 anchor，
        那会无限递归。这里直接走 `_raw`（同一个种子、同一份 CRN 抽样），
        再用与 `evaluate()` **相同的两个分量函数**算 `(A, B)`。
        """
        if self.anchor is None:
            if self.anchor_name not in self.index:
                raise KeyError(f"锚点设计 {self.anchor_name!r} 不在候选集里 —— "
                               "Objective 的 (A,B) 归一化要求锚点由同一个内环评估器算出")
            res = self._raw(self.designs[self.index[self.anchor_name]])
            self.anchor = {
                "A": S9O.component_A(res),
                "B": S9O.component_B(float(res["se_rho"]), self.n_subjects),
            }
            self.cache[self.anchor_name] = self._objective_record(self.anchor_name, res)
            if self.verbose:
                print(f"  锚点 {self.anchor_name!r}：A={self.anchor['A']:.4f} "
                      f"B={self.anchor['B']:.4f}", flush=True)
        return self.anchor

    def _objective_record(self, name: str, res: dict) -> dict:
        """把一次内环评估折算成缓存条目（**唯一的折算入口**）。"""
        d = self.designs[self.index[name]]
        rec: dict = {"name": name, "index": self.index[name],
                     "T_ms": d["T_ms"], "W_ms": d["W_ms"], "n_rep": d["n_rep"],
                     "n_trials": d["n_trials"],
                     "seed": cell_seed(name, self.base_seed),
                     "model": S9I.M_T1, "rho": self.rho, "n_fim": self.n_fim,
                     "P": self.P}
        rec.update({k: res[k] for k in
                    ("se", "se_rho", "se_sd", "cond", "n_bad", "omission", "acc",
                     "rt_ms", "relative_se", "param_names", "n_trials")})
        rec["relative_se"] = [float(v) for v in rec["relative_se"]]
        try:
            ev = S9O.evaluate(res, self.n_subjects, self._anchor_of())
        except ValueError as exc:                       # Objective 拒绝该评估
            rec.update({"feasible": False, "gates": [f"Objective 拒绝：{exc}"],
                        "A": float("nan"), "B": float("nan"), "C": float("nan"),
                        "J": float("inf")})
            return rec
        rec.update({k: ev[k] for k in
                    ("A", "B", "C", "J", "A_norm", "B_norm", "A_verdict",
                     "feasible", "gates")})
        # ---- D54：把 (C) 从"陡峭二次罚分"改成**可行域约束** ----
        # 罚分仍然算（它冻结在哈希里），但它**不再进入判据**：遗漏率落在冻结带之外的
        # 设计直接从可行集里移出，而不是拿一个被放大的标量去排名次。
        om = float(rec["omission"])
        lo, hi = OMISSION_BAND
        if not (lo <= om <= hi):
            rec["feasible"] = False
            rec["gates"] = list(rec["gates"]) + [
                f"D54 约束：遗漏率 {om:.4f} 落在冻结带 [{lo:g}, {hi:g}] 之外"
                f"（罚分改为约束，不进可行集）"]
        rec["omission_band"] = [lo, hi]
        return rec

    # ---- 带 Objective 的缓存读取 ----
    def get(self, name: str) -> dict:
        if name in self.cache:
            return self.cache[name]
        d = self.designs[self.index[name]]
        try:
            for T in d["T_ms"]:
                for W in d["W_ms"]:
                    check_design(T, W)
        except ValueError as exc:
            self.cache[name] = {
                "name": name, "index": self.index[name],
                "T_ms": d["T_ms"], "W_ms": d["W_ms"], "n_rep": d["n_rep"],
                "n_trials": d["n_trials"],
                "seed": cell_seed(name, self.base_seed),
                "model": S9I.M_T1, "rho": self.rho, "n_fim": self.n_fim,
                "P": self.P, "feasible": False,
                "gates": [f"设计本身不可行：{exc}"],
                "A": float("nan"), "B": float("nan"), "C": float("nan"),
                "J": float("inf")}
            return self.cache[name]
        self.cache[name] = self._objective_record(name, self._raw(d))
        return self.cache[name]

    def value(self, name: str) -> float:
        """优化器唯一允许看的标量（不可行 ⇒ ``+inf``）。"""
        r = self.get(name)
        return float(r["J"]) if r["feasible"] else float("inf")

    def features(self, name: str) -> np.ndarray:
        """设计的**结构特征**（不含任何内环读数，防止用真值作弊）。"""
        d = self.designs[self.index[name]]
        T = np.asarray(d["T_ms"]) / 1000.0
        u = np.asarray([postmask_s(t, w) for t in d["T_ms"] for w in d["W_ms"]])
        return np.array([T.mean(), T.max() - T.min(),
                         u.mean(), u.max() - u.min(),
                         np.log2(float(d["n_rep"]))], dtype=float)

    def feasible_names(self) -> list[str]:
        """可行集 = Objective 的四道闸门 + **D54 的遗漏率带**都通过的设计。"""
        return [n for n in self.index if self.value(n) < np.inf]

    def best(self, key: str = "J") -> tuple[str, dict]:
        """可行集内按 `key` 取最优。

        - `key="J"`（默认，历史口径）：标量 `J` 最小 —— ⚠️ D54 之后它**受 (C) 支配**，
          只作参考，不作推荐；
        - `key="A"`：**(A) 最小（B 大者优先打破并列）** —— 这是 D54 之后的**推荐点**。
        """
        feas = [(n, r) for n, r in self.cache.items() if r["feasible"]]
        if not feas:
            raise RuntimeError("缓存里没有任何可行设计")
        if key == "A":
            return min(feas, key=lambda kv: (float(kv[1]["A"]), -float(kv[1]["B"])))
        if key != "J":
            raise ValueError(f"best(key=...) 只接受 'J' 或 'A'，收到 {key!r}")
        return min(feas, key=lambda kv: float(kv[1]["J"]))


# ==================================================================
# 3. 四路选择策略（同样的预算、同样的候选集、同样的 CRN）
# ==================================================================
def arm_grid(ev: Evaluator, budget: int, rng=None) -> list[str]:
    """网格臂：在候选表上做**空间填充**的等距扫掠（无信息的选择）。

    ❗ **不能取"候选表的前 N 个"** —— 候选表的顺序是按 (n_t, n_w, 水平组合)
    字典序排的，前 N 个全部落在同一个角落（实测：前 6 个都是
    `r24 / T=3 档 / W=2 档`，即"最短 T + 最短 W"，**全部不可行**）。
    那样得到的不是"网格搜索"，而是一个**有偏的角落样本**，四个臂就不是同题竞赛了。
    """
    names = [d["name"] for d in ev.designs]
    n = len(names)
    if budget >= n:
        return list(names)
    idx = np.unique(np.round(np.linspace(0.0, n - 1.0, budget)).astype(int))
    out = [names[i] for i in idx]
    j = 0
    while len(out) < budget and j < n:                   # linspace 可能取重
        if names[j] not in out:
            out.append(names[j])
        j += 1
    return out[:budget]


def arm_random(ev: Evaluator, budget: int, rng: np.random.Generator) -> list[str]:
    """随机臂：均匀随机不放回。"""
    names = [d["name"] for d in ev.designs]
    perm = rng.permutation(len(names))
    return [names[i] for i in perm[:budget]]


def arm_manual(ev: Evaluator, budget: int, rng=None) -> list[str]:
    """人工补点臂：Stage 4 手挑设计（D4 / D4-3T / D4-rep16 / W-wide / T-wide）
    的**对应候选**优先，其余按网格顺序补足。

    为什么必须有人工臂：`README.md` §6 处方⑥ —— "GP 必须自己证明配得上"。
    人工先验是 GP 的**竞争者**，不是它的初始化。
    """
    picked: list[str] = []
    for d in ev.designs:
        n_t, n_w, r = len(d["T_ms"]), len(d["W_ms"]), d["n_rep"]
        is_d4 = (n_t == 4 and n_w == 3 and r == 12
                 and d["T_ms"] == T_POOL_MS[:4] and d["W_ms"] == W_POOL_MS[:3])
        is_3t = (n_t == 3 and n_w == 3 and r == 16)
        is_r16 = (n_t == 4 and n_w == 3 and r == 16)
        is_wide_w = (n_w == 2 and d["W_ms"] == (W_POOL_MS[0], W_POOL_MS[-1]))
        is_wide_t = (n_t == 6 and n_w == 2
                     and d["W_ms"] == W_POOL_MS[1:3])
        if is_d4 or is_3t or is_r16 or is_wide_w or is_wide_t:
            picked.append(d["name"])
        if len(picked) >= budget:
            return picked[:budget]
    for d in ev.designs:                                 # 不足则按网格顺序补
        if len(picked) >= budget:
            break
        if d["name"] not in picked:
            picked.append(d["name"])
    return picked


def arm_bo(ev: Evaluator, budget: int, rng: np.random.Generator,
           n_init: int = 8) -> list[str]:
    """贝叶斯优化臂：GP（Matérn 5/2）拟合 ``J`` + 自实现 EI 采集。

    ``alpha`` 由**实测**的 MC 噪声给出（``noise_alpha``），不是拍脑袋的 1e-6 ——
    这是方案 §7 点名"最容易做错的一处"。
    """
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, ConstantKernel
    from scipy.stats import norm

    # ❗ 预算必须**逐字相等**：`n_init` 若大于预算，这个臂就会超支
    #    （首版实测：预算 6、`n_init=8` ⇒ 实际评估 8 个 ⇒ 四臂不同题）。
    # ❗ 下限必须是 **1**，不能是 2：`--budget 1` 时 `max(2, 1) = 2 > 1` ⇒ 本臂评估 2 个、
    #    触发 `run_arms` 的「四路消融必须同预算」守卫并**中断整轮**（2026-10-16 实测：
    #    `--budget 1 --n-fim 12` 跑到臂 bo 时 `RuntimeError: 臂 bo 用了 2 次评估，预算 1`）。
    #    守卫本身是对的（它拦住的是超支），错的是这里把下限写成了 2。
    n_init = max(1, min(int(n_init), int(budget)))
    # 预算 ≤ n_init ⇒ `while` 循环一次都不进 ⇒ GP **从未拟合**，本臂等价于随机采样。
    # 这在小预算下是必然的（BO 需要「初始点 + 至少一步」），必须说出来，否则读者会把
    # 「bo 与 random 在此预算下差不多」当成「BO 没用」的证据。
    if n_init >= budget:
        print(f"  [臂 bo] ⚠️ 预算 {budget} ≤ n_init {n_init}：GP 不会拟合，"
              f"本臂退化为**随机采样**，其读数**不能作为 BO 的证据**", flush=True)
    all_names = [d["name"] for d in ev.designs]
    X_all = np.vstack([ev.features(n) for n in all_names])
    lo, hi = X_all.min(axis=0), X_all.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)

    def norm_x(names):
        X = np.vstack([ev.features(n) for n in names])
        return (X - lo) / span

    order = list(rng.permutation(len(all_names))[:n_init])
    picked = [all_names[i] for i in order]
    for n in picked:
        ev.get(n)

    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        length_scale=np.ones(X_all.shape[1]), length_scale_bounds=(1e-2, 1e2), nu=2.5)
    while len(picked) < budget:
        X = norm_x(picked)
        y = np.array([ev.value(n) for n in picked])
        ok = np.isfinite(y)
        if ok.sum() < 2:                                  # 全是 inf
            rest = [n for n in all_names if n not in picked]
            picked.append(rest[0])
            continue
        gp = GaussianProcessRegressor(kernel=kernel, alpha=float(ev.noise_alpha),
                                      normalize_y=True,
                                      n_restarts_optimizer=1, random_state=0)
        gp.fit(X[ok], y[ok])
        cand = [n for n in all_names if n not in picked]
        mu, sd = gp.predict(norm_x(cand), return_std=True)
        best = float(y[ok].min())
        z = (best - mu) / np.maximum(sd, 1e-12)           # 越小越好 ⇒ 取负号
        ei = (best - mu) * norm.cdf(z) + sd * norm.pdf(z)
        pick = cand[int(np.argmax(ei))]
        picked.append(pick)
        ev.get(pick)                                      # 计入预算（评估一次）
    return picked


ARMS = {"grid": arm_grid, "random": arm_random, "manual": arm_manual, "bo": arm_bo}
ARM_ORDER = ("grid", "random", "manual", "bo")


# ==================================================================
# 4. 噪声标定与运行
# ==================================================================
def measure_noise(ev: Evaluator, n_repeats: int = 3) -> dict:
    """直接量 ``J`` 的 MC 噪声（方案 §7 要求 ``alpha`` 来自实测）。

    做法：把锚点设计在**不同种子**下重算 ``n_repeats`` 次，取 ``J`` 的标准差。
    这**不改动** CRN：CRN 只要求"同一个设计在臂间用同一个种子"，
    而噪声标定是一次独立的、显式声明的诊断。

    ❗ **D59：标定种子必须是与设计种子同分布、但彼此独立的抽样。**
    旧写法用 ``cell_seed(name, base + 791_900 + 37k)`` —— 这 6 个种子是**同一个
    哈希值加小偏移**，即一族**算术邻居**。实测（`_scratch_anchor_seed_scan.py`，
    `n_fim = 1`、锚点 D4）：

    * 这一族 6 个种子的 ``sd_A = 0.004779``；
    * 48 个**无关**种子的 ``sd_A = 0.018933``（**4.0 倍**）；
    * 另一族**同样是算术邻居**的种子（``base + 4_000_000 + 37k``）给出
      ``sd_A = 0.015623``（0.83 倍）⇒ **不是"邻居种子相关"**，而是那一族恰好
      抽在分布的密集区（6 个样本估 ``sd`` 本就有约 32% 的相对不确定度，
      而 ``A`` 的种子分布是**重尾**的：48 个读数的极差 0.092 = 4.9 个 ``sd``）。

    带宽 ``2·sd_A`` / ``2·sd_B`` 与 ``alpha = sd_J²``（BO 的探索尺度）全建立在
    这个估计上 ⇒ 用下面这种"把标定当成**另一个设计**来做"的种子：名字不同 ⇒
    哈希不同 ⇒ 与任意设计种子同分布且独立。
    """
    if ev.anchor_name not in ev.index:
        raise KeyError("噪声标定需要锚点设计在候选集里")
    d = ev.designs[ev.index[ev.anchor_name]]
    js, a_s, b_s, om_s, c_s, seeds_used = [], [], [], [], [], []
    for k in range(int(n_repeats)):
        seed = cell_seed(f"{d['name']}#noise{k}", ev.base_seed)
        seeds_used.append(int(seed))
        res = S9I.inner_eval(levels_sec(d["T_ms"]), levels_sec(d["W_ms"]), d["n_rep"],
                             model=S9I.M_T1,
                             rho=ev.rho, n_fim=ev.n_fim, seed=seed,
                             param_set=ev.param_set, P=ev.P)
        ev.n_evals += 1
        ev.seconds += 0.0
        anchor = ev._anchor_of()                          # noqa: SLF001
        one = S9O.evaluate(res, ev.n_subjects, anchor)
        js.append(one["J"])
        a_s.append(one["A"])
        b_s.append(one["B"])
        # D54：把 C（遗漏率罚分）也记下来 —— 它是 J 的噪声**主要来源**，
        # 而它的斜率 dC/d(omission) 在 D4 附近约 125，于是把遗漏率的 MC 噪声放大两个数量级。
        om_s.append(float(one["omission"]))
        c_s.append(float(one["C"]))
    sd_j = float(np.std(js, ddof=1)) if len(js) > 1 else 0.0
    out = {"n_repeats": int(n_repeats), "J": [float(v) for v in js],
           "A": [float(v) for v in a_s], "B": [float(v) for v in b_s],
           "omission": om_s, "C": c_s,
           # ❗ D59：把**标定种子族**落盘 —— 没有它，落盘件的 `sd` 无法被复核，
           # 也无法判断它是"重抽的独立种子"还是"同一族算术邻居"（后者低报约 4 倍）。
           "seeds": seeds_used,
           "family": "cell_seed(f'{name}#noise{k}', base_seed), k = 0..n_repeats-1",
           "sd_J": sd_j, "sd_A": float(np.std(a_s, ddof=1)) if len(a_s) > 1 else 0.0,
           "sd_B": float(np.std(b_s, ddof=1)) if len(b_s) > 1 else 0.0,
           "sd_omission": float(np.std(om_s, ddof=1)) if len(om_s) > 1 else 0.0,
           "sd_C": float(np.std(c_s, ddof=1)) if len(c_s) > 1 else 0.0}
    # GP 的 alpha 是"观测方差"⇒ 用 sd_J²；下界 1e-12 防止 alpha=0
    ev.noise_alpha = max(sd_j ** 2, 1e-12)
    out["alpha"] = float(ev.noise_alpha)
    return out


def run_arms(ev: Evaluator, budget: int, seed: int = 0,
             noise: dict | None = None) -> dict:
    """四个臂在**同一个 Evaluator（同一个缓存）**上跑同样的预算。"""
    if noise is not None:
        ev.noise_alpha = float(noise["alpha"])
    else:
        ev.noise_alpha = 1e-12
    histories = {}
    for arm in ARM_ORDER:
        rng = np.random.default_rng(seed)
        t0 = time.time()
        print(f"\n[臂 {arm}] 预算 {budget}…", flush=True)
        names = ARMS[arm](ev, budget, rng)
        # ❗ 四臂必须**同预算**，否则消融变成"谁预算大谁赢"。这是机器可检的。
        if len(names) != budget:
            raise RuntimeError(f"臂 {arm} 用了 {len(names)} 次评估，预算 {budget} "
                               "—— 四路消融必须同预算，否则结论无效")
        curve = []
        curve_a = []
        cur = float("inf")
        cur_a = float("inf")
        best_a_name = ""
        best_a_b = float("nan")
        b_max = float("nan")
        n_feasible = 0
        for n in names:
            if n not in ev.cache:                          # grid/manual 走这里
                ev.get(n)
            r = ev.get(n)
            v = ev.value(n)
            cur = min(cur, v)
            if r["feasible"]:
                n_feasible += 1
                a_i, b_i = float(r["A"]), float(r["B"])
                b_max = b_i if not np.isfinite(b_max) else max(b_max, b_i)
                # D54：臂代表点 = 可行集内 **A 最小**的那个设计；B 取**同一点**的 B
                # （同一点 ⇒ 配对比较，不拿 A 的最好点和 B 的最好点拼一个不存在的设计）
                if a_i < cur_a:
                    cur_a, best_a_name, best_a_b = a_i, n, b_i
            curve.append(float(cur))
            curve_a.append(float(cur_a))
        histories[arm] = {"picked": list(names), "best_so_far": curve,
                          "best_A_so_far": curve_a,
                          "best_name": names[int(np.argmin(curve))],
                          "best_J": float(curve[-1]),
                          "best_A": float(curve_a[-1]),
                          # ⚠️ 这个键名必须与 `compare_arms` 构造的行**同名**（D57）：两处曾分别
                          # 写成 `B_at_best_A` / `B_at_A_best`，报告生成器读错一个键就把
                          # `B`@`(A)` 最优点**静默**印成 `—`（「缺失」与「零」在读者眼里差别极大）。
                          "B_at_A_best": float(best_a_b),
                          "B_max": float(b_max),
                          "A_best_name": best_a_name,
                          "n_feasible": int(n_feasible),
                          "seconds": time.time() - t0}
        print(f"[臂 {arm}] 完成：可行 {histories[arm]['n_feasible']}/{budget}、"
              f"best A = {curve_a[-1]:.4f}（参考 best J = {curve[-1]:.4f}）"
              f"（{histories[arm]['seconds']:.1f}s）", flush=True)
    return histories


def compare_arms(histories: dict, noise: dict) -> list[dict]:
    """按 **D54** 比较四臂：判据只建立在 `(A)/(B)` 上，且差异必须**大于 MC 噪声带**。

    **为什么不再用 `J`**：`J` 的 MC 噪声有 95–101% 来自 (C) 那条二次罚分，
    而臂间差异（0.47–0.64）小于噪声带 ⇒ 用 `J` 排序等于用噪声排序（§11 第 16 条）。
    现在 (C) 已改为**可行域约束**（见 `OMISSION_BAND`），`J` 只作为参考数列出。

    ⚠️ 四条纪律：
      1. 每条臂的代表点 = **可行集内 (A) 最小的那个设计**，`B` 取**同一个点**的 `B`
         （同一点 ⇒ 配对比较；不拿 A 的最好点和 B 的最好点拼出一个不存在的设计）；
      2. `ΔA ≤ 噪声带` ⇒ 必须说**不可分辨**，不宣称最好；
      3. `A` 与 `B` 各有一根噪声带，**分别判**：
         - `ΔA > 带` 且 `ΔB < -带` ⇒ **被支配**；
         - `ΔA > 带` 且 `ΔB > +带` ⇒ **权衡**，不可排序，必须报出来而不是按单一标量硬排；
         - `ΔA > 带` 但 `|ΔB| ≤ 带` ⇒ ❗**在 (A) 上显著更差**，只是 B 分量不可分辨
           ⇒ **不得**写成「两者不可分辨」。把 A 上 30% 的差距说成"不可分辨"，
           正好是处方⑥「GP 必须自己证明配得上」要防的那种洗白。
      4. ❗ **D59：两根带子不许互相顶替。**
         `ΔA ≤ 带` 但 `ΔB` **超出** `band_b` ⇒ 必须明说「在 (B) 上显著更差/更好，
         而 (A) 分量不可分辨」，**不得**只写一句「不可分辨」把 B 上的真实差距吞掉。
         反向的短路同样要防：`band_a` 偏窄时「A 超带」会盖住 B，于是印成「被支配」。
         实测（`_scratch_anchor_seed_scan.py`）标定用的 `sd_A` 在 `n_fim = 1` 下比
         真实种子散布**小 4 倍** ⇒ 先按旧门槛判出的**每一条**结论都要重新看一眼。
      5. ❗ **D60：带宽是「差的」噪声带 —— 系数是 `2·√2`，不是 `2`。**
         `measure_noise` 量的是**同一个设计**（锚点）的种子间 `sd`（`sd_A`），
         而这里比的是两条臂各自选中的**不同设计**：种子由名字哈希导出 ⇒ 两次
         MC 误差**独立** ⇒ `Var(差) = 2·sd²` ⇒ `SE(差) = √2·sd`。
         用 `2·sd` 判「差异是否显著」会把差的噪声低估 `√2 ≈ 1.41` 倍，
         即**偏宽松**、更容易宣称「显著更差 / 最好」—— 与上面几条要防的方向相反，
         所以必须显式乘上 `DIFF_BAND_FACTOR`。
         ⚠️ 同方差假设与选择偏差两条限制见 `DIFF_BAND_FACTOR` 处的注释（未解决）。
    """
    band_a = DIFF_BAND_FACTOR * float(noise.get("sd_A", 0.0))
    band_b = DIFF_BAND_FACTOR * float(noise.get("sd_B", 0.0))
    rows = []
    for arm in ARM_ORDER:
        h = histories.get(arm)
        if h is None:
            continue
        rows.append({"arm": arm, "best_J": float(h["best_J"]),
                     "best_name": h["best_name"], "seconds": float(h["seconds"]),
                     "A_best_name": h.get("A_best_name", ""),
                     "n_feasible": int(h.get("n_feasible", 0)),
                     "A_best": float(h.get("best_A", float("inf"))),
                     "B_at_A_best": float(h.get("B_at_A_best", float("nan"))),
                     "B_max": float(h.get("B_max", float("nan")))})
    if not rows:
        return rows
    rows.sort(key=lambda r: r["A_best"])          # `inf` 排到最后
    for r in rows:
        r["has_feasible_point"] = bool(np.isfinite(r["A_best"]))
    # ❗ 判据的**先决条件**：至少要有一条臂在可行集内取到设计，否则没有对照。
    # 实测踩过：`--budget 2` 时三条臂的 `A_best` 是 `inf`（本预算内一个可行点都没抽到），
    # 旧代码便把 `gap = inf - 0.39` 当成"领先很多"印成「小 inf > 噪声带 0.0050」——
    # 那是把**没有数据**说成**大幅领先**，与本文件要防的洗白是同一类错误。
    with_pt = [r for r in rows if r["has_feasible_point"]]
    top = with_pt[0] if with_pt else None
    n_no_pt = len(rows) - len(with_pt)
    for r in rows:
        if top is None:
            r["dA_vs_best"] = float("inf") if r["A_best"] == float("inf") else 0.0
            r["dB_vs_best"] = float("nan")
            r["verdict"] = ("本预算下**没有任何一条臂**在可行集内取到设计 ⇒ **无对照、无排序证据**"
                            "（这**不是**「谁更差」，是**没有数据**：要么预算太小，"
                            "要么遗漏率带把这一片设计全排除了）")
            continue
        d_a = r["A_best"] - top["A_best"]
        d_b = r["B_at_A_best"] - top["B_at_A_best"]     # B 越大越好 ⇒ 正数是更好
        r["dA_vs_best"] = float(d_a)
        r["dB_vs_best"] = float(d_b)
        if not r["has_feasible_point"]:
            r["verdict"] = ("本预算下**可行集内没有任何设计**（`A = ∞`）⇒ 不参与排序。"
                            "⚠️ 这**不是**「比谁更差」的证据，而是**这条臂没有取到可行点**；"
                            "要区分「预算不足」与「该臂确实偏向不可行区」，"
                            "得看它的 `picked` 里有几个点被 D54 带判为不可行")
            continue
        if r is top:
            rest = [q for q in with_pt if q is not top]
            if not rest:
                r["verdict"] = (f"本预算下**只有它一条臂**在可行集内取到设计"
                                f"（另外 {n_no_pt} 条臂都没有可行点）⇒ **无对照、不构成排序证据**，"
                                f"不得写成「最好」；只能如实报「本预算下唯一有可行点的臂」")
            else:
                second = rest[0]
                gap = second["A_best"] - top["A_best"]
                d_b_top = top["B_at_A_best"] - second["B_at_A_best"]
                tail = (f"（另有 {n_no_pt} 条臂在本预算内没有可行点）" if n_no_pt else "")
                # ❗ D59：`A` 与 `B` 必须**分别判**，不许短路。
                # 实测踩过：门槛 `band_a` 一旦偏窄，「A 超带」会盖住「B 差很多」，
                # 于是印成「被支配」；门槛一旦偏宽，「A 在带内」又会盖住「B 差很多」，
                # 于是印成「不可分辨」。两种方向都是**用一根带子替另一根做决定**。
                if gap <= band_a and abs(d_b_top) <= band_b:
                    r["verdict"] = (f"与次好臂 `{second['arm']}` **在 (A) 与 (B) 上都不可分辨**"
                                    f"（ΔA = {gap:.4f} ≤ 带 {band_a:.4f}、"
                                    f"|ΔB| = {abs(d_b_top):.4f} ≤ 带 {band_b:.4f}）"
                                    f"⇒ 不得宣称最好{tail}")
                elif gap <= band_a and d_b_top < -band_b:
                    r["verdict"] = (f"与次好臂 `{second['arm']}` **在 (A) 上不可分辨**"
                                    f"（ΔA = {gap:.4f} ≤ 带 {band_a:.4f}），"
                                    f"但**在 (B) 上显著更差**（ΔB = {d_b_top:.4f}，"
                                    f"超出 ±{band_b:.4f}）⇒ **不得宣称最好**："
                                    f"(A) 上没有排序证据，而 (B) 上它是明显更差的一方{tail}")
                elif gap <= band_a:
                    r["verdict"] = (f"与次好臂 `{second['arm']}` **在 (A) 上不可分辨**"
                                    f"（ΔA = {gap:.4f} ≤ 带 {band_a:.4f}），"
                                    f"但**在 (B) 上更好**（ΔB = +{d_b_top:.4f} > {band_b:.4f}）"
                                    f"⇒ 仍**不得宣称最好**：主判据 (A) 不可分辨{tail}")
                elif d_b_top < -band_b:
                    r["verdict"] = (f"**权衡**：A 比次好臂 `{second['arm']}` 好 {gap:.4f}"
                                    f"（> {band_a:.4f}）但 B 差 {-d_b_top:.4f}（> {band_b:.4f}）"
                                    f"⇒ **不可排序**，不得宣称最好{tail}")
                else:
                    r["verdict"] = (f"本预算下 (A,B) 上最好（比次好臂 `{second['arm']}` 的 A "
                                    f"小 {gap:.4f} > 噪声带 {band_a:.4f}，"
                                    f"且 B 不差）{tail}")
        elif d_a <= band_a and d_b < -band_b:
            r["verdict"] = (f"在 **(B) 上显著更差**（ΔB = {d_b:.4f} < -{band_b:.4f}），"
                            f"而 (A) 分量不可分辨（ΔA = {d_a:.4f} ≤ {band_a:.4f}）"
                            f"⇒ **不是**「两者不可分辨」：B 上的差距是真的")
        elif d_a <= band_a and d_b > band_b:
            r["verdict"] = (f"在 **(B) 上显著更好**（ΔB = {d_b:.4f} > {band_b:.4f}），"
                            f"而 (A) 分量不可分辨（ΔA = {d_a:.4f} ≤ {band_a:.4f}）"
                            f"⇒ **不是**「两者不可分辨」，但也不构成 (A) 上的排序")
        elif d_a <= band_a:
            r["verdict"] = (f"与最好臂 `{top['arm']}` **在 (A) 与 (B) 上都不可分辨**"
                            f"（ΔA = {d_a:.4f} ≤ 带 {band_a:.4f}、"
                            f"|ΔB| = {abs(d_b):.4f} ≤ 带 {band_b:.4f}）")
        elif d_b < -band_b:
            r["verdict"] = (f"被 `{top['arm']}` **支配**（ΔA = {d_a:.4f} > {band_a:.4f}、"
                            f"ΔB = {d_b:.4f} < -{band_b:.4f}）")
        elif d_b > band_b:
            r["verdict"] = (f"**权衡**：A 差 {d_a:.4f}（> {band_a:.4f}）但 B 好 "
                            f"{d_b:.4f}（> {band_b:.4f}）⇒ **不可排序**")
        else:
            r["verdict"] = (f"在 **(A) 上显著更差**（ΔA = {d_a:.4f} > 噪声带 {band_a:.4f}），"
                            f"而 B 分量不可分辨（ΔB = {d_b:.4f} 落在 ±{band_b:.4f} 内）"
                            f"⇒ **不是**「两者不可分辨」，只是差距落在 B 上看不出来")
    return rows


def pareto_front(ev: Evaluator, names: list[str] | None = None) -> list[dict]:
    """在 Evaluator 缓存上算 (A 小, B 大) 的 Pareto 前沿。"""
    pts = []
    for n in (names or list(ev.cache)):
        r = ev.get(n)
        if r["feasible"]:
            pts.append({"name": n, "A": float(r["A"]), "B": float(r["B"]),
                        "J": float(r["J"])})
    front: list[dict] = []
    for p in sorted(pts, key=lambda q: (q["A"], -q["B"])):
        if not front or p["B"] > front[-1]["B"]:
            front.append(p)
    return front


# ==================================================================
# 5. 主程序
# ==================================================================
def _jsonable(x):
    """把内环记录里可能出现的 numpy 标量/数组折成 JSON 可写的东西。

    为什么需要它：`inner_eval` 返回的 `se` / `se_sd` / `acc` 是 numpy 数组，
    `json.dumps` 对它们直接抛 `TypeError`，而如果为省事只挑几个标量写进载荷，
    落盘件就**无法离线复算支配关系与前沿** —— 那正是 D55 里必须另起一个探针补评估的原因。
    """
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.generic):
        return x.item()
    return x


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget", type=int, default=40, help="每个臂的评估预算")
    ap.add_argument("--n-fim", type=int, default=1, help="每个设计的内环重复数")
    ap.add_argument("--n-subjects", type=int, default=40, help="Objective (B) 的组人数")
    ap.add_argument("--P", type=float, default=None, help="关联强度 P（缺省用 P_SINGLE）")
    ap.add_argument("--rho", type=float, default=None,
                    help=f"两阶段漂移真值（缺省冻结值 {S9O.FROZEN['rho_mu']}）")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-candidates", type=int, default=0,
                    help="只取候选表的前 N 个（0 = 全部）；用于冒烟")
    ap.add_argument("--noise-repeats", type=int, default=5,
                    help="噪声标定的重复数；2 只有 1 个自由度、极不稳定（D53），默认 5")
    ap.add_argument("--out", type=str, default="")
    a = ap.parse_args()

    print("=" * 70)
    print("Stage 9 优化循环（有限候选集 + 共享 CRN + 四路消融）")
    print(f"冻结 Objective：spec={S9O.FROZEN['spec_version']} "
          f"sha256={S9O.SPEC_SHA256[:16]}…")
    S9O.assert_frozen()
    print("=" * 70)

    designs = enumerate_designs(verbose=True)
    if a.max_candidates and a.max_candidates < len(designs):
        designs = designs[:a.max_candidates]
        print(f"（冒烟模式：只取前 {len(designs)} 个候选）")
    names = [d["name"] for d in designs]
    if ANCHOR_DESIGN not in names:
        print("⚠️ 锚点设计 D4 不在候选子集里 —— Objective 无法归一化，退出")
        return 2

    ev = Evaluator(designs, rho=a.rho, n_fim=a.n_fim, n_subjects=a.n_subjects,
                   P=a.P, base_seed=a.seed)
    t0 = time.time()
    print("\n[噪声标定] 锚点设计在不同种子下重算…", flush=True)
    noise = measure_noise(ev, a.noise_repeats)
    print(f"[噪声标定] J = {['%.4f' % v for v in noise['J']]}")
    print(f"[噪声标定] sd_J = {noise['sd_J']:.4f} ⇒ alpha = {noise['alpha']:.3e}")
    print(f"[噪声标定] sd_A = {noise['sd_A']:.4f}、sd_B = {noise['sd_B']:.4f}"
          f"（D54 的判据用这两个）、sd_omission = {noise['sd_omission']:.5f}、"
          f"sd_C = {noise['sd_C']:.4f}")

    budget = min(int(a.budget), len(designs))
    histories = run_arms(ev, budget, seed=a.seed, noise=noise)
    rows = compare_arms(histories, noise)
    # —— ❗ 前沿与推荐点必须建立在**整个候选空间**上，不能只用四臂抽到的那些点 ——
    # `pareto_front` 走的是 `names or list(ev.cache)`，而 `best()` 也只在缓存里找；
    # 若先算它们再补全空间，报出来的「推荐点」其实是「四臂抽到的点里最好的那一个」，
    # 其好坏完全取决于 `--budget`，而输出里看不出这一点（D55 实测：`--budget 12` 时报
    # `A = 0.3881`，补全空间后是 `0.3446`，并且后者**可行集内支配 D4**）。
    n_cached_before = len(ev.cache)
    print(f"\n[前沿] 先补全候选空间（缓存里现有 {n_cached_before} 个，候选共 "
          f"{len(designs)} 个）—— 前沿与推荐点只在整个空间上才有意义…", flush=True)
    ev.feasible_names()          # 触发全空间评估（幂等：命中缓存的不重算）
    print(f"[前沿] 全空间评估完毕：缓存 {len(ev.cache)} 个、"
          f"累计 {ev.n_evals} 次内环评估、{ev.seconds:.0f}s")
    front = pareto_front(ev)
    best_name, best_rec = ev.best("A")          # D54：推荐点 = 可行集内 A 最小
    best_j_name, best_j_rec = ev.best("J")      # 参考：J 最小（受 (C) 支配）
    n_band = sum(1 for r in ev.cache.values()
                 if any("D54 约束" in g for g in r.get("gates", [])))
    n_feas = len(ev.feasible_names())

    print("\n" + "=" * 70)
    print(f"总评估次数 {ev.n_evals}、内环耗时 {ev.seconds:.0f}s、"
          f"墙钟 {time.time() - t0:.0f}s")
    print(f"D54 遗漏率约束带 = [{OMISSION_BAND[0]:g}, {OMISSION_BAND[1]:g}]"
          f" ⇒ 缓存里被判不可行的 {n_band} 个、可行 {n_feas} 个")
    print(f"判据只建立在 (A,B) 上；噪声带 2·sd_A = {2 * noise['sd_A']:.4f}、"
          f"2·sd_B = {2 * noise['sd_B']:.4f}（2·sd_J = {2 * noise['sd_J']:.4f} 仅参考）")
    for r in rows:
        # `A_best = inf` ⇒ 这条臂在本预算内**没有可行点** ⇒ 印 `—`，不要印 `inf`/`nan`
        # （印 `inf` 会被读成"极好"或"极差"，两种读法都错：那是**没有数据**）
        a_s = f"{r['A_best']:.4f}" if np.isfinite(r["A_best"]) else "—"
        b_s = f"{r['B_at_A_best']:.4f}" if np.isfinite(r["B_at_A_best"]) else "—"
        j_s = f"{r['best_J']:.4f}" if np.isfinite(r["best_J"]) else "—"
        print(f"  {r['arm']:7s} A_best = {a_s}、B@A_best = {b_s}、"
              f"可行 {r['n_feasible']:2d}、参考 best J = {j_s}\n"
              f"            {r['verdict']}")
    print(f"\n推荐点（D54：(A) 最小）：A = {best_rec['A']:.4f}  B = {best_rec['B']:.4f}  "
          f"遗漏 = {best_rec['omission']:.3f}  J(参考) = {best_rec['J']:.4f}")
    print(f"  {best_name}")
    print(f"参考点（J 最小，受 (C) 支配）：A = {best_j_rec['A']:.4f}  J = {best_j_rec['J']:.4f}")
    print(f"  {best_j_name}")
    d4 = ev.get(ANCHOR_DESIGN)
    print(f"锚点 D4：A = {d4['A']:.4f}  B = {d4['B']:.4f}  C = {d4['C']:.4f}  "
          f"J = {d4['J']:.4f}  可行 = {d4['feasible']}"
          f"（离推荐点 ΔA = {d4['A'] - best_rec['A']:.4f}）")
    print(f"Pareto 前沿 {len(front)} 个点；前 5：")
    for p in front[:5]:
        print(f"  A={p['A']:.4f} B={p['B']:.4f} J={p['J']:.4f}  {p['name']}")

    if a.out:
        payload = {"designs": designs, "noise": noise, "histories": histories,
                   "compare": rows, "pareto": front,
                   "best": {"name": best_name, "A": best_rec["A"], "B": best_rec["B"],
                            "J": best_rec["J"], "criterion": "A（D54）"},
                   "best_J_reference": {"name": best_j_name, "J": best_j_rec["J"]},
                   "anchor": {"name": ANCHOR_DESIGN, "A": d4["A"], "B": d4["B"],
                              "J": d4["J"], "feasible": d4["feasible"]},
                   "d54": {"omission_band": list(OMISSION_BAND),
                           "n_band_rejected": n_band, "n_feasible": n_feas,
                           "criterion": list(CRITERION)},
                   # 前沿/推荐点的**作用域**：必须显式落盘，否则读者会把一个
                   # 只覆盖四臂抽样点的前沿当成整个候选空间的前沿（D55 记的缺陷）
                   "front_scope": {"n_candidates": len(designs),
                                   "n_cached_before_full_eval": n_cached_before,
                                   "n_evaluated": len(ev.cache),
                                   "n_front": len(front)},
                   "settings": {"budget": budget, "n_fim": a.n_fim,
                                "n_subjects": a.n_subjects, "P": a.P,
                                "rho": ev.rho, "seed": a.seed},
                   "spec_sha256": S9O.SPEC_SHA256,
                   # 裁决文本是运行时生成的**冻结产物**，报告不重算 ⇒ 必须把它出自哪一版
                   # 规则一起落盘（D59；否则「报告由落盘件生成」只保证了转印，不保证可归因）
                   "verdict_logic": VERDICT_LOGIC,
                   "n_evals": ev.n_evals, "seconds": ev.seconds,
                   # D55 待办(2)：把**逐设计**的记录一起落盘，否则 D4 与其它设计的
                   # 支配/权衡关系无法离线复算（原先只能另跑一次探针补评估）
                   "cache": {k: _jsonable(v) for k, v in ev.cache.items()}}
        Path(a.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                               encoding="utf-8", newline="\n")
        print(f"\n已写出 {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
