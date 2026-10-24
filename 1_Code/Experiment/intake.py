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

# 边收边查：落报告 + 判「够不够」
python -X utf8 1_Code/Experiment/intake.py 2_Data/Real_Data/New_Design \\
    --out 4_Reports/筛查_New_Design.md --csv 4_Reports/筛查_New_Design.csv \\
    --json 4_Reports/筛查_New_Design.json --expect-n 40
```

退出码：0 = 没有「不计入」；1 = 至少一场不计入；2 = 输入不可用（没有可识别的场次）。

## 两层附加判据（D120 增补，服务「边收边查」）

前三条回答「这一场能不能计入 N」；后两条回答「这批数据够不够、还差多少人」：

| 层 | 判据 |
|---|---|
| 质量层 | 时限内响应率、提前按键率、响应试次正确率、清洗后 RT 中位、逐格试次数、刺激时长偏差 |
| 统计层 | 逐被试 Δacc / ΔRT 中位 / 分位斜率 → 组均值、SE、95% CI、**达到目标 SE 还需几人** |

统计层的目标精度（可调，报告里会写明）：`SE(ΔRT中位) ≤ 10 ms`、`SE(Δacc) ≤ 0.03`。

## 已知限制

- 有 CSV 时以 CSV 为权威快照；**只有 txt 也能判**（三层都退用 txt，报告里会警告一声），
  但此时「CSV 与 txt 是否一致」这件事就核不了。
- 只看 CSV 与孪生 txt；**启动回显**（6-A）与现场纸质记录不在数据里，需人看。
- 不替代 `qc_group.py` 的组层报告（G1 进度、G9 跨被试帧长）——组层要等齐人再跑。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "exp_Check"))

import pandas as pd                                           # noqa: E402
import qc_group as Q                                          # noqa: E402
import check_stage1_acceptance as S1                          # noqa: E402
import read_formal_data as RF                                 # noqa: E402
import real_data_check as R                                   # noqa: E402

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
def _few_rows(detail: str, limit: int = 3) -> bool:
    """判据细节里出现「N 处 / N 行」且**最小**的 N ≤ limit ⇒ 单行级异常，不算整场报废。

    取最小是因为细节里常同时出现「检查了 580 行」与「（1 处：…）」——前者是样本量，
    后者才是坏行数。
    """
    nums = [int(x) for x in re.findall(r"(\d+)\s*(?:处|行|个)", detail)]
    return bool(nums) and min(nums) <= limit


def layer_tech(csv: Path) -> tuple[bool, list[str], list[str]]:
    """技术层 → (ok, 强制失败, 信息项)。

    D120 两处降级（都是「20 人批次 vs 数人验收」的口径差）：

    - `6-B`：原判据是「最小 T 档里至少 1 例 `RT < T`」——Stage 1 **实机验收**的取证检查，
      只对数人的小样本有效。当逐场强制项，20 人批次必然全灭（实得 0 例，数据里 RT
      最小 72 ms）。降为信息项。
    - `6-C` 的**单行级**异常（细节里点名 ≤3 行）：掉帧一两行是硬件抖动，不是程序错。
      同一条物理量由质量层的 `时长偏差占比` 定量把关，这里降为信息项。
      帧量化若成片失败（无行数可数）仍是硬项。

    返回的第三项**只记录、不阻塞入库**——「信息项」不进裁决。
    """
    rep = S1.analyze([csv])
    hard, notes = [], []
    for section, ok, detail, mand in rep.items:
        if ok:
            continue
        if section.startswith("6-B"):
            notes.append(f"{section}：{detail}")
            continue
        if section.startswith("6-C") and _few_rows(detail):
            notes.append(f"{section}（单行级）：{detail}")
            continue
        (hard if mand else notes).append(f"{section}：{detail}")
    return (not hard), hard, notes


def layer_structure(txt: Path, gid: int, sid: int) -> dict:
    """结构层 → qc_group 的逐被试记录 + 裁决。"""
    rec = Q.subject_metrics(txt, gid, sid)
    rec["verdicts"] = Q.run_subject_check(txt, None)
    cls, reasons = Q.classify(rec, None)

    p_expect = Q.P_BY_GROUP.get(gid)
    # D120：练习段行数 = P（组 1 的 P=0 就是**零练习**，不是「至少 4」）。
    # 旧口径 `max(4, P)` 会把 P=0 组全部判死（20 人数据里 5/5 全中）——那是 v3 早期
    # 「练习段至少 4 试次」的遗留假设，与定稿设计（P 即练习量）不符。
    # 兼容旧快照：P=0 时也接受 4 行（老程序写过 4 行占位），但记一条信息项。
    n_prac_expect = p_expect
    prac_legacy = False
    if p_expect == 0:
        n_prac_ok = {0, 4}
    else:
        n_prac_ok = {p_expect}

    hard, soft, notes = [], [], []
    if n_prac_expect is not None and rec["n_practice"] not in n_prac_ok:
        hard.append(f"练习段 {rec['n_practice']} 行 ≠ {n_prac_expect}"
                    f"（组 {gid} 的 P={p_expect} ⇒ 练习试次数应等于 P）")
    elif p_expect == 0 and rec["n_practice"] == 4:
        notes.append("练习段 4 行：P=0 组按定稿设计应为 0 行（老程序占位 4 行）")
    if rec["n_formal"] < 0.9 * Q.N_FORMAL:
        hard.append(f"正式段 {rec['n_formal']}/{Q.N_FORMAL}（提前退出）")
    if cls == EXCLUDE:
        hard.extend(reasons or ["结构层判 EXCLUDE"])
    elif cls == REVIEW:
        # 行为/统计层面的偏离（timeout 偏高、正确率偏低等）只记录、不阻塞：
        # 拿行为当剔除理由会把样本筛成「好被试」，直接污染组间比较（D120 口径）。
        notes.extend(reasons or ["结构层判 REVIEW"])
    if rec["n_dropped"] > 0:
        soft.append(f"txt 按 (stage, trialID) 去重丢弃 {rec['n_dropped']} 行"
                    "（`fopen(...,'a+')` 追加写 ⇒ 整场跑了两遍；CSV 以最后一次为准，"
                    "只能计一次，需确认不是两场混写）")
    return {"rec": rec, "cls": cls, "hard": hard, "soft": soft, "notes": notes,
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
# 质量层：逐场「数据干不干净」（D120）
# --------------------------------------------------------------------------- #
#: 统计层的目标精度（配对 SE）。写进报告，改口径要连报告一起改。
TARGET = {"drt_med": 10.0, "d_acc": 0.03, "slope": 30.0}
METRIC_CN = {"drt_med": "ΔRT 中位 (ms)", "d_acc": "Δacc（比例，×100 = pp）", "slope": "分位斜率 (ms)"}

#: 阈值一律「(软, 硬)」；None = 该方向不设。写进报告，便于别人复核口径。
Q_RESP = (0.60, 0.50)       # 时限内响应率（低于 ⇒ 报警）
Q_PREM = (0.10, 0.20)       # 提前按键率（高于 ⇒ 报警）
Q_ACC = (0.60, 0.55)        # 响应试次正确率（低于 ⇒ 报警；机会水平 0.5）
Q_RT_MED = (400.0, 250.0)   # 清洗后 RT 中位（低于 ⇒ 不像在辨识刺激）
Q_DEV = (0.05, 0.15)        # |实际时长 − T| > 20 ms 的试次占比
Q_EFF = (0.60, 0.45)        # 可用试次率 = 清洗后/576（可达 12 试次/格的统计密度）
Q_CELL_RAW = (12, 10)       # 正式段逐格原始试次（设计 48 格 × 12）


def quality_one(sub: "pd.DataFrame") -> dict:
    """单场质量指标 → {metrics, hard, notes}（只看正式段：练习段固定 T/W，混进来会带偏）。"""
    sub = sub[sub["is_formal"]]
    responded = sub[sub["responded"] == 1]
    dev = sub["dur_dev_ms"].abs()
    cl = R.clean(sub)
    keys = ["T_lvl", "W_lvl", "is_self", "Shape"]
    cells_raw = sub.groupby(keys).size()
    cells_cl = cl.groupby(keys).size()
    m = {
        "n_trials": int(len(sub)),
        "n_clean": int(len(cl)),
        "eff_rate": float(len(cl) / len(sub)) if len(sub) else 0.0,
        "resp_rate": float(sub["responded"].mean()),
        "prem_rate": float(sub["premature"].mean()),
        "acc_resp": float(responded["correct"].mean()) if len(responded) else float("nan"),
        "rt_med": float(responded["rt_ms"].median()) if len(responded) else float("nan"),
        "dev_frac": float((dev > 20).mean()),
        "dev_max": float(dev.max()),
        "n_cells": int(len(cells_raw)),
        "cell_min_raw": int(cells_raw.min()) if len(cells_raw) else 0,
        "cell_min_clean": int(cells_cl.min()) if len(cells_cl) else 0,
        "cell_med_clean": float(cells_cl.median()) if len(cells_cl) else 0.0,
    }
    hard, notes = [], []

    def band(lo_hi, val, label, lower_is_bad=True, fmt="{:.3f}"):
        soft_v, hard_v = lo_hi
        if val != val:                       # NaN：整场没有可用响应
            hard.append(f"{label} 无法计算（没有响应试次）")
            return
        if lower_is_bad:
            if hard_v is not None and val < hard_v:
                hard.append(f"{label} {fmt.format(val)} < {hard_v:g}（硬阈值）")
            elif soft_v is not None and val < soft_v:
                notes.append(f"{label} {fmt.format(val)} < {soft_v:g}（软阈值）")
        else:
            if hard_v is not None and val > hard_v:
                hard.append(f"{label} {fmt.format(val)} > {hard_v:g}（硬阈值）")
            elif soft_v is not None and val > soft_v:
                notes.append(f"{label} {fmt.format(val)} > {soft_v:g}（软阈值）")

    band(Q_RESP, m["resp_rate"], "时限内响应率")
    band(Q_PREM, m["prem_rate"], "提前按键率", lower_is_bad=False, fmt="{:.1%}")
    band(Q_ACC, m["acc_resp"], "响应试次正确率")
    band(Q_RT_MED, m["rt_med"], "清洗后 RT 中位 (ms)", fmt="{:.0f}")
    band(Q_DEV, m["dev_frac"], "刺激时长偏差>20ms 占比", lower_is_bad=False, fmt="{:.1%}")
    band(Q_EFF, m["eff_rate"], "可用试次率", fmt="{:.1%}")
    # 结构完整性只看**原始**正式段（清洗后变薄是超时造成的，不是采集缺失）
    if m["cell_min_raw"] < Q_CELL_RAW[1]:
        hard.append(f"正式段逐格最小 {m['cell_min_raw']} 试次 < {Q_CELL_RAW[1]}（48 格有整格缺失）")
    elif m["cell_min_raw"] < Q_CELL_RAW[0]:
        notes.append(f"正式段逐格最小 {m['cell_min_raw']} 试次 < {Q_CELL_RAW[0]}")
    return {"metrics": m, "hard": hard, "notes": notes}


# --------------------------------------------------------------------------- #
# 统计层：这批数据「够不够、还差几人」（D120）
# --------------------------------------------------------------------------- #
def stats_layer(df_all: "pd.DataFrame", keep_ids: set[str], expect_n: int) -> dict:
    """逐被试 SPE → 组均值 / SE / 需补人数。"""
    d = R.clean(df_all)
    per = R.spe_per_subject(d)
    per = per[per["subject_id"].isin(keep_ids)].copy()

    def block(x: "pd.DataFrame", label: str, n_plan: int) -> dict:
        out = {"label": label, "n": int(len(x)), "n_plan": int(n_plan), "metrics": []}
        need = 0
        for key, target in TARGET.items():
            v = x[key].to_numpy(float)
            if len(v) < 2:
                out["metrics"].append({"key": key, "name": METRIC_CN[key], "n": len(v),
                                       "mean": float("nan"), "sd": float("nan"),
                                       "se": float("nan"), "target": target,
                                       "n_need": None, "ok": False})
                continue
            sd = float(v.std(ddof=1))
            se = sd / math.sqrt(len(v))
            n_need = int(math.ceil((sd / target) ** 2)) if sd > 0 else len(v)
            need = max(need, n_need)
            out["metrics"].append({"key": key, "name": METRIC_CN[key], "n": int(len(v)),
                                   "mean": float(v.mean()), "sd": sd, "se": se,
                                   "ci": list(R.t_ci(v)), "target": target,
                                   "n_need": n_need, "ok": se <= target})
        out["n_need"] = need
        out["need_more"] = max(0, need - out["n"])
        out["hire"] = int(math.ceil(need * 1.2))
        out["status"] = "达标" if out["need_more"] == 0 else "需补"
        return out

    stats = {"overall": block(per, "全体", expect_n * 4), "by_group": []}
    for gid in sorted({int(g) for g in range(1, 5)}):
        p = Q.P_BY_GROUP.get(gid)
        sub = per[per["P"].round().astype(int) == p] if p is not None else per.iloc[0:0]
        stats["by_group"].append(block(sub, f"组 {gid}（P={p}）", expect_n))

    # 总判定：按组逐组定编（P 是组间因子，组内精度不够就等于这条曲线没法定量）。
    total_need = 0
    total_have = 0
    short = []
    for blk in stats["by_group"]:
        total_need += blk["n_need"]
        total_have += blk["n"]
        if blk["need_more"] > 0:
            short.append(f"{blk['label']} 差 {blk['need_more']} 人")
    ov = stats["overall"]
    ov["group_plan"] = total_need
    ov["group_have"] = total_have
    ov["group_short"] = short
    needs = [blk["n_need"] for blk in stats["by_group"]]
    ov["group_need_min"] = min(needs) if needs else 0
    ov["group_need_max"] = max(needs) if needs else 0
    ov["status"] = ("达标" if (not short and ov["need_more"] == 0) else "需补")
    ov["need_more"] = max(ov["need_more"], total_need - total_have)
    ov["hire"] = int(math.ceil(ov["need_more"] * 1.2))
    return {"per": per, "stats": stats}


# 判据代码 → 人话（报告里不能只留"S6-1 FAIL"）
NOTE_CN = {
    "S6-1 FAIL": "S6-1（超时率：整体 ≤20% 且最差单元 ≤40%）未过",
    "S6-5 FAIL": "S6-5（组内正确率离群）未过",
}


def _note(nt: str) -> str:
    return NOTE_CN.get(nt, nt)


# --------------------------------------------------------------------------- #
# 报告（Markdown / CSV / JSON）
# --------------------------------------------------------------------------- #
def render_report(res: list[dict], qmap: dict, st: dict, expect_n: int,
                  data: str, cmd: str) -> str:
    n = {k: sum(1 for r in res if r["verdict"] == k) for k in (KEEP, REVIEW, EXCLUDE)}
    ov = st["stats"]["overall"]
    out = ["# 数据快速筛查报告", "",
           f"- 数据目录：`{data}`",
           f"- 场次：{len(res)} ｜ 计入 **{n[KEEP]}** ｜ 待复核 **{n[REVIEW]}** ｜ 不计入 **{n[EXCLUDE]}**",
           f"- 生成命令：`{cmd}`", ""]

    out += ["## 一、结论", ""]
    if n[EXCLUDE]:
        out.append(f"- ❌ **{n[EXCLUDE]} 场不计入 N**：见 §三 的 ❌ 条目。这些场次不计入样本量，"
                   "先修程序/重跑再补人。")
    else:
        out.append("- ✅ 没有不计入的场次。")
    if n[REVIEW]:
        out.append(f"- 🟠 {n[REVIEW]} 场待复核：可进分析，但要在论文方法节报备。")
    out.append(f"- 统计层：计入 n={ov['n']}，判 **{ov['status']}**")
    if ov["status"] != "达标":
        out.append(f"  - 按组定编：每组需 {ov['group_need_min']}–{ov['group_need_max']} 人，"
                   f"四个组合计 **{ov['group_plan']}** 人，现有 {ov['group_have']} 人 ⇒ "
                   f"差 **{ov['need_more']} 人**（按 20% 损耗应再招 {ov['hire']} 人）。")
        if ov["group_short"]:
            out.append("  - 分组缺口：" + "；".join(ov["group_short"]) + "。")
    out.append("")

    out += ["## 二、统计层：SPE 能不能测出来", "",
            f"目标精度：SE(ΔRT 中位) ≤ {TARGET['drt_med']} ms、SE(Δacc) ≤ {TARGET['d_acc']:.2f}（Δacc 以比例记）、"
            f"SE(分位斜率) ≤ {TARGET['slope']} ms（配对设计，`n = (SD/目标SE)²`）。", "",
            "| 范围 | n | 指标 | 均值 | SD | SE | 95% CI | 目标 SE | 需 n | 判定 |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for blk in [ov] + st["stats"]["by_group"]:
        for i, mm in enumerate(blk["metrics"]):
            if mm["n"] < 2:
                out.append(f"| {blk['label'] if i == 0 else ''} | {mm['n']} | {mm['name']} | — | — | — | — | {mm['target']:g} | — | 样本不足 |")
                continue
            lo, hi = mm["ci"]
            mark = "✅" if mm["ok"] else "🟠"
            out.append(f"| {blk['label'] if i == 0 else ''} | {mm['n']} | {mm['name']} | "
                       f"{mm['mean']:.3f} | {mm['sd']:.3f} | {mm['se']:.3f} | "
                       f"[{lo:.3f}, {hi:.3f}] | {mm['target']:g} | {mm['n_need']} | {mark} |")
    out += ["", f"全体判定：**{ov['status']}**（全体 18 人以上的『全体精度』已满足，"
            f"需 n = {ov['n_need']}；真正的缺口在分组精度，见 §一）。", ""]

    out += ["## 三、逐场判定", "",
            "| # | 组-被试 | 正式/练习 | 响应率 | 提前 | 正确率 | RT中位 | 可用率 | 逐格(原) | 裁决 | 理由 |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(res, 1):
        q = qmap.get((r["gid"], r["sid"]), {"metrics": {}})["metrics"]
        reasons = (r["hard"] + r["soft"])[:2]
        reason = "；".join(reasons) if reasons else "—"
        out.append(f"| {i} | {r['gid']}-{r['sid']} | {r['rec'].get('n_formal')}/{r['rec'].get('n_practice')} | "
                   f"{q.get('resp_rate', float('nan')):.1%} | {q.get('prem_rate', float('nan')):.1%} | "
                   f"{q.get('acc_resp', float('nan')):.3f} | {q.get('rt_med', float('nan')):.0f} | "
                   f"{q.get('eff_rate', float('nan')):.1%} | {q.get('cell_min_raw', 0)} | "
                   f"{MARK[r['verdict']]} {r['verdict']} | {reason} |")
    out.append("")

    hard_rows = [(r, qmap[(r["gid"], r["sid"])]) for r in res
                 if r["verdict"] != KEEP and (r["gid"], r["sid"]) in qmap]
    if hard_rows:
        out += ["## 四、复核清单", ""]
        for r, q in hard_rows:
            out.append(f"### {r['gid']}-{r['sid']} · {MARK[r['verdict']]} {r['verdict']}")
            for h in r["hard"]:
                out.append(f"- ❌ {h}")
            for s in r["soft"]:
                out.append(f"- 🟠 {s}")
            out.append("")

    note_rows = [(r, qmap[(r["gid"], r["sid"])]) for r in res
                 if r["notes"] and (r["gid"], r["sid"]) in qmap]
    if note_rows:
        out += ["## 五、信息项（只记录，不阻塞入库）", "",
                "行为层面的偏离（超时偏高、正确率偏低等）在这里汇总。**不据此剔除**——"
                "拿行为当剔除理由会把样本筛成「好被试」，直接污染组间比较。", ""]
        # 普遍项单独汇总：同一句在过半数场次出现，逐场重复只会把报告淹掉。
        from collections import Counter
        cnt = Counter(_note(nt) for r, _ in note_rows for nt in r["notes"])
        common_floor = max(3, len(res) // 2)
        common = {nt for nt, c in cnt.items() if c >= common_floor}
        for nt, c in cnt.most_common():
            if nt in common:
                out.append(f"- **普遍项（{c} 场）**：{nt}")
        if common:
            out.append("")
        for r, q in note_rows:
            rest = [_note(nt) for nt in r["notes"] if _note(nt) not in common]
            if rest:
                out.append(f"- **{r['gid']}-{r['sid']}**：" + "；".join(rest))
        out.append("")

    out += ["## 六、口径与复现", "",
            "1. 技术层：Stage 1 六项（`check_stage1_acceptance.py`）；**6-B 降级为信息项**"
            "（它是实机验收的取证检查，不适合 20 人批次逐场强制）；6-C 的单行级异常同样降为信息项。",
            "2. 结构层：`qc_group.classify` + 正式段 576 + 练习段 = P（P=0 即零练习）。",
            "3. 一致层：`read_formal_data.validate()`；**列结构问题**为硬项，逐行取值异常为信息项。",
            f"4. 质量层阈值（软/硬）：响应率 {Q_RESP}、提前按键 {Q_PREM}、正确率 {Q_ACC}、"
            f"RT 中位 {Q_RT_MED[1]:g}/{Q_RT_MED[0]:g} ms、时长偏差占比 {Q_DEV}、"
            f"可用试次率 {Q_EFF}、正式段逐格原始试次 {Q_CELL_RAW[0]}/{Q_CELL_RAW[1]}。",
            f"5. 统计层清洗：**只看正式段**（练习段固定 T=83.3/W=1200，混进来会带偏），"
            f"再按期响应 + `120 < RT ≤ W+50`；Δ 均为「他人 − 自我」（RT）/「自我 − 他人」（acc）。",
            f"6. 同一命令可重复跑：`{cmd}`。", ""]
    return "\n".join(out)



def audit_one(gid: int, sid: int, csv: Path | None, txt: Path | None,
              shadowed: list[Path] | None = None) -> dict:
    source = csv or txt
    if source is None:
        raise ValueError(f"组 {gid} 被试 {sid} 既没有 CSV 也没有 txt")
    tech_ok, tech_hard, tech_notes = layer_tech(source)
    cons_errors, cons = layer_consistency(source)
    if txt is None:
        st = {"rec": {"n_formal": -1, "n_practice": -1, "n_dropped": -1,
                      "acc_mean": None, "timeout_prop": None},
              "cls": EXCLUDE,
              "hard": [f"缺孪生 txt（`exp_group{gid}_subject{sid}.txt`）⇒ 结构层无法核"],
              "soft": [], "notes": [], "n_prac_expect": None}
    else:
        st = layer_structure(txt, gid, sid)

    # 一致层：列结构问题（缺列/多列/列名）是硬项；逐行取值异常只记录——
    # 它和 6-C 是同一批掉帧行的两种说法（D120）。
    cons_hard = [f"一致层：{e}" for e in cons_errors if "列" in e]
    cons_notes = [f"一致层：{e}" for e in cons_errors if "列" not in e]
    hard = tech_hard + st["hard"] + cons_hard
    soft = list(st["soft"])
    notes = tech_notes + list(st.get("notes", [])) + cons_notes
    verdict = EXCLUDE if hard else (REVIEW if soft else KEEP)
    return {"gid": gid, "sid": sid, "csv": csv, "txt": txt, "source": source,
            "verdict": verdict,
            "hard": hard, "soft": soft, "notes": notes, "tech_ok": tech_ok,
            "rec": st["rec"], "cls": st["cls"],
            "n_prac_expect": st["n_prac_expect"], "cons": cons,
            "shadowed": shadowed or []}


def render(res: list[dict]) -> str:
    out = [f"═══ 数据快速筛查：{len(res)} 个场次 ═══", ""]
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
        for nt in r["notes"]:
            out.append(f"    ℹ {_note(nt)}")
        out.append(f"    ⇒ {MARK[r['verdict']]} **{r['verdict']}**")
        out.append("")

    n = {k: sum(1 for r in res if r["verdict"] == k) for k in (KEEP, REVIEW, EXCLUDE)}
    out.append(f"汇总：计入 {n[KEEP]} ｜ 待复核 {n[REVIEW]} ｜ 不计入 {n[EXCLUDE]}")
    if n[EXCLUDE]:
        out.append("⇒ 有场次不计入 N：见上面 ❌ 条目；先修程序/重跑，别把它算进样本量。")
    elif n[REVIEW]:
        out.append("⇒ 全部可计入门槛之外还有人要看的项：逐条确认后再并入 N。")
    else:
        out.append("⇒ 全部可计入 N（信息项只记录，见 ℹ 行）。")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="数据快速筛查：技术层 + 结构层 + 一致层 + 质量层 + 统计层")
    ap.add_argument("paths", nargs="+", help="目录或 CSV 文件")
    ap.add_argument("--out", help="把 Markdown 报告写到这个路径")
    ap.add_argument("--csv", help="把逐场表写到这个 CSV")
    ap.add_argument("--json", help="把逐场表 + 统计层写到这个 JSON")
    ap.add_argument("--expect-n", type=int, default=40, help="每组**计划**人数（默认 40，用于算需补）")
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

    res, qmap, frames = [], {}, []
    for x in sessions:
        r = audit_one(x["gid"], x["sid"], x["csv"], x["txt"], x["shadowed"])
        if r["csv"] is not None:
            df = R.load_files([r["csv"]])
            gid = pd.to_numeric(df["groupID"], errors="coerce").fillna(-1).astype(int)
            sid = pd.to_numeric(df["subjectID"], errors="coerce").fillna(-1).astype(int)
            df = df[(gid == r["gid"]) & (sid == r["sid"])]
            if len(df):
                q = quality_one(df)
                frames.append(df)
            else:
                q = {"metrics": {}, "hard": [f"CSV 里找不到组 {r['gid']} 被试 {r['sid']} 的行"], "notes": []}
            r["hard"] += q["hard"]
            r["notes"] += q["notes"]
            r["verdict"] = EXCLUDE if r["hard"] else (REVIEW if r["soft"] else KEEP)
            qmap[(r["gid"], r["sid"])] = q
        res.append(r)

    print(render(res))

    st = None
    if frames:
        keep_ids = {f"{r['gid']}-{r['sid']}" for r in res if r["verdict"] != EXCLUDE}
        st = stats_layer(pd.concat(frames, ignore_index=True), keep_ids, args.expect_n)
        ov = st["stats"]["overall"]
        print(f"\n═══ 统计层（可计入 N={ov['n']}，计划每组 {args.expect_n} 人）═══")
        print("| 范围 | n | 指标 | 均值 | SD | SE | 95% CI | 需 n | 判定 |")
        print("|---|---|---|---|---|---|---|---|---|")
        for blk in [ov] + st["stats"]["by_group"]:
            for i, mm in enumerate(blk["metrics"]):
                if mm["n"] < 2:
                    print(f"| {blk['label'] if i == 0 else ''} | {mm['n']} | {mm['name']} | — | — | — | — | — | 样本不足 |")
                    continue
                lo, hi = mm["ci"]
                print(f"| {blk['label'] if i == 0 else ''} | {mm['n']} | {mm['name']} | {mm['mean']:.3f} | "
                      f"{mm['sd']:.3f} | {mm['se']:.3f} | [{lo:.3f}, {hi:.3f}] | {mm['n_need']} | "
                      f"{'✅' if mm['ok'] else '🟠'} |")
        print(f"\n⇒ 全体判定：**{ov['status']}**"
              + ("" if ov["status"] == "达标" else
                 f"；还需 {ov['need_more']} 人（按 20% 损耗应招 {ov['hire']} 人）。"))

    cmd = "python -X utf8 1_Code/Experiment/intake.py " + " ".join(str(p) for p in paths)
    if st is not None and args.out:
        rep = render_report(res, qmap, st, args.expect_n, str(paths[0]), cmd)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rep, encoding="utf-8", newline="\n")
        print(f"\n[报告] {args.out}")
    if st is not None and args.csv:
        rows = []
        for r in res:
            q = qmap.get((r["gid"], r["sid"]), {"metrics": {}})["metrics"]
            rows.append({"group": r["gid"], "subject": r["sid"], "verdict": r["verdict"],
                         "n_formal": r["rec"].get("n_formal"),
                         "n_practice": r["rec"].get("n_practice"),
                         "n_clean": q.get("n_clean"),
                         **{k: v for k, v in q.items() if k in (
                             "resp_rate", "prem_rate", "acc_resp", "rt_med", "eff_rate",
                             "n_clean", "dev_frac", "dev_max", "n_cells",
                             "cell_min_raw", "cell_min_clean", "cell_med_clean")},
                         "hard": " | ".join(r["hard"]), "soft": " | ".join(r["soft"]),
                         "notes": " | ".join(r["notes"]),
                         "path": str(r["source"])})
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(args.csv, index=False, encoding="utf-8-sig")
        print(f"[逐场表] {args.csv}")
    if st is not None and args.json:
        payload = {
            "data": str(paths[0]), "expect_n": args.expect_n,
            "counts": {k: sum(1 for r in res if r["verdict"] == k) for k in (KEEP, REVIEW, EXCLUDE)},
            "sessions": [{"group": r["gid"], "subject": r["sid"], "verdict": r["verdict"],
                          "path": str(r["source"]), "hard": r["hard"], "soft": r["soft"],
                          "notes": r["notes"]}
                         for r in res],
            "stats": st["stats"],
            "targets": TARGET,
        }
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                   encoding="utf-8", newline="\n")
        print(f"[JSON] {args.json}")
    return 1 if any(r["verdict"] == EXCLUDE for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
