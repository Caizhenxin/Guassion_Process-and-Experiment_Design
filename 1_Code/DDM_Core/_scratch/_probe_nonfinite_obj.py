"""定位「`_numdiff.py:686 invalid value encountered in subtract`」的出处（v2）。

背景：analytic 干跑（`stage8_run.py --synthetic 4 --synth-n-rep 4 --n-em 2
--n-draws 32 --n-x 31 --hyper-method analytic`）里出现
    `scipy/optimize/_numdiff.py:686` 的
    `RuntimeWarning: invalid value encountered in subtract`
代码行 = `df = [f_eval - f0 for f_eval in f_evals]`（在 `_dense_difference` 里）。

v1 只猴补了 `hier.minimize` 并只跑 `hier_fit` ⇒ **未复现**（2223 次目标调用、0 次非有限）。
v2 的做法（本次）：
  * **在 import 任何本项目模块之前**先猴补 `scipy.optimize.minimize`（以及
    `minimize_scalar`），这样 `hier` / `likelihood` / `twophase` 通过
    `from scipy.optimize import minimize` 绑定到的都是带记录器的版本；
  * **跑完整的 `hier.fit_and_loo`**（含 `hier_fit` → `hyper_draws` → `loo_matrix`
    → `psis_loo`），而不是只跑 `hier_fit`；
  * 每次非有限目标取值都记录**调用方文件:行号**与参数向量，
    这样能直接指出是哪一处优化在找死。

⚠️ 与干跑一样用 `make_fake_pilot.py` 造数据（seed 7 / group 1 / n-rep 4），
已确认与干跑逐被试试次数与 `t0` 上界完全一致。`n_draws` 调小到 4 只为省时
（非有限目标与抽取条数无关：`loo_matrix` 每个 (抽取, 被试) 都独立重求众数）。

用法：`python _scratch/_probe_nonfinite_obj.py [n_subjects] [n_rep] [n_em] [n_draws]`
"""

from __future__ import annotations

