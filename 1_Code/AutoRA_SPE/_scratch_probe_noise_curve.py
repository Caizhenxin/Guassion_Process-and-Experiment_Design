# -*- coding: utf-8 -*-
"""量内环 MC 噪声随 `n_fim` 的标度，用来决定四路消融需要多大的 `n_fim`。

**为什么需要它**（D53 的开放项 (1)）：`stage9_loop.py` 的冒烟在 `n_fim=1` 上量到
`sd_J = 2.92`，而四臂的 `best J` 只差 0.47–0.64 ⇒ 该配置下的臂间比较不可解释。噪声带
`2·sd_J` 必须**小于**设计之间的差异，四路消融才有分辨力；而 `sd_J` 应该按 `1/sqrt(n_fim)`
缩小，所以先把这条标度测出来，再决定预算。

**它测什么**：对锚点设计（D4）在 `n_fim ∈ {1,2,4,8}` 上用**同一组种子偏移**
（`cell_seed(name, base_seed + 791_900 + 37·k)`，k = 0…4）各算 5 次，报 `J` 的样本 SD、
`2·sd_J`，以及按 `1/sqrt(n_fim)` 反推到「要使 `2·sd_J < 0.47`（冒烟里最小的臂间差异）
所需的 `n_fim`」。

用法：
    python -u 1_Code/AutoRA_SPE/_scratch_probe_noise_curve.py [n_repeats] [rho]
"""
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import stage9_loop as L  # noqa: E402

N_REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
RHO = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
N_FIMS = (1, 2, 4, 8)
ARM_SPREAD = 0.47  # 冒烟里最小的臂间 best-J 差异（grid 0.4673 vs manual 0.5112）


def main() -> int:
    print("=" * 78)
    print(f"内环 MC 噪声标度：锚点 = {L.ANCHOR_DESIGN}")
    print(f"n_fim ∈ {N_FIMS}、n_repeats = {N_REPEATS}、rho = {RHO}、"
          f"每设计 n_subjects = 40、P = {L.P_SINGLE if hasattr(L, 'P_SINGLE') else 'P_SINGLE'}")
    print("=" * 78)
    designs = L.enumerate_designs(verbose=False)
    one = [d for d in designs if d["name"] == L.ANCHOR_DESIGN]
    if not one:
        print("❌ 锚点不在候选集里")
        return 2
    rows = []
    t0 = time.time()
    for f in N_FIMS:
        ev = L.Evaluator([one[0]], rho=RHO, n_fim=f, n_subjects=40, verbose=False)
        noise = L.measure_noise(ev, N_REPEATS)
        js = list(noise["J"])
        rows.append(noise)
        print(f"\nn_fim = {f}：sd_J = {noise['sd_J']:.4f}、2·sd_J = {2 * noise['sd_J']:.4f}、"
              f"sd_A = {noise['sd_A']:.4f}、sd_B = {noise['sd_B']:.4f}")
        print(f"    J = {['%.4f' % v for v in js]}")
        print(f"    A = {['%.4f' % v for v in noise['A']]}")
        print(f"    B = {['%.4f' % v for v in noise['B']]}")
        print(f"    ❗ 遗漏率 = {['%.4f' % v for v in noise['omission']]}"
              f"（sd = {noise['sd_omission']:.5f}）")
        print(f"    ❗ C（遗漏率罚分）= {['%.4f' % v for v in noise['C']]}"
              f"（sd = {noise['sd_C']:.4f}）"
              f" ⇒ 占 J 方差 {100 * noise['sd_C'] ** 2 / max(noise['sd_J'] ** 2, 1e-30):.1f}%")

    print("\n" + "=" * 78)
    print("| n_fim | sd_J | 2·sd_J | sd_omission | sd_C | C 占 J 方差 | 能否分辨 0.47 的臂间差异 |")
    print("|---|---|---|---|---|---|---|")
    ok = {}
    for f, noise in zip(N_FIMS, rows):
        sd = noise["sd_J"]
        frac = noise["sd_C"] ** 2 / max(sd ** 2, 1e-30)
        resolved = (2 * sd) < ARM_SPREAD
        ok[f] = resolved
        print(f"| {f} | {sd:.4f} | {2 * sd:.4f} | {noise['sd_omission']:.5f} | "
              f"{noise['sd_C']:.4f} | {100 * frac:.1f}% | {'✅ 能' if resolved else '❌ 不能'} |")

    base = rows[0]["sd_J"]
    if base > 0:
        need = (2 * base / ARM_SPREAD) ** 2
        print(f"\n按 `sd_J ∝ 1/sqrt(n_fim)` 从 n_fim=1 反推："
              f"要使 `2·sd_J < {ARM_SPREAD}` 需 `n_fim ≥ {need:.1f}`。")
        for f, noise in zip(N_FIMS, rows):
            pred = base / (f ** 0.5)
            print(f"  预测 n_fim={f}：sd_J ≈ {pred:.4f}（实测 {noise['sd_J']:.4f}）")
    print(f"\n总耗时 {time.time() - t0:.1f}s")
    return 0 if any(ok.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
