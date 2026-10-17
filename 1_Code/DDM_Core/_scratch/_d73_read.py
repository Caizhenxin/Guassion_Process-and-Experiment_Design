# -*- coding: utf-8 -*-
"""读一次 Stage 8 的 `stage8_results.json`（+ 同名 `stage8_report.md`），把 D73 要看的数字摊开。

用法：
    python -X utf8 -u _d73_read.py _scratch/stage8_n4_576/stage8_results.json

回答的唯一问题：**「被试层 LOO 无效」是人均试次太少（92–143）造成的，还是结构问题？**
判据（与 Stage 8 §11 第 3 条同一口径）：
    p_loo / n_obs < 1.0 且 k_max < 0.7  ⇒ LOO 可用（试次数是主因，旧结论要改）
    p_loo / n_obs > 3.0 或 k_max > 1.0  ⇒ 结构问题（旧结论成立，须换 LOO 口径）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "_scratch/stage8_n4_576/stage8_results.json")
    obj = json.loads(path.read_text(encoding="utf-8"))
    rep = path.with_name("stage8_report.md")
    print(f"文件：{path}")
    print(f"组数：{len(obj.get('groups', {}))}；报告：{'有' if rep.exists() else '缺'}\n")

    for g, res in sorted(obj.get("groups", {}).items()):
        print("=" * 92)
        print(f"组 {g}")
        for model, r in sorted(res.items()):
            if not isinstance(r, dict) or "loo" not in r:
                continue
            lk = r["loo"]
            elpd, se = lk.get("elpd_loo"), lk.get("se")
            p_loo, n_obs = lk.get("p_loo"), lk.get("n_obs")
            k_max = lk.get("k_max")
            ratio = (p_loo / n_obs) if (p_loo is not None and n_obs) else None
            print(f"\n[{model}]  rho_free={r.get('rho_free')}  拟合 {r.get('seconds', 0):.1f}s")
            print(f"  elpd_loo = {elpd:.3f} ± {se:.3f}" if elpd is not None else "  elpd 缺")
            print(f"  p_loo    = {p_loo:.3f}；n_obs = {n_obs}；p_loo/n_obs = "
                  f"{'—' if ratio is None else round(ratio, 3)}")
            print(f"  k_max    = {k_max:.3f}；k>0.7 的单元 {lk.get('n_k_gt_bad')}/{n_obs}；"
                  f"k>1（不可用）{lk.get('n_k_gt_unusable', 0)}")
            if ratio is not None and k_max is not None:
                if ratio < 1.0 and k_max < 0.7:
                    print("  判词：**LOO 可用** —— 试次数是主因，D65/D70 的「LOO 无效」须改口径")
                elif ratio > 3.0 or k_max > 1.0:
                    print("  判词：**仍无效** —— 结构问题，不是人均试次太少")
                else:
                    print("  判词：**灰区** —— 比 92 试次好，但没到可用；需再压缩参数或改口径")

    if rep.exists():
        print("\n" + "=" * 92 + "\n报告里的 PPC 计数（每行一名被试）")
        for ln in rep.read_text(encoding="utf-8").split("\n"):
            if "分单元" in ln and re.search(r"分单元 \d+/\d+", ln):
                print("  " + ln.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
