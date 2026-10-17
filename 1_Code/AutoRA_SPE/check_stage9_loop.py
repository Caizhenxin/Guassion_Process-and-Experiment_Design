#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""`stage9_loop.py` 的自测：候选空间、单位、CRN、预算公平性、比较纪律。

判据纪律（本项目已多次踩坑，见 `1_Code/DDM_Core/README.md` §8.19/§8.25/§8.27）：
**判据必须来自实测的抽样分布，不能来自期望。** 因此本文件里的每个阈值都附上
它是在哪个配置下量到的；凡是"应该相等"的地方一律用逐位相等或相对差，不用"看起来差不多"。

用法：
    python check_stage9_loop.py [n_fim] [输出路径]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import stage9_inner as S9I          # noqa: E402
import stage9_loop as L             # noqa: E402
import stage9_objective as S9O      # noqa: E402
from spe_timing_convention import current_postmask_pressable_ms  # noqa: E402

N_FIM = int(sys.argv[1]) if len(sys.argv) > 1 else 1
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else None
RHO = float(S9O.FROZEN["rho_mu"])

_RESULTS: list[tuple[str, bool, str]] = []
_NOTES: list[tuple[str, str]] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    _RESULTS.append((label, bool(ok), detail))
    print(f"{'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""),
          flush=True)
    return bool(ok)


def note(label: str, detail: str) -> None:
    """记录一条**实测读数**（不是判据，不计入通过/未通过）。"""
    _NOTES.append((label, detail))
    print(f"  · {label}：{detail}", flush=True)


