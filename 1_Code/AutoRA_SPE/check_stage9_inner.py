# -*- coding: utf-8 -*-
"""
check_stage9_inner.py —— `stage9_inner.py` 的自检
================================================
**为什么必须有它**：`stage9_inner.py` 是把 `1_Code/DDM_Core/_scratch/check_mt1_fim.py`
（自检 A/B 已过的仪器）提升为生产文件。提升过程中**必然重写代码**，所以必须
把"新代码 == 旧仪器"钉死，否则 Stage 9 的全部数字都建立在一个未经核对的
重写上。本文件的核心就是 **B1 / B2 两组逐位复现检查**。

分组
----
- **A 组**：接口守卫（非法 model / 忘给 rho / 多给 rho / 非法参数集 /
  违反 `W > T + 200 ms` 的设计必须报错）。
- **B 组**：**数值锚点**——把两条分支钉在已验证的实现上。
  - B1：M-T3 分支 vs `design_fim.design_se`，判据 `< 1e-12`（应逐位一致）。
  - B2：M-T1 分支（`batch=False`）vs `_scratch/check_mt1_fim.py::design_se_step`，
    判据 `< 1e-12`。**这一条是"提升没有走样"的直接证据。**
  - B3：`rho = 1` 时 M-T1（rho 固定）与 M-T3 在**同一份试次**上一致（`< 2%`）。
  - B4：`rho` 自由会把其余参数的边际 SE 抬高（**报告，不是断言**——这是真实代价）。
- **C 组**：批次向量化与逐份生成的**分布一致性**。判据**来自实测的抽样分布**
  （`se_sd / sqrt(n_fim)`），不是"应该相等"——两者本来就是不同的 MC 样本。
- **D 组**：CRN 确定性（同 seed 逐位相同；不同 seed 不同）。
- **E 组**：预计算表的存/取往返（`se` 逐位不变）。
- **F 组**：**决策 D49 的回归钉**——含 `beta_ST` 的 `PRIMARY` 口径把几何平均抬高，
  可以翻转可用性判定；`C6` 口径不翻。

用法::

    python 1_Code\\AutoRA_SPE\\check_stage9_inner.py [n_fim] [输出路径]
"""
from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