import sys
import tempfile
import traceback
import warnings
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
DDM_DIR = HERE.parent
REPO = DDM_DIR.parent.parent
for p in (str(DDM_DIR), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------
# 0. 先装记录器，再 import 本项目模块（顺序是关键）
# ---------------------------------------------------------------
import scipy.optimize as so  # noqa: E402

N_SUBJECTS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
N_REP = int(sys.argv[2]) if len(sys.argv) > 2 else 4
N_EM = int(sys.argv[3]) if len(sys.argv) > 3 else 2
N_DRAWS = int(sys.argv[4]) if len(sys.argv) > 4 else 4
N_X = 31

#: (参数向量或 None, 目标值, method, 调用方 file:line)
NONFINITE: list[tuple[np.ndarray | None, float, str, str]] = []
CALLS = [0]


def _caller() -> str:
    st = traceback.extract_stack()
    for fr in reversed(st[:-2]):
        if "DDM_Core" in fr.filename and "_probe_nonfinite_obj" not in fr.filename:
            return f"{Path(fr.filename).name}:{fr.lineno}"
    return "?"


def _method_of(a, kw, default: str) -> str:
    if "method" in kw:
        return str(kw["method"])
    return str(a[1]) if len(a) > 1 else default


def make_spy(orig, default_method: str):
    def spy(fun, *a, **kw):
        if not callable(fun):
            return orig(fun, *a, **kw)
        who = _caller()
        meth = _method_of(a, kw, default_method)

        def wrapped(x):
            CALLS[0] += 1
            v = fun(x)
            if not np.isfinite(v):
                try:
                    xa = np.asarray(x, float).ravel().copy()
                except Exception:                                  # noqa: BLE001
                    xa = None
                NONFINITE.append((xa, float(v), meth, who))
                # 立刻打印：即使进程被中断也能拿到归因（v1 的教训）
                shown = "?" if xa is None else np.round(xa, 3).tolist()
                print(f"      ⛔ 非有限目标 #{len(NONFINITE):<3d} v={v:+.1f} "
                      f"method={meth} caller={who} x={shown}", flush=True)
            return v

        return orig(wrapped, *a, **kw)

    return spy


_orig_minimize = so.minimize
_orig_minimize_scalar = so.minimize_scalar
so.minimize = make_spy(_orig_minimize, "L-BFGS-B(默认)")
so.minimize_scalar = make_spy(_orig_minimize_scalar, "bounded(默认)")

import hier  # noqa: E402
import stage8_run as S8  # noqa: E402
from mapping import MappingParams  # noqa: E402
from twophase import log_likelihood_step  # noqa: E402

print("已装的记录器：")
print(f"  hier.minimize is so.minimize                     → {hier.minimize is so.minimize}")
print(f"  stage8_run 模块已加载 = {'stage8_run' in sys.modules}")


def main() -> int:
    print("=" * 92)
    print("探针 v2：`_numdiff` 警告的出处（全量 minimize 覆盖 + 完整 fit_and_loo）")
    print("=" * 92)

    tmp = Path(tempfile.mkdtemp(prefix="probe_nonfinite_"))
    S8._synthetic(N_SUBJECTS, 7, 1, tmp, n_rep=N_REP)
    p_base = MappingParams(shape_model="lin")
    people, rejected = S8.collect([tmp], None, p_base)
    print(f"\n可用被试 {len(people)} 名；被拒 {len(rejected)} 份")

    MODELS = S8.MODELS
    print(f"模型表 = {MODELS}（True ⇒ rho 自由 = M-T1）")

    out = {}
    for name, rho_free in MODELS.items():
        subs = S8._subjects(people, rho_free, N_X)
        before = len(NONFINITE)
        print(f"\n{'-' * 92}\n[{name}] rho_free={rho_free}：fit_and_loo"
              f"（n_em={N_EM}、n_draws={N_DRAWS}、analytic）\n{'-' * 92}")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            r = hier.fit_and_loo(subs, n_draws=N_DRAWS, seed=0, n_em=N_EM,
                                 hyper_method="analytic")
        numdiff = [w for w in caught if "_numdiff" in str(w.filename)]
        lk = r["loo"]
        print(f"  ✅ 完成：ELPD {lk['elpd_loo']:.3f} ± {lk['se']:.3f}；"
              f"p_loo {lk['p_loo']:.2f}；k_max {lk['k_max']}；"
              f"越界 {lk['n_k_gt_bad']}/{lk['n_obs']}；"
              f"**非有限 LOO 项 {r['n_nonfinite_loglik']}**")
        print(f"  本模型新捕获非有限目标取值 {len(NONFINITE) - before} 次；"
              f"`_numdiff` 警告 {len(numdiff)} 条")
        out[name] = r

    print("\n" + "=" * 92)
    print(f"合计：目标函数调用 {CALLS[0]} 次；非有限取值 {len(NONFINITE)} 次")
    print("=" * 92)

    if not NONFINITE:
        print("❗ 仍未复现非有限目标取值 —— 说明该警告依赖干跑的具体随机路径，")
        print("   不能据此宣称「无害」。")
        return 0

    by_caller: dict[tuple[str, str], int] = {}
    for _x, _v, meth, who in NONFINITE:
        by_caller[(who, meth)] = by_caller.get((who, meth), 0) + 1
    print("\n按调用方归因：")
    for (who, meth), c in sorted(by_caller.items(), key=lambda kv: -kv[1]):
        print(f"  {c:6d} ×  {who:>28s}  method={meth}")

    names = S8._subjects(people, True, N_X)[0]["names"]
    lo, hi = S8._subjects(people, True, N_X)[0]["lo"], S8._subjects(people, True, N_X)[0]["hi"]
    print("\n前 5 个非有限取值的参数向量（无约束 x 解码到自然尺度）：")
    for xa, v, meth, who in NONFINITE[:5]:
        if xa is None:
            print(f"  目标值={v}  {who}  （参数向量不可解码）")
            continue
        th = hier._from_x(xa, lo, hi)
        tags = []
        for j, n in enumerate(names):
            span = hi[j] - lo[j]
            rel = (th[j] - lo[j]) / span if span > 0 else 0.0
            if rel < 0.02 or rel > 0.98:
                tags.append(f"{n}={th[j]:.4g}{'↓' if rel < 0.02 else '↑'}")
        print(f"  目标值={v:+.1f}  来自 {who}  触界={tags or '（无）'}")
        print(f"    θ = {dict(zip(names, np.round(th, 5).tolist()))}")

    # 判定：把第一个捕获点代入原始似然，看它是不是真的不可求值
    xa, v, meth, who = NONFINITE[0]
    if xa is not None:
        th = hier._from_x(xa, lo, hi)
        k_lin = len(S8.WITHIN_FREE_LIN)
        ll = log_likelihood_step(p_base.with_vector(names[:k_lin], th[:k_lin]),
                                 people[0]["tr"], float(th[-1]), n_x=N_X)
        print(f"\n把首个捕获点代入 `log_likelihood_step` ⇒ {ll!r}"
              f"（finite={np.isfinite(ll)}）")

    print("\n" + "=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
