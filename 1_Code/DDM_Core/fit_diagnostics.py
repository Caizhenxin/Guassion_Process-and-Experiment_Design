# -*- coding: utf-8 -*-
"""
fit_diagnostics.py —— 拟合健康检查与病态拟合处置（D30，2026-10-14）
==================================================================
把 `recover_single.py` 与 `recover_group.py` **共用**的判据集中在这里，
避免两套脚本对「什么算一个可用的拟合」给出不同答案：

* `se_from_hessian()` —— 数值 Hessian → 无约束坐标 SE → delta 方法换算回参数坐标。
* `pathology()`       —— 判定一次拟合的健康状况，返回**三值判决**，不是布尔。
* `fit_with_retry()`  —— 只在「Hessian 退化」时把起点数 ×4 重试，其余交由调用方。

为什么需要它（第一层：SE = 0 不能当正常值）
-------------------------------------------
lin 参数化的组层回归残差 RMS = **0.4942**，而 **oracle 只有 0.1044**。逐点追下去，
残差的绝大部分来自**一个**被试（P=8/subj7）：`d_ref = 4.8009`（撞上界 6.0）、
`SE = 0.0000`、logL −3530.5（同批其余 −350…−530）。

`SE = 0` 是一个**明确的危险信号**：数值 Hessian 在该点已退化，参数估计无意义。
但旧代码只检查 `np.isfinite(ses)`，于是一个无意义的点以**同等权重**进入组间
最小二乘，并把整条回归拖偏。

教训一：**必须显式检查 SE 是否退化，而不能只检查它是不是 NaN。**

为什么需要它（第二层：布尔判决本身是错的）
-------------------------------------------
第一版修正把「参数贴界」也归入病态，于是 8 名被试的冒烟测试剔除了 `P=0/subj0`
（理由 `d_ref=0.2 贴下界 0.2`）。但 `_scratch/check_bounds.py` 重放被试层真值后
发现：**该被试的真值恰好就是 0.2000 = 下界本身**。根因在
`simulate.draw_subject_params` 的 `np.clip(..., lo, hi)` —— 抽到界外时真值被
**压在界上**，产生一个位于边界的概率堆。于是：

* 拟合落在 0.2000 **不是失败，而是答对了**；
* 把它剔除，等于把一个合法的（而且正是最需要锚点的）低漂移被试从 P=0 组里删掉，
  反而**引入**偏差。

⚠️ **2026-10-14 更新（D36）：这个 `np.clip` 的堆已经被量化并修掉了。**
`simulate.draw_subject_params` 现在多一个 `mode` 参数：
`"clip"`（**默认**，与手写 `np.clip` 逐位相同 ⇒ `_scratch/` 的历史日志仍可逐位复现）
与 `"truncate"`（界内截断正态，逆 CDF 法，只抽 1 个均匀数 ⇒ 随机数流与平台无关）。
**新工作一律用 `mode="truncate"`**；只有要复现旧日志时才用默认值。
量化结果见 `README.md` **§8.18**：只有 `d_ref`、只有低 P 会压边（P=0 解析式
**3.16%（exp）/ 6.53%（lin）**，`lin` 是 `exp` 的两倍 ⇒ 最低 P 水平的 lin/exp 比较不是干净对照）；
截断把 P=0 的边际 SD 从 `SUBJECT_SD` 的 0.1500 压到 **0.1390 / 0.1321**
⇒ 凡以「被试间 SD 0.1500」为参照的表述都要改用对应档的截断 SD。
⚠️ **生成侧的「堆」与拟合侧的「贴界」不是一回事**：前者是本文件要处理的对象，后者按下面的规则**只报告、不剔除**。

这两件事必须分开：

* **贴界**——估计落在箱体边缘。真值有可能就在那里（本例即是），
  也常见于 `t0` 的逐被试收窄上界。**只报告，不剔除。**
* **退化**——SE 非有限/非正/相对量级过小，或拟合本身失败。Hessian 在该点不可用，
  点估计不可信。**先重试，仍退化才剔除。**

教训二：**「估计贴界」是箱体信息，「SE 退化」是曲率信息；用一个布尔把两者合并，
必然在某一侧犯错。**

判定规则
--------
对每个自由参数 x（合法区间 [lo, hi]）：

1. `SE` 非有限 或 `SE ≤ 0`                              ⇒ **退化**（Hessian 不可用）
2. `SE < PATHOLOGY_SE_REL · max(|x|, 1)`                ⇒ **退化**（相对量级过小）
3. `x` 距 `lo` 或 `hi` 不足 `BOUND_TOL_REL · (hi − lo)`  ⇒ **贴界**（仅报告）

判决取最严重者：`"degenerate"` > `"bound"` > `"ok"`。

处置（`fit_with_retry`）
------------------------
① 只要判决是 `degenerate`，起点数 ×4 重试，最多 `PATH_RETRIES` 轮（2 → 8 → 32）；
② 仍 `degenerate` ⇒ 返回判决与原因，由调用方**剔除并报告**，
   且必须同时给出「含病态」与「剔除后」两套统计，让读者自己判断影响；
③ `bound` **不重试、不剔除**，只进报告。

**绝不允许** `SE = 0` 的点默默进入任何汇总。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from likelihood import fit_mle, numerical_hessian  # noqa: E402
from mapping import PARAM_BOUNDS  # noqa: E402

# ------------------------------------------------------------------
# 阈值
# ------------------------------------------------------------------
PATHOLOGY_SE_REL = 1e-4   # SE < 1e-4 × max(|x|, 1) 视为 Hessian 退化
BOUND_TOL_REL = 1e-3      # 参数距边界 < 0.1% 界宽视为「贴界」
PATH_RETRIES = 2          # 重试轮数：起点数 2 → 8 → 32

#: 三值判决，严重度递增。
VERDICTS = ("ok", "bound", "degenerate")


def se_from_hessian(tr, names, p, bounds_override=None):
    """数值 Hessian → 无约束坐标 SE → delta 方法换算回参数坐标 SE。"""
    H, x0, lo, hi = numerical_hessian(tr, names, p,
                                      bounds_override=bounds_override)
    try:
        cov_x = np.linalg.pinv(H)
    except np.linalg.LinAlgError:
        return np.full(len(names), np.nan)
    se_x = np.sqrt(np.maximum(np.diag(cov_x), 0.0))
    s = 1.0 / (1.0 + np.exp(-x0))
    dtheta_dx = (hi - lo) * s * (1.0 - s)
    return se_x * dtheta_dx


def _bounds_of(nm, bounds_override):
    lo, hi = PARAM_BOUNDS[nm]
    if bounds_override and nm in bounds_override:
        lo, hi = bounds_override[nm]
    return float(lo), float(hi)


def pathology(x_vec, se_vec, names, bounds_override=None):
    """判定一次拟合的健康状况。

    返回 ``(verdict, reasons)``，``verdict ∈ {"ok", "bound", "degenerate"}``。

    **不要把 ``verdict == "bound"`` 当作失败**：真值可能就在边界上（见模块 docstring），
    调用方应当报告它，但不应据此剔除该次拟合。
    """
    degen: list[str] = []
    bound: list[str] = []
    for i, nm in enumerate(names):
        x = float(x_vec[i])
        se = float(se_vec[i])
        lo, hi = _bounds_of(nm, bounds_override)
        if not np.isfinite(se) or se <= 0.0:
            degen.append(f"{nm}: SE={se:.3g} 非正/非有限")
        elif se < PATHOLOGY_SE_REL * max(abs(x), 1.0):
            degen.append(f"{nm}: SE={se:.3g} ≪ |{x:.4g}|（Hessian 退化）")
        width = hi - lo
        if width > 0.0:
            tol = BOUND_TOL_REL * width
            if x - lo <= tol:
                bound.append(f"{nm}={x:.4g} 贴下界 {lo:g}")
            elif hi - x <= tol:
                bound.append(f"{nm}={x:.4g} 贴上界 {hi:g}")
    if degen:
        return "degenerate", degen + bound
    if bound:
        return "bound", bound
    return "ok", []


def is_excludable(verdict):
    """只有 `degenerate` 才允许被剔除；`bound` 必须保留。"""
    return verdict == "degenerate"


def fit_with_retry(tr, names, init, seed, bounds_override=None,
                   n_restart0=2, maxiter=250, maxfun=None):
    """带病态处置的拟合。

    返回 ``(fit, theta, se, verdict, reasons, n_restart_used)``。

    * 只有 ``verdict == "degenerate"`` 会触发「起点数 ×4」重试；
    * ``verdict == "bound"`` 立即返回（估计可信，只是落在箱体边缘）；
    * 调用方应使用 :func:`is_excludable` 决定是否剔除。
    """
    n_restart = n_restart0
    fit = theta = se = None
    reasons: list[str] = []
    verdict = "ok"
    for attempt in range(PATH_RETRIES + 1):
        kwargs = {}
        if maxfun is not None:
            kwargs["maxfun"] = maxfun
        fit = fit_mle(tr, names, init, n_restart=n_restart,
                      seed=seed + 7919 * attempt, maxiter=maxiter,
                      bounds_override=bounds_override, **kwargs)
        theta = fit["params"].vector(names)
        if fit["x"] is not None:
            se = se_from_hessian(tr, names, fit["params"],
                                 bounds_override=bounds_override)
        else:
            se = np.full(len(names), np.nan)
        verdict, reasons = pathology(theta, se, names, bounds_override)
        if not is_excludable(verdict):
            return fit, theta, se, verdict, reasons, n_restart
        n_restart *= 4
    return fit, theta, se, verdict, reasons, n_restart
