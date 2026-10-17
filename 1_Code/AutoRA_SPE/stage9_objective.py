"""Stage 9 的**冻结 Objective**（事前登记 + 哈希锁定）。

对应 `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §6。
本文件是**唯一**的 Objective 事实来源：所有常量、聚合方式、判定线、罚则都写在
`FROZEN` 里；`SPEC_SHA256` 是它的哈希；`assert_frozen()` 在每次运行前自检。

为什么要哈希锁定
----------------
`1_Code/AutoRA_SPE/README.md` §6 的三条处方：
  ② 日志记录"试了多少配置"——否则优化器的搜索过程无法被审阅；
  ③ **冻结 Objective**——优化过程中改目标函数 = 事后为结果挑判据；
  ④ CRN（见 `stage9_inner.crn_seeds`）——所有迭代共用同一组种子。
处方 ③ 的机器可检形式就是本文件的 `assert_frozen()`。

三个分项（**全部来自 `5_Reference/.../Stage9_...md` §6.2，逐字实现**）
--------------------------------------------------------------------
(A) 参数恢复精度：`relSE_p = SE_p / |truth_p|`，取 **D24 确证集 `C6`** 的几何平均
    `A = exp( (1/6) · Σ_{p∈C6} ln relSE_p )`。**越小越好。**
    ⚠️ 参数集是 `C6`（6 个），**不是** `design_fim.PRIMARY`（5 个、含 `beta_ST`）。
    两者会给出相反的可用性判定（主计划 **D49**）；引用时**必须**写明是哪一套。

(B) 模型判别信息：`rho` 在 M-T1 下是被试层参数，判别力是**群体均值的检验**
    `SE_group(rho)² = [σ_ρ² + mean_s(SE_s(rho)²)] / N`、`B = |μ_ρ − 1| / SE_group(rho)`
    （期望 |t|）。**越大越好。** 事前登记 `μ_ρ = 0.6`、`σ_ρ = 0.25`，
    并**必须**把 `rho_sensitivity()` 给出的 3×3 网格一起报（结论对网格的依赖要标明）。

(C) 遗漏率约束：事前登记带 `[0.05, 0.20]`；越界按 **5 个百分点罚 1** 的二次罚。
    带内罚 0。**Stage 6 Pilot 到手后必须替换为实测区间**（见 §10）。

(D) 可行性闸门：`cond > 1e10` / `n_bad > 0` / `rt_ms > RT_CAP(1000 ms)` /
    `n_trials != 576` **一律拒收**。闸门不是罚分——被拒的设计**不进** Pareto 前沿。

合成（§6.3）
------------
    J = A_norm − 0.5 · B_norm + penalty_C          # A/B 各自按 D4 的值归一化
**论文主表用 (A, B) 的 Pareto 前沿**；标量 `J` **只**用来驱动优化器。
这是为了不让"权重 0.5"悄悄决定论文的推荐设计。

用法
----
    from stage9_objective import assert_frozen, evaluate, SPEC_SHA256
    assert_frozen()
    out = evaluate(res, N=40, anchor={"A": 0.268, "B": 1.0})

其中 `res` 是 `stage9_inner.inner_eval(...)` 的返回（M-T1、rho 自由）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[2]
for _p in (str(REPO / "1_Code" / "DDM_Core"), str(REPO / "1_Code" / "AutoRA_SPE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ------------------------------------------------------------------
# 1. 冻结规格（**改动此字典必须同步更新 SPEC_SHA256 与方案文档 §6.4**）
# ------------------------------------------------------------------
FROZEN: dict = {
    "spec_version": "1.0",
    "date": "2026-10-14",
    "source_doc": "5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md §6",
    # ---- (A) ----
    "params_C6": ["d_ref", "beta_T", "beta_S", "a_ref", "delta_a", "t0"],
    "A_aggregation": "geomean_relative_se",
    "A_bands": {"usable": 0.30, "marginal": 0.60},      # <0.30 ✅ / <0.60 ⚠️ / else ❌
    # ---- (B) ----
    "rho_mu": 0.6,
    "rho_sigma": 0.25,
    "rho_sensitivity": {"mu": [0.5, 0.6, 0.8], "sigma": [0.15, 0.25, 0.40]},
    "B_direction": "larger_is_better",
    # ---- (C) ----
    "omission_band": [0.05, 0.20],
    "omission_penalty_step_pp": 0.05,                   # 5 个百分点 → 罚 1
    # ---- (D) ----
    "cond_max": 1.0e10,
    "n_bad_max": 0,
    "rt_cap_ms": 1000.0,
    "n_trials_expected": 576,
    # ---- 合成 ----
    "weights": {"A": 1.0, "B": -0.5},
    "normalise_by": "anchor_design_D4",
    "main_table": "pareto_front_A_B",
}

#: `FROZEN` 的 sha256（`json.dumps(FROZEN, sort_keys=True)`，无分隔符压缩）。
#: ⚠️ 改 `FROZEN` 的任何一位都必须重算此值，并同步更新方案文档 §6.4 的正文。
SPEC_SHA256 = "cf5b57e05bbe1ea30dde307f2a607cf603a386132ca4284c2bddc552827676d4"

#: 锚点设计名（`1_Code/DDM_Core/design_fim.py::DESIGNS` 的键）
ANCHOR_DESIGN = "D4"


def compute_sha256(spec: dict | None = None) -> str:
    """`FROZEN` 的哈希（**唯一**算法：`sort_keys=True` 的紧凑 JSON）。"""
    payload = json.dumps(FROZEN if spec is None else spec,
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assert_frozen(spec: dict | None = None) -> str:
    """自检哈希；不一致就**拒绝运行**（处方 ③ 的机器可检形式）。"""
    got = compute_sha256(spec)
    if got != SPEC_SHA256:
        raise RuntimeError(
            "❗ 冻结 Objective 的规格与 `SPEC_SHA256` 不一致 —— 优化过程中改目标函数"
            "等于事后挑判据，禁止运行。\n"
            f"    记录的哈希 = {SPEC_SHA256}\n"
            f"    当前的哈希 = {got}\n"
            "    若这是**有意的**事前修订：重算哈希 → 更新本文件的 `SPEC_SHA256` "
            "→ 更新 `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §6.4 "
            "→ 在 §12 变更日志写明理由。")
    return got


# ------------------------------------------------------------------
# 2. 分项
# ------------------------------------------------------------------
def _index_of(res: dict, name: str) -> int:
    names = list(res["param_names"])
    if name not in names:
        raise ValueError(
            f"参数 {name!r} 不在本次内环评估的参数集里（{names}）——"
            "Objective (A) 需要 C6 的 6 个参数全部在场。"
            "若用 M-T1，请确认 `include_rho` 之外的 7 个 lin 参数已全部包含。")
    return names.index(name)


def component_A(res: dict, params: list[str] | None = None) -> float:
    """(A) `C6` 相对 SE 的几何平均（**越小越好**）。"""
    ps = list(FROZEN["params_C6"] if params is None else params)
    rel = np.asarray(res["relative_se"], dtype=float)
    vals = np.array([rel[_index_of(res, k)] for k in ps], dtype=float)
    if not np.all(np.isfinite(vals)):
        raise ValueError(f"(A) 的相对 SE 含非有限值：{dict(zip(ps, vals.tolist()))}")
    if np.any(vals <= 0.0):
        raise ValueError(f"(A) 的相对 SE 必须为正：{dict(zip(ps, vals.tolist()))}")
    return float(np.exp(np.mean(np.log(vals))))


def component_B(se_rho: float, n_subjects: int,
                mu_rho: float | None = None,
                sigma_rho: float | None = None) -> float:
    """(B) `rho` 的组层期望 |t|（**越大越好**）。

    `se_rho` 是**逐被试**的 `rho` SE（`inner_eval` 的 `se_rho`：人均信息矩阵的
    `pinv` 对角），`n_subjects` 是每组人数。
    """
    mu = float(FROZEN["rho_mu"] if mu_rho is None else mu_rho)
    sd = float(FROZEN["rho_sigma"] if sigma_rho is None else sigma_rho)
    if not np.isfinite(se_rho) or se_rho < 0.0:
        raise ValueError(f"(B) se_rho 必须是非负有限值，收到 {se_rho!r}"
                         "（M-T3 下 rho 不存在 ⇒ 必须用 M-T1 评估）")
    if int(n_subjects) < 1:
        raise ValueError(f"(B) n_subjects 必须 ≥ 1，收到 {n_subjects!r}")
    se_group = np.sqrt((sd ** 2 + float(se_rho) ** 2) / float(n_subjects))
    return float(abs(mu - 1.0) / se_group)


def component_C(omission: float, band: list[float] | None = None) -> float:
    """(C) 遗漏率罚分（带内 0；越界按 5 个百分点罚 1 的二次罚）。"""
    lo, hi = (FROZEN["omission_band"] if band is None else [float(x) for x in band])
    step = float(FROZEN["omission_penalty_step_pp"])
    o = float(omission)
    if lo <= o <= hi:
        return 0.0
    over = (o - hi) if o > hi else (lo - o)
    return float((over / step) ** 2)


def gates(res: dict) -> list[str]:
    """(D) 可行性闸门；返回违规说明列表（空 = 通过）。

    ⚠️ `cond` 与 `n_bad` 取自 `inner_eval`，它们与 `design_fim.design_se` **同源**
    （都用 `likelihood.fim_diagnostics`），不能换成 `np.linalg.cond`。
    """
    out = []
    cond = float(res.get("cond", np.inf))
    if not np.isfinite(cond) or cond > float(FROZEN["cond_max"]):
        out.append(f"cond={cond:.3g} > {FROZEN['cond_max']:.0e}（病态，相关不可信）")
    n_bad = int(res.get("n_bad", 0))
    if n_bad > int(FROZEN["n_bad_max"]):
        out.append(f"n_bad={n_bad} > {FROZEN['n_bad_max']}（有不可识别方向）")
    rt = float(res.get("rt_ms", np.nan))
    if not np.isfinite(rt) or rt > float(FROZEN["rt_cap_ms"]):
        out.append(f"rt_ms={rt:.1f} > {FROZEN['rt_cap_ms']:.0f}（行为负担）")
    nt = int(res.get("n_trials", -1))
    if nt != int(FROZEN["n_trials_expected"]):
        out.append(f"n_trials={nt} != {FROZEN['n_trials_expected']}（总试次必须固定）")
    # 相对 SE 必须**全部**有限且为正：退化评估不得进 Pareto 前沿。
    # ⚠️ 这里查的是**整条** relative_se，不只 C6 —— `n_bad` 只反映特征值，
    #    而真值为 0 / 分母退化会让某一个参数的相对 SE 直接变成 inf，
    #    那种评估结果不是一个可以拿去比较的设计。
    rel = np.asarray(res.get("relative_se", []), dtype=float)
    bad_rel = [str(n) for n, v in zip(res.get("param_names", []), rel)
               if not (np.isfinite(v) and v > 0.0)]
    if rel.size == 0 or bad_rel:
        out.append(f"relative_se 非有限或非正：{bad_rel or '空'}"
                   "（该评估退化，不能参与比较）")
    return out


# ------------------------------------------------------------------
# 3. 合成与 Pareto
# ------------------------------------------------------------------
def evaluate(res: dict, n_subjects: int, anchor: dict,
             mu_rho: float | None = None,
             sigma_rho: float | None = None,
             band: list[float] | None = None) -> dict:
    """把一个内环评估结果折算成 `(A, B, C, J, gates)`。

    `anchor` = `{"A": A(锚点设计), "B": B(锚点设计)}`，**必须由同一个内环评估器
    在同样的 N 上算出**（`normalise_by = "anchor_design_D4"`）；它**不是**冻结常量，
    所以每轮都要落盘，供审阅。

    `J` **只**用于驱动优化器；论文主表用 `pareto_front()`。
    """
    A = component_A(res)
    if res["model"] == "M-T3" or not np.isfinite(float(res.get("se_rho", np.nan))):
        raise ValueError("Objective (B) 需要 M-T1（rho 自由）的评估结果 —— "
                         "M-T3 下 rho 不存在，B 无从计算")
    B = component_B(float(res["se_rho"]), int(n_subjects), mu_rho, sigma_rho)
    C = component_C(float(res["omission"]), band)
    bad = gates(res)

    a_ref, b_ref = float(anchor["A"]), float(anchor["B"])
    if not (np.isfinite(a_ref) and a_ref > 0 and np.isfinite(b_ref) and b_ref > 0):
        raise ValueError(f"anchor 必须是两个正的有限值，收到 {anchor!r}")
    A_norm, B_norm = A / a_ref, B / b_ref
    J = A_norm + float(FROZEN["weights"]["B"]) * B_norm + C
    return {"A": A, "B": B, "C": C, "J": J,
            "A_norm": A_norm, "B_norm": B_norm,
            "A_verdict": verdict_A(A),
            "gates": bad, "feasible": not bad,
            "n_subjects": int(n_subjects),
            "mu_rho": float(FROZEN["rho_mu"] if mu_rho is None else mu_rho),
            "sigma_rho": float(FROZEN["rho_sigma"] if sigma_rho is None else sigma_rho),
            "omission": float(res["omission"]), "rt_ms": float(res["rt_ms"]),
            "spec_sha256": SPEC_SHA256}


def verdict_A(A: float) -> str:
    """(A) 的既有分档（`design_fim` 的判定线，逐字沿用）。"""
    bands = FROZEN["A_bands"]
    if A < bands["usable"]:
        return "✅可用"
    if A < bands["marginal"]:
        return "⚠️勉强"
    return "❌不可用"


def rho_sensitivity() -> list[dict]:
    """(B) 的事前登记敏感性网格（3×3，**必须随结果一起报**）。"""
    g = FROZEN["rho_sensitivity"]
    return [{"mu": float(m), "sigma": float(s)} for m in g["mu"] for s in g["sigma"]]


def pareto_front(points: list[dict]) -> list[dict]:
    """(A, B) 的 Pareto 前沿：A 越小越好、B 越大越好。

    `points` 的每项须含 `A`、`B`，可选 `name`。被**拒收**（`gates` 非空）的点
    请先过滤掉再传进来 —— 闸门不参与权衡。
    返回按 `A` 升序排列的前沿子集。
    """
    pts = [p for p in points if np.isfinite(p["A"]) and np.isfinite(p["B"])]
    front = []
    for p in pts:
        dominated = any((q["A"] <= p["A"] and q["B"] >= p["B"])
                        and (q["A"] < p["A"] or q["B"] > p["B"]) for q in pts)
        if not dominated:
            front.append(p)
    return sorted(front, key=lambda p: p["A"])


def spec_card() -> dict:
    """"这次跑了什么规格"的可落盘卡片（处方 ②）。"""
    return {"frozen": FROZEN, "sha256": SPEC_SHA256,
            "anchor_design": ANCHOR_DESIGN,
            "rho_sensitivity_grid": rho_sensitivity()}


# ------------------------------------------------------------------
# 4. 自检
# ------------------------------------------------------------------
def main() -> int:
    print("=" * 92)
    print("Stage 9 冻结 Objective —— 规格卡片")
    print("=" * 92)
    print(json.dumps(FROZEN, ensure_ascii=False, indent=2, sort_keys=True))
    got = compute_sha256()
    print(f"\nspec_version = {FROZEN['spec_version']}     date = {FROZEN['date']}")
    print(f"sha256(当前 FROZEN) = {got}")
    print(f"SPEC_SHA256(记录)   = {SPEC_SHA256}")
    print(f"一致 = {got == SPEC_SHA256}")
    if got != SPEC_SHA256:
        print("\n❗ 哈希不一致 —— `assert_frozen()` 会拒绝运行（这正是它存在的理由）。")
        print("   若本次是**有意的**事前修订，请把上面的哈希写进 SPEC_SHA256 与方案 §6.4。")
        return 1

    assert_frozen()
    print("\n✅ assert_frozen() 通过")

    # ---- 分项的单元自检（纯算术，不跑内环） ----
    print("\n" + "-" * 92)
    print("分项自检（用构造的 res，不跑仿真）")
    print("-" * 92)
    names = ["d_ref", "beta_T", "beta_S", "beta_ST", "a_ref", "delta_a", "t0", "rho"]
    res = {"param_names": names,
           "relative_se": np.array([0.147, 0.636, 0.707, 4.739, 0.038, 2.564, 0.057, 0.30]),
           "model": "M-T1", "se_rho": 0.30, "omission": 0.314, "rt_ms": 761.0,
           "cond": 1.1e5, "n_bad": 0, "n_trials": 576}
    A = component_A(res)
    expect = float(np.exp(np.mean(np.log([0.147, 0.636, 0.707, 0.038, 2.564, 0.057]))))
    print(f"  A = {A:.6f}（手算 {expect:.6f}，一致 = {abs(A - expect) < 1e-12}）")
    print(f"      A 的分档 = {verdict_A(A)}；锚点 A(D4) = 0.268（README §9 第 31 项）")
    B = component_B(0.30, 40)
    print(f"  B(se_rho=0.30, N=40) = {B:.4f}"
          f"  （SE_group = {np.sqrt((0.25**2 + 0.30**2) / 40):.6f}）")
    print(f"  C(omission=0.314) = {component_C(0.314):.4f}"
          f"（带 = {FROZEN['omission_band']}，越界 {(0.314 - 0.20) / 0.05:.2f} 步 ⇒"
          f" 二次罚 {(0.114 / 0.05) ** 2:.2f}）")
    print(f"  闸门 = {gates(res) or '全部通过'}")
    print(f"  敏感性网格 {len(rho_sensitivity())} 格："
          f"{[(r['mu'], r['sigma']) for r in rho_sensitivity()]}")

    # ---- 闸门必须有牙齿 ----
    print("\n牙齿测试（每个闸门都必须拒收，而不是静默算出一个数）：")
    for key, val, why in [("cond", 1e11, "病态"), ("n_bad", 1, "不可识别方向"),
                          ("rt_ms", 1200.0, "行为负担"), ("n_trials", 192, "试次数不对")]:
        r2 = dict(res)
        r2[key] = val
        g = gates(r2)
        print(f"  {key}={val!r:>8}（{why}）→ {'✅ 拒收：' + g[0] if g else '❌ 未拦下！'}")
    # 第 5 道闸门：relative_se 里任何一个非有限/非正值（**不只 C6**）
    for idx, tag in [(3, "beta_ST（不在 C6 里，也必须拦）"), (0, "d_ref（在 C6 里）")]:
        r2 = dict(res)
        rel2 = np.array(res["relative_se"], dtype=float)
        rel2[idx] = np.inf
        r2["relative_se"] = rel2
        g = gates(r2)
        print(f"  relative_se[{tag}] = inf → "
              f"{'✅ 拒收：' + g[0] if g else '❌ 未拦下！'}")

    # ---- 合成路径 evaluate() 必须真的跑一遍 ----
    print("\n" + "-" * 92)
    print("合成路径 evaluate()（anchor 用 D4 的实测值：A = 0.268、B 归一化基准取本 res 的 B）")
    print("-" * 92)
    anch = {"A": 0.268, "B": B}          # B 的锚点必须同基准；此处只为打通路径
    ev = evaluate(res, n_subjects=40, anchor=anch)
    print(f"  A = {ev['A']:.6f}（{ev['A_verdict']}）   A_norm = {ev['A_norm']:.6f}")
    print(f"  B = {ev['B']:.4f}   B_norm = {ev['B_norm']:.6f}")
    print(f"  C = {ev['C']:.4f}   J = {ev['J']:.6f}   feasible = {ev['feasible']}")
    print(f"  spec_sha256 = {ev['spec_sha256']}")
    # (B) 的敏感性：同一 se_rho 在 3×3 网格上的取值范围
    bs = [component_B(0.30, 40, r["mu"], r["sigma"]) for r in rho_sensitivity()]
    print(f"  B 在 3×3 网格上 = {min(bs):.3f} … {max(bs):.3f}"
          f"（跨 {max(bs) / min(bs):.2f}× ⇒ **必须连同网格一起报**）")

    # ---- 守卫必须有牙齿（报错而不是静默算出一个数） ----
    print("\n守卫牙齿测试：")
    bad_res = dict(res, model="M-T3", se_rho=float("nan"))
    for label, fn, arg in [
            ("evaluate() 收到 M-T3（rho 不存在）", lambda a: evaluate(a, 40, anch), bad_res),
            ("component_A 缺 C6 成员", lambda a: component_A(
                dict(a, param_names=["d_ref", "beta_T"], relative_se=np.array([0.1, 0.2]))), res),
            ("component_A 收到 C6 内的非有限相对 SE", lambda a: component_A(
                dict(a, relative_se=np.array([np.inf, 0.636, 0.707, 4.739, 0.038, 2.564, 0.057, 0.30]))), res),
            ("component_B 收到负 se_rho", lambda a: component_B(-0.1, 40), res),
            ("component_B 收到 N=0", lambda a: component_B(0.3, 0), res),
            ("evaluate() 收到非正 anchor", lambda a: evaluate(a, 40, {"A": 0.0, "B": 1.0}), res)]:
        try:
            fn(arg)
            print(f"  {label} → ❌ 未报错（静默算出了一个数）！")
        except (ValueError, RuntimeError) as exc:
            print(f"  {label} → ✅ {type(exc).__name__}: {str(exc).splitlines()[0][:76]}")
    try:
        assert_frozen(dict(FROZEN, cond_max=1e12))
        print("  assert_frozen() 收到被篡改的规格 → ❌ 未报错！")
    except RuntimeError:
        print("  assert_frozen() 收到被篡改的规格 → ✅ RuntimeError（处方 ③ 的机器可检形式）")

    # ---- Pareto 前沿的手算例子 ----
    demo = [{"name": "p1", "A": 0.30, "B": 2.0},
            {"name": "p2", "A": 0.25, "B": 1.5},   # 被 p1 支配？ A 更小但 B 更小 ⇒ 不被支配
            {"name": "p3", "A": 0.35, "B": 1.0},   # 被 p1 支配（A 大、B 小）
            {"name": "p4", "A": 0.20, "B": 3.0}]   # 支配 p1/p2/p3
    front = pareto_front(demo)
    print(f"\nPareto 前沿示例 = {[p['name'] for p in front]}（期望 ['p4']）"
          f" ⇒ {'✅' if [p['name'] for p in front] == ['p4'] else '❌'}")

    print("\n" + "=" * 92)
    print("下一步：`stage9_loop.py`（CRN 预计算表 + 四路消融）—— 本文件只定义目标。")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
