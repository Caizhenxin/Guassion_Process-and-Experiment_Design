"""一次性探针：比较**两个 `n_fim`** 下的可行域构成（主计划 L529 仍开放第 (2) 件的证据）。

为什么需要它：`n_fim = 1` 的落盘件里 174 个候选有 123 个被数值条件数挡在可行集之外。
但 `(A)` 随 `n_fim` 变小（`stage9_inner.inner_eval` 把 `n_fim` 份重复的信息矩阵**平均**后再求
逆），所以「可行域构成」必须问一句：那 123 个是**小样本产物**，还是**设计本身病态**？

判据分两层：
  - `n_bad > 0`（有坏试次）⇒ **结构性的**，与 `n_fim` 无关（同一设计重复多少次都还带坏试次）；
  - 只有 `cond > 1e10` 而 `n_bad == 0` ⇒ **可能**是小样本产物，加大 `n_fim` 后有可能回到可行集。

用法：
    python -u _scratch_cmp_nfim.py <基线 payload.json> <新 payload.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CATS = ("feasible", "band_only", "ill_cond", "band_and_ill", "other")
LABEL = {
    "feasible": "可行",
    "band_only": "只被 D54 遗漏率带否决",
    "ill_cond": "只被数值病态否决",
    "band_and_ill": "两者兼有",
    "other": "其它闸门",
}


def load(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def has_band(r: dict) -> bool:
    return any("D54" in g for g in (r.get("gates") or []))


def has_ill(r: dict) -> bool:
    """两个数值闸门是**两段文本**，必须都认（见 `stage9_report.py::_composition` 的注释）。"""
    gates = r.get("gates") or []
    return (any(("cond" in g) or ("n_bad" in g) for g in gates)
            or float(r.get("cond", 0.0)) > 1e10
            or int(r.get("n_bad", 0)) > 0)


def cls(r: dict) -> str:
    if r.get("feasible"):
        return "feasible"
    if has_band(r) and has_ill(r):
        return "band_and_ill"
    if has_band(r):
        return "band_only"
    if has_ill(r):
        return "ill_cond"
    return "other"


def composition(cache: dict) -> dict:
    out = {k: 0 for k in CATS}
    for r in cache.values():
        out[cls(r)] += 1
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="比较两个 n_fim 下的可行域构成")
    ap.add_argument("baseline")
    ap.add_argument("new")
    a = ap.parse_args(argv[1:])
    base, new = load(a.baseline), load(a.new)
    cb, cn = base["cache"], new["cache"]
    nb, nn = int(base["settings"]["n_fim"]), int(new["settings"]["n_fim"])
    print(f"基线：`{Path(a.baseline).name}`  n_fim = {nb}  缓存 {len(cb)} 个")
    print(f"新件：`{Path(a.new).name}`  n_fim = {nn}  缓存 {len(cn)} 个")
    print()
    if set(cb) != set(cn):
        only_b, only_n = sorted(set(cb) - set(cn)), sorted(set(cn) - set(cb))
        print(f"⚠️ 两次的候选集不同：只在基线 {len(only_b)} 个、只在新件 {len(only_n)} 个")
    common = sorted(set(cb) & set(cn))

    print("## 1. 可行域构成")
    print()
    print("| 类别 | n_fim = %d | n_fim = %d | 差 |" % (nb, nn))
    print("|---|---|---|---|")
    bcomp, ncomp = composition(cb), composition(cn)
    for k in CATS:
        print(f"| {LABEL[k]} | {bcomp[k]} | {ncomp[k]} | {ncomp[k] - bcomp[k]:+d} |")
    print(f"| **合计** | {sum(bcomp.values())} | {sum(ncomp.values())} | "
          f"{sum(ncomp.values()) - sum(bcomp.values()):+d} |")
    print()

    print("## 2. 逐设计迁移（只数列数）")
    print()
    trans: dict[tuple[str, str], int] = {}
    for n in common:
        trans[(cls(cb[n]), cls(cn[n]))] = trans.get((cls(cb[n]), cls(cn[n])), 0) + 1
    print("| 基线 → 新件 | 个数 |")
    print("|---|---|")
    for (x, y), c in sorted(trans.items(), key=lambda kv: -kv[1]):
        mark = "" if x == y else "  ← 变化"
        print(f"| {LABEL[x]} → {LABEL[y]} | {c}{mark} |")
    print()

    print("## 3. 病态的成因：不可识别方向（`n_bad > 0`）还是只剩条件数（`cond > 1e10`）")
    print()
    print("`n_bad` 的定义（`1_Code/DDM_Core/likelihood.py::fim_diagnostics` L271）：平均信息矩阵里")
    print("`ev < max(ev_max * 1e-8, 1e-300)` 的**方向个数** —— 即数值上不可识别的方向有多少条。")
    print()
    for tag, c in (("基线", cb), ("新件", cn)):
        bad = [n for n in c if int(c[n].get("n_bad", 0)) > 0]
        cond_only = [n for n in c if int(c[n].get("n_bad", 0)) == 0 and has_ill(c[n])]
        print(f"- {tag}：`n_bad > 0` **{len(bad)}** 个（该设计存在不可识别方向）；"
              f"`n_bad == 0` 但 `cond > 1e10` **{len(cond_only)}** 个（只由条件数否决）")
    print()
    still = [n for n in common if int(cb[n].get("n_bad", 0)) > 0
             and int(cn[n].get("n_bad", 0)) > 0]
    cured = [n for n in common if int(cb[n].get("n_bad", 0)) > 0
             and int(cn[n].get("n_bad", 0)) == 0]
    born = [n for n in common if int(cb[n].get("n_bad", 0)) == 0
            and int(cn[n].get("n_bad", 0)) > 0]
    print(f"- 逐设计对照：两边都有不可识别方向 **{len(still)}** 个；只有基线有 **{len(cured)}** 个；"
          f"只有新件有 **{len(born)}** 个")
    print()

    print("## 4. 判据的带宽与锚点")
    print()
    for tag, d in (("基线", base), ("新件", new)):
        ns = d.get("noise", {})
        an = d.get("anchor", {})
        print(f"- {tag}：`2·sd_A = {2 * float(ns.get('sd_A', float('nan'))):.4f}`、"
              f"`2·sd_B = {2 * float(ns.get('sd_B', float('nan'))):.4f}`；"
              f"锚点 `A = {float(an.get('A', float('nan'))):.4f}`、"
              f"`B = {float(an.get('B', float('nan'))):.4f}`、"
              f"`feasible = {an.get('feasible')}`；`n_evals = {d.get('n_evals')}`")
    print()

    print("## 5. 可行集里 `(A)` 最小的那个设计")
    print()
    for tag, c in (("基线", cb), ("新件", cn)):
        feas = [n for n in c if c[n].get("feasible")]
        if not feas:
            print(f"- {tag}：**没有可行设计**")
            continue
        best = min(feas, key=lambda n: float(c[n]["A"]))
        r = c[best]
        print(f"- {tag}：`A = {r['A']:.4f}`、`B = {r['B']:.4f}`、遗漏 {r['omission']:.4f}"
              f"（{len(feas)} 个可行）")
        print(f"  - `{best}`")
    print()
    same = None
    fb = [n for n in cb if cb[n].get("feasible")]
    fn = [n for n in cn if cn[n].get("feasible")]
    if fb and fn:
        bb = min(fb, key=lambda n: float(cb[n]["A"]))
        bn = min(fn, key=lambda n: float(cn[n]["A"]))
        same = (bb == bn)
        print(f"- 两档的最优点**{'相同' if same else '不同'}**"
              f"{'' if same else f'：`{bb}` → `{bn}`'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
