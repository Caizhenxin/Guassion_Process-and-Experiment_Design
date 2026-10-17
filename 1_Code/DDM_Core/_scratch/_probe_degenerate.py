"""探针：量"被静默吸收的退化"到底有多频繁（主计划 D51 的证据）。

背景
----
`1_Code/DDM_Core/_scratch/_probe_nonfinite_obj.py` 已经证明：4 人合成数据上跑
M-T1 的 `hier.fit_and_loo`，会出现 **18 次非有限目标取值 / 16 条 `_numdiff` 警告**，
而同一份结果里 **`n_nonfinite_loglik = 0`**。

`subject_map_laplace` 有两条**静默吸收**退化的路径：
  (a) `if not np.isfinite(g(xm)): xm = x_init` —— 优化失败时把众数换成**起点**；
  (b) `g` 在某个扰动点返回 `-inf` —— 经过 `lambda x: -g(x)` 变成 `+inf`，
      SciPy 的数值梯度算出 `inf - finite` 就发警告，L-BFGS-B 照旧继续。

`n_nonfinite_loglik` 只看 **LOO 矩阵的元素**是否有限，所以 (a)(b) 它都看不见。
本探针量的是新增的两个计数器 `n_fallback` / `n_nonfinite_g`。

用法::

    python 1_Code\\DDM_Core\\_scratch\\_probe_degenerate.py [n_subjects] [n_rep] [n_em] [n_draws]
"""

from __future__ import annotations

import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[3]
_DDM = REPO / "1_Code" / "DDM_Core"
for _p in (str(_DDM), str(_DDM / "_scratch"), str(REPO / "1_Code" / "AutoRA_SPE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hier  # noqa: E402
import stage8_run as S8  # noqa: E402
from mapping import MappingParams  # noqa: E402

N_SUBJECTS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
N_REP = int(sys.argv[2]) if len(sys.argv) > 2 else 4
N_EM = int(sys.argv[3]) if len(sys.argv) > 3 else 2
N_DRAWS = int(sys.argv[4]) if len(sys.argv) > 4 else 4
#: 似然网格点数。**这不是无关紧要的旋钮**：`_probe_nonfinite_obj.py`（v2）在 `n_x=31`
#: 上量到 18 次非有限目标，本探针在 `n_x=41` 上量到 0 次 ⇒ 必须能改。
N_X = int(sys.argv[5]) if len(sys.argv) > 5 else 41


def teeth(sub: dict) -> bool:
    """(a) 必须有牙齿：`ll_x` 处处非有限 ⇒ 必须报出**带诊断**的显式错误。

    修守卫之前这里得到的是 `numpy.linalg.LinAlgError: Eigenvalues did not
    converge` —— 由 `eigvalsh` 在一个 NaN 的 Hessian 上抛出，消息里不含被试、
    超参数、也不含"众数已退回初值"这个关键事实。
    """
    print("\n" + "=" * 92)
    print("牙齿测试：`ll_x` 处处非有限 ⇒ 必须是**可归因**的显式报错")
    print("=" * 92)
    bad = dict(sub)
    bad["ll_x"] = lambda x: -np.inf
    k = len(bad["names"])
    try:
        r = hier.subject_map_laplace(bad, None, np.zeros(k), np.full(k, np.log(0.4)))
    except ValueError as exc:
        msg = str(exc)
        ok = ("fell_back=True" in msg) and ("n_nonfinite_g=" in msg)
        print("  ✅ 报出 ValueError（不再是 eigvalsh 的 LinAlgError）：")
        for line in msg.splitlines():
            print(f"     {line}")
        print(f"  ⇒ 诊断含 fell_back 与 n_nonfinite_g = {ok}")
        return ok
    except Exception as exc:                                    # noqa: BLE001
        print(f"  ❌ 报出了别的异常：{type(exc).__name__}: {exc}")
        return False
    print(f"  ❌ 没有报错，静默返回 fell_back={r['fell_back']}、"
          f"log_marginal={r['log_marginal']}")
    print("     ⇒ 这才是最坏情形：一个 NaN 的边际似然被当成正常结果")
    return False


def main() -> int:
    print("=" * 92)
    print("探针：D51 的退化计数（`n_nonfinite_loglik` 看不见的东西）")
    print(f"配置：n_subjects={N_SUBJECTS} n_rep={N_REP} n_em={N_EM} "
          f"n_draws={N_DRAWS} **n_x={N_X}**")
    print("=" * 92)
    tmp = Path(tempfile.mkdtemp(prefix="probe_degenerate_"))
    S8._synthetic(N_SUBJECTS, 7, 1, tmp, n_rep=N_REP)
    p_base = MappingParams(shape_model="lin")
    people, rejected = S8.collect([tmp], None, p_base)
    print(f"\n可用被试 {len(people)} 名；被拒 {len(rejected)} 份")

    teeth_ok = teeth(S8._subjects(people, True, N_X)[0])

    print("\n" + "=" * 92)
    print(f"真实路径：`fit_and_loo`（n_em={N_EM}、n_draws={N_DRAWS}、analytic）")
    print("=" * 92)
    for name, rho_free in S8.MODELS.items():
        subs = S8._subjects(people, rho_free, N_X)
        print(f"\n{'-' * 92}\n[{name}] rho_free={rho_free}\n{'-' * 92}")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            r = hier.fit_and_loo(subs, n_draws=N_DRAWS, seed=0, n_em=N_EM,
                                 hyper_method="analytic")
        st = r["loo_stats"]
        lk = r["loo"]
        print(f"  ELPD {lk['elpd_loo']:.3f} ± {lk['se']:.3f}；p_loo {lk['p_loo']:.2f}；"
              f"k_max {lk['k_max']}；越界 {lk['n_k_gt_bad']}/{lk['n_obs']}")
        print(f"  ❗ n_nonfinite_loglik = {r['n_nonfinite_loglik']}"
              f"（**只看 LOO 矩阵元素**，看不见下面两项）")
        print(f"  拟合阶段 degenerate：众数退回初值 {r['n_fallback_fit']} 次、"
              f"目标非有限 {r['n_nonfinite_g_fit']} 次")
        print(f"  LOO 阶段 degenerate：{st.get('n_fallback', 0)}/"
              f"{st.get('n_searches', 0)} 次搜索退回初值、"
              f"目标非有限 {st.get('n_nonfinite_g', 0)} 次")
        print(f"  `_numdiff` 警告 = "
              f"{len([w for w in caught if '_numdiff' in str(w.filename)])} 条")

    print("\n" + "=" * 92)
    print(f"牙齿测试 = {'✅ 通过' if teeth_ok else '❌ 失败'}")
    print("结论要点：`n_nonfinite_loglik` 是一个**只看矩阵元素**的计数器，")
    print("         它无法反映众数搜索退回初值与数值梯度失效 —— 两者都要单独报。")
    print("=" * 92)
    return 0 if teeth_ok else 1


if __name__ == "__main__":
    sys.exit(main())
