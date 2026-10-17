# -*- coding: utf-8 -*-
"""D68 的稳健性补测：换一个种子重跑 N=3 的两个组合。

动机：`_probe_hess_scaling.py` 每组只跑了一个种子（DDM 用 `seed=7`、非 DDM 用 0/1）。
若「N=3 非正定」只是某一个种子的偶然，那 D68 的结论就要打折扣。
本脚本只跑 **N=3 × {DDM, 非 DDM} × seed=99** 两格（各约 150–170 s），够回答「换种子还会不会」。

用法：``python -X utf8 -u _probe_hess_seedcheck.py``
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _probe_hess_scaling as S                                    # noqa: E402

SEED = 99


def main() -> int:
    print("=" * 78)
    print(f"稳健性补测：N=3、seed = {SEED}（主扫描用 seed 7 / 0 / 1）")
    print("=" * 78)
    bad = 0

    for tag, kw in (
        ("DDM、M-T1", dict(ddm=True, rho_free=True)),
        ("非 DDM、M-T1", dict(ddm=False, rho_free=True)),
    ):
        t0 = time.perf_counter()
        r = S.fit_group(3, seed=SEED, **kw)
        rep = S.eig_report(r["fit"])
        print(S.line(f"seed{SEED}: N=3、{tag}", r)
              + f"、{time.perf_counter() - t0:.0f}s")
        if rep["n_nonpos"] == 0:
            print(f"  ❗ {tag}：换种子后变正定 ⇒ 「N=3 必然非正定」不成立")
            bad += 1

    print("\n结论：" + ("两类数据换种子后**仍然非正定** ⇒ N=3 非正定不是单一种子的偶然。"
                    if bad == 0 else f"有 {bad} 格变正定 ⇒ 结论需降级为「多数种子非正定」。"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
