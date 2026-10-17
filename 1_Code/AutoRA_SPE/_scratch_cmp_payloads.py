# -*- coding: utf-8 -*-
"""比较两次落盘 payload：同一 seed 下「逐位相同」是否成立（D57 的证据之一）。

用法：python -u _scratch_cmp_payloads.py <旧.json> <新.json>
"""
import json
import sys
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    a = load(sys.argv[1])
    b = load(sys.argv[2])
    print(f"旧 {sys.argv[1]}：{Path(sys.argv[1]).stat().st_size} 字节")
    print(f"新 {sys.argv[2]}：{Path(sys.argv[2]).stat().st_size} 字节")
    bad = 0

    # 标量段：完全相同的键集合
    for key in ("settings", "front_scope", "d54", "spec_sha256", "n_evals"):
        same = a.get(key) == b.get(key)
        bad += 0 if same else 1
        print(f"[{ '✓' if same else '✗' }] {key}: {a.get(key)}")

    # 浮点段：逐位比较（== 对 float 是精确比较）
    for key in ("best", "anchor"):
        same = a[key] == b[key]
        bad += 0 if same else 1
        print(f"[{ '✓' if same else '✗' }] {key}: A={a[key]['A']!r} / 新 A={b[key]['A']!r}")

    # compare：除逐臂墙钟 `seconds` 外必须逐位相同。
    ca2 = [{k: v for k, v in r.items() if k != "seconds"} for r in a["compare"]]
    cb2 = [{k: v for k, v in r.items() if k != "seconds"} for r in b["compare"]]
    same = ca2 == cb2
    bad += 0 if same else 1
    print(f"[{ '✓' if same else '✗' }] compare（{len(ca2)} 项，已排除逐臂 `seconds`）")
    for x, y in zip(a["compare"], b["compare"]):
        if x.get("seconds") != y.get("seconds"):
            print(f"      · {x.get('arm')}: 墙钟 {x['seconds']:.1f}s → {y['seconds']:.1f}s（计时不计入判定）")

    for key in ("pareto", "noise"):
        same = a[key] == b[key]
        bad += 0 if same else 1
        print(f"[{ '✓' if same else '✗' }] {key}（{len(a[key])} 项）")

    # histories：`B_at_best_A` → `B_at_A_best` 是 D57 的**改名**（同一个量），
    # `seconds` 是**墙钟计时**（本质不确定）⇒ 两者都不参与"逐位相同"的判定，但要单独印出来。
    ha, hb = a["histories"], b["histories"]
    drop = lambda d: {k: v for k, v in d.items()              # noqa: E731
                      if k not in ("B_at_best_A", "B_at_A_best", "seconds")}
    for arm in sorted(ha):
        ba = ha[arm].get("B_at_best_A", ha[arm].get("B_at_A_best"))
        bb = hb[arm].get("B_at_best_A", hb[arm].get("B_at_A_best"))
        same = drop(ha[arm]) == drop(hb[arm]) and ba == bb
        bad += 0 if same else 1
        print(f"[{ '✓' if same else '✗' }] histories[{arm}]：新键名 = "
              f"{[k for k in hb[arm] if 'B_at' in k]}、B = {ba!r} vs {bb!r}"
              f"、墙钟 {ha[arm].get('seconds'):.1f}s → {hb[arm].get('seconds'):.1f}s（计时不计入判定）")

    # cache：逐设计比较（A/B/J/omission/feasible/gates）
    ca, cb = a["cache"], b["cache"]
    print(f"cache：旧 {len(ca)} 项 / 新 {len(cb)} 项")
    keys = ("A", "B", "J", "omission", "feasible", "gates", "cond", "n_bad", "name")
    diff = [n for n in ca if n not in cb or any(ca[n].get(k) != cb[n].get(k) for k in keys)]
    bad += len(diff)
    print(f"[{ '✓' if not diff else '✗' }] cache 逐设计差异：{len(diff)} 个"
          + (f"（前 3 个：{diff[:3]}）" if diff else ""))

    print("=" * 60)
    print("结论：两次运行" + ("**逐位相同**" if bad == 0 else f"有 **{bad}** 处不同"))


if __name__ == "__main__":
    main()
