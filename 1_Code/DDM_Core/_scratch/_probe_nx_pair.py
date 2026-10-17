# -*- coding: utf-8 -*-
"""单被试的 `n_x` A/B 对照：同一名被试、同一起点，只改似然网格点数。

问题：`_probe_nonfinite_obj.py`（v2，n_x=31）量到 18 次非有限目标取值，
而 `_probe_degenerate.py`（n_x=41）量到 0 次。两者数据逐位相同、spy 已被确认
数值惰性 ⇒ 怀疑差别出在 `n_x`。本脚本在**最小代价**下把这一点单独隔出来：
不做 EM、不做 LOO，只反复调 `subject_map_laplace`，读 D51 新增的
`fell_back` / `n_nonfinite_g` 两个计数器。

用法：
    python 1_Code/DDM_Core/_scratch/_probe_nx_pair.py [n_subjects] [n_rep] [n_x...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
_DDM = _HERE.parent
_CODE = _DDM.parent
for _p in (_DDM, _CODE / "Experiment", _CODE / "AutoRA_SPE"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import stage8_run as S8                                            # noqa: E402
from hier import subject_map_laplace                               # noqa: E402
from mapping import MappingParams                                  # noqa: E402

N_SUBJECTS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
N_REP = int(sys.argv[2]) if len(sys.argv) > 2 else 4
NX_LIST = [int(a) for a in sys.argv[3:]] or [31, 41]


def main() -> int:
    import tempfile
    print("=" * 92)
    print("单被试 n_x A/B 对照（数据与人干跑逐位相同）")
    print("=" * 92)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        S8._synthetic(N_SUBJECTS, 7, 1, tmp, n_rep=N_REP)
        people, _rejected = S8.collect([tmp], None, MappingParams(shape_model="lin"))

    for rho_free in (True, False):
        label = "M-T1" if rho_free else "M-T3"
        print("\n" + "-" * 92)
        print(f"[{label}] rho_free={rho_free}")
        print("-" * 92)
        ref = None
        for n_x in NX_LIST:
            subs = S8._subjects(people, rho_free, n_x)
            k = len(subs[0]["names"])
            mu0 = np.zeros(k)
            ls0 = np.full(k, np.log(0.4))
            tot_nfg = 0
            tot_fb = 0
            tot_ev = 0
            lm = []
            for s in subs:
                r = subject_map_laplace(s, None, mu0, ls0)
                tot_nfg += r["n_nonfinite_g"]
                tot_fb += int(r["fell_back"])
                tot_ev += r["n_evals"]
                lm.append(r["log_marginal"])
            key = tuple(round(v, 6) for v in lm)
            if ref is None:
                ref = key
                dmax = 0.0
            else:
                dmax = max(abs(a - b) for a, b in zip(key, ref))
            print(f"  n_x={n_x:<4d} 非有限 g={tot_nfg:<4d} 退回初值={tot_fb:<3d} "
                  f"总评估={tot_ev:<5d} Σlog_marg={sum(lm):+.6f} "
                  f"与 n_x={NX_LIST[0]} 的 max|Δlm|={dmax:.3e}")
    print("\n" + "=" * 92)
    print("读法：若非有限 g 只在较粗的网格上非零 ⇒ 现象是**网格分辨率依赖**的，")
    print("      那么 D51 的结论必须连同 `n_x` 一起报，且干跑（--n-x 31）与自测")
    print("      （n_x=41）不是同一配置。")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
