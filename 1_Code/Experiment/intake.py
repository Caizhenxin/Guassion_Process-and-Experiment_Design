# -*- coding: utf-8 -*-
"""单场入库判定器：把「一场数据能不能计入 N」从四处手工判断收成一条命令。

## 为什么需要它

一个场次要判三件事，原先要手工跑三个工具、再心算合并：

1. **技术层**（Stage 1 六项）：`check_stage1_acceptance.py` —— 帧量化、6-B/6-C/6-D；
2. **结构层**（Stage 7 逐被试 G2–G9）：`qc_group.py` 的 `subject_metrics` + `classify`
   —— 576 正式试次、练习段 = `max(4, P)`、每格 48、P 值、帧长；
3. **一致层**：`read_formal_data.py` 的 `validate()` —— 25 列、`matchKey`、`P` 与组别。

三件事各判各的，最容易出事的地方恰好是**合并那一步**：D93 的「练习段 0 试次」和 D94 的
「跑了两遍」都是单层都看不清、合并时才显形的问题。所以本工具**不重写任何判据**，只 import
那三个模块的既有函数（避免 D94 的教训：把「读行」抄进新工具、却把「去重」留在旧工具里）。

## 判定口径（三层任一硬失败 ⇒ 不计入）

| 层 | 硬失败（不计入） | 软失败（待复核） |
|---|---|---|
| 技术 | 六项强制项任一 FAIL | 信息项 FAIL |
| 结构 | `classify` = EXCLUDE；练习段行数 ≠ `max(4, P)` | `classify` = REVIEW |
| 结构补充 | 正式段 < 0.9 × 576（提前退出） | txt 去重丢弃 > 0 行（整场跑了两遍） |
| 一致 | `validate()` 报错 | — |

「待复核」不是淘汰：`qc_group.py` 的口径是「进得去分析、但要人看一眼」。
「不计入」才是淘汰——它意味着这一场不能算进 N=8。

## 用法

```
python -X utf8 1_Code/Experiment/intake.py <目录或文件> [<目录或文件> ...]
python -X utf8 1_Code/Experiment/intake.py D:\\Desktop\\Test\\exp_matlab_v3
```

退出码：0 = 没有「不计入」；1 = 至少一场不计入；2 = 输入不可用（没有可识别的场次）。

## 已知限制

- 有 CSV 时以 CSV 为权威快照；**只有 txt 也能判**（三层都退用 txt，报告里会警告一声），
  但此时「CSV 与 txt 是否一致」这件事就核不了。
- 只看 CSV 与孪生 txt；**启动回显**（6-A）与现场纸质记录不在数据里，需人看。
- 不替代 `qc_group.py` 的组层报告（G1 进度、G9 跨被试帧长）——组层要等齐人再跑。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "exp_Check"))

import qc_group as Q                                          # noqa: E402
import check_stage1_acceptance as S1                          # noqa: E402
import read_formal_data as RF                                 # noqa: E402

CSV_RE = re.compile(r"^EXP_data_group(\d+)_(\d+)\.csv$", re.I)
TXT_RE = re.compile(r"^exp_group(\d+)_subject(\d+)\.txt$", re.I)

KEEP, REVIEW, EXCLUDE = "KEEP", "REVIEW", "EXCLUDE"
MARK = {KEEP: "✅", REVIEW: "🟠", EXCLUDE: "❌"}


# --------------------------------------------------------------------------- #
# 找场次
# --------------------------------------------------------------------------- #
def find_sessions(paths: list[Path]) -> list[dict]:
    """→ [{gid, sid, csv, txt, shadowed}]，按 (组, 编号) 排序。

    同一 (组, 编号) 在多个目录里都有快照时（典型：`test/_full_session_out/` 的自测产物
    与真实交付同名），**取层级最浅的那个**，其余记进 `shadowed` 并在报告里点名 ——
    静默挑一个会让"这场到底判的是哪份数据"完全不可追（本轮就踩过：真实场次被自测产物顶掉）。
    """
    cands: dict[tuple[int, int], dict[str, list[Path]]] = {}
    for p in paths:
        files = [p] if p.is_file() else sorted(p.rglob("*"))
        for f in files:
            if not f.is_file():
                continue
            mc, mt = CSV_RE.match(f.name), TXT_RE.match(f.name)
            m = mc or mt
            if not m:
                continue
            g, s = int(m.group(1)), int(m.group(2))
            key = "csv" if mc else "txt"
            cands.setdefault((g, s), {"csv": [], "txt": []})[key].append(f)

    out = []
    for (g, s), got in sorted(cands.items()):
        csvs = sorted(got["csv"], key=lambda it: (len(it.parts), str(it)))
        txts = sorted(got["txt"], key=lambda it: (len(it.parts), str(it)))
        # 只有 txt 的场次也收（现场只肯交 txt 的情况很常见），但 CSV 是权威快照：有 CSV 就用它
        out.append({"gid": g, "sid": s,
                    "csv": csvs[0] if csvs else None,
                    "txt": txts[0] if txts else None,
                    "shadowed": csvs[1:] + txts[1:]})
    return out


# --------------------------------------------------------------------------- #
# 三层
# --------------------------------------------------------------------------- #
def layer_tech(csv: Path) -> tuple[bool, list[str], list[str]]:
    """技术层 → (ok, 强制失败, 信息项失败)。"""
    rep = S1.analyze([csv])
    hard, soft = [], []
    for section, ok, detail, mand in rep.items:
        if ok:
            continue
        (hard if mand else soft).append(f"{section}：{detail}")
    return rep.ok(), hard, soft


def layer_structure(txt: Path, gid: int, sid: int) -> dict:
    """结构层 → qc_group 的逐被试记录 + 裁决。"""
    rec = Q.subject_metrics(txt, gid, sid)
    rec["verdicts"] = Q.run_subject_check(txt, None)
    cls, reasons = Q.classify(rec, None)

    p_expect = Q.P_BY_GROUP.get(gid)
    n_prac_expect = max(4, p_expect) if p_expect is not None else None

    hard, soft = [], []
    if n_prac_expect is not None and rec["n_practice"] != n_prac_expect:
        hard.append(f"练习段 {rec['n_practice']} 行 ≠ {n_prac_expect}"
                    f"（组 {gid} 的 P={p_expect} ⇒ `max(4, P)`）")
    if rec["n_formal"] < 0.9 * Q.N_FORMAL:
        hard.append(f"正式段 {rec['n_formal']}/{Q.N_FORMAL}（提前退出）")
    if cls == EXCLUDE:
        hard.extend(reasons or ["结构层判 EXCLUDE"])
    elif cls == REVIEW:
        soft.extend(reasons or ["结构层判 REVIEW"])
    if rec["n_dropped"] > 0:
        soft.append(f"txt 按 (stage, trialID) 去重丢弃 {rec['n_dropped']} 行"
                    "（`fopen(...,'a+')` 追加写 ⇒ 整场跑了两遍；CSV 以最后一次为准，"
                    "只能计一次，需确认不是两场混写）")
    return {"rec": rec, "cls": cls, "hard": hard, "soft": soft,
            "n_prac_expect": n_prac_expect}


def layer_consistency(csv: Path) -> tuple[list[str], dict]:
    """一致层 → (错误列表, 供打印的摘要)。"""
    rec, meta = RF.load_file(csv)
    tr = RF.to_trials(rec)
    errors = RF.validate(rec, tr)
    mk = rec.get("matchKey")
    pv = rec.get("P")
    mk0 = str(mk[0]).strip() if mk is not None and len(mk) else "—"
    return errors, {"matchKey": mk0,
                    "P": sorted({int(round(float(x))) for x in pv}) if pv is not None else []}


# --------------------------------------------------------------------------- #
# 汇总一个场次
# --------------------------------------------------------------------------- #
def audit_one(gid: int, sid: int, csv: Path | None, txt: Path | None,
              shadowed: list[Path] | None = None) -> dict:
    source = csv or txt
    if source is None:
        raise ValueError(f"组 {gid} 被试 {sid} 既没有 CSV 也没有 txt")
    tech_ok, tech_hard, tech_soft = layer_tech(source)
    cons_errors, cons = layer_consistency(source)
    if txt is None:
        st = {"rec": {"n_formal": -1, "n_practice": -1, "n_dropped": -1,
                      "acc_mean": None, "timeout_prop": None},
              "cls": EXCLUDE,
              "hard": [f"缺孪生 txt（`exp_group{gid}_subject{sid}.txt`）⇒ 结构层无法核"],
              "soft": [], "n_prac_expect": None}
    else:
        st = layer_structure(txt, gid, sid)

    hard = tech_hard + st["hard"] + [f"一致层：{e}" for e in cons_errors]
    soft = tech_soft + st["soft"]
    verdict = EXCLUDE if hard else (REVIEW if soft else KEEP)
    return {"gid": gid, "sid": sid, "csv": csv, "txt": txt, "source": source,
            "verdict": verdict,
            "hard": hard, "soft": soft, "tech_ok": tech_ok,
            "rec": st["rec"], "cls": st["cls"],
            "n_prac_expect": st["n_prac_expect"], "cons": cons,
            "shadowed": shadowed or []}


def render(res: list[dict]) -> str:
    out = [f"═══ 单场入库判定：{len(res)} 个场次 ═══", ""]
    for i, r in enumerate(res, 1):
        rec = r["rec"]
        acc = "—" if rec.get("acc_mean") is None else f"{rec['acc_mean']:.3f}"
        tmo = "—" if rec.get("timeout_prop") is None else f"{rec['timeout_prop']:.1%}"
        out.append(f"[{i}] 组 {r['gid']} · 被试 {r['sid']} · {r['source'].name}")
        out.append(f"    路径：{r['source']}")
        if r["csv"] is None:
            out.append("    ⚠ 只有 txt（无 CSV 快照）：三层都退用 txt；"
                       "CSV 是权威快照，请让主试把同目录的 CSV 一并交回")
        for sh in r["shadowed"]:
            out.append(f"    ⚠ 同名快照被忽略（层级更深）：{sh}")
        out.append(f"    结构：正式 {rec.get('n_formal')}/{Q.N_FORMAL} 试次 · "
                   f"练习 {rec.get('n_practice')}/{r['n_prac_expect']} 行 · "
                   f"去重丢弃 {rec.get('n_dropped')} 行 · 正确率 {acc} · timeout {tmo}")
        out.append(f"    技术层：{'✅ 强制项全过' if r['tech_ok'] else '❌ 有强制项未通过'}")
        out.append(f"    结构层：{MARK.get(r['cls'], '·')} {r['cls']}")
        out.append(f"    一致层：{'✅ 无异常' if not r['hard'] else '见下列理由'}"
                   f"（matchKey={r['cons']['matchKey']}，P={r['cons']['P']}）")
        for h in r["hard"]:
            out.append(f"    ❌ {h}")
        for s in r["soft"]:
            out.append(f"    🟠 {s}")
        out.append(f"    ⇒ {MARK[r['verdict']]} **{r['verdict']}**")
        out.append("")

    n = {k: sum(1 for r in res if r["verdict"] == k) for k in (KEEP, REVIEW, EXCLUDE)}
    out.append(f"汇总：计入 {n[KEEP]} ｜ 待复核 {n[REVIEW]} ｜ 不计入 {n[EXCLUDE]}")
    if n[EXCLUDE]:
        out.append("⇒ 有场次不计入 N：见上面 ❌ 条目；先修程序/重跑，别把它算进样本量。")
    elif n[REVIEW]:
        out.append("⇒ 全部可计入门槛之外还有人要看的项：逐条确认后再并入 N。")
    else:
        out.append("⇒ 全部可计入 N。")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="单场入库判定：技术层（Stage 1）+ 结构层（Stage 7）+ 一致层")
    ap.add_argument("paths", nargs="+", help="目录或 CSV 文件")
    args = ap.parse_args(argv)

    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        print(f"找不到路径：{[str(p) for p in missing]}")
        return 2
    sessions = find_sessions(paths)
    if not sessions:
        print("没有找到场次。\n"
              "（要 `EXP_data_group<组>_<编号>.csv` 或 `exp_group<组>_subject<编号>.txt`；"
              "只有 txt 也能判，但 CSV 是权威快照）")
        return 2

    res = [audit_one(x["gid"], x["sid"], x["csv"], x["txt"], x["shadowed"])
           for x in sessions]
    print(render(res))
    return 1 if any(r["verdict"] == EXCLUDE for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
