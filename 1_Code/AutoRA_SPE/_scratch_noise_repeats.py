"""量「噪声标定」本身的稳定性：同一个锚点设计在 `n_fim` 下换种子重算 6 次。

**为什么要做这件事**：判据的噪声带是 `2·sd_A` / `2·sd_B`，而它们目前由
`measure_noise(..., n_repeats=2)` 估出 —— 2 个样本的标准差（`ddof=1`）本身极不稳，
`sd` 的相对不确定度大约 50%。第 26 轮实测 `n_fim = 1 → 12` 时
`sd_J` 由 2.9247 掉到 0.4056（−86%），但 `sd_A` 反而由 0.0025 涨到 0.0082。
后者是**真的**还是**2 次重复估不准**的产物，只有把重复数加大才能回答 ——
而这条读数直接决定「判据带宽报多少」。

**它不改任何冻结量**：只读 `stage9_loop.measure_noise`，不写任何落盘件。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import stage9_loop as L  # noqa: E402

N_REPEATS = 6


def main() -> int:
    designs = L.enumerate_designs(verbose=False)
    print(f"候选设计 {len(designs)} 个；锚点 = {L.ANCHOR_DESIGN}；每个 n_fim 重复 {N_REPEATS} 次", flush=True)
    for n_fim in (1, 12):
        ev = L.Evaluator(designs, rho=None, n_fim=int(n_fim), n_subjects=40,
                         P=None, param_set="exp", base_seed=0, verbose=False)
        t0 = time.time()
        out = L.measure_noise(ev, n_repeats=N_REPEATS)
        dt = time.time() - t0
        print()
        print("=" * 70)
        print(f"n_fim = {n_fim}：{dt:.1f} s、{ev.n_evals} 次内环评估")
        print("=" * 70)
        print("  A (逐次) =", [round(float(v), 5) for v in out["A"]])
        print("  B (逐次) =", [round(float(v), 4) for v in out["B"]])
        print("  遗漏率   =", [round(float(v), 5) for v in out["omission"]])
        print("  C (逐次) =", [round(float(v), 4) for v in out["C"]])
        print("  J (逐次) =", [round(float(v), 4) for v in out["J"]])
        for k in ("sd_A", "sd_B", "sd_J", "sd_omission", "sd_C"):
            print(f"  {k:12s} = {float(out[k]):.5f}")
        print(f"  2·sd_A      = {2 * float(out['sd_A']):.5f}")
        print(f"  2·sd_B      = {2 * float(out['sd_B']):.5f}")
        print(f"  alpha       = {float(out['alpha']):.5g}")
        # 相对离散度：sd 与量级之比，用来跨 n_fim 比较（(A) 本身随 n_fim 变小）
        import numpy as _np
        for k, arr in (("A", out["A"]), ("B", out["B"]), ("omission", out["omission"])):
            m = float(_np.mean(arr))
            print(f"  {k:12s}: 均值 {m:.5f}、相对离散 sd/|均值| = "
                  f"{float(out['sd_' + k]) / m * 100:.3f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