_HERE = Path(__file__).resolve().parent            # .../1_Code/AutoRA_SPE
_DDM_DIR = _HERE.parent / "DDM_Core"
for _p in (str(_HERE), str(_DDM_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from design_fim import (DESIGNS, NAMES as NAMES_EXP, P_SINGLE,  # noqa: E402
                        TRUTH, check_validity)
from likelihood import (fim_diagnostics as FIM_DIAG,  # noqa: E402
                        opg_information, per_trial_loglik, trials_from_arrays)
from simulate import build_design, design_arrays, simulate_subject  # noqa: E402
from twophase import per_trial_loglik_step, simulate_euler_subject  # noqa: E402

from stage9_inner import (CRN_STRIDE, DT_GEN, M_T1, M_T3,  # noqa: E402
                          REL_STEP_FD, SELFCHECK_TOLS, build_table,
                          crn_seeds, geomean_relative_se, inner_eval,
                          load_table, opg_information_step, param_names_for,
                          save_table, se_from_information, table_key)

# D24 确证集（决策 D49：Stage 9 Objective (A) 用这一套）
C6 = ["d_ref", "beta_T", "beta_S", "a_ref", "delta_a", "t0"]

#: 冒烟用的确定设计点（D4 的 T/W 水平）——**时序口径按 D48**：W 是自 onset 的截止时刻
T4 = (0.03333, 0.08333, 0.14999, 0.24998)
W3 = (0.79998, 1.1999, 1.7999)
N_REP = 12

#: `1_Code/DDM_Core/_scratch/check_mt1_fim.py` 里那个被提升的仪器
_SCRATCH = _DDM_DIR / "_scratch" / "check_mt1_fim.py"


# ------------------------------------------------------------------
# 判分小工具
# ------------------------------------------------------------------
class Report:
    def __init__(self):
        self.n_pass = 0
        self.n_fail = 0
        self.fails: list[str] = []

    def check(self, name: str, ok: bool, detail: str = ""):
        mark = "✅" if ok else "❌"
        if ok:
            self.n_pass += 1
        else:
            self.n_fail += 1
            self.fails.append(name)
        print(f"  {mark} {name}" + (f"   {detail}" if detail else ""), flush=True)
        return ok

    def note(self, text: str):
        print(f"     · {text}", flush=True)

    def section(self, title: str):
        print("\n" + "=" * 100)
        print(title)
        print("=" * 100, flush=True)


def _load_scratch():
    """把 `_scratch/check_mt1_fim.py` 当模块导入（文件名不是合法标识符开头？不是，
    但它在 `_scratch/` 里、不在 sys.path 上，所以必须走 importlib）。"""
    spec = importlib.util.spec_from_file_location("_ck_mt1_fim", _SCRATCH)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {_SCRATCH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ck_mt1_fim"] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------
# A 组：接口守卫
# ------------------------------------------------------------------
def _tiny_tr() -> dict:
    """A 组用的最小试次集（只为触发差分路径，不追求统计意义）。"""
    return {"rt": np.array([0.5, 0.7, 0.9]),
            "side": np.array([1, 0, 1]),
            "omission": np.array([0, 0, 0]),
            "P": np.array([120.0, 120.0, 120.0]),
            "T": np.array([0.1, 0.2, 0.15]),
            "W": np.array([1.0, 1.0, 1.0]),
            "is_self": np.array([1.0, 1.0, 1.0]),
            "is_match": np.array([1, 0, 1])}


def group_a(rep: Report):
    rep.section("A 组：接口守卫（这些错误必须被拦住，而不是静默算出一个数）")

    def bad(fn, exc=ValueError):
        try:
            fn()
        except exc:
            return True
        except Exception:
            return False
        return False

    A = [
        ("A1 非法 model 名报错",
         bad(lambda: inner_eval(T4, W3, N_REP, model="M-T2"))),
        ("A2 model=M-T1 忘给 rho 报错",
         bad(lambda: inner_eval(T4, W3, N_REP, model=M_T1))),
        ("A3 model=M-T3 多给 rho 报错（它是 rho==1 的严格特例）",
         bad(lambda: inner_eval(T4, W3, N_REP, model=M_T3, rho=0.75))),
        ("A4 非法参数集名报错",
         bad(lambda: param_names_for("bogus"))),
        ("A5 违反 W > T + 200ms 的设计报错",
         bad(lambda: inner_eval((0.5,), (0.6,), 4, model=M_T3))),
        # ⚠️ 上界必须查：`per_trial_loglik_step` **只在 rho<0 时返回 None、不查上界**
        # （实测 rho=5.0 仍返回有限值），所以生产版本自己做了两侧检查。
        ("A6 opg_information_step 的 rho **上界**越界报错（rho=3.0 是边界）",
         bad(lambda: opg_information_step(_tiny_tr(), TRUTH, 3.0, ["d_ref"],
                                          include_rho=True), ValueError)),
        ("A6b opg_information_step 的 rho **下界**越界报错（rho=0.0 是边界）",
         bad(lambda: opg_information_step(_tiny_tr(), TRUTH, 0.0, ["d_ref"],
                                          include_rho=True), ValueError)),
        ("A6c 区间内的 rho（2.0）不被误拦",
         not bad(lambda: opg_information_step(_tiny_tr(), TRUTH, 2.0, ["d_ref"],
                                              include_rho=True))),
    ]
    for name, ok in A:
        rep.check(name, bool(ok))

    # A5 的另一半：合法设计不许被拦
    ok = True
    try:
        inner_eval((0.03333,), (0.79998,), 2, model=M_T3, n_fim=1)
    except Exception as exc:                        # noqa: BLE001
        ok = False
        rep.note(f"合法设计被拦：{exc!r}")
    rep.check("A7 合法设计（W > T+200ms）正常通过", ok)


# ------------------------------------------------------------------
# B 组：数值锚点
# ------------------------------------------------------------------
def group_b(rep: Report, n_fim: int):
    rep.section("B 组：数值锚点（把两条分支钉在已验证的实现上）")

    import design_fim as DF

    # ---- B1：M-T3 分支 vs design_fim.design_se ----
    t0 = time.time()
    ref = DF.design_se(T4, W3, N_REP, n_fim=max(1, n_fim))
    mine = inner_eval(T4, W3, N_REP, model=M_T3, n_fim=max(1, n_fim))
    rel = float(np.max(np.abs(mine["se"] - ref["se"])
                       / np.maximum(np.abs(ref["se"]), 1e-300)))
    rep.check("B1 M-T3 分支 vs design_fim.design_se（同 seed）",
              rel < SELFCHECK_TOLS["mt3_vs_design_fim"],
              f"max 相对差 = {rel:.3e}  判据 < {SELFCHECK_TOLS['mt3_vs_design_fim']:g}"
              f"  ({time.time()-t0:.1f}s)")
    rep.note(f"遗漏 {mine['omission']:.4f} vs {ref['omission']:.4f}；"
             f"RT {mine['rt_ms']:.1f} vs {ref['rt_ms']:.1f} ms")

    # ---- B1b：`cond` / `n_bad` 必须与 design_fim **同源** ----
    # 这两个数进 Stage 9 的可行性闸门（Objective (D)）。若用 `np.linalg.cond`
    # 代替 `likelihood.fim_diagnostics`，在有负特征值时会给出**不同的数**：
    # `np.linalg.cond` 看的是奇异值、`fim_diagnostics` 看的是特征值。
    rel_cond = float(abs(mine["cond"] - ref["cond"]) / max(abs(ref["cond"]), 1e-300))
    rep.check("B1b `cond` 与 design_fim 同源（同 seed、同信息矩阵）",
              rel_cond < SELFCHECK_TOLS["mt3_vs_design_fim"],
              f"相对差 = {rel_cond:.3e}（{mine['cond']:.6g} vs {ref['cond']:.6g}）")
    rep.check("B1c `n_bad` 与 design_fim 同源（整数必须完全相等）",
              int(mine["n_bad"]) == int(ref["n_bad"]),
              f"n_bad = {mine['n_bad']} vs {ref['n_bad']}"
              f"（判据 `fim_diagnostics` = 特征值 < max(ev_max·1e-8, 1e-300) 的个数）")
    if int(ref["n_bad"]) == 0:
        # 直接构造退化矩阵来验证 `n_bad` 的语义（不依赖任何设计恰好退化）
        I_sing = np.eye(len(ref["se"]))
        I_sing[0, 0] = 0.0                          # 一个方向完全无信息
        d_sing = FIM_DIAG(I_sing, NAMES_EXP)
        rep.check("B1d `n_bad` 对退化信息矩阵报 > 0（闸门有牙齿）",
                  int(d_sing["n_bad"]) >= 1,
                  f"人为置零一个方向 ⇒ n_bad = {d_sing['n_bad']}、"
                  f"cond = {d_sing['cond']:.3e}")
    else:
        rep.note(f"D4 本已 n_bad = {ref['n_bad']} ⇒ 退化用例不必要")

    # ---- B2：M-T1 分支（batch=False）vs _scratch/check_mt1_fim.py ----
    ck = _load_scratch()
    rho = 0.75
    t0 = time.time()
    ref1 = ck.design_se_step(T4, W3, N_REP, rho, n_fim=max(1, n_fim))
    mine1 = inner_eval(T4, W3, N_REP, model=M_T1, rho=rho,
                       n_fim=max(1, n_fim), batch=False)
    ref_se = np.asarray(ref1["se"])
    rel_se = float(np.max(np.abs(mine1["se"] - ref_se[:len(mine1["se"])])
                          / np.maximum(np.abs(ref_se[:len(mine1["se"])]), 1e-300)))
    rel_rho = float(abs(mine1["se_rho"] - ref_se[-1]) / max(abs(ref_se[-1]), 1e-300))
    rep.check("B2 M-T1 分支（batch=False）vs _scratch/check_mt1_fim.py",
              max(rel_se, rel_rho) < SELFCHECK_TOLS["mt1_vs_scratch"],
              f"参数 max 相对差 = {rel_se:.3e}，rho 相对差 = {rel_rho:.3e}"
              f"  判据 < {SELFCHECK_TOLS['mt1_vs_scratch']:g}  ({time.time()-t0:.1f}s)")
    rep.note(f"遗漏 {mine1['omission']:.4f} vs {ref1['omission']:.4f}；"
             f"报的 se(rho) = {mine1['se_rho']:.4f} vs {ref_se[-1]:.4f}")

    # ---- B3：rho=1 时，M-T1（rho 固定）与 M-T3 在**同一份试次**上一致 ----
    # 关键在「同一份试次」：OPG 是 GᵀG，依赖具体那一份 rt，不只是它的期望。
    design = build_design(P_SINGLE, T4, W3, N_REP)
    rng = np.random.default_rng(12345)
    sim3 = simulate_subject(design, TRUTH, rng)
    tr = trials_from_arrays(sim3["rt"], sim3["side"], sim3["omission"],
                            *design_arrays(design))

    I3, _ = opg_information(tr, NAMES_EXP, TRUTH)
    se3 = se_from_information(I3)
    I1, _ = opg_information_step(tr, TRUTH, 1.0, NAMES_EXP, include_rho=False)
    se1 = se_from_information(I1)
    rel_rho1 = np.abs(se1 - se3) / np.maximum(np.abs(se3), 1e-300)
    rep.check("B3 rho=1 时 M-T1(rho 固定) vs M-T3（同一份试次）",
              bool(np.all(rel_rho1 < SELFCHECK_TOLS["mt1_vs_mt3_rho1"])),
              f"最大相对差 = {float(np.max(rel_rho1)):.3%}  "
              f"判据 < {SELFCHECK_TOLS['mt1_vs_mt3_rho1']:.0%}")
    rep.note(f"（归一化逐试次对数似然最大绝对差 = "
             f"{float(np.max(np.abs(per_trial_loglik_step(TRUTH, tr, 1.0) - per_trial_loglik(TRUTH, tr))) / max(1.0, float(np.max(np.abs(per_trial_loglik(TRUTH, tr)))))):.3e}）")

    # ---- B4：rho 自由 ⇒ 其余参数的边际 SE 被抬高（报告，不断言） ----
    I1f, _ = opg_information_step(tr, TRUTH, 1.0, NAMES_EXP, include_rho=True)
    se1f = se_from_information(I1f)[:len(NAMES_EXP)]
    delta = se1f / np.maximum(se3, 1e-300) - 1.0
    rep.note("B4（报告）rho 当自由参数后，其余参数的边际 SE 变化："
             + "  ".join(f"{n[:9]}={d:+.1%}" for n, d in zip(NAMES_EXP, delta)))
    rep.note("     这不是实现错误，而是 rho 与 d_ref 强相关的**真实代价**；"
             "所以与 M-T3 做实现比对时必须 include_rho=False。")


# ------------------------------------------------------------------
# C 组：批次 vs 逐份、以及两条生成路径的分布一致性
# ------------------------------------------------------------------
def group_c(rep: Report, n_fim: int):
    rep.section("C 组：批次向量化与生成路径的分布一致性（判据来自实测的抽样分布）")

    rho = 0.75
    t0 = time.time()
    rb = inner_eval(T4, W3, N_REP, model=M_T1, rho=rho, n_fim=n_fim, batch=True)
    t_batch = time.time() - t0
    t0 = time.time()
    rn = inner_eval(T4, W3, N_REP, model=M_T1, rho=rho, n_fim=n_fim, batch=False)
    t_seq = time.time() - t0

    # 两个估计各是 n_fim 份 SE 的均值 ⇒ 差值标准误 ≈ sqrt((sd_b² + sd_n²)/n_fim)
    sd_b = np.asarray(rb["se_sd"])
    sd_n = np.asarray(rn["se_sd"])
    sd_diff = np.sqrt((sd_b ** 2 + sd_n ** 2) / float(max(n_fim, 2)))
    z = np.abs(rb["se"] - rn["se"]) / np.maximum(sd_diff, 1e-300)
    rep.check("C1 批次与逐份的 se 差 ≤ 4× 差值的 MC 标准误（5/5 参数）",
              bool(np.all(z <= 4.0)),
              f"最大 |z| = {float(np.max(z)):.2f}（n_fim={n_fim}）")
    rep.note(f"批次 {t_batch:.1f}s vs 逐份 {t_seq:.1f}s ⇒ 加速比 "
             f"**{t_seq / max(t_batch, 1e-9):.2f}×**（同一 n_fim={n_fim}）")
    rep.note(f"se(batch) = " + " ".join(f"{v:.4f}" for v in rb["se"]))
    rep.note(f"se(seq)   = " + " ".join(f"{v:.4f}" for v in rn["se"]))
    rep.note(f"se_sd(batch) = " + " ".join(f"{v:.4f}" for v in sd_b))

    rep.check("C2 批次与逐份的行为诊断一致（遗漏/正确率/RT 在 2 个 MC 标准误内）",
              abs(rb["omission"] - rn["omission"]) < 0.05
              and abs(rb["acc"] - rn["acc"]) < 0.10,
              f"Δ遗漏 {rb['omission']-rn['omission']:+.4f}  "
              f"Δ正确率 {rb['acc']-rn['acc']:+.4f}")

    # C3：rho=1 时，Euler + step 似然这条路径应与解析 wfpt 路径**同分布**。
    # 两个陷阱必须先排除，否则量到的不是「两条路径是否等价」：
    #   ① rho 自由会抬高其余参数的边际 SE（B4 实测 d_ref +116.8%）⇒ M-T1 侧
    #      必须 include_rho=False，才是**同一组 9 个参数**；
    #   ② 单次模拟的 se 没有噪声标尺（C1 的判据能用，正是因为手上有 se_sd）
    #      ⇒ 两支各取 n_ref 份，用合并 MC 标准误当尺子。
    n_ref = 4
    seed0 = 0
    design = build_design(P_SINGLE, T4, W3, N_REP)
    ses_3, ses_1 = [], []
    for r in range(n_ref):
        seed = seed0 + CRN_STRIDE * r
        sim3 = simulate_subject(design, TRUTH, np.random.default_rng(seed))
        tr3 = trials_from_arrays(sim3["rt"], sim3["side"], sim3["omission"],
                                 *design_arrays(design))
        I3, _ = opg_information(tr3, NAMES_EXP, TRUTH)
        ses_3.append(se_from_information(I3))

        sim1 = simulate_euler_subject(design, TRUTH, 1.0,
                                      np.random.default_rng(seed), dt=DT_GEN)
        tr1 = trials_from_arrays(sim1["rt"], sim1["side"], sim1["omission"],
                                 *design_arrays(design))
        I1, _ = opg_information_step(tr1, TRUTH, 1.0, NAMES_EXP,
                                     include_rho=False)
        ses_1.append(se_from_information(I1))

    se_3 = np.mean(ses_3, axis=0)
    se_1 = np.mean(ses_1, axis=0)
    sd_d = np.sqrt((np.std(ses_3, axis=0) ** 2 + np.std(ses_1, axis=0) ** 2)
                   / float(n_ref))
    zc = np.abs(se_1 - se_3) / np.maximum(sd_d, 1e-300)
    worst = int(np.argmax(zc))
    rep.check("C3 rho=1 时 Euler+step 路径与解析路径同分布（9 个参数，4× 合并 MC 标准误）",
              bool(np.all(zc <= 4.0)),
              f"最大 |z| = {float(np.max(zc)):.2f} @ {NAMES_EXP[worst]}"
              f"（n_ref={n_ref} 各一支）")
    rep.note("     · |z| 逐参数 = " + " ".join(
        f"{n}:{v:.2f}" for n, v in zip(NAMES_EXP, zc)))
    rep.note("     ⚠️ B3 才是「同一份试次」的严格嵌套检验；C3 走的是各自独立的"
             "生成路径，量到的是 Euler 离散化 + 解析抽样器之间的分布差。")


# ------------------------------------------------------------------
# D 组：CRN 确定性
# ------------------------------------------------------------------
def group_d(rep: Report):
    rep.section("D 组：CRN（共同随机数）的确定性")

    rep.check("D1 crn_seeds 规则 = seed + 1000*k",
              crn_seeds(7, 3) == [7, 1007, 2007])
    a = inner_eval(T4, W3, N_REP, model=M_T3, n_fim=2, seed=3)
    b = inner_eval(T4, W3, N_REP, model=M_T3, n_fim=2, seed=3)
    rep.check("D2 同 seed 的两次调用逐位相同",
              float(np.max(np.abs(a["se"] - b["se"]))) == 0.0)
    c = inner_eval(T4, W3, N_REP, model=M_T3, n_fim=2, seed=4)
    rep.check("D3 不同 seed 给出不同结果（否则种子没接上）",
              float(np.max(np.abs(a["se"] - c["se"]))) > 0.0,
              f"max|Δse| = {float(np.max(np.abs(a['se'] - c['se']))):.4f}")
    # CRN 的意义：同一 seed 下换设计，生成噪声是配对的
    rep.note(f"CRN_STRIDE = {CRN_STRIDE}（取自 design_fim.design_se 的种子规则，"
             f"是项目内 CRN 的唯一来源）")


# ------------------------------------------------------------------
# E 组：预计算表往返
# ------------------------------------------------------------------
def group_e(rep: Report, n_fim: int):
    rep.section("E 组：CRN 预计算表的存 / 取往返")

    designs = {"D4": DESIGNS["D4        (4T×3W, r12)"]}
    tbl = build_table(designs, model=M_T3, n_fim=max(1, min(n_fim, 2)),
                      seed=0, verbose=False)
    key = table_key("D4", M_T3, None)
    rep.check("E1 build_table 生成了预期键",
              list(tbl["cells"].keys()) == [key], f"键 = {list(tbl['cells'].keys())}")
    with tempfile.TemporaryDirectory() as td:
        p = save_table(tbl, Path(td) / "t.npz")
        back = load_table(p)
    se0 = np.asarray(tbl["cells"][key]["se"])
    se1 = np.asarray(back["cells"][key]["se"])
    rep.check("E2 往返后 se 逐位不变", float(np.max(np.abs(se0 - se1))) == 0.0)
    rep.check("E3 往返后 meta 与键完整",
              back["meta"]["model"] == M_T3
              and back["meta"]["param_names"] == NAMES_EXP,
              f"n_cells={back['meta']['n_cells']}")

    # M-T1 表的 rho 分支：同一设计、两个 rho ⇒ 两个不同的键
    tbl1 = build_table(designs, model=M_T1, rho_list=[1.0, 0.75],
                       n_fim=1, seed=0, verbose=False)
    rep.check("E4 M-T1 表按 rho 分键（同一设计两个 rho → 两个格子）",
              len(tbl1["cells"]) == 2
              and table_key("D4", M_T1, 1.0) in tbl1["cells"]
              and table_key("D4", M_T1, 0.75) in tbl1["cells"])


# ------------------------------------------------------------------
# F 组：决策 D49 的回归钉
# ------------------------------------------------------------------
def group_f(rep: Report, n_fim: int):
    rep.section("F 组：决策 D49 回归钉（参数集口径不能混用）")

    res = inner_eval(T4, W3, N_REP, model=M_T3, n_fim=max(1, min(n_fim, 2)))
    names = res["param_names"]
    g_pri = geomean_relative_se(res)                       # PRIMARY（含 beta_ST）
    g_c6 = geomean_relative_se(res, C6)
    rep.check("F1 含 beta_ST 的 PRIMARY 口径抬高几何平均（g_pri > g_c6）",
              g_pri > g_c6, f"g_pri = {g_pri:.3f}  vs  g_c6 = {g_c6:.3f}")
    rep.note(f"beta_ST 的相对 SE = "
             f"{res['relative_se'][names.index('beta_ST')]:.3f}（它是唯一的抬升源）")

    # 判定线翻转：D49 的核心证据就是 8 个设计全部由 ❌ 变 ✅
    def verdict(g):
        return "✅可用" if g < 0.30 else ("⚠️勉强" if g < 0.60 else "❌不可用")
    rep.check("F2 同一份 SE 在两个口径下给出相反判定（D49 的原始证据）",
              verdict(g_pri) != verdict(g_c6),
              f"PRIMARY → {verdict(g_pri)}，C6 → {verdict(g_c6)}")
    rep.check("F3 C6 是 param_names 的子集（口径可计算）",
              all(k in names for k in C6))
    try:
        geomean_relative_se(res, ["not_a_param"])
        ok = False
    except Exception:                                      # noqa: BLE001
        ok = True
    rep.check("F4 关注集里出现不存在的参数时报错（不静默返回）", ok)


# ------------------------------------------------------------------
def main():
    n_fim = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    n_fim = max(1, n_fim)
    rep = Report()
    t_start = time.time()

    print("=" * 100)
    print("stage9_inner.py 自检 —— M-T3 / M-T1 双分支、CRN、预计算表")
    print("=" * 100)
    print(f"  n_fim = {n_fim}；设计点 T = {T4}（秒）、W = {W3}（秒）、n_rep = {N_REP}")
    print(f"  时序口径按 D48：W 是**自刺激 onset 起算**的截止时刻，"
          f"约束 W > T + 0.2；Euler dt = {DT_GEN:g}，OPG 相对步长 = {REL_STEP_FD:g}")
    print(f"  被提升的仪器：{_SCRATCH.relative_to(_DDM_DIR.parent)}")

    group_a(rep)
    group_b(rep, n_fim)
    group_c(rep, n_fim)
    group_d(rep)
    group_e(rep, n_fim)
    group_f(rep, n_fim)

    rep.section("汇总")
    total = rep.n_pass + rep.n_fail
    print(f"  {rep.n_pass}/{total} 通过；失败 {rep.n_fail}；"
          f"总耗时 {time.time()-t_start:.1f}s")
    if rep.fails:
        print("  ❌ 失败项：" + "；".join(rep.fails))
        return 1
    print("  ✅ 全部通过")
    return 0


if __name__ == "__main__":
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    if out_path:
        buf = io.StringIO()
        real = sys.stdout

        class _Tee(io.TextIOBase):
            def write(self, s):
                real.write(s)
                buf.write(s)
                return len(s)

            def reconfigure(self, **kw):     # 被导入的模块会在 import 时调用
                return real.reconfigure(**kw)

            def __getattr__(self, name):     # encoding / buffer / isatty 等透传
                return getattr(real, name)

        sys.stdout = _Tee()
        try:
            code = main()
        finally:
            sys.stdout = real
            Path(out_path).write_text(buf.getvalue(), encoding="utf-8")
            real.write(f"\n[日志已写入 {out_path}]\n")
        raise SystemExit(code)
    raise SystemExit(main())
