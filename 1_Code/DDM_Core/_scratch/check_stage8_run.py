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


def make_results(people, k_max: float = 0.5, seed: int = 1):
    rng = np.random.default_rng(seed)
    res = {}
    for name, rho_free in SR.MODELS.items():
        names = SR.WITHIN_FREE_LIN + (["rho"] if rho_free else [])
        S, N = 30, len(people)
        res[name] = {
            "loo": {"elpd_loo": -100.0 + (0.0 if name == "M-T1" else -50.0),
                    "se": 3.0, "p_loo": 5.0, "k_max": k_max,
                    "n_bad": 0, "n": N, "n_failed": 0},
            "seconds": 1.0, "rho_free": rho_free,
            "fit": {"modes": modes_for(people, names)},
            "log_lik": rng.normal(-3.0, 0.3, size=(S, N)),
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

    print("\n" + "=" * 88)
    print(f"共 {N_OK + len(FAILS)} 项，未通过 {len(FAILS)} 项"
          + (f"：{', '.join(FAILS)}" if FAILS else "。"))
    print("=" * 88)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
