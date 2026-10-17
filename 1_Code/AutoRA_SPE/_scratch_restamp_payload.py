# -*- coding: utf-8 -*-
"""把旧落盘件的 `compare`（四臂判词）**离线重算**成当前代码口径，并补上 `verdict_logic`。

【为什么需要】判词文本是**运行时代码的产物**：`stage9_loop.py` 直出 payload 时，`compare`
里的每一句「不可分辨 / 被支配 / 权衡 / 在 (A) 上显著更差」都由**当时代码**的 `compare_arms`
生成。D59（标定种子必须独立重抽 ⇒ `sd_A` 修正）与 D60（跨设计带宽系数 `2·sd` → `2·√2·sd`）
之后，任何 **D60 之前**跑出来的 payload 的 `compare` 段都**不可能**与当前代码一致：
  - 没有 `verdict_logic` 键（无法归因它出自哪一版规则）；
  - 判词用的带宽偏窄 `√2` 倍 ⇒ 旧判词系统性地**更容易宣称「显著更差 / 更好」**。

【重算为什么**不等于**篡改】`compare_arms(histories, noise)` 是**纯函数**：它只读 payload 里
已有的 `histories` 与 `noise` 两个块，**不碰**内环、不碰缓存、不碰任何随机数。因此：
  - 内环读数（`cache` 的逐设计 `(A)/(B)/(C)/gates`）与种子哈希派生关系**逐字继承**，没有重跑；
  - 被改写的只有「在同一批读数上按哪一版规则下判」这一层；
  - 旧判词逐条留在 `provenance.old_verdicts` 里，可对照、可追责。

⚠️ 但它**修不了**噪声带本身的标定：若源 payload 的 `noise` 块出自 D59 之前的口径
（`n_fim = 1` 下 `sd_A` 低报约 4 倍），重算出来的带子仍然是错的 —— 本脚本会在
`provenance.anchors` 里记下 `noise.n_repeats` 与 `sd_A/sd_B/sd_omission`，并在
`--` 之外的场景**不掩饰**这一点：口径是否可用，由 `1_Code/DDM_Core/README.md` §8.35/§8.36
的噪声标定登记决定，不由本脚本决定。

用法：
    python -X utf8 -u _scratch_restamp_payload.py <payload.json> <out.json> [--apply]
不加 `--apply` ⇒ 干跑：只打印对照，不写盘。输出一律 UTF-8 无 BOM + 裸 LF。
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage9_loop as L                                   # noqa: E402
import stage9_report as R                                 # noqa: E402


def _fmt(x) -> str:
    try:
        v = float(x)
    except Exception:
        return str(x)
    if v != v or v in (float("inf"), float("-inf")):
        return "—"
    return f"{v:.4f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("out")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    src = Path(a.payload)
    d = json.load(io.open(src, encoding="utf-8"))
    for k in ("histories", "noise"):
        if k not in d:
            print(f"❌ 源件缺 `{k}` ⇒ 无法离线重算（本脚本只认 stage9_loop.py 直出的 payload）")
            return 2

    old_rows = d.get("compare") or []
    new_rows = L.compare_arms(R._norm_histories(d["histories"]), d["noise"])
    old_logic = d.get("verdict_logic")

    sd_a = float(d["noise"].get("sd_A", 0.0))
    sd_b = float(d["noise"].get("sd_B", 0.0))
    print(f"源件：{src}")
    print(f"  带宽：旧 `2·sd` = {_fmt(2.0 * sd_a)} / {_fmt(2.0 * sd_b)}"
          f"  ⇒  新 `2·√2·sd` = {_fmt(L.DIFF_BAND_FACTOR * sd_a)} / "
          f"{_fmt(L.DIFF_BAND_FACTOR * sd_b)}"
          f"（系数 {L.DIFF_BAND_FACTOR:.4f}，旧值偏窄 {L.DIFF_BAND_FACTOR / 2.0:.4f} 倍）")
    print(f"  源件 `verdict_logic`：{'缺（D59/D60 之前跑出）' if not old_logic else '有'}")
    print(f"  噪声标定：n_repeats = {d['noise'].get('n_repeats')}、sd_A = {sd_a:.6f}、"
          f"sd_B = {sd_b:.6f}、sd_omission = {d['noise'].get('sd_omission')}")
    print(f"  四臂判词对照（旧 → 新）：")

    old_by_arm = {r.get("arm"): r for r in old_rows if isinstance(r, dict)}
    changed = 0
    for r in new_rows:
        o = old_by_arm.get(r["arm"])
        ov = (o or {}).get("verdict", "（无）")
        nv = r.get("verdict", "（无）")
        same = (ov == nv)
        changed += 0 if same else 1
        print(f"    [{r['arm']:7s}] {'逐字相同' if same else '❗不一致'}")
        if not same:
            print(f"        旧：{ov}")
            print(f"        新：{nv}")
    print(f"  ⇒ {len(new_rows)} 条臂中 {changed} 条判词与旧件不同"
          f"（若为 0，说明本次重算没有改变任何结论）")

    payload = dict(d)
    payload["compare"] = new_rows
    payload["verdict_logic"] = L.VERDICT_LOGIC
    payload["provenance"] = {
        "restamp": "compare_arms 离线重算（当前代码口径）",
        "source": src.name,
        "source_verdict_logic": old_logic,
        "band_factor": L.DIFF_BAND_FACTOR,
        "n_verdicts_changed": changed,
        "old_verdicts": [{"arm": r.get("arm"), "verdict": r.get("verdict")}
                         for r in old_rows if isinstance(r, dict)],
        "note": ("内环读数（cache/histories/noise/designs）逐字继承自源件，未重跑任何评估；"
                 "被改写的只有「在同一批读数上按哪一版规则下判」这一层。"
                 "⚠️ 噪声带本身的标定若出自 D59 之前，本脚本无法修正。"),
    }
    if not a.apply:
        print(f"\n[干跑] 不写盘：{a.out}（加 --apply 才写）")
        return 0
    out = Path(a.out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\n✅ 已写盘：{out}（{out.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
