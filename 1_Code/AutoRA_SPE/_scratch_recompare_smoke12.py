# -*- coding: utf-8 -*-
"""用**当前**判据重算 `_scratch_stage9_loop_smoke12.json` 里四臂的名次与裁决。

为什么需要它：那次冒烟跑在 `compare_arms` 的裁决规则修正**之前**，日志里 BO 那一行把
"A 差 32%" 印成了"不可分辨"。重跑整套内环要 13 分钟，而 `histories` 已经落在 JSON 里
⇒ 直接用同一份数据重算即可（数值完全一致，只有措辞被修正）。

用法：python -u _scratch_recompare_smoke12.py [json 路径]
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import stage9_loop as L                                        # noqa: E402

PATH = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                    else "_scratch_stage9_loop_smoke12.json")


def main() -> int:
    d = json.loads(PATH.read_text(encoding="utf-8"))
    noise = d["noise"]
    print("=" * 72)
    print(f"用当前判据重算 {PATH.name}")
    print("=" * 72)
    print(f"噪声：2·sd_A = {2*noise['sd_A']:.4f}、2·sd_B = {2*noise['sd_B']:.4f}、"
          f"2·sd_J = {2*noise['sd_J']:.4f}（仅参考）")
    print(f"锚点 D4：A = {d['anchor']['A']:.4f}、B = {d['anchor']['B']:.4f}、"
          f"可行 = {d['anchor'].get('feasible')}")
    print(f"推荐点：A = {d['best']['A']:.4f}、B = {d['best']['B']:.4f}")
    print(f"推荐设计：{d['best']['name']}")
    print("-" * 72)
    rows = L.compare_arms(d["histories"], noise)
    for r in rows:
        print(f"{r['arm']:7s} A_best = {r['A_best']:.4f}、B@A_best = "
              f"{r['B_at_A_best']:.4f}、可行 {r['n_feasible']}、参考 best J = "
              f"{r['best_J']:.4f}")
        print(f"        ⇒ {r['verdict']}")
    print("-" * 72)
    print(f"总评估次数 {d['n_evals']}、内环耗时 {d['seconds']:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
