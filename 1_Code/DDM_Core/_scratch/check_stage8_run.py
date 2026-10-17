# -*- coding: utf-8 -*-
"""`stage8_run.py` 的自测 —— **廉价**验证渲染链路与成本模型（不真的拟合）。

为什么需要它：
* 端到端干跑动辄小时级（主因是 `hier.hyper_hessian` 的 `4·n(n+1)/2 · N` 次众数搜索），
  不能当作迭代循环的一部分；
* 本轮在 `render_group` 里抓到过一个**静默换参**缺陷：分单元 PPC 用了**被试 1** 的
  `t0` bounds 去反变换**所有被试**的众数 ⇒ PPC 模拟的不是刚拟合的那个模型。
  A5 就是这个缺陷的回归守卫；
* `project()` 曾**漏掉**超参数 Hessian 这一主导成本项 ⇒ A6 是它的守卫。

跑法：``python 1_Code/DDM_Core/_scratch/check_stage8_run.py``
"""

from __future__ import annotations

import inspect
import re
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
REPO = CORE.parent.parent
EXP_DIR = REPO / "1_Code" / "Experiment"
for _p in (CORE, EXP_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hier                                        # noqa: E402
import likelihood as L                             # noqa: E402
import mapping                                     # noqa: E402
import read_formal_data as RF                      # noqa: E402
import simulate                                    # noqa: E402
import stage8 as S8                                # noqa: E402
import stage8_run as SR                            # noqa: E402
from loo import psis_loo                           # noqa: E402
from mapping import MappingParams                  # noqa: E402

FAILS: list[str] = []
N_OK = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global N_OK
    if ok:
        N_OK += 1
        print(f"  ✅ {name}" + (f"：{detail}" if detail else ""))
    else:
        FAILS.append(name)
        print(f"  ❌ {name}" + (f"：{detail}" if detail else ""))


# ---------------------------------------------------------------- 造人（不拟合）

def make_people(n: int = 3, seed: int = 0):
    rng = np.random.default_rng(seed)
    design = simulate.build_design(0, [0.03333, 0.24998], [0.79998, 1.7999], 2)
    truth = MappingParams(d_ref=1.0, beta_T=0.45, beta_S=0.10, beta_ST=0.10,
                          shape_model="lin", t0=0.25)
    people = []
    for i in range(n):
        tr = simulate.simulate_subject(design, truth, rng)
        tr = {**design, **tr}
        tr, _fr = RF.fit_ready(tr)
        tb = RF.t0_bounds(tr)
        people.append({"file": f"fake_{i + 1}.txt", "subject": i + 1, "group": 1,
                       "t0_hi": float(tb["t0"][1]), "tr": tr, "tr_full": tr,
                       "t0_bounds": tb, "p_base": truth})
    return people


def modes_for(people, names):
    """给每名被试一个**互不相同**的无约束坐标（越靠后越偏），便于抓 bounds 串用。"""
    out = []
    for i, p in enumerate(people):
        lo, hi = hier._bounds_with_rho(names, p["t0_bounds"])
        out.append(np.full(len(lo), 0.2 * (i + 1)))
    return out


def names_of(rho_free: bool) -> list:
    return SR.WITHIN_FREE_LIN + (["rho"] if rho_free else [])


def make_results(people, k_max: float | None = None, seed: int = 1):
    """伪造 ``fit_group`` 的产物。

    ❗ ``loo`` 一律由**真实的** `loo.psis_loo` 产生，**不手写字典**：曾经这里手写成
    ``{"n_bad": 0, "n": N}``，而 `psis_loo` 实际返回的是 ``n_k_gt_bad`` / ``n_obs``
    ⇒ 自测 13/13 全绿，真实运行却在 `stage8_run.fit_group` 上 `KeyError: 'n_bad'`。
    **手写的 fixture 用与代码相同的错误键名时，测的是我的虚构，不是接口。**
    """
    rng = np.random.default_rng(seed)
    res = {}
    for name, rho_free in SR.MODELS.items():
        S, N = 30, len(people)
        L = rng.normal(-3.0, 0.3, size=(S, N))
        lk = psis_loo(L)                      # ← 真实产物；键名不可能与代码漂移
        if k_max is not None:
            lk = {**lk, "k_max": float(k_max)}   # 只覆盖被测判据的输入
        lk = {**lk, "elpd_loo": -100.0 + (0.0 if name == "M-T1" else -50.0)}
        res[name] = {
            "loo": lk,
            "seconds": 1.0, "rho_free": rho_free,
            "fit": {"modes": modes_for(people, names_of(rho_free))},
            "log_lik": L,
        }
    return res


# ---------------------------------------------------------------- A 组

def main() -> int:
    print("=" * 88)
    print("stage8_run.py 自测（廉价；不真的拟合层级模型）")
    print("=" * 88)

    people = make_people(3, seed=0)
    print(f"\n[准备] 造出 {len(people)} 名被试；"
          f"逐人 t0 上界 = {[round(p['t0_hi'], 4) for p in people]}；"
          f"逐人试次 = {[len(p['tr']['rt']) for p in people]}")

    # ---- A0：接口守卫 —— 从**源码本身**抽出 `stage8_run` 读的 loo 键，断言它们
    #          真实存在于 `loo.psis_loo` 的返回里。这条判据是本轮抓到的真 bug 的直接
    #          守卫：代码曾读 `lk["n_bad"]` / `lk["n"]`，而 psis_loo 返回的是
    #          `n_k_gt_bad` / `n_obs` ⇒ 真实运行 KeyError，自测却全绿（因为 fixture
    #          手写成了同样的错键名）。**必须用正则从源码抽，不能靠字面串匹配**：
    #          代码里单引号与双引号混用，字面匹配会漏掉一半。
    _real = psis_loo(np.random.default_rng(0).normal(-3.0, 0.3, size=(30, 3)))
    _src = inspect.getsource(SR)
    _read = set(re.findall(r"""lk\[\s*['"](\w+)['"]""", _src))
    _read |= set(re.findall(r"""lk\.get\(\s*['"](\w+)['"]""", _src))
    _missing = sorted(_read - set(_real))
    check("A0 接口守卫：`stage8_run` 从源码里读的 loo 键都真实存在",
          not _missing and len(_read) >= 5,
          f"源码中读到 {sorted(_read)}；`loo.psis_loo` 实际提供 "
          f"{sorted(_real)}；缺失 = {_missing or '无'}")

    # ---- A1：逐人 bounds 确实不同（否则 A5 是盲的）----
    his = [p["t0_hi"] for p in people]
    check("A1 逐人 t0 上界互不相同（A5 才有牙齿）",
          len(set(round(h, 9) for h in his)) == len(his),
          f"{[round(h, 6) for h in his]}")

    # ---- 装 spy：捕获 subject_laplace 收到的 p_map ----
    captured: list[dict] = []
    real_sl = S8.subject_laplace

    def spy_subject_laplace(tr, names, p_map, **kw):
        captured.append({"names": list(names),
                         "vector": np.asarray(p_map.vector(list(names)), float),
                         "bounds_override": kw.get("bounds_override")})
        return real_sl(tr, names, p_map, **kw)

    S8.subject_laplace = spy_subject_laplace
    sentinel = "SENTINEL_COMPARE_MODELS"
    real_cmp = hier.compare_models
    hier.compare_models = lambda results: sentinel
    try:
        results = make_results(people, k_max=0.5)
        lines = SR.render_group(results, people, tag="1", n_draws=8, seed=0)
        text = "\n".join(lines)
    finally:
        S8.subject_laplace = real_sl
        hier.compare_models = real_cmp

    # ---- A2：两个模型都出现在报告里 ----
    check("A2 两个模型都出现在报告里",
          all(n in text for n in SR.MODELS), f"{list(SR.MODELS)}")

    # ---- A3：compare_models 确实被调用（不靠猜输出格式）----
    check("A3 调用了 hier.compare_models（哨兵字符串出现）", sentinel in text)

    # ---- A4：每模型每人都渲染了 n_flipped ----
    n_flip_lines = sum(1 for ln in lines if "n_flipped" in ln)
    check("A4 分单元 PPC 段落齐全（n_flipped 行数 = 模型数 × 人数）",
          n_flip_lines == len(SR.MODELS) * len(people),
          f"{n_flip_lines} 行")

    # ---- A5：❗（d）缺陷的回归守卫 —— 逐人用**自己**的 bounds 反变换 ----
    expect = []
    for name, rho_free in SR.MODELS.items():
        names = SR.WITHIN_FREE_LIN + (["rho"] if rho_free else [])
        modes = modes_for(people, names)
        for i, p in enumerate(people):
            lo, hi = hier._bounds_with_rho(names, p["t0_bounds"])
            th = hier._from_x(modes[i], lo, hi)
            expect.append(np.asarray(th[:len(SR.WITHIN_FREE_LIN)], float))
    got = [c["vector"][:len(SR.WITHIN_FREE_LIN)] for c in captured]
    same = (len(got) == len(expect)
            and all(np.allclose(a, b, atol=1e-9) for a, b in zip(got, expect)))
    worst = max((float(np.max(np.abs(a - b))) for a, b in zip(got, expect)),
                default=float("nan"))
    check("A5 每名被试都用**自己**的 bounds 反变换（(d) 的守卫）",
          same, f"max|Δ| = {worst:.3e}")

    # A5b：这条守卫确实能分辨 —— 若串用被试 1 的 bounds，结果会明显不同
    names_mt1 = SR.WITHIN_FREE_LIN + ["rho"]
    m2 = modes_for(people, names_mt1)[1]
    lo1, hi1 = hier._bounds_with_rho(names_mt1, people[0]["t0_bounds"])
    lo2, hi2 = hier._bounds_with_rho(names_mt1, people[1]["t0_bounds"])
    d_wrong = np.max(np.abs(hier._from_x(m2, lo1, hi1) - hier._from_x(m2, lo2, hi2)))
    check("A5b 守卫可分辨（串用被试 1 的 bounds 会明显改变结果）",
          d_wrong > 1e-6, f"|Δ| = {d_wrong:.3e}")

    # ---- A6：project() 必须含超参数 Hessian 这一主导项 ----
    pj = SR.project(people, n_em=3, n_draws=20, n_models=len(SR.MODELS), n_ppc=5)
    nw = len(SR.WITHIN_FREE_LIN)
    want = sum(4.0 * (2 * (nw + (1 if rf else 0))) * (2 * (nw + (1 if rf else 0)) + 1) / 2.0
               for rf in SR.MODELS.values()) * len(people)
    check("A6 project() 含「超参数 Hessian」且计数正确",
          "超参数 Hessian" in pj and f"{want:.0f}" in pj,
          f"应为 {want:.0f} 次众数搜索")
    print("      " + pj.replace("\n", "\n      "))

    # ---- A7：k 挡位三条分支都印得出来 ----
    verdicts = {}
    for k in (0.5, 0.9, 1.4):
        r = make_results(people, k_max=k)
        t = "\n".join(SR.render_group(r, people, tag="1", n_draws=4, seed=0))
        verdicts[k] = t
    check("A7 k 挡位三档判定都正确",
          "可报 ΔELPD" in verdicts[0.5]
          and "降级为提示性" in verdicts[0.9]
          and "不构成证据" in verdicts[1.4])

    # ---- A7b：❗ `nan` 不是最差挡位。端到端干跑实测暴露：`k_max = nan` 时
    #           `nan <= 0.7` 与 `nan <= 1.0` 都是 False ⇒ 会掉进「k > 1.0」那一档，
    #           把"k 不可用"误报成"k 超界"。必须分开。
    r_nan = make_results(people, k_max=float("nan"))
    for v in r_nan.values():
        v["loo"] = {**v["loo"], "n_failed": v["loo"]["n_obs"]}
    t_nan = "\n".join(SR.render_group(r_nan, people, tag="1", n_draws=4, seed=0))
    check("A7b `k_max = nan` 必须报「LOO 无效」，不得误报成「k > 1.0 不构成证据」",
          "LOO 无效" in t_nan and "k > 1.0" not in t_nan,
          "命中「LOO 无效」" if "LOO 无效" in t_nan else "未命中「LOO 无效」")

    # ---- A7c/A7d：❗ 决策 D52 —— `k_max` 单独**没有分辨力**。N=4 analytic 干跑实测：
    #           `k_max = 0.000`、`n_failed = 0`（A7 的两条判据全过），而
    #           `p_loo = 2816.26` 对 `n_obs = 4`（LOO 单位 = 被试）⇒ 有效参数数是
    #           观测数的 704 倍。同一个 `k_max = 0.000` 在**健康**矩阵上也会出现
    #           （实测 `rng.normal(-3.0, 0.3, size=(30, 3))` 的另一次抽样：
    #           `p_loo = 0.222`、`k_max = 0.0`）⇒ 必须再看 `p_loo` 是否落在
    #           `[0, n_obs]`。
    r_ploo = make_results(people, k_max=0.0)
    for v in r_ploo.values():
        v["loo"] = {**v["loo"], "p_loo": 704.0 * v["loo"]["n_obs"]}   # 复刻干跑比值
    t_ploo = "\n".join(SR.render_group(r_ploo, people, tag="1", n_draws=4, seed=0))
    check("A7c `k_max = 0` 且 `n_failed = 0`、但 `p_loo` 越界 ⇒ 必须报「LOO 无效」",
          "LOO 无效" in t_ploo and "p_loo" in t_ploo,
          "命中「LOO 无效」" if "LOO 无效" in t_ploo else "未命中「LOO 无效」")
    r_neg = make_results(people, k_max=0.0)
    for v in r_neg.values():
        v["loo"] = {**v["loo"], "p_loo": -353.0}      # N=2 干跑实测 −706.37/−2900.54 同型
    t_neg = "\n".join(SR.render_group(r_neg, people, tag="1", n_draws=4, seed=0))
    check("A7d 负 `p_loo`（留一比拟合内还准）⇒ 也必须报「LOO 无效」",
          "LOO 无效" in t_neg)
    # 反向对照（防"一刀切"）：健康的 `p_loo` 必须仍然给出正常档位
    r_ok = make_results(people, k_max=0.5)
    for v in r_ok.values():
        v["loo"] = {**v["loo"], "p_loo": 0.05 * v["loo"]["n_obs"]}
    t_ok = "\n".join(SR.render_group(r_ok, people, tag="1", n_draws=4, seed=0))
    check("A7e 健康 `p_loo`（0 < p_loo/n_obs < 1）不得被 D52 闸门误伤",
          "LOO 无效" not in t_ok and "可报 ΔELPD" in t_ok)

    # ---- A7f（D74）：**「换到试次层」不是充分条件**。同一份代码的两个实测对照：
    #      3 人/n_em=2/n_x=21/S=20（Hessian 正定、`n_flipped`=0）⇒ 试次层 `p_loo/n_obs`=0.138；
    #      2 人/n_em=1/n_x=11/S=15（2 个负特征值、θ 逐维 SD 达 134）⇒ 试次层 8.57 / 12.7。
    #      所以 `p_loo` 即便落在健康区间，只要超参数 Hessian 非正定就必须一并拒绝。
    r_pd = make_results(people, k_max=0.5)
    for v in r_pd.values():
        v["loo"] = {**v["loo"], "p_loo": 0.05 * v["loo"]["n_obs"]}   # p_loo 健康
        v["hyper"] = {"eigval": [-0.9, 1.0, 2.0], "n_flipped": 1}
        v["loo_level"] = "trial"
    t_pd = "\n".join(SR.render_group(r_pd, people, tag="1", n_draws=4, seed=0))
    check("A7f `p_loo` 健康但超参数 Hessian 非正定 ⇒ 仍必须判「LOO 无效」（D74）",
          "LOO 无效" in t_pd and "非正定" in t_pd and "D74" in t_pd,
          "命中" if "LOO 无效" in t_pd else "未命中「LOO 无效」")
    # 反向对照：Hessian 正定 + 健康 p_loo ⇒ 不得被 D74 误伤
    r_pd_ok = make_results(people, k_max=0.5)
    for v in r_pd_ok.values():
        v["loo"] = {**v["loo"], "p_loo": 0.05 * v["loo"]["n_obs"]}
        v["hyper"] = {"eigval": [0.03, 1.0, 2.0], "n_flipped": 0}
        v["loo_level"] = "trial"
    t_pd_ok = "\n".join(SR.render_group(r_pd_ok, people, tag="1", n_draws=4, seed=0))
    check("A7g Hessian 正定 ⇒ 健康的 `p_loo` 照旧给「可报 ΔELPD」（D74 不误伤）",
          "LOO 无效" not in t_pd_ok and "可报 ΔELPD" in t_pd_ok)

    # ---- A8：剥离矩阵必须在**渲染之后** ----
    src = inspect.getsource(SR.run_group)
    i_render, i_strip = src.find("render_group("), src.find("strip_matrices(")
    check("A8 run_group 里 render_group 在 strip_matrices 之前（否则 compare_models KeyError）",
          -1 < i_render < i_strip, f"render@{i_render} strip@{i_strip}")
    r9 = make_results(people)
    SR.strip_matrices(r9)
    check("A8b strip_matrices 确实剥掉了 log_lik",
          all("log_lik" not in v for v in r9.values()))

    # ---- A9：结果可 JSON 序列化 ----
    try:
        js = json.dumps(SR._jsonable(make_results(people)), ensure_ascii=False)
        ok9, det9 = len(js) > 100, f"{len(js)} 字符"
    except Exception as exc:                                    # noqa: BLE001
        ok9, det9 = False, f"{type(exc).__name__}: {exc}"
    check("A9 _jsonable + json.dumps 可用", ok9, det9)

    # ---- A10：`x_init=None` 的守卫 ----
    # ❗ 误传 `None` 时，`np.asarray(None, float)` 是长度为 1 的 `[nan]`；
    #    L-BFGS 与 `hessian_x` 于是在 NaN 上原地打转，约 5 ms 就"收敛"、
    #    `n_flipped = 0` —— 一个**静默的无意义结果**（实测踩过，让两版微基准
    #    低估了两个数量级）。守卫必须是"回退到区间中点 + 非有限值报错"。
    sub1 = SR._subjects(people[:1], False, n_x=41)[0]
    npar = len(sub1["lo"])
    mu0 = np.zeros(npar)
    ls0 = np.full(npar, np.log(0.4))
    r_none = hier.subject_map_laplace(sub1, None, mu0, ls0)
    r_mid = hier.subject_map_laplace(sub1, hier._x0_of(sub1), mu0, ls0)
    ok10 = (r_none["mode"].size == npar
            and bool(np.all(np.isfinite(r_none["mode"])))
            and bool(np.allclose(r_none["mode"], r_mid["mode"], atol=1e-6)))
    check("A10 x_init=None 回退到区间中点（而不是 np.asarray(None) = [nan]）",
          ok10, f"size={r_none['mode'].size}、n_evals={r_none['n_evals']}、"
                f"与中点版 max|Δ|={np.max(np.abs(r_none['mode'] - r_mid['mode'])):.3e}")
    try:
        hier.subject_map_laplace(sub1, np.full(npar, np.nan), mu0, ls0)
        ok10b, det10b = False, "未报错"
    except ValueError as exc:                                   # noqa: BLE001
        ok10b, det10b = True, str(exc)[:70]
    check("A10b 非有限 x_init 显式报 ValueError", ok10b, det10b)

    # ---- A11/A12（D68）：超参数 Hessian 不正定 ⇒ 报告必须写清「σ 不得解读」 ----
    # 为什么这两条必须有：`hier.subject_map_laplace` 会把非正特征值抬到
    # `floor = max(1e-8·max|λ|, 1e-12)` 再取逆 ⇒ 该方向方差 ≈ 1/floor（可到 1e5），
    # 而层级 σ² = mean[(x − μ)² + Cov_kk] ⇒ 一个被抬过的方向就能把 σ 撑到没有意义。
    # 报告若只写「n_flipped = 1」而不写后果，读者会以为「记一笔就行」。
    r_np = make_results(people)
    for v in r_np.values():
        v["hyper"] = {"eigval": np.array([1e-2, 0.5, -2.3725, 3.0]),
                      "n_flipped": 1}
    t_np = "\n".join(SR.render_group(r_np, people, tag="1", n_draws=4, seed=0))
    check("A11 超参数 Hessian 有非正特征值 ⇒ 报告写明「σ 不得解读」",
          "n_flipped` = **1/4**" in t_np and "不得解读" in t_np
          and "1/floor" in t_np
          # 只禁止**无条件**说「正定」：D74 起同一份报告里会出现「非正定 ⇒ p_loo 不可解读」
          # 这句短语，它本身不是误报（`replace` 两版都剥掉，否则 D74 的判词会假阳）
          and "正定" not in t_np.replace("不正定", "").replace("非正定", ""),
          f"含 n_flipped = 1/4 = {'1/4' in t_np}、含「不得解读」= {'不得解读' in t_np}")
    r_pd = make_results(people)
    for v in r_pd.values():
        v["hyper"] = {"eigval": np.array([1e-2, 0.5, 2.0, 3.0]), "n_flipped": 0}
    t_pd = "\n".join(SR.render_group(r_pd, people, tag="1", n_draws=4, seed=0))
    check("A12 超参数 Hessian 正定 ⇒ 报「正定」、不得误报「不得解读」",
          "**正定**" in t_pd and "不得解读" not in t_pd,
          f"含「正定」= {'**正定**' in t_pd}、含「不得解读」= {'不得解读' in t_pd}")

    # ---- A13/A13b（D75）：`n_flipped` 是符号判据，必须与「抽样跑了多远」并列 ----
    # 实测（n_em=2、n_x=21、S=2、seed=7、~46 试次/人）：正定拟合 max|θ| ≤ 7.3，
    # 非正定拟合 33.6 / 62.8 / 97.9（2 人 S=15 那次 303）⇒ 两者分离 5–40 倍。
    r_ma = make_results(people)
    for v in r_ma.values():
        v["hyper"] = {"eigval": np.array([1e-2, 0.5, 2.0, 3.0]), "n_flipped": 0,
                      "max_abs_theta": 97.9}
    t_ma = "\n".join(SR.render_group(r_ma, people, tag="1", n_draws=4, seed=0))
    check("A13 报告必须印本次抽样的 `|θ|` 最大值（与 `n_flipped` 并列）",
          "97.9" in t_ma and "最大" in t_ma,
          f"含 97.9 = {'97.9' in t_ma}")
    r_ma2 = make_results(people)
    for v in r_ma2.values():
        v["hyper"] = {"eigval": np.array([1e-2, 0.5, 2.0, 3.0]), "n_flipped": 0}
    t_ma2 = "\n".join(SR.render_group(r_ma2, people, tag="1", n_draws=4, seed=0))
    check("A13b 缺 `max_abs_theta` 时必须写「未记录」（不得静默省略这一栏）",
          "未记录" in t_ma2, f"含「未记录」= {'未记录' in t_ma2}")
    # A14：退化拟合（无 `sigma` 字段）时不得印出 `****` 空粗体（D75 实跑踩到）
    check("A14 无 `sigma` 字段时不得印出空粗体 `****`",
          "****" not in t_ma2 and "****" not in t_ma,
          f"t_ma2 含 **** = {'****' in t_ma2}、t_ma 含 **** = {'****' in t_ma}")

    # ---- E 组（D66）：输入契约——不该吃的输入必须在入口点名拒绝 ----
    # ❗ 历史行为：把 `2_Data/Real_Data/EXP_data_combined.csv` 当 `--data` 喂进来，
    #    运行器一路走到 `RF.to_trials(rec)` 才抛**未捕获的 `KeyError: 'matchKey'`**
    #    （裸 traceback、exit 1）——而真实原因是"这个文件根本没有那 9 列"。
    csv = REPO / "2_Data" / "Real_Data" / "EXP_data_combined.csv"
    reason = SR._non_txt_reason(csv)
    expect_missing = ["block", "premature_press", "timeout",
                      "responded_by_deadline", "stimulus_onset_actual",
                      "stimulus_offset_actual", "mask_onset_actual",
                      "stimulus_dur_actual", "stimulus_frames"]
    n_missing = sum(1 for c in expect_missing if f"`{c}`" in reason)
    check("E1 非 txt 输入的拒绝理由点了 v4.1 契约、并列全缺列",
          ("v4.1" in reason and "HEADER25" in reason and n_missing == 9),
          f"点名缺列 {n_missing}/9；理由 {len(reason)} 字")
    try:
        SR.collect([csv], None, MappingParams(shape_model="lin"))
        ok_e2, det_e2 = False, "未抛 SystemExit"
    except SystemExit as exc:                                   # noqa: PERF203
        ok_e2, det_e2 = (exc.code == 2), f"exit code = {exc.code}"
    check("E2 喂 CSV ⇒ SystemExit(2)（不是裸 KeyError）", ok_e2, det_e2)
    try:
        SR.collect([REPO / "2_Data" / "Real_Data" / "HDDM_Traces"], None,
                   MappingParams(shape_model="lin"))
        ok_e3, det_e3 = False, "未抛 SystemExit"
    except SystemExit as exc:                                   # noqa: PERF203
        ok_e3, det_e3 = (exc.code == 2), f"exit code = {exc.code}"
    check("E3 目录里没有 *.txt ⇒ SystemExit(2) 且点名目录", ok_e3, det_e3)
    src = inspect.getsource(SR)
    ok_e4 = ("if not rec:" in src and "校验异常" in src
             and "_no_inputs_message" in src and "if not files:" in src)
    check("E4 静态：入口有 not rec / 校验异常 / 无输入三条守卫", ok_e4)

    # 正路不能因为新守卫而坏掉：合成 1 人仍应被收下
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        SR._synthetic(1, 7, 1, Path(td), n_rep=2)
        ppl, rej = SR.collect([Path(td)], None, MappingParams(shape_model="lin"))
        ok_e5 = (len(ppl) == 1 and not rej)
        check("E5 正路未被误伤：合成 1 人仍被收下", ok_e5,

              f"people={len(ppl)}、rejected={len(rej)}")
        check("E6 静态：报告表头的「来源」不再硬编码成「正式数据」（对照运行里那是错的标签）",
              "'--data '" in src and "if args.synthetic else '正式数据'" not in src)

    # ---- E13/E14（D72）：组级缓存 + `--resume` —— 真实 N 下跑几十小时，
    #      中途崩掉不能把已完成的组一起丢掉；同时"命中缓存"必须在日志里看得见。
    import contextlib
    import io as _io

    calls: list[str] = []
    real_run_group = SR.run_group

    def fake_run_group(plist, tag, *a, **kw):        # noqa: ANN001
        calls.append(str(tag))
        return {"lines": [f"FAKE-GROUP-{tag}"], "results": {"n": len(plist)}}

    with tempfile.TemporaryDirectory() as td:
        outd = Path(td) / "out"
        argv = ["--synthetic", "2", "--synth-n-rep", "2", "--n-em", "1",
                "--n-draws", "1", "--n-x", "11", "--out", str(outd)]
        SR.run_group = fake_run_group
        try:
            buf1 = _io.StringIO()
            with contextlib.redirect_stdout(buf1):
                rc1 = SR.main(argv)
            gf = SR._group_file(outd, 1)
            ok13a = (rc1 == 0 and calls == ["1"] and gf.exists())
            payload = json.loads(gf.read_text(encoding="utf-8"))
            ok13b = (payload.get("tag") == "1" and payload.get("lines") == ["FAKE-GROUP-1"]
                     and payload.get("results") == {"n": 2})
            rep = (outd / "stage8_report.md").read_text(encoding="utf-8")
            ok13c = "FAKE-GROUP-1" in rep and "命中缓存" not in buf1.getvalue()
            ok13d = not list(outd.glob("*.tmp"))
            calls_first = list(calls)
            config_before = gf.read_text(encoding="utf-8")
            calls.clear()
            buf2 = _io.StringIO()
            with contextlib.redirect_stdout(buf2):
                rc2 = SR.main(argv + ["--resume"])
            calls_second = list(calls)
            rep2 = (outd / "stage8_report.md").read_text(encoding="utf-8")
            ok14 = (rc2 == 0 and calls_second == [] and "命中缓存" in buf2.getvalue()
                    and "FAKE-GROUP-1" in rep2
                    and "复用缓存" in rep2
                    and gf.read_text(encoding="utf-8") == config_before)
        finally:
            SR.run_group = real_run_group
        check("E13 每组拟合完立刻落盘 `stage8_group_<组>.json`（长跑崩溃只丢当前组）",
              ok13a and ok13b and ok13c and ok13d,
              f"exit={rc1}、run_group 调用={calls_first}、缓存存在={gf.exists()}")
        check("E14 `--resume` 命中缓存 ⇒ 不再拟合、日志写明「命中缓存」、缓存不被改写",
              ok14, f"exit={rc2}、run_group 调用={calls_second}")
        # E15：缓存必须绑定配置 —— 换 `n_em` 再 `--resume` 必须报错（不许混配置）
        try:
            with contextlib.redirect_stdout(_io.StringIO()):
                SR.main(argv + ["--resume", "--n-em", "2"])
            ok15, det15 = False, "未报错"
        except ValueError as exc:
            ok15, det15 = ("配置" in str(exc)), str(exc)[:80]
        check("E15 换 `n_em` 再 `--resume` ⇒ 报配置不一致（不许静默混配置）", ok15, det15)
        # E14b：缓存损坏 ⇒ 大声失败（不静默重算）
        gf.write_text("{ not json", encoding="utf-8")
        try:
            with contextlib.redirect_stdout(_io.StringIO()):
                SR.main(argv + ["--resume"])
            ok14b, det14b = False, "未报错"
        except ValueError as exc:
            ok14b, det14b = True, str(exc)[:70]
        check("E14b 缓存损坏 ⇒ 报 ValueError（不静默重拟合）", ok14b, det14b)

    # E16（D72 加固）：缓存必须**原子**落盘 —— `Path.write_text` 写到一半被杀会留下
    # 半截 JSON，`--resume` 就会把它当损坏缓存（用户得手工删）；原子写让「存在」=「完整」。
    src2 = inspect.getsource(SR)
    ok16 = ("_write_json_atomic" in src2 and "os.replace(tmp, path)" in src2
            and "gf.write_text(" not in src2 and "import os" in src2)
    check("E16 静态：单组缓存走 `*.tmp` + `os.replace`（原子写，半截文件不冒充完整缓存）", ok16)

    # E17（D73）：`--loo-level` 必须**透传到拟合**、进报告头、并进缓存配置键 ——
    # 后者是硬要求：同一个 `--out` 目录先用 participant 跑完、再用 trial `--resume`，
    # 若配置键里没有口径，就会静默复用**另一层**的矩阵去算 ΔELPD。
    with tempfile.TemporaryDirectory() as td2:
        outd2 = Path(td2) / "out"
        kw_seen: list[dict] = []

        def fake_run_group2(plist, tag, *a, **kw):     # noqa: ANN001
            kw_seen.append(dict(kw))
            return {"lines": [f"FAKE-GROUP-{tag}"], "results": {"n": len(plist)}}

        argv2 = ["--synthetic", "2", "--synth-n-rep", "2", "--n-em", "1",
                 "--n-draws", "1", "--n-x", "11", "--out", str(outd2)]
        SR.run_group = fake_run_group2
        try:
            with contextlib.redirect_stdout(_io.StringIO()):
                rc3 = SR.main(argv2 + ["--loo-level", "trial"])
            rep3 = (outd2 / "stage8_report.md").read_text(encoding="utf-8")
            # 同口径 resume 必须命中缓存、不报错
            with contextlib.redirect_stdout(_io.StringIO()):
                rc4 = SR.main(argv2 + ["--loo-level", "trial", "--resume"])
            kw_after_resume = list(kw_seen)
            # 换回 participant 再 resume ⇒ 必须报配置不一致
            try:
                with contextlib.redirect_stdout(_io.StringIO()):
                    SR.main(argv2 + ["--resume"])
                ok17c, det17c = False, "未报错"
            except ValueError as exc:
                ok17c, det17c = ("配置" in str(exc)), str(exc)[:90]
        finally:
            SR.run_group = real_run_group
        ok17a = bool(kw_seen) and kw_seen[0].get("loo_level") == "trial"
        ok17b = "LOO 口径 = `trial`" in rep3
        check("E17 `--loo-level` 透传到拟合 + 写进报告头 + 进缓存配置键（D73）",
              rc3 == 0 and ok17a and ok17b and len(kw_after_resume) == 1 and ok17c,
              f"exit={rc3}、拟合收到 loo_level={kw_seen[0].get('loo_level') if kw_seen else None}、"
              f"报告头含口径={ok17b}、同口径 resume 未重拟合="
              f"{len(kw_after_resume) == 1}、换口径报错={det17c}")

    print("\n" + "=" * 88)
    print(f"共 {N_OK + len(FAILS)} 项，未通过 {len(FAILS)} 项"
          + (f"：{', '.join(FAILS)}" if FAILS else "。"))
    print("=" * 88)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
