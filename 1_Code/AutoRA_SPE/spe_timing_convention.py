"""实验时序口径桥：`v2`（旧，本目录历史实现） ⇄ `v4.1`（当前程序 `Exp_Design_Formal.m`）。

为什么需要这个模块
==================
本目录的 `spe_design_model.py` 把 `deadline = T + W` 写成"权威口径"，它是对的 —— 但只对
**旧程序** `Exp_Design_Formal_v2.m` 对。当前程序 `Exp_Design_Formal.m` v4.1 改了 W 的定义，
两者的 deadline 相差**恰好 `T + 200 ms`**，而参数名叫同一个字母 W。若把 v4.1 的设计点直接喂进
本目录的历史函数，误差**随 T 单调增长**，会把一个纯口径错误伪装成 T 的主效应。

两套口径（逐字依据）
====================
- **v2 / 本目录历史实现**（`1_Code/AutoRA_SPE/spe_design_model.py` L112–119、L122–129）
  - `deadline = T + W_legacy`（自刺激起点计）
  - 反应窗口 **在 `T + 200 ms` 才打开**（`window_open_ms = T + MASK`）
  - `window_duration = W_legacy − 200` 是"掩蔽之后真正可按键的时长"
  - W_legacy 的语义 = **掩蔽之后的反应窗口长度**
- **v4.1 / 当前程序**（`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m` L14–22）
  - L18：`W 的定义：W = 【从刺激 onset 起算】到最晚可反应时刻的时长，
    deadline = stimulusFlipTime + W（旧版误为 onset + T + W，相当于"从刺激结束起算"）`
  - L14–17：自**刺激 onset** 起全程轮询键盘（刺激期 / 掩蔽期 / 反应窗口 三段都采集）
  - L22：约束 `W 必须 > T + 200ms`；掩蔽之后真正可按键时长 = `W − T − 200ms`
  - W 的语义 = **自 onset 起算的截止时刻本身**

换算
====
    物理 deadline = T + W_legacy = W_current
    ⇒ W_current = T + W_legacy
    ⇒ W_legacy  = W_current − T

历史 8 组（v2）的最大反应 RT ≈ `T + W_legacy + 2 ms`，换成当前口径即 ≈ `W_current + 2 ms`。
**这是同一组数据、同一个物理量，只是参数名换了含义。**

本目录历史代码在 v4.1 下的三处失真
==================================
1. `deadline_ms` / `design_to_params` 的 `deadline_s`：多算 `T`（D4 四档 T = 33.33–249.98 ms、
   相对误差 3%–31%，且随 T 单调增长）。
2. `design_to_params` 的 `M_ms = T + W` 与 `boundary_a(M_ms)`：同样多算 `T`，边界尺度 `a` 被抬高。
3. ⚠️ **`apply_window_gate` 不是"删掉"早反应，而是把它"抬到窗口打开时刻"**：
   `rt[mask_ok] = np.maximum(rt[mask_ok], floor)`，`floor = T + 0.2 s`（L326–330）。
   于是任何 `rt < T + 200 ms` 的 v4.1 反应**被静默改写成 `T + 200 ms`**，而刺激期内按键
   （D5 存在的全部理由：实际呈现时长 = min(T, RT)）连同它的 RT 一起消失，并**人为复现出
   legacy 的"最小 RT ≈ T + 203 ms"伪迹**。当前程序里这个门控**必须不施加**（窗口自 onset 即开）。

不做的事
========
本模块**不修改** `spe_design_model.py`（该文件的历史数值是旧数据诊断的证据，动了会让证据失效），
只把两套口径显式化、给出换算、并对误用**主动报错**。自测见 `check_timing_convention.py`。
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:  # 掩蔽时长只有一处事实来源
    from spe_design_model import MASK_MS as _MASK_MS_FROM_MODEL
    from spe_design_model import window_open_ms as _legacy_window_open_ms

    MASK_MS = float(_MASK_MS_FROM_MODEL)
    _ORIGIN_MASK = "spe_design_model.MASK_MS"
except Exception:  # pragma: no cover - 仅在孤立环境下发生
    MASK_MS = 200.0
    _legacy_window_open_ms = None
    _ORIGIN_MASK = "fallback(200.0)"

# 口径标签：任何跨模块调用都应显式带上其中之一，避免"同名不同义"静默通过
LEGACY = "v2"
CURRENT = "v4.1"

__all__ = [
    "MASK_MS",
    "LEGACY",
    "CURRENT",
    "legacy_deadline_ms",
    "current_deadline_ms",
    "legacy_to_current_W",
    "current_to_legacy_W",
    "current_postmask_pressable_ms",
    "current_window_open_ms",
    "assert_current_design",
    "misuse_distortion",
    "apply_current_window_gate",
]


# ------------------------------------------------------------------
# 两套口径各自的 deadline
# ------------------------------------------------------------------
def legacy_deadline_ms(T_ms, W_legacy_ms) -> float:
    """v2 口径：`deadline = T + W_legacy`（毫秒，自刺激起点计）。"""
    return float(T_ms) + float(W_legacy_ms)


def current_deadline_ms(T_ms, W_current_ms) -> float:
    """v4.1 口径：`deadline = W`（毫秒，自刺激起点计）。

    `T_ms` 不参与该式 —— 保留参数只为让调用点显式看到它**不**被加进去。
    """
    _ = float(T_ms)  # 显式：T 不进 deadline
    return float(W_current_ms)


def legacy_to_current_W(T_ms, W_legacy_ms) -> float:
    """v2 的 W（掩蔽后窗口长度） → v4.1 的 W（自 onset 的截止时刻）。"""
    return float(T_ms) + float(W_legacy_ms)


def current_to_legacy_W(T_ms, W_current_ms) -> float:
    """v4.1 的 W（自 onset 的截止时刻） → v2 的 W（掩蔽后窗口长度）。"""
    return float(W_current_ms) - float(T_ms)


def current_postmask_pressable_ms(T_ms, W_current_ms) -> float:
    """v4.1 下掩蔽之后真正可按键的时长（毫秒）= `W − T − MASK`。

    对应 `Exp_Design_Formal.m` L22。v2 的 `W_legacy − MASK` 只有在
    `W_current = T + W_legacy` 时才等于它。
    """
    return float(W_current_ms) - float(T_ms) - MASK_MS


def current_window_open_ms() -> float:
    """v4.1 的反应窗口开启时刻（毫秒，自刺激起点计）= **0**（自 onset 即采集按键）。"""
    return 0.0


# ------------------------------------------------------------------
# 守卫
# ------------------------------------------------------------------
def assert_current_design(T_ms, W_current_ms) -> None:
    """断言 `(T, W)` 满足 v4.1 的启动自检：`W > T + 200 ms`（程序 L22）。

    这是程序**自己**会拦的条件，所以它必须在这里也拦 —— 否则我们会先跑完仿真、
    再在实机上被程序拒绝，或者更糟：把不可实现的点当成候选设计写进论文。
    """
    T = float(T_ms)
    W = float(W_current_ms)
    if T <= 0.0:
        raise ValueError(f"T 必须为正（毫秒），得到 T={T}")
    need = T + MASK_MS
    if not W > need:
        raise ValueError(
            f"违反 Exp_Design_Formal.m L22 的启动自检：需要 W > T + MASK = {need} ms，"
            f"得到 W={W} ms（T={T}）。该设计点程序会拒绝启动。"
        )


def misuse_distortion(T_ms, W_current_ms) -> dict:
    """把 v4.1 的 `(T, W)` 当成 legacy W 用时，各量的偏离（毫秒/相对）。"""
    T = float(T_ms)
    W = float(W_current_ms)
    correct = current_deadline_ms(T, W)
    wrong = legacy_deadline_ms(T, W)
    out = {
        "deadline_correct_ms": correct,
        "deadline_if_legacy_ms": wrong,
        "deadline_abs_err_ms": wrong - correct,
        "deadline_rel_err": (wrong - correct) / correct if correct else float("nan"),
        "M_ms_if_legacy": T + W,
        "M_ms_correct": W,
        "boundary_a_arg_if_legacy_ms": T + W,
        "boundary_a_arg_correct_ms": W,
        "gate_floor_if_legacy_ms": T + MASK_MS,
        "gate_floor_correct_ms": current_window_open_ms(),
        "postmask_pressable_if_legacy_ms": W - MASK_MS,
        "postmask_pressable_correct_ms": current_postmask_pressable_ms(T, W),
        "legacy_equivalent_W_ms": current_to_legacy_W(T, W),
    }
    return out


# ------------------------------------------------------------------
# v4.1 的"窗口门控"
# ------------------------------------------------------------------
def apply_current_window_gate(rt, omission=None):
    """v4.1 下的窗口门控 = **恒等映射**（什么都不做），返回输入副本。

    为什么是恒等：`Exp_Design_Formal.m` v4.1 自刺激 onset 起就采集按键，
    窗口没有"还没打开"的时段，所以没有需要把早反应推迟到的 floor。
    保留这个函数是为了让调用点能显式地写 `apply_current_window_gate(...)`，
    而不是误调 legacy 的 `apply_window_gate`（后者会把 `rt < T+200` 抬到 `T+200`）。
    """
    import numpy as _np

    rt_arr = _np.asarray(rt, dtype=float)
    if rt_arr.size and _np.any(_np.isfinite(rt_arr) & (rt_arr < 0.0)):
        bad = float(_np.nanmin(rt_arr[_np.isfinite(rt_arr) & (rt_arr < 0.0)]))
        raise ValueError(f"RT 自刺激 onset 起算，不应为负；最小有限值 = {bad}")
    return rt_arr.copy()
