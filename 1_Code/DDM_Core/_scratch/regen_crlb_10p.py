# -*- coding: utf-8 -*-
"""只重跑 CRLB 部分（10 参数口径，含 dz_S），不动 oracle / 试次图。

用 `make_sim_figures.py` 自己的函数，保证产物与整套脚本逐字节同源：
    fig_sim_crlb.png   ——  3_Figures/figures_sim/
    sim_crlb.csv       ——  5_Reference/03_论文写作/figures_sim/

为什么单独写：`make_sim_figures.main()` 会顺带跑 oracle（3 场景 × 6 个 N ×
400 次重复），与 `dz_S` 无关，几分钟纯浪费；且 oracle 的 CSV 不该被这次改动覆盖。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "1_Code" / "Experiment"))

import make_sim_figures as M  # noqa: E402


def main() -> int:
    out = _ROOT / "5_Reference" / "03_论文写作" / "figures_sim"
    figout = _ROOT / "3_Figures" / "figures_sim"
    out.mkdir(parents=True, exist_ok=True)
    figout.mkdir(parents=True, exist_ok=True)

    plt, lang = M.setup_matplotlib("zh")
    print("CRLB（10 参数，含 dz_S）…", flush=True)
    c = M.crlb(12)
    for n in c["names"]:
        se, tv = c["se"][n], c["truth"][n]
        print(f"  {n:8s} 真值={tv:7.4f}  SE={se:9.4f}  相对={se / abs(tv):7.3f}  "
              f"10% 需 N={M.n_for_target(c, n, 0.10)}  25% 需 N={M.n_for_target(c, n, 0.25)}")

    p = M.fig_crlb(plt, c, figout, lang)
    print(f"\n图 → {p}")
    with (out / "sim_crlb.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["param", "truth", "se_per_subject", "n_for_10pct", "n_for_25pct"])
        for n in c["names"]:
            w.writerow([n, c["truth"][n], c["se"][n],
                        M.n_for_target(c, n, 0.10), M.n_for_target(c, n, 0.25)])
    print(f"表 → {out / 'sim_crlb.csv'}")
    print(f"   试次={c['n_trials']}  正确率={c['acc']:.3f}  遗漏={c['omission']:.3f}  RT={c['rt_ms']:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
