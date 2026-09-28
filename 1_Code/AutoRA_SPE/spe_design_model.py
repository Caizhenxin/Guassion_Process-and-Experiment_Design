# -*- coding: utf-8 -*-
"""
spe_design_model.py —— AutoRA-SPE 的"设计 → 参数"映射层（修正版）
=================================================================
本模块是「GP × AutoRA」路线的地基，用于取代 `automation/core/sigmoid_model.py`
以及 `1_Code/Python_for_Generate/` 下各 notebook 中互相矛盾的参数映射实现，
成为**唯一事实来源**。

相对历史实现的 5 处修正（依据 2026-09-16 两份审计报告的 P0 清单）
------------------------------------------------------------------
1. **实验时序口径唯一化 —— 且此处更正了两份文档（含本文件初版）的错误**
   权威口径：**`deadline = T + W`**（毫秒，自刺激起点计）。

   实验源码 `1_Code/Experiment/exp_matlab/Exp_Design_Formal_v2.m` 直接给出：
     * L20  表头注释：`deadline 同为 T+W=1.2s`（T=100, W=1100 → 1200 ms）
     * L479 `maskDuration = 0.2;`
     * L506 `maskOffsetTime = maskFlipTime + maskDuration;`
     * L513 `% 4. 显示空白屏，等待键盘反应，持续反应窗口 W - maskDuration`
     * L519 `%   deadline 与 v1 完全一致（responseFlipTime + W - maskDuration）`
     * L963 `while GetSecs() - responseFlipTime < W - maskDuration`

   即：反应窗口在 `刺激onset + T + 200 ms` **打开**，持续 `W − 200 ms`，
   因此在 `刺激onset + T + W` **关闭**。

   实测数据独立确证（`diag_observed_rt.py`）：8 组的**最大反应 RT ≈ T + W + 2 ms**
   （g2 632.8 vs 630；g3 635.4 vs 630；g4 683.6 vs 680；g6 1975.2 vs 2000），
   而 8 组的反应窗口时长 `W − 200` 与其遗漏率完全对应
   （g3/g4 同为 400 ms → 遗漏 .386/.384；g7/g8 同为 600 ms → 遗漏 .143/.147）。

   ⚠️ 由此更正的两处：
     * 本文件初版写的 `T + 200 + W` **是错的**（多加了一个掩蔽时长）；
     * `项目脉络梳理与行动清单_20260916.md` §5 P0-1 称「统一为 T/1000 + 0.2 + W/1000」
       **也是错的**，且该段落自相矛盾——它同时把 `sim_utils.py` 的 `(T+W)/1000` 标为 ✅。
     * `sim_utils.py` 与历史 `automation/core/generative_model.py` 的 `T + W` **才是对的**。

   ⚠️ 另需注意：设计表里的 `W` 不是"反应窗口时长"，而是**窗口关闭时刻**
   （自刺激起点计）。真正的可反应时长 = `W − 200 ms`。

2. **反应窗口门控（response-window gate）**——本模块相对历史实现最重要的新增
   关键观察：真实数据里**各组最小 RT ≈ T + 0.233 s，斜率恰好为 1.0**
   （即 RT 下界完全由实验时序决定，不由心理过程决定）。
   历史实现把这一现象交给 DDM 的非决策时间 `t` 去吸收，后果是
   `t` 从 0.337 s（T=30）漂到 0.663 s（T=500），跨条件不稳定的 `t` 无法心理解释。
   本模块改为：**决策自刺激起始即开始积累，但按键只在窗口 `[T+200, T+200+W]` 内被记录；
   窗口开启前完成的决策须等待至窗口开启方可按键**。于是 RT 下界由时序自然产生，
   `t0` 可以（也应该）跨条件恒定。

3. **身份项由乘性改加性**
   `v_self = v_base + ΔI/2`，`v_stranger = v_base − ΔI/2`。
   乘性形式 `(1+α₁)/(1+α₂)` 强制 self/stranger 的漂移率比值在所有设计点相同，
   而实测逐条件 Δv 从 −0.16 到 +0.71，与乘性形式不相容；加性形式下
   `ΔI ≡ SPE_v = v_self − v_stranger` 可直接解释，且允许为负（可表达 G3 的反转）。

4. **参数改名**：`k_min` / `k_max` → `k_at_low_P` / `k_at_high_P`
   （原命名与语义相反，是版本间漂移的根源）。

5. **移除 lapse 项**：遗漏只由 deadline 产生，不再用
   `compute_lapse_omission_prob` 把遗漏率钉死在 ~43%；真实遗漏率为 5.6%–71.6%。

本模块**不做**的事
------------------
* 不实现 GP：GP 在本路线中的位置是「设计空间上的代理模型 + 采集信号」，
  不属于"设计 → 参数"映射层（见 `README.md`）。
* 不实现仿真：仿真统一复用 `sim_utils.simulate_trials`（单一事实来源），
  由 `spe_runner.py` 调用。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict, fields
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------
# 复用已验证的仿真器：sim_utils（TenRules_Revision_20260912 包）
# ------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_SIM_DIR = _HERE.parent / "Python_for_Check" / "TenRules_Revision_20260912"
if str(_SIM_DIR) not in sys.path:
    sys.path.insert(0, str(_SIM_DIR))

from sim_utils import SIM_DT, TRIALS_PER_IDENTITY, simulate_trials  # noqa: E402

__all__ = [
    "MASK_MS", "DESIGN_BOUNDS", "TRIALS_PER_IDENTITY", "SIM_DT",
    "deadline_ms", "window_open_ms", "window_close_ms", "window_duration_ms",
    "deadline_s", "window_open_s",
    "v_T", "v_P", "boundary_a", "DesignParams", "DEFAULT_PARAMS",
    "design_to_params", "apply_window_gate",
]

# ------------------------------------------------------------------
# 实验时序（唯一权威口径）
# ------------------------------------------------------------------
MASK_MS = 200.0
"""掩蔽呈现时长（毫秒）。实验程序 `experiment_formal_newcon.m` L419 固定为 0.2 s。"""

DESIGN_BOUNDS = {
    # 名称 -> (下界, 上界)。上界刻意放宽到历史 8 点之外，使主动设计有空间；
    # 但**候选点必须落在实验程序可实现的范围内**（见 README 的约束一节）。
    #
    # ⚠️ W_ms 是"反应窗口关闭时刻（自刺激起点计）"，不是窗口时长。
    #    真正的可反应时长 = W_ms − MASK_MS，必须为正；实验上还应设一个下限
    #    （历史最小值为 g1 的 100 ms）。
    "P": (0.0, 240.0),
    "T_ms": (30.0, 600.0),
    "W_ms": (MASK_MS + 50.0, 2500.0),
}


def deadline_ms(T_ms, W_ms, mask_ms: float = MASK_MS) -> float:
    """可反应窗口的关闭时刻（毫秒，自刺激起点计）。

    **权威口径：deadline = T + W**（见本模块 docstring 对实验源码的引用）。
    注意 `mask_ms` 不参与该式——掩蔽时长已经包含在 W 的语义里。
    保留该参数仅为向后兼容与显式标注，默认调用不应传它。
    """
    return float(T_ms) + float(W_ms)


def window_open_ms(T_ms, mask_ms: float = MASK_MS) -> float:
    """反应窗口开启时刻（毫秒，自刺激起点计）= 刺激结束 + 掩蔽 = T + 200。"""
    return float(T_ms) + float(mask_ms)


def window_duration_ms(T_ms, W_ms, mask_ms: float = MASK_MS) -> float:
    """**真正的可反应时长**（毫秒）= W − 200。这是设计空间里真正起作用的量。"""
    return float(W_ms) - float(mask_ms)


def window_close_ms(T_ms, W_ms) -> float:
    """反应窗口关闭时刻（毫秒，自刺激起点计）= T + W = deadline。"""
    return deadline_ms(T_ms, W_ms)


def deadline_s(T_ms, W_ms) -> float:
    return deadline_ms(T_ms, W_ms) / 1000.0


def window_open_s(T_ms, mask_ms: float = MASK_MS) -> float:
    return window_open_ms(T_ms, mask_ms) / 1000.0


# ------------------------------------------------------------------
# 机制函数（修正版）
# ------------------------------------------------------------------
def v_T(T_ms, T0: float = 100.0, k_T: float = 0.01):
    """刺激呈现时间 T → 证据质量因子（S 型，半效点 T0）。"""
    T_ms = np.asarray(T_ms, dtype=float)
    return 1.0 / (1.0 + np.exp(-k_T * (T_ms - T0)))


def v_P(P, P1: float = 4.0, P0: float = 32.0, gamma: float = 0.1,
        k_at_low_P: float = 0.01, k_at_high_P: float = 0.15):
    """练习次数 P → 证据质量因子（二阶 S 型）。

    命名修正：历史上写作 `k_min` / `k_max`，但调用时传入 `k_min=0.1, k_max=0.05`
    使语义反转，是版本漂移的根源。此处改名为 `k_at_low_P` / `k_at_high_P`：
    P 很小时 k = k_at_low_P，P 很大时 k → k_at_high_P。
    """
    P = np.asarray(P, dtype=float)
    k = k_at_low_P + (k_at_high_P - k_at_low_P) / (1.0 + np.exp(-gamma * (P - P0)))
    return 1.0 / (1.0 + np.exp(-k * (P - P1)))


def boundary_a(M_ms, base_scale_a: float = 1.5, M0: float = 900.0, k_a: float = 0.002):
    """总可用时间 M = T + W → 决策边界 a（谨慎度）的单调整 S 型。

    ⚠️ 重要局限，必须在论文中声明：
    实测的 a 与 M 的关系**不是单调的**——M=630→1.218、680→1.419、830→1.092、
    880→2.416、1200→1.335、2000→1.477。因此在 6 个设计点下
    **a(M) 的函数形式不可识别**，本函数只是一个"弱先验占位"，
    默认参数刻意取在使 a ≈ 1.2–1.5 的范围内，不声称拟合结果。
    「需要哪些设计点才能让 a(M) 可识别」本身是 AutoRA 路线要回答的问题之一。
    """
    M_ms = np.asarray(M_ms, dtype=float)
    return base_scale_a / (1.0 + np.exp(-k_a * (M_ms - M0)))


# ------------------------------------------------------------------
# 参数容器
# ------------------------------------------------------------------
@dataclass
class DesignParams:
    """设计 → 参数映射的自由参数。

    默认值取自**配置 C**（4 链 × 8000 draws / 2000 burn-in、p_outlier=0）
    的冻结真值表 `2_Data/Generate_Data/GP_Sigmoid_Frozen6/input_conditions_g3g8.csv`
    的跨条件均值，凡无法由数据约束者（`t0`、`z_ratio`、`boundary_a` 的参数）
    显式标注为"先验占位"。
    """

    # --- v 骨架 ---
    base_scale_v: float = 0.774
    """v_base 的总体尺度。取自配置 C 的 (v_self+v_stranger)/2 跨条件均值 0.774。"""

    T0: float = 100.0
    k_T: float = 0.01
    P1: float = 4.0
    P0: float = 32.0
    gamma: float = 0.1
    k_at_low_P: float = 0.01
    k_at_high_P: float = 0.15

    # --- 身份效应（加性，核心量）---
    delta_identity: float = 0.428
    """ΔI = SPE_v = v_self − v_stranger。取自配置 C 的跨条件均值 0.428
    （逐条件 −0.159 ~ +0.714）。被试水平变异由 runner 的 jitter 提供。"""

    # --- 边界 ---
    base_scale_a: float = 1.5
    M0: float = 900.0
    k_a: float = 0.002

    # --- 非决策时间与起点 ---
    t0: float = 0.20
    """非决策时间（秒）。⚠️ 先验占位。在窗口门控生效后，t0 应跨条件恒定；
    历史实现中 t 随 T 从 0.337 漂到 0.663 s，正是缺少门控的后果。

    两个有用的恒等式（t0 = 200 ms 时）：
      * **有效证据积累窗口** = deadline − t0 = (T + W) − 0.2 = M − 0.2 秒；
      * **可反应的物理窗口** = W − 0.2 秒（自窗口开启计）。
    数据侧佐证：8 组的最小 RT 恒为 T + 203 ms（窗口开启 + 按键延迟）。
    """

    z_ratio: float = 0.5
    """起始点占边界的比例（0.5 = 无偏）。历史拟合 0.452–0.714。"""

    # --- 注意失败（lapse）---
    lapse_prob: float = 0.0
    """注意失败概率：该试次**不进行证据积累**（漂移率置零）。默认 0.0（未启用）。

    ⚠️ 2026-09-17 的复议结论（三次尝试的完整记录，供后续判断是否还需要它）：

    1. 初版（用错误的 `deadline = T+200+W`）显示仿真遗漏率只有观测的 1/5~1/2。
    2. 加入**被试间参数变异**：正确率误差 0.111 → 0.068，遗漏率几乎不变（0.126 → 0.122）。
    3. 加入**跨试次漂移变异 sv**：遗漏率 MAE 0.121 → 0.115，**假设被否证**（D6）。
    4. 加入**机制化 lapse（v ← 0）**：遗漏率 MAE 0.121 → 0.088，但
       responded 正确率 MAE **变差**（0.096 → 0.145），**形式被否证**（D7）。
    5. `diag_observed_rt.py` 给出决定性线索：8 组的最大反应 RT ≈ **T + W + 2 ms**，
       且各组的遗漏率与其"窗口时长 W − 200 ms"精确对应。

    → **遗漏缺口的真正原因是 deadline 口径本身写错了**（见本模块 docstring 第 1 条），
      而不是缺少 lapse 机制。改用 `deadline = T + W` 后若缺口闭合，
      则审计报告「去掉 lapse」的结论**成立**，本参数应保持 0.0。
      若仍不闭合，再回来考虑 lapse，但形式不能是"零漂移扩散"（D7 已排除）。"""

    # --- 被试水平抖动（生成虚拟被试用；0 表示群体同质）---
    sd_v_base: float = 1.0
    sd_delta_identity: float = 0.6
    sd_a: float = 0.35
    sd_t0: float = 0.05
    sd_z_ratio: float = 0.05

    def as_dict(self) -> dict:
        return asdict(self)

    def replace(self, **kw) -> "DesignParams":
        d = self.as_dict()
        unknown = set(kw) - {f.name for f in fields(self)}
        if unknown:
            raise KeyError(f"未知参数：{sorted(unknown)}")
        d.update(kw)
        return DesignParams(**d)


DEFAULT_PARAMS = DesignParams()


# ------------------------------------------------------------------
# 设计 → 参数
# ------------------------------------------------------------------
def design_to_params(P, T_ms, W_ms, params: DesignParams | None = None) -> dict:
    """把实验设计 (P, T, W) 映射为 DDM 参数与实验时序常量。

    Returns
    -------
    dict:
        v_self, v_stranger, v_base, delta_identity : 漂移率（加性身份项）
        a, t0, z                                   : 边界、非决策时间、起始点
        deadline_s, window_open_s, window_duration_s : 实验时序（秒）
        M_ms                                       : T + W = deadline（毫秒）
    """
    p = params or DEFAULT_PARAMS
    T_ms = float(T_ms)
    W_ms = float(W_ms)
    P = float(P)

    v_base = float(p.base_scale_v * v_T(T_ms, p.T0, p.k_T) * v_P(
        P, p.P1, p.P0, p.gamma, p.k_at_low_P, p.k_at_high_P))
    half = 0.5 * float(p.delta_identity)

    a = float(boundary_a(T_ms + W_ms, p.base_scale_a, p.M0, p.k_a))
    return {
        "v_base": v_base,
        "delta_identity": float(p.delta_identity),
        "v_self": v_base + half,
        "v_stranger": v_base - half,
        "a": a,
        "t0": float(p.t0),
        "z": float(p.z_ratio),
        "M_ms": T_ms + W_ms,
        "window_duration_ms": window_duration_ms(T_ms, W_ms),
        "deadline_s": deadline_s(T_ms, W_ms),
        "window_open_s": window_open_s(T_ms),
        "window_duration_s": window_duration_ms(T_ms, W_ms) / 1000.0,
    }


def apply_window_gate(rt, response, omission, T_ms, mask_ms: float = MASK_MS):
    """反应窗口门控：窗口开启前完成的决策须等待至窗口开启方可按键。

    RT 自刺激起点计。若决策在掩蔽结束前完成，记录到的 RT 被推迟到窗口开启时刻。
    这是真实数据中「最小 RT ≈ T + 0.233 s、斜率 1.0」这一现象的机制来源。

    Args
    ----
    rt : ndarray，秒（omission 为 NaN）
    response, omission : ndarray

    Returns
    -------
    rt_gated : ndarray，秒
    """
    rt = np.asarray(rt, dtype=float).copy()
    omission = np.asarray(omission, dtype=int)
    floor = window_open_s(T_ms, mask_ms)
    mask_ok = omission == 0
    rt[mask_ok] = np.maximum(rt[mask_ok], floor)
    return rt