def main() -> int:
    t_start = time.time()
    print("=" * 72)
    print(f"stage9_loop 自测（n_fim={N_FIM}、rho={RHO}）")
    print("=" * 72)

    designs = L.enumerate_designs()
    names = [d["name"] for d in designs]

    # ---------------- A 组：候选空间与坐标 ----------------
    print("\n[A 组] 候选空间与坐标")
    check("A1 每个候选设计的 n_trials 都等于冻结值 576",
          all(d["n_trials"] == S9O.FROZEN["n_trials_expected"] for d in designs),
          f"共 {len(designs)} 个候选")
    n_t_set = sorted({len(d["T_ms"]) for d in designs})
    n_w_set = sorted({len(d["W_ms"]) for d in designs})
    n_rep_set = sorted({d["n_rep"] for d in designs})
    note("A1b 候选空间形状", f"n_t∈{n_t_set} n_w∈{n_w_set} n_rep∈{n_rep_set}")
    check("A2 锚点 D4 在候选集里，且名字与 T_POOL[:4]×W_POOL[:3]×r12 逐字一致",
          L.ANCHOR_DESIGN in names
          and L.design_name(L.T_POOL_MS[:4], L.W_POOL_MS[:3], 12) == L.ANCHOR_DESIGN,
          L.ANCHOR_DESIGN)
    # levels_sec：毫秒 → 秒，逐位
    check("A3 `levels_sec` 是毫秒→秒（33.33 → 0.03333，逐位）",
          L.levels_sec((33.33, 149.99)) == (0.03333, 0.14999),
          f"{L.levels_sec((33.33, 149.99))}")
    # postmask_s 必须与桥模块逐位一致（不允许自己重写一个 W−T−0.2）
    worst_u = max(abs(L.postmask_s(t, w)
                      - current_postmask_pressable_ms(t, w) / 1000.0)
                  for t in L.T_POOL_MS for w in L.W_POOL_MS)
    check("A4 `postmask_s` 与桥模块的 `current_postmask_pressable_ms` 逐位一致",
          worst_u == 0.0, f"max|Δ| = {worst_u:.3e}")
    # C3 是真正的过滤器（不是 C1）
    import itertools
    n_c1 = n_c3 = 0
    for n_t in L.N_T_CHOICES:
        for n_w in L.N_W_CHOICES:
            if L.CELL_BUDGET % (n_t * n_w):
                continue
            for Ts in itertools.combinations(L.T_POOL_MS, n_t):
                for Ws in itertools.combinations(L.W_POOL_MS, n_w):
                    try:
                        for T in Ts:
                            for W in Ws:
                                L.check_design(T, W)
                    except ValueError as exc:
                        if "C3 违反" in str(exc):
                            n_c3 += 1
                        else:
                            n_c1 += 1
    note("A5 可行性过滤的构成", f"被 C1 否决 {n_c1} 个、被 C3 否决 {n_c3} 个")
    check("A5b 全部否决都来自 C3（C1 单独不会剔除任何候选）", n_c1 == 0,
          f"被 C1 否决 {n_c1} 个")

    # ---------------- B 组：单位与缓存（关键牙齿）----------------
    print("\n[B 组] 单位与缓存（这一组就是为‘毫秒当秒’那个坑立的）")
    one = [d for d in designs if d["name"] == L.ANCHOR_DESIGN]
    ev = L.Evaluator(one, n_fim=N_FIM, n_subjects=40, verbose=False)
    t0 = time.time()
    rec = ev.get(L.ANCHOR_DESIGN)
    dt = time.time() - t0
    direct = S9I.inner_eval(L.levels_sec(one[0]["T_ms"]),
                            L.levels_sec(one[0]["W_ms"]), one[0]["n_rep"],
                            model=S9I.M_T1, rho=RHO, n_fim=N_FIM,
                            seed=L.cell_seed(L.ANCHOR_DESIGN))
    d_rel = float(np.max(np.abs(np.asarray(rec["relative_se"])
                                - np.asarray(direct["relative_se"]))))
    check("B1 缓存路径与直接 `inner_eval` 的 relative_se **逐位相同**",
          d_rel == 0.0, f"max|Δ| = {d_rel:.3e}（{dt:.1f}s）")
    check("B1b omission / rt_ms / cond / se_rho 也逐位相同",
          rec["omission"] == direct["omission"]
          and rec["rt_ms"] == direct["rt_ms"]
          and rec["cond"] == direct["cond"]
          and rec["se_rho"] == direct["se_rho"],
          f"omission={rec['omission']:.4f} rt={rec['rt_ms']:.1f}ms "
          f"cond={rec['cond']:.3g} se_rho={rec['se_rho']:.4f}")
    check("B1c 锚点读数落在健康区间（cond < 1e10、n_bad = 0、遗漏在带外也算读数）",
          np.isfinite(rec["cond"]) and rec["cond"] < S9O.FROZEN["cond_max"],
          f"cond={rec['cond']:.3g} n_bad={rec['n_bad']} "
          f"omission={rec['omission']:.4f} A={rec['A']:.4f} B={rec['B']:.4f}")

    # ❗ 把"毫秒当秒"这个失败模式固定成测试：它**不报错**，只是静默给出垃圾
    bad = S9I.inner_eval(one[0]["T_ms"], one[0]["W_ms"], one[0]["n_rep"],
                         model=S9I.M_T1, rho=RHO, n_fim=N_FIM,
                         seed=L.cell_seed(L.ANCHOR_DESIGN))
    d_om = abs(bad["omission"] - rec["omission"])
    check("B2 把毫秒当秒喂进去会给出**完全不同**的读数（这个坑不报错）",
          d_om > 0.2 and bad["cond"] > 1e3 * rec["cond"],
          f"Δ遗漏={d_om:.3f}；cond {bad['cond']:.3g} vs {rec['cond']:.3g}")

    n_before = ev.n_evals
    ev.get(L.ANCHOR_DESIGN)
    check("B3 缓存命中不重算（第二次 get 的 n_evals 不变）",
          ev.n_evals == n_before, f"n_evals = {ev.n_evals}")

    # ---------------- C 组：CRN ----------------
    print("\n[C 组] CRN：种子由内容决定、与候选表形状无关")
    truncated = designs[:20]
    if L.ANCHOR_DESIGN not in [d["name"] for d in truncated]:
        truncated = truncated + one
    ev2 = L.Evaluator(truncated, n_fim=N_FIM, n_subjects=40, verbose=False)
    rec2 = ev2.get(L.ANCHOR_DESIGN)
    check("C1 同一个设计在完整表与截断表里有**相同的 CRN 种子与相同读数**"
          "（种子由内容导出，不由下标导出）",
          ev2.index[L.ANCHOR_DESIGN] != ev.index[L.ANCHOR_DESIGN]
          and rec2["seed"] == rec["seed"]
          and rec2["relative_se"] == rec["relative_se"],
          f"seed={rec['seed']}；下标 完整表={ev.index[L.ANCHOR_DESIGN]} "
          f"截断表={ev2.index[L.ANCHOR_DESIGN]}")
    seeds = [L.cell_seed(n) for n in names[:200]]
    check("C2 不同设计的种子不碰撞", len(set(seeds)) == len(seeds),
          f"{len(seeds)} 个设计 → {len(set(seeds))} 个不同种子")
    r_a = ev.get(L.ANCHOR_DESIGN)
    check("C3 同一 Evaluator 重复取同一设计，读数逐位不变",
          r_a["relative_se"] == rec["relative_se"] and r_a["J"] == rec["J"],
          f"J = {rec['J']:.6f}")

    # ---------------- D 组：四臂同预算 ----------------
    print("\n[D 组] 四臂同预算（消融的前提）")
    sub = [d for d in designs[:6]]
    if L.ANCHOR_DESIGN not in [d["name"] for d in sub]:
        sub = sub + one
    ev3 = L.Evaluator(sub, n_fim=N_FIM, n_subjects=40, verbose=False)
    budget = 4
    hist = L.run_arms(ev3, budget, seed=0, noise={"alpha": 1e-6, "sd_J": 0.01})
    lens = {a: len(h["picked"]) for a, h in hist.items()}
    check(f"D1 四个臂都用满且仅用 {budget} 次评估",
          all(v == budget for v in lens.values()), f"{lens}")
    check("D2 `arm_bo` 的 `n_init` 被预算夹住（budget=3 时取 3 个，不会按 n_init=8 超支）",
          len(L.arm_bo(ev3, 3, np.random.default_rng(0))) == 3,
          "budget=3 < 默认 n_init=8")
    n_grid = [d["name"] for d in designs[:6]]
    picked_grid = L.arm_grid(ev3, 6)
    check("D3 `arm_grid` 不是‘候选表前 N 个’（那是一个有偏的角落样本）",
          sorted(picked_grid) != sorted(n_grid),
          f"grid 取 {len(picked_grid)} 个，与前 6 个{'相同' if sorted(picked_grid) == sorted(n_grid) else '不同'}")

    # D2b：预算守卫有牙齿 —— 人为让一个臂超支
    saved = L.ARMS["grid"]
    try:
        L.ARMS["grid"] = lambda e, b, rng=None: [d["name"] for d in designs[:b + 1]]
        raised = False
        try:
            L.run_arms(ev3, budget, seed=0, noise={"alpha": 1e-6, "sd_J": 0.01})
        except RuntimeError:
            raised = True
    finally:
        L.ARMS["grid"] = saved
    check("D2b 预算守卫有牙齿：某臂超支时报 RuntimeError（不静默继续）", raised)

    # ---------------- E 组：臂间比较纪律（D54：判据只建立在 (A)/(B) 上） ----------------
    print("\n[E 组] 臂间比较纪律（D54：只比较 (A) 最小点上的 (A,B)，差异须超噪声带）")

    def _arm(a_name, a_v, b_v):
        return {a_name: {"best_J": 9.9, "best_name": f"{a_name}-pt", "seconds": 1.0,
                         "best_A": a_v, "B_at_A_best": b_v, "A_best_name": f"{a_name}-pt",
                         "n_feasible": 3, "B_max": b_v}}

    # 噪声带：2·sd_A = 0.04、2·sd_B = 0.10
    NOISE = {"sd_J": 0.10, "sd_A": 0.02, "sd_B": 0.05}

    rows = L.compare_arms({**_arm("grid", 0.40, 8.0), **_arm("random", 0.42, 8.0)}, NOISE)
    top = [r for r in rows if r["arm"] == "grid"][0]
    check("E1 前两名 ΔA = 0.02 ≤ 噪声带 0.04 ⇒ 必须说不可分辨、不得宣称最好",
          "不可分辨" in top["verdict"] and "不得宣称最好" in top["verdict"],
          top["verdict"])

    rows2 = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.40, 8.0)}, NOISE)
    top2 = [r for r in rows2 if r["arm"] == "grid"][0]
    check("E2 ΔA = 0.10 > 0.04 且 B 不差 ⇒ 才允许说「本预算下 (A,B) 上最好」",
          "本预算下 (A,B) 上最好" in top2["verdict"], top2["verdict"])

    rows2b = L.compare_arms({**_arm("grid", 0.30, 6.0), **_arm("random", 0.50, 8.0)}, NOISE)
    top2b = [r for r in rows2b if r["arm"] == "grid"][0]
    check("E2b 头名 A 更好但 B 明显更差 ⇒ 必须判「权衡」且明说「不得宣称最好」"
          "（A 赢不能抵消 B 输）",
          "权衡" in top2b["verdict"] and "不得宣称最好" in top2b["verdict"],
          top2b["verdict"])

    rows3 = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.50, 6.0)}, NOISE)
    r3 = [r for r in rows3 if r["arm"] == "random"][0]
    check("E3 A 更差且 B 也更差（两个差都超带）⇒ 必须判「被支配」",
          "支配" in r3["verdict"], r3["verdict"])

    rows4 = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.50, 9.0)}, NOISE)
    r4 = [r for r in rows4 if r["arm"] == "random"][0]
    check("E4 A 更差但 B 更好（都超带）⇒ 必须判「权衡」且明说「不可排序」，"
          "不许用单一标量硬排",
          "权衡" in r4["verdict"] and "不可排序" in r4["verdict"], r4["verdict"])

    rows5 = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.50, 8.02)}, NOISE)
    r5 = [r for r in rows5 if r["arm"] == "random"][0]
    check("E5 ΔA 超带但 ΔB 落在噪声带内 ⇒ 必须判「在 (A) 上显著更差」，"
          "**不得**把 A 上 5 倍的差距说成「两者不可分辨」（那正是洗白）",
          "显著更差" in r5["verdict"], r5["verdict"])

    # E8：判据的**先决条件** —— 「没有可行点」不等于「更差」，更不等于「最好」。
    # 实测踩过：`--budget 2` 全空间冒烟里三条臂的 `A_best` 是 `inf`，旧代码把
    # `gap = inf - 0.39` 当成"领先很多"，印成「本预算下 (A,B) 上最好（… A 小 inf > 噪声带 0.0050）」
    # ⇒ 把**没有数据**说成了**大幅领先**。
    def _arm_nopt(a_name):
        """一条在本预算内**没有抽到任何可行点**的臂（`A_best = inf`）。"""
        return {a_name: {"best_J": float("inf"), "best_name": "", "seconds": 1.0,
                         "best_A": float("inf"), "B_at_A_best": float("nan"),
                         "A_best_name": "", "n_feasible": 0, "B_max": float("nan")}}

    rows8 = L.compare_arms({**_arm("grid", 0.39, 8.0), **_arm_nopt("random"),
                            **_arm_nopt("manual"), **_arm_nopt("bo")}, NOISE)
    top8 = [r for r in rows8 if r["arm"] == "grid"][0]
    norandom = [r for r in rows8 if r["arm"] == "random"][0]
    check("E8 只有一条臂有可行点、其余三条都 `inf` ⇒ 头名必须说「无对照、不构成排序证据」，"
          "**不得**写成「(A,B) 上最好」（那会把「没数据」当成「领先」）",
          "只有它一条臂" in top8["verdict"] and "无对照" in top8["verdict"]
          and "本预算下 (A,B) 上最好" not in top8["verdict"],
          top8["verdict"])
    check("E8b `A_best = inf` 的臂必须判「可行集内没有任何设计 ⇒ 不参与排序」，"
          "且标记 `has_feasible_point = False`（不是「更差」）",
          "可行集内没有任何设计" in norandom["verdict"]
          and "不参与排序" in norandom["verdict"]
          and norandom["has_feasible_point"] is False
          and norandom["n_feasible"] == 0,
          f"has_feasible_point={norandom['has_feasible_point']}；{norandom['verdict']}")
    rows8b = L.compare_arms({**_arm_nopt("grid"), **_arm_nopt("random"),
                             **_arm_nopt("manual"), **_arm_nopt("bo")}, NOISE)
    check("E8c 四条臂全都没有可行点 ⇒ 必须说「无对照、无排序证据、这不是谁更差而是没有数据」",
          all("没有任何一条臂" in r["verdict"] and "没有数据" in r["verdict"] for r in rows8b)
          and all(r["has_feasible_point"] is False for r in rows8b),
          rows8b[0]["verdict"])
    rows8d = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.40, 8.0),
                             **_arm_nopt("manual"), **_arm_nopt("bo")}, NOISE)
    top8d = [r for r in rows8d if r["arm"] == "grid"][0]
    check("E8d 回归：有真对照时仍须允许说「(A,B) 上最好」，**并如实注明**有 2 条臂没有可行点"
          "（修 E8 不得把正常路径也堵死）",
          "本预算下 (A,B) 上最好" in top8d["verdict"]
          and "另有 2 条臂在本预算内没有可行点" in top8d["verdict"],
          top8d["verdict"])

    # ---------------- E9 组：`arm_bo` 在小预算下不得超支（D58） ----------------
    # ❗ 实测缺陷：`n_init = max(2, min(n_init, budget))` 在 `--budget 1` 时得到 2 ⇒
    #    BO 臂评估 2 个点 ⇒ `run_arms` 的「四路消融必须同预算」守卫抛 RuntimeError
    #    ⇒ **整轮跑不完**（2026-10-16：`--budget 1 --n-fim 12` 跑到臂 bo 中断，7 次评估白跑）。
    #    守卫是对的，错的是下限 2。这里用**桩评估器**测真实 `arm_bo` 的取点数。
    print("\n[E 组·续] `arm_bo` 的预算纪律：预算 1 必须只取 1 个点（D58）")

    class _StubEv:
        """只实现 `arm_bo` 真正用到的那几个方法（避免为了一个取点数跑内环）。"""

        def __init__(self, n_pt=6):
            self.designs = [{"name": f"d{i}"} for i in range(n_pt)]
            self.noise_alpha = 0.1
            self.got = []
            self.cache = {}

        def features(self, name):
            i = int(name[1:])
            return np.array([i / 5.0, (i % 2) / 1.0])

        def get(self, name):
            self.got.append(name)
            return {"J": 1.0}

        def value(self, name):
            return 1.0

    for _b in (1, 2, 3):
        _ev9 = _StubEv()
        _picked9 = L.arm_bo(_ev9, _b, np.random.default_rng(0))
        check(f"E9 预算 {_b} ⇒ BO 臂取点数必须**逐字等于**预算（多取一个就会触发同预算守卫并中断整轮）",
              len(_picked9) == _b and len(_ev9.got) == _b,
              f"取点数 {len(_picked9)}、评估数 {len(_ev9.got)}")

    # ---------------- E10 组：`(A)` 在带内、但 `(B)` 差别很大（D59） ----------------
    # ❗ 实测缺陷：`compare_arms` 里 `gap <= band_a` 那一支**直接**印「在 (A) 与 (B) 上都不可分辨」，
    #    完全不看 `ΔB` ⇒ E5 的镜像（E5 管「ΔA 超带、ΔB 在带内」，这里管「ΔA 在带内、ΔB 超带」）。
    #    后果：把「(A) 分不出高下，但 (B) 上有两倍带宽的差距」说成「两者都不可分辨」，
    #    与 `1_Code/AutoRA_SPE/README.md` §6 处方⑥要防的洗白同族。
    print("\n[E 组·续 2] `(A)` 在带内但 `(B)` 超带：不得印成「两者都不可分辨」（D59）")

    # ⚠️ 夹具要点：**头名靠最小 `A` 选出**，所以「陪跑」臂的 `A` 必须明显更大，
    #    否则陪跑臂会顶掉头名（第一版就踩了：`manual`/`bo` 的 `A = 0.29` 比 `grid` 小，
    #    于是头名成了 `manual`，被测的 `random` 反而变成「B 上显著更好」）。
    def _extra():
        return {**_arm("manual", 0.95, 1.0), **_arm("bo", 0.96, 1.0)}

    rows10 = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.31, 7.5),
                             **_extra()}, NOISE)
    r10 = {r["arm"]: r for r in rows10}
    check("E10a 非头名臂 `(A)` 在带内、`(B)` 明显更差 ⇒ 必须说「在 (B) 上显著更差」，"
          "**不得**说「在 (A) 与 (B) 上都不可分辨」",
          "在 **(B) 上显著更差**" in r10["random"]["verdict"]
          and "在 (A) 与 (B) 上都不可分辨" not in r10["random"]["verdict"],
          r10["random"]["verdict"])

    # E10b：头名 `(A)` 更小但 `(B)` **更差** ⇒ 不得宣称最好（E10a 的镜像，方向相反）
    rows10b = L.compare_arms({**_arm("grid", 0.30, 7.5), **_arm("random", 0.31, 8.0),
                              **_extra()}, NOISE)
    t10b = [r for r in rows10b if r["arm"] == "grid"][0]
    check("E10b 头名 `(A)` 更小但 `(B)` 明显更差 ⇒ 必须说「在 (B) 上显著更差」且"
          "**不得**说「本预算下 (A,B) 上最好」",
          "在 (B) 上显著更差" in t10b["verdict"]
          and "本预算下 (A,B) 上最好" not in t10b["verdict"],
          t10b["verdict"])

    # E10c 回归：`ΔA` **超带**且 `B` 不差 ⇒ 正常路径必须仍然允许说「(A,B) 上最好」
    rows10c = L.compare_arms({**_arm("grid", 0.30, 8.0), **_arm("random", 0.40, 8.0),
                              **_extra()}, NOISE)
    t10c = [r for r in rows10c if r["arm"] == "grid"][0]
    check("E10c 回归：`ΔA` 超带且 `B` 不差 ⇒ 仍须允许说「本预算下 (A,B) 上最好」"
          "（加 E10 不得把正常路径堵死）",
          "本预算下 (A,B) 上最好" in t10c["verdict"],
          t10c["verdict"])

    # E10d：头名 `(A)` 在带内但 `(B)` **明显更好** ⇒ 必须如实说「(B) 上更好」，
    #       同时仍然不许把 (A) 上的不可分辨说成「最好」
    rows10d = L.compare_arms({**_arm("grid", 0.30, 8.5), **_arm("random", 0.31, 7.0),
                              **_extra()}, NOISE)
    t10d = [r for r in rows10d if r["arm"] == "grid"][0]
    check("E10d 头名 `(A)` 在带内但 `(B)` 明显更好 ⇒ 必须说「在 (B) 上更好」且"
          "仍**不得**说「本预算下 (A,B) 上最好」（主判据 (A) 不可分辨）",
          "在 (B) 上更好" in t10d["verdict"]
          and "本预算下 (A,B) 上最好" not in t10d["verdict"],
          t10d["verdict"])

    # ---------------- E11 组：带宽必须是「**差**」的噪声带（D60） ----------------
    # ❗ 实测缺陷：`measure_noise` 量的是**同一个设计**（锚点）在不同种子下的 `sd`，
    #    而 `compare_arms` 比的是两条臂各自选中的**不同设计**（CRN 种子由名字哈希导出
    #    ⇒ 两次 MC 误差独立）⇒ `Var(差) = 2·sd²` ⇒ 系数必须是 `2·√2`。
    #    用 `2·sd` 会把差的噪声低估 `√2 ≈ 1.41` 倍（**偏宽松**：更容易宣称「显著 / 最好」）。
    #    这一组挑一个正好落在两根带**之间**的 `ΔA`：旧带说「最好」、新带必须说「不可分辨」。
    print("\n[E 组·续 3] 判据带宽是「两个设计的差」的噪声带 ⇒ 系数 `2·√2`（D60）")
    _band_a = L.DIFF_BAND_FACTOR * float(NOISE["sd_A"])
    _band_a_old = 2.0 * float(NOISE["sd_A"])
    check("E11 带宽系数必须是 `2·√2`（`DIFF_BAND_FACTOR`）—— 用 `2·sd` 会把"
          "「差的噪声」低估 √2 倍",
          abs(L.DIFF_BAND_FACTOR - 2.0 * float(np.sqrt(2.0))) < 1e-12
          and abs(_band_a - 0.0565685424949238) < 1e-12,
          f"DIFF_BAND_FACTOR = {L.DIFF_BAND_FACTOR!r} ⇒ band_a = {_band_a:.6f}"
          f"（旧的 2·sd 会是 {_band_a_old:.6f}）")

    _d_between = 0.5 * (_band_a_old + _band_a)          # 0.0483…，落在两根带之间
    rows11 = L.compare_arms({**_arm("grid", 0.30, 8.0),
                             **_arm("random", 0.30 + _d_between, 8.0),
                             **_extra()}, NOISE)
    t11 = [r for r in rows11 if r["arm"] == "grid"][0]
    check(f"E11a `ΔA = {_d_between:.4f}`（旧带 {_band_a_old:.4f} 与 D60 带 {_band_a:.4f} 之间）"
          f"⇒ 必须判「不可分辨」，**不得**说「本预算下 (A,B) 上最好」",
          "不可分辨" in t11["verdict"] and "本预算下 (A,B) 上最好" not in t11["verdict"],
          t11["verdict"])

    # E11b 回归：`ΔA` **超过** D60 的带 ⇒ 正常路径仍要允许说「最好」（否则 E11 就变成了
    #    「把带无限放大」的借口，那是另一种洗白）
    rows11b = L.compare_arms({**_arm("grid", 0.30, 8.0),
                              **_arm("random", 0.30 + 1.2 * _band_a, 8.0),
                              **_extra()}, NOISE)
    t11b = [r for r in rows11b if r["arm"] == "grid"][0]
    check(f"E11b 回归：`ΔA = {1.2 * _band_a:.4f} > 带 {_band_a:.4f}` ⇒ 仍须允许说"
          f"「本预算下 (A,B) 上最好」（加 E11 不得把正常路径堵死）",
          "本预算下 (A,B) 上最好" in t11b["verdict"],
          t11b["verdict"])

    # E11c：报告生成器里的同一个常数必须与生产代码**逐位相等**（两处各写一遍最容易漂移）
    try:
        import stage9_report as R11
        _same = abs(float(R11.DIFF_BAND_FACTOR) - float(L.DIFF_BAND_FACTOR)) < 1e-12
        _val = f"{R11.DIFF_BAND_FACTOR!r}"
    except Exception as exc:                            # noqa: BLE001
        _same, _val = False, f"{type(exc).__name__}: {exc}"
    check("E11c `stage9_report.py` 的 `DIFF_BAND_FACTOR` 必须与 `stage9_loop.py` 的逐位相等"
          "（报告 §2/§7 用它印判据带）",
          bool(_same), f"report.DIFF_BAND_FACTOR = {_val}")

    # E6/E6b：D54 的遗漏率**约束**必须有牙齿（正例 + 反向对照），且走的是真实折算路径
    print("\n[E′ 组] D54 遗漏率约束（罚分 → 可行域）")
    # ⚠️ 用**模块级**已导入的 S9I（`import stage9_inner as S9I` 在本函数里会把它变成局部名，
    #    于是前面 B 组对 S9I 的引用会抛 UnboundLocalError —— 已踩过一次）。
    saved_eval = S9I.inner_eval

    def _stub_with_omission(om):
        def fake(*args, **kwargs):
            # 用真实 rec 里那套键（`_objective_record` 会逐个取），只改 `omission`
            out = {key: rec[key] for key in
                   ("model", "se", "se_rho", "se_sd", "cond", "n_bad", "omission", "acc",
                    "rt_ms", "relative_se", "param_names", "n_trials")}
            out["omission"] = float(om)
            return out
        return fake

    try:
        S9I.inner_eval = _stub_with_omission(0.90)
        ev_t = L.Evaluator(one, n_fim=N_FIM, n_subjects=40, verbose=False)
        r_bad = ev_t.get(L.ANCHOR_DESIGN)
    finally:
        S9I.inner_eval = saved_eval
    gate_txt = " ".join(r_bad.get("gates", []))
    check("E6 遗漏率 0.90 超出冻结带 ⇒ `feasible = False` 且闸门说明里点名 D54 与约束",
          r_bad["feasible"] is False and "D54 约束" in gate_txt,
          f"feasible={r_bad['feasible']}；gates={gate_txt[:90]}")

    try:
        S9I.inner_eval = _stub_with_omission(0.10)
        ev_t2 = L.Evaluator(one, n_fim=N_FIM, n_subjects=40, verbose=False)
        r_ok = ev_t2.get(L.ANCHOR_DESIGN)
    finally:
        S9I.inner_eval = saved_eval
    check("E6b 反向对照：遗漏率 0.10 落在带内 ⇒ 不得被这条约束误伤",
          r_ok["feasible"] is True and not any("D54 约束" in g for g in r_ok.get("gates", [])),
          f"feasible={r_ok['feasible']}；band={L.OMISSION_BAND}")
    note("E 组读数", f"D54 约束带 = {list(L.OMISSION_BAND)}；判据 CRITERION = {list(L.CRITERION)}")

    # E7：把"锚点是否落在冻结带内"变成**每次都打印的读数**
    #     理由：D4 的遗漏率实测约 0.31–0.36，而上界是 0.20 ⇒ 锚点**自身不可行**。
    #     这不是 bug，而是 9A 的头条结论；但它绝不能被忘记，所以做成强制读数。
    note("E7 锚点与冻结带的关系",
         f"锚点 D4：遗漏率 {rec['omission']:.4f}、可行={rec['feasible']}"
         f"（冻结带 [{L.OMISSION_BAND[0]:g}, {L.OMISSION_BAND[1]:g}]）"
         + ("" if rec["feasible"] else "  ⚠️ **锚点自身落在带外 ⇒ 本带与已被定稿采用的设计不相容**"))
    check("E7 锚点可行性是否被如实记录（可行 ⇒ 无 D54 闸门；不可行 ⇒ 必须有 D54 闸门）",
          rec["feasible"] is (not any("D54 约束" in g for g in rec.get("gates", []))),
          f"feasible={rec['feasible']}、omission={rec['omission']:.4f}")

    # ---------------- F 组：Pareto 前沿 ----------------
    print("\n[F 组] Pareto 前沿（A 小、B 大）")
    ev4 = L.Evaluator(one, n_fim=N_FIM, n_subjects=40, verbose=False)
    ev4.cache[L.ANCHOR_DESIGN] = dict(rec)
    ev4.cache["p_dom"] = {"feasible": True, "A": 0.5, "B": 1.0, "J": 9.0}
    ev4.cache["p_ok"] = {"feasible": True, "A": 0.4, "B": 2.0, "J": 8.0}
    ev4.cache["p_bad"] = {"feasible": False, "A": 0.1, "B": 99.0, "J": float("inf")}
    front = L.pareto_front(ev4)
    fnames = [p["name"] for p in front]
    check("F1 被支配点与不可行点都不在前沿、前沿 B 严格递增",
          "p_dom" not in fnames and "p_bad" not in fnames
          and all(front[i]["B"] < front[i + 1]["B"] for i in range(len(front) - 1))
          and all(front[i]["A"] <= front[i + 1]["A"] for i in range(len(front) - 1)),
          f"前沿 = {fnames}")

    # ---------------- G 组：噪声标定 ----------------
    print("\n[G 组] 噪声标定（alpha 必须来自实测）")
    ev5 = L.Evaluator(one, n_fim=N_FIM, n_subjects=40, verbose=False)
    noise = L.measure_noise(ev5, n_repeats=2)
    check("G1 alpha = max(sd_J², 1e-12) > 0，且样本数与要求一致",
          noise["alpha"] > 0 and noise["alpha"] >= noise["sd_J"] ** 2 - 1e-18
          and len(noise["J"]) == 2,
          f"sd_J={noise['sd_J']:.4f} alpha={noise['alpha']:.3e} "
          f"J={['%.4f' % v for v in noise['J']]}")

    # ---------------- H 组：前沿作用域（D56） ----------------
    # 起因（一手实测）：`pareto_front()` 走 `names or list(ev.cache)`、`best()` 也只在缓存里找，
    # 而 `main()` 原先在 `ev.feasible_names()` 补全空间**之前**调用它们 ⇒ 报出的「推荐点」其实
    # 是**四臂抽到的那些点里最好的**，其好坏完全取决于 `--budget`。实测：`--budget 12` 报
    # `A = 0.3881`，补全 174 个候选后真值 `A = 0.3446`（且后者**在可行集内支配 D4**，
    # `ΔA = +0.0412` = 噪声带 `2·sd_A = 0.0050` 的 8 倍）。
    # 这一组是**静态源码判据**：不重跑 13 分钟的内环，只钉住"顺序"与"作用域落盘"这两件事。
    print("\n[H 组] 前沿作用域：补全空间必须在算前沿之前，且作用域必须落盘（D56）")
    _src = Path(L.__file__).resolve().read_text(encoding="utf-8")
    _i_main = _src.index("def main(")
    # ⚠️ `main()` 是文件里**最后一个**函数 ⇒ 不能找下一个 `\ndef `（第一版这么写直接
    # `ValueError: substring not found`）。用「下一个顶层语句」定位，兜底到文件尾。
    _j = _src.find("\nif __name__", _i_main + 1)
    _body = _src[_i_main:_j if _j > 0 else len(_src)]
    _i_feas = _body.find("ev.feasible_names()")
    _i_front = _body.find("pareto_front(ev)")
    _i_best = _body.find('ev.best("A")')
    check("H1 `main()` 里**先补全候选空间、后算前沿与推荐点**"
          "（顺序反了就等于按 `--budget` 报结论）",
          _i_feas >= 0 and 0 <= _i_feas < _i_front and 0 <= _i_feas < _i_best,
          f"index(feasible_names)={_i_feas} < index(pareto_front)={_i_front}、"
          f"index(best)={_i_best}")
    check("H2 payload 里有 `front_scope` 且四个键齐全（作用域必须落盘，"
          "否则事后无法判断那个前沿是在哪个点集上算的）",
          '"front_scope"' in _body
          and all(k in _body for k in ("n_candidates", "n_cached_before_full_eval",
                                       "n_evaluated", "n_front")),
          "front_scope = {n_candidates, n_cached_before_full_eval, n_evaluated, n_front}")
    check("H3 payload 的 `cache` 段存在且经 `_jsonable()` 折算"
          "（`inner_eval` 的 se/se_sd/acc 是 numpy 数组，直接 dump 抛 TypeError）",
          "_jsonable" in _src
          and '"cache": {k: _jsonable(v) for k, v in ev.cache.items()}' in _body,
          "逐设计 cache + `_jsonable` 都在")
    # D57：同一个量在 `histories[arm]` 与 `compare` 行里必须**同名**。
    # 起因（一手）：两处曾分别写成 `B_at_best_A` / `B_at_A_best` ⇒ 报告生成器读错一个键，
    # 把「`B`@`(A)` 最优点」这一列**静默**印成 `—`（`inf`/`nan` 会被 `_f` 折成 `—`，
    # 而 `—` 在读者眼里是"没数据"，不会被当成错误）。静态判据足够：错名字一旦回来就会命中。
    check("H4 同一个量只有一个键名：`B_at_A_best`（两处曾各写一个名字 ⇒ 报告静默印 `—`）",
          '"B_at_best_A"' not in _src and _src.count('"B_at_A_best"') >= 3,
          f"`B_at_A_best` 出现 {_src.count(chr(34) + 'B_at_A_best' + chr(34))} 次、"
          f"旧名 {_src.count(chr(34) + 'B_at_best_A' + chr(34))} 次")
    # D58：`n_init` 的下限必须是 1（静态钉子配合 E9 的实测）。
    # 起因：下限写成 2 ⇒ `--budget 1` 时 BO 臂取 2 个点 ⇒ 同预算守卫中断整轮。
    check("H5 `arm_bo` 的 `n_init` 下限必须是 1（曾是 2 ⇒ `--budget 1` 取 2 个点，整轮被守卫中断）",
          "n_init = max(1, min(int(n_init), int(budget)))" in _src,
          "下限 1 已钉住")
    check("H5b 预算 ≤ n_init 时 BO 臂必须**自报**退化为随机采样（否则读者会把它当 BO 的证据）",
          "本臂退化为**随机采样**" in _src and "不能作为 BO 的证据" in _src,
          "退化提示已钉住")
    # D59：标定种子必须**独立重抽**，不能是「同一个哈希值加小偏移」的算术邻居。
    # 起因：旧写法 `cell_seed(name, base + 791_900 + 37k)` 的 6 个种子恰好抽在
    # `(A)` 种子分布的密集区 ⇒ `sd_A = 0.0048`，而 48 个无关种子给 `0.0189`（4.0 倍）
    # ⇒ `n_fim = 1` 下的所有裁决带宽都窄了 4 倍。钉子必须钉**调用**，不能钉字面词
    # （docstring 里为说明来历保留了旧写法的**描述**，那是有意留的）。
    check("H6 噪声标定的种子必须独立重抽：`cell_seed(f\"{name}#noise{k}\", base_seed)`；"
          "旧写法 `cell_seed(d[\"name\"], ev.base_seed + 791_900 + 37 * k)` 不得回来",
          "cell_seed(f\"{d['name']}#noise{k}\", ev.base_seed)" in _src
          and 'cell_seed(d["name"], ev.base_seed + 791_900 + 37 * k)' not in _src,
          f"独立重抽已钉住（`#noise{{k}}` 出现 {_src.count('#noise{k}')} 次）")
    check("H6b 标定结果必须自报种子与生成式（否则落盘件无法复核带宽是怎么来的）",
          '"seeds": seeds_used' in _src and '"family":' in _src,
          "`seeds` / `family` 已钉住")
    # D59 同族第四条：裁决文本是**运行时**生成的冻结产物，报告只转印、不重算
    # ⇒ 落盘件必须自报它出自哪一版规则，否则读者无法区分当前判词与已被修正的判词。
    check("H7 落盘件必须自报裁决规则版本（`VERDICT_LOGIC` 常量 + payload 的 "
          "`\"verdict_logic\"` 键）—— 否则报告里那些判词无法归因到某一版规则",
          "VERDICT_LOGIC = " in _src and '"verdict_logic": VERDICT_LOGIC' in _src,
          "裁决规则版本已随 payload 落盘")
    # D60：判据带宽必须是「**差**的」噪声带。静态钉子钉住**系数**与**旧写法不再出现**：
    # 旧写法 `band_a = 2.0 * float(noise.get("sd_A", 0.0))` 把「两个不同设计的差」的
    # 噪声低估 √2 倍（偏宽松 ⇒ 更容易宣称「显著 / 最好」）。
    check("H8 判据带宽的系数必须是 `2·√2`（`DIFF_BAND_FACTOR`），且旧的 `2·sd` 写法不得回来"
          "（比的是两个不同设计的**差**，不是单个设计的读数）",
          "DIFF_BAND_FACTOR = 2.0 * float(np.sqrt(2.0))" in _src
          and 'band_a = 2.0 * float(noise.get("sd_A", 0.0))' not in _src
          and 'band_b = 2.0 * float(noise.get("sd_B", 0.0))' not in _src,
          f"`DIFF_BAND_FACTOR` 出现 {_src.count('DIFF_BAND_FACTOR')} 次")

    # ---------------- 汇总 ----------------
    n_bad = sum(1 for _, ok, _ in _RESULTS if not ok)
    print("\n" + "=" * 72)
    print(f"共 {len(_RESULTS)} 项，未通过 {n_bad} 项（另有 {len(_NOTES)} 条实测读数）。")
    print(f"总耗时 {time.time() - t_start:.1f}s")
    for lab, det in _NOTES:
        print(f"  · {lab}：{det}")
    if n_bad:
        print("未通过：")
        for lab, ok, det in _RESULTS:
            if not ok:
                print(f"  ❌ {lab} —— {det}")
    if OUT:
        OUT.write_text("\n".join(f"{'OK ' if ok else 'NO '} {lab} :: {det}"
                                 for lab, ok, det in _RESULTS) + "\n",
                       encoding="utf-8", newline="\n")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
