# -*- coding: utf-8 -*-
"""模型章渲染的冒烟自测（不需要真实数据、不跑 stage8）。

覆盖四件事：
  A1  `group_between` 能在 4 个 P 水平上把 `beta_P` 估回来（用映射真值造点）；
  A2  只有一个 P 水平时**不**硬拟合，返回 `None`（正是「组间回归需要 ≥2 水平」的守卫）；
  A3  `render_model` 把占位符换成值，`## 3.11` 之后的清单小节原样保留；
  A4  没给值的占位符**不静默留白**：换成 `【待数据：…】` 且出现在 `missed` 里。

用法：`python -X utf8 1_Code\\Experiment\\_scratch_check_model_chapter.py`
退出码 0 = 全过；1 = 有失败项。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(HERE))

import manuscript as MS  # noqa: E402

FAILS: list[str] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'✅' if cond else '❌'} {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


def synth_points(truth: dict, n_per_level: int = 4, levels=(0.0, 8.0, 32.0, 120.0),
                 noise: float = 0.0, seed: int = 7) -> list[dict]:
    """按 `mapping.drift_magnitude` 造「被试层估计」，噪声模拟估计误差。

    `drift_magnitude(P, T, is_self, p)` 的参考点取 `T_ref`、`is_self=0`，
    这样 `d_ref` 就是 P=P_ref 处的漂移，组间回归看到的就是真值。
    """
    import numpy as np
    from mapping import MappingParams, drift_magnitude

    p = MappingParams(beta_P=truth["beta_P"], tau_P=truth["tau_P"],
                      P_ref=truth["P_ref"], d_ref=truth["d_ref"],
                      beta_T=truth.get("beta_T", 0.55), beta_S=truth.get("beta_S", 0.16),
                      beta_SP=truth.get("beta_SP", 0.0))
    rng = np.random.default_rng(seed)
    pts = []
    for P in levels:
        d = float(drift_magnitude(np.array([P]), p.T_ref, 0.0, p)[0])
        for _ in range(n_per_level):
            pts.append({"P": float(P),
                        "d_ref": d + (rng.normal(0, noise) if noise else 0.0),
                        "beta_S": truth.get("beta_S", 0.16),
                        "beta_T": truth.get("beta_T", 0.55)})
    return pts


def main() -> int:
    truth = {"P_ref": 120.0, "d_ref": 0.70, "beta_P": 0.35, "tau_P": 30.0,
             "beta_S": 0.16, "beta_SP": 0.0, "beta_T": 0.55}

    # ---- A1：无噪声时应几乎精确复原
    pts = synth_points(truth, n_per_level=4, noise=0.0)
    gb = MS.group_between(pts, truth, n_boot=20)
    ok("A1 组间回归能跑", gb is not None)
    if gb:
        err = abs(gb["beta_P"] - truth["beta_P"])
        ok("A1 beta_P 复原", err < 0.05, f"估 {gb['beta_P']:.4f} vs 真 {truth['beta_P']}（差 {err:.4f}）")
        ok("A1 自举区间存在", gb.get("ci") is not None,
           f"CI = {gb.get('ci')}" if gb.get("ci") else "无 CI")

    # ---- A1b：加噪声后应仍在合理范围（不是精确复原，但别跑飞）
    pts_n = synth_points(truth, n_per_level=8, noise=0.06, seed=11)
    gb_n = MS.group_between(pts_n, truth, n_boot=20)
    if gb_n:
        ok("A1b 有噪声时 beta_P 仍接近真值", abs(gb_n["beta_P"] - truth["beta_P"]) < 0.12,
           f"估 {gb_n['beta_P']:.4f}")

    # ---- A2：单一 P 水平 ⇒ 不硬拟合
    one = synth_points(truth, n_per_level=8, levels=(0.0,))
    ok("A2 单水平返回 None", MS.group_between(one, truth, n_boot=10) is None)

    # ---- A3/A4：渲染
    tpl = ("# 测试\n\n组数 {{n_groups}}，被试 {{n_subjects_total}} 人，"
           "beta_P = {{beta_P}} {{beta_P_ci}}，beta_T = {{beta_T}}。\n\n"
           "演示语法：`{{双花括号}}` = 必须由数据填入。\n\n"
           "## 3.11 待填清单\n\n| `{{n_groups}}` | 数值总表 |\n")
    text, missed = MS.render_model(tpl, {"n_groups": "4", "n_subjects_total": "128",
                                         "beta_P": "0.351", "beta_T": "0.552"})
    ok("A3 正文的值被替换", "组数 4" in text and "128 人" in text and "beta_P = 0.351" in text)
    ok("A3 §3.11 数值总表也被替换", "| `4` | 数值总表 |" in text,
       "§3.11 是数值表，不是清单，必须替换")
    ok("A4 缺值换成【待数据】", "【待数据：β_P 的区间：只有 1 档 P 或自举样本不足】" in text,
       "缺项写原因，不写裸名字")
    ok("A4 missed 记录缺项", "beta_P_ci" in missed, f"missed = {missed}")
    ok("A3/A4 无残留 {{", "{{" not in text.replace("{{双花括号}}", ""),
       repr(text[:30]))
    ok("A6 演示用的例子标记不动", "{{双花括号}}" in text)

    # ---- A5：模板真的能加载、真的没有未声明的占位符命名
    t = MS.load_model_template()
    ok("A5 模型章模板可加载", len(t.splitlines()) > 200, f"{len(t.splitlines())} 行")
    names, bounds = MS._param_names()
    ok("A5 参数名 8 个且含 rho", len(names) == 8 and names[-1] == "rho", str(names))

    print()
    if FAILS:
        print(f"❌ {len(FAILS)} 项失败：" + "、".join(FAILS))
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
