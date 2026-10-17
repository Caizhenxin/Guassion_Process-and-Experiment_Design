#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""`stage9_report.py` 的自测：证明报告生成器**不会印出它不该印的东西**。

为什么要单独立一个自测（而不是靠读一遍生成的报告）：
  - 报告是交付件，它的错法不是「崩掉」，而是**安静地印出一个被误读的数字** ——
    最典型的是把 `inf` / `nan` 印进表格（`A_best = inf` 的真实含义是「这条臂在本预算内
    没有取到可行点」，印出来会被读成「极好」或「极差」，两种读法都错）；
  - 其次是**作用域错**：`front_scope.n_evaluated != n_candidates` 时，报告必须自己说
    「前沿/推荐点只覆盖了一部分候选空间」，而不是照印推荐点。

判据分五组：
  R1 真实落盘件（durable payload，存在时）—— 端到端可读、作用域打 ✅、
     「支配 D4 的可行设计」与从 `cache` 现算的真值一致、推荐点 = 可行集内 `(A)` 最小点、
     **交付件 `stage9_report.md` 与当前生成器的输出逐字相同**（R1l；缺这条就只测了生成器、
     没测交付的那一份 —— 本自测第一版正是这么放过了磁盘上一条不该出现的「旧版措辞」告警）；
  R2 `_f` / `_dominates` 单元判据（`inf`/`nan`/缺失 ⇒ `—`）；
  R3 合成 payload：作用域不全 ⇒ 必须打 ⚠️ 且不得打 ✅；`d54` 计数必须标注「不是全空间真值」；
  R4 合成 payload：`A_best = inf`/`nan` 的臂 ⇒ 表格单元一律 `—`、裁决段必须点明
     「没有可行点」；全臂无可行点 ⇒ 不得出现「最好」类结论；
  R5 命令行接口（退出码 0 / 写出内容 == `build()` / 无参 ⇒ 2）。

用法：
    python check_stage9_report.py [日志文件]
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import stage9_report as R  # noqa: E402  （同目录脚本，按路径导入）

_RESULTS: list[tuple[str, bool, str]] = []
# 交付件报告所依据的落盘件：**durable** 文件名（报告头里写的就是它），
# 报告里每个数字都必须能回到这个文件、且它的 sha256 由本自测复算。
#
# ❗ D62：依据件从 `n_fim = 1` 那批（`stage9_payload_nfim1_budget12.json`）换到
# **正式 `n_fim = 12` 的 budget-12 件**（`--budget 12 --n-fim 12 --noise-repeats 16`）。
# 换的是「报告以哪一次运行为准」，不是判据；而且 D60 之后 §5 的判词由报告自己按
# **当前代码**重算，所以依据件里转印的旧判词与复核不一致时，报告会自己标出来。
# 用的是 `_restamped` 件：它的 `compare` 段已由 `_scratch_restamp_payload.py` 按当前代码
# 离线重算并写入 `provenance`（内环读数逐字继承自原始件 `stage9_payload_nfim12_budget12.json`），
# 这样 §5 的「转印 vs 复核」比的是**同一版规则**，而不是两个时代。
_REAL = _HERE / "stage9_payload_nfim12_budget12_restamped.json"


def check(label: str, cond: bool, detail: str = "") -> None:
    _RESULTS.append((label, bool(cond), detail))
    print(f"{'✅' if cond else '❌'} {label}" + (f" —— {detail}" if detail else ""))


def _cell_inf(text: str) -> list[str]:
    """找出**表格单元里**的 inf/nan（表体文字里提到 `inf` 是在解释缺陷，不算违规）。"""
    hits = []
    for ln in text.splitlines():
        if not ln.lstrip().startswith("|"):
            continue
        for cell in ln.split("|")[1:-1]:
            if re.fullmatch(r"\s*(?:[+-]?inf(?:inity)?|[+-]?nan)\s*", cell, re.I):
                hits.append(ln.strip())
                break
    return hits


def _section(text: str, n: int) -> str:
    """取第 `n` 节的正文（`## n.` 到下一个 `## ` 之前）。

    ⚠️ 必须分节后再找表格行：同一个臂名（如 `` | `random` ``）在第 4 节与第 5 节**都**是表格行，
    按整篇搜会命中第 4 节那张「抽到的设计数 / 参考 `best J` / 耗时」表 —— 本自测第一版
    就是因此误报（读数 `| random | 12 | 0.4203 | 34.7 s |` 显然不是第 5 节的裁决表）。
    """
    head = f"## {n}."
    i = text.find(head)
    if i < 0:
        return ""
    j = text.find("\n## ", i + 1)
    return text[i:j if j > 0 else len(text)]


def _mk_payload(**over) -> dict:
    """一个**最小但字段齐全**的 payload，用于合成场景。"""
    base = {
        "designs": [{"name": "A", "T_ms": [33.33], "W_ms": [799.98], "n_rep": 12, "n_trials": 12},
                    {"name": "B", "T_ms": [83.33], "W_ms": [1199.90], "n_rep": 16, "n_trials": 16}],
        "noise": {"A": [0.30, 0.32], "B": [7.0, 7.2], "omission": [0.10, 0.12], "J": [1.0, 1.4],
                  "C": [1.0, 1.4], "sd_A": 0.010, "sd_B": 0.100, "sd_omission": 0.010,
                  "sd_J": 0.200, "sd_C": 0.200, "alpha": 0.04, "n_repeats": 2},
        "histories": {
            "grid": {"picked": ["A"], "best_so_far": [1.0], "best_A_so_far": [0.30],
                     "best_name": "A", "best_J": 1.0, "best_A": 0.30, "B_at_best_A": 7.0,
                     "B_max": 7.0, "A_best_name": "A", "n_feasible": 1, "seconds": 3.0},
            "random": {"picked": ["B"], "best_so_far": [float("inf")], "best_A_so_far": [float("inf")],
                       "best_name": None, "best_J": float("inf"), "best_A": float("inf"),
                       "B_at_best_A": float("nan"), "B_max": float("nan"), "A_best_name": None,
                       "n_feasible": 0, "seconds": 2.0},
            "manual": {"picked": ["B"], "best_so_far": [float("inf")], "best_A_so_far": [float("inf")],
                       "best_name": None, "best_J": float("inf"), "best_A": float("inf"),
                       "B_at_best_A": float("nan"), "B_max": float("nan"), "A_best_name": None,
                       "n_feasible": 0, "seconds": 1.0},
            "bo": {"picked": ["B"], "best_so_far": [float("inf")], "best_A_so_far": [float("inf")],
                   "best_name": None, "best_J": float("inf"), "best_A": float("inf"),
                   "B_at_best_A": float("nan"), "B_max": float("nan"), "A_best_name": None,
                   "n_feasible": 0, "seconds": 0.1},
        },
        "compare": [
            {"arm": "grid", "A_best": 0.30, "B_at_A_best": 7.0, "n_feasible": 1, "best_J": 1.0,
             "dA_vs_best": 0.0, "dB_vs_best": 0.0, "verdict": "本预算下 (A,B) 上最好。"},
            {"arm": "random", "A_best": float("inf"), "B_at_A_best": float("nan"),
             "n_feasible": 0, "best_J": float("inf"), "dA_vs_best": float("inf"),
             "dB_vs_best": float("nan"), "verdict": "在 (A) 上显著更差。"},
            {"arm": "manual", "A_best": float("inf"), "B_at_A_best": float("nan"),
             "n_feasible": 0, "best_J": float("inf"), "dA_vs_best": float("inf"),
             "dB_vs_best": float("nan"), "verdict": "在 (A) 上显著更差。"},
            {"arm": "bo", "A_best": float("inf"), "B_at_A_best": float("nan"),
             "n_feasible": 0, "best_J": float("inf"), "dA_vs_best": float("inf"),
             "dB_vs_best": float("nan"), "verdict": "在 (A) 上显著更差。"},
        ],
        "pareto": [{"name": "A", "A": 0.30, "B": 7.0, "J": 1.0}],
        "best": {"name": "A", "A": 0.30, "B": 7.0, "J": 1.0, "criterion": "A（D54）"},
        "best_J_reference": {"name": "A", "J": 1.0},
        "anchor": {"name": "B", "A": 0.40, "B": 6.5, "J": 2.0, "feasible": False},
        "d54": {"omission_band": [0.05, 0.2], "n_band_rejected": 1, "n_feasible": 1,
                "criterion": ["A", "B"]},
        "front_scope": {"n_candidates": 2, "n_cached_before_full_eval": 1, "n_evaluated": 2,
                        "n_front": 1},
        "settings": {"budget": 1, "n_fim": 2, "n_subjects": 4, "P": 4, "rho": 0.6, "seed": 0},
        "spec_sha256": "deadbeef",
        "n_evals": 2,
        "seconds": 6.0,
        "cache": {
            "A": {"name": "A", "A": 0.30, "B": 7.0, "J": 1.0, "feasible": True, "gates": [],
                  "omission": 0.10, "omission_band": [0.05, 0.2], "cond": 1.0e5, "n_bad": 0,
                  "n_fim": 2},
            "B": {"name": "B", "A": 0.40, "B": 6.5, "J": 2.0, "feasible": False,
                  "gates": ["D54 约束：遗漏率 0.3000 落在冻结带 [0.05, 0.2] 之外"],
                  "omission": 0.30, "omission_band": [0.05, 0.2], "cond": 1.0e5, "n_bad": 0,
                  "n_fim": 2},
        },
    }
    base.update(over)
    return base


def _write(tmp: Path, payload: dict, name: str) -> Path:
    p = tmp / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


print("=" * 72)
print("R1 真实落盘件（存在时端到端；不存在则跳过，且有 R1p 兜底覆盖同一路径）")
print("=" * 72)
if _REAL.is_file():
    d = json.loads(_REAL.read_text(encoding="utf-8"))
    text = R.build(_REAL)
    check("R1a 报告可生成且非空", len(text.splitlines()) > 40, f"{len(text.splitlines())} 行")
    check("R1b 作用域为全空间 ⇒ 必须打 ✅", "✅ `n_evaluated == n_candidates`" in text)
    check("R1c 不得打作用域 ⚠️ 分支",
          "只覆盖了一部分候选空间" not in text)
    check("R1d 表格单元里不得出现 inf/nan", not _cell_inf(text),
          f"命中 {_cell_inf(text)}" if _cell_inf(text) else "")
    check("R1e 头部必须带落盘件的 sha256 前缀",
          R.hashlib.sha256(_REAL.read_bytes()).hexdigest()[:16] in text)
    # 从 cache 现算真值，与报告互证
    feas = [r for r in d["cache"].values() if r.get("feasible")]
    amin = min(feas, key=lambda r: float(r["A"]))
    check("R1f 推荐点 = 可行集内 (A) 最小点",
          d["best"]["name"] == amin["name"], f"报告 {d['best']['name']} / 现算 {amin['name']}")
    anc = d["anchor"]
    dom = [r for r in feas if float(r["A"]) <= float(anc["A"]) + 1e-12
           and float(r["B"]) >= float(anc["B"]) - 1e-12 and r["name"] != anc["name"]]
    check("R1g 「支配锚点的可行设计」个数与现算一致",
          f"支配它的可行设计**：{len(dom)} 个" in text, f"现算 {len(dom)} 个")
    # ❗ 这里原先硬编码 `0.361`（`n_fim = 1` 那批落盘件的锚点读数）⇒ 一旦换依据件就会红，
    #    而它想守的并不是那个数字，是「锚点的遗漏率必须从 `cache` 取到、不得印成 `—`」。
    #    改为从 `cache` 现算锚点的遗漏率，断言报告印出的正是它（同一件事，但对依据件免疫）。
    _a_rec = d["cache"].get(anc["name"], {})
    _a_om = R._f(_a_rec.get("omission"), 3)
    check("R1h 锚点的遗漏率必须从 `cache` 取到并与报告一致（不得印 —）",
          _a_om != "—" and f"遗漏率 `{_a_om}`" in text, f"现算 {_a_om}")
    check("R1i 必须印出锚点的闸门文本", "D54 约束" in text)
    # ❗ R1j 原先写死「这条告警**不得**出现」—— 那是 `n_fim = 1` 那批依据件的性质
    #    （四条臂都取到了可行点）。D62 换成正式 `n_fim = 12` 的 budget-12 件后，`manual`
    #    臂在本预算内**没有**可行点（`A_best = inf`）⇒ 这条告警**应该**出现。
    #    它想守的不是「不得出现」，而是「**跟着依据件走**」：有臂非有限 ⇒ 必须有；
    #    全臂有限 ⇒ 不得有。所以改成按 payload 现算条件（同 R1h 的处理方式）。
    _has_inf_arm = any(
        not math.isfinite(float(r.get("A_best", float("inf"))))
        for r in (d.get("compare") or []))
    _has_warn = "已被修正的措辞" in text
    check("R1j 旧版措辞告警必须**跟着依据件走**：有臂的 `(A)` 非有限 ⇒ 必须有；全臂有限 ⇒ 不得有",
          _has_warn == _has_inf_arm,
          f"现算 has_inf={_has_inf_arm}、报告{'有' if _has_warn else '无'}该告警")
    _top = d["compare"][0]
    _row = [ln for ln in _section(text, 5).splitlines() if ln.startswith(f"| `{_top['arm']}`")]
    check("R1k 第 5 节 `B`@同一点必须印出真值（键名读错会**静默**印成 `—`）",
          bool(_row) and R._f(_top["B_at_A_best"]) in _row[0],
          _row[0] if _row else "找不到该行")
    # ❗ 措辞纪律：`n_bad` 是 `likelihood.py::fim_diagnostics` 数出的**不可识别方向条数**，
    #    不是「坏试次」。把它写成坏试次会把「这个设计有方向不可识别」说成「这份数据里有几试次坏了」，
    #    两者要采取的行动完全不同（前者要改设计，后者要查采集）。
    check("R1m 报告里不得把 `n_bad` 说成「坏试次」（它是不可识别方向条数）",
          "坏试次" not in text,
          "；".join(ln.strip()[:80] for ln in text.splitlines() if "坏试次" in ln))
    # ❗ R1a–R1k 测的都是**内存里重新生成**的那份报告；交付件是磁盘上那一份。
    #    两者分开就出现了本自测第一版的洞：磁盘上的报告带着一条**已经不该出现**的
    #    「旧版措辞」告警（生成器读错了键 ⇒ 永远判定为含 `inf`），而 R1j 读的是内存版 ⇒ 全绿。
    #    牙齿：交付件必须与当前生成器的输出**逐字相同**。
    _deliv = _HERE / "stage9_report.md"
    _same = _deliv.is_file() and _deliv.read_text(encoding="utf-8") == text
    check("R1l 交付件 `stage9_report.md` 必须与当前生成器的输出**逐字相同**"
          "（否则自测只证明了生成器、没有证明交付的那份）",
          _same, "缺失" if not _deliv.is_file() else ("相同" if _same else "不同 ⇒ 需重跑 `stage9_report.py`"))
else:
    print(f"⏭️ 跳过 R1：缺 {_REAL.name} —— 它是**交付件报告的依据件**，缺了就无法重算报告里的数字"
          f"（同一渲染路径由 R1p 的合成 payload 覆盖）")

print()
print("=" * 72)
print("R1p 合成 payload（全空间作用域）：同一端到端路径，不依赖任何一次性落盘件")
print("=" * 72)
with tempfile.TemporaryDirectory() as td0:
    tp = _write(Path(td0), _mk_payload(), "full.json")
    t0 = R.build(tp)
    check("R1p-a 全空间作用域 ⇒ 打 ✅ 且不打 ⚠️",
          ("✅ `n_evaluated == n_candidates`" in t0)
          and ("只覆盖了一部分候选空间" not in t0))
    check("R1p-b 锚点的遗漏率从 `cache` 取到（`anchor` 段本身不带它）",
          "遗漏率 `0.300`" in t0)
    check("R1p-c 锚点的闸门文本被印出", "D54 约束" in t0)
    check("R1p-d 支配锚点的可行设计 = 1 个（`(0.30, 7.0)` 支配 `(0.40, 6.5)`）",
          "支配它的可行设计**：1 个" in t0)
    check("R1p-e `d54` 全空间 ⇒ 不得出现「不是全空间真值」", "不是全空间真值" not in t0)
    check("R1p-f 头部必须带落盘件的 sha256 前缀",
          R.hashlib.sha256(tp.read_bytes()).hexdigest()[:16] in t0)
    _g = [ln for ln in _section(t0, 5).splitlines() if ln.startswith("| `grid`")]
    check("R1p-g 第 5 节 `B`@同一点的**列**必须印出真值（合成件里为 `7.0000`）",
          bool(_g) and "7.0000" in _g[0], _g[0] if _g else "找不到该行")
    # ❗ `sd` 是**估计量**：样本标准差的相对不确定度 ≈ `1/√(2(n−1))`，2 次重复时约 71%，
    #    而 `alpha = sd_J²` 是这个的两倍。报告必须按 payload 自报的 `n_repeats` 打出这件事 ——
    #    否则读者会把 `2·sd_A` 当成精确门槛（实测 2 次 vs 6 次重复：`alpha` 差 2.4 倍）。
    # 141% = 2 × 70.7%（`alpha = sd_J²` 的相对不确定度是 `sd` 的两倍）
    check("R1p-h `n_repeats = 2` ⇒ 必须先警「`sd` 自身的不确定度约 71%」（不得静默）",
          "`sd` 自身的不确定度约 71%" in t0 and "`alpha = sd_J²` 约 141%" in t0)
    _n6 = dict(_mk_payload()["noise"])
    _n6["n_repeats"] = 6
    t6 = R.build(_write(Path(td0), _mk_payload(noise=_n6), "six.json"))
    check("R1p-i `n_repeats = 6` ⇒ 不得出现该先警（只留陈述句）",
          "`sd` 自身的不确定度约 32%" in t6 and "⚠️ 本次标定只用" not in t6)
    # ❗ D59：`sd` 不只是「估计得粗」，它在旧写法里还**抽错了地方** —— 标定种子是
    #    `cell_seed(name, base + 791_900 + 37k)`（同一哈希值加小偏移的算术邻居），
    #    `n_fim = 1` 下这 6 个种子恰好落在 `(A)` 种子分布的密集区 ⇒ `sd_A = 0.0048`，
    #    而 48 个无关种子给 `0.0189`（**4.0 倍**）。报告必须能区分：
    #    「标定种子已自报」 vs 「落盘件没记种子 ⇒ 无法复核」。
    check("R1p-j 落盘件**没有**标定种子记录（D59 之前的版本）⇒ 报告必须明说无法复核带宽来源",
          "没有记录标定种子" in t0, "先警已印出" if "没有记录标定种子" in t0 else "缺失")
    _nk = dict(_mk_payload()["noise"])
    _nk["n_repeats"] = 6
    _nk["seeds"] = [11, 22, 33, 44, 55, 66]
    _nk["family"] = "cell_seed(f'{name}#noise{k}', base_seed), k = 0..5"
    tk = R.build(_write(Path(td0), _mk_payload(noise=_nk), "seeds.json"))
    check("R1p-k 有种子记录 ⇒ 必须把种子印出来，且**不得**再印「没有记录标定种子」",
          "没有记录标定种子" not in tk and "11, 22, 33" in tk)
    check("R1p-l 第 7 节的「几倍带宽」必须自带 D59 限制句（换标定种子可把 8.2 倍变成 1.1 倍）",
          "只与标定种子样本一样可靠" in t0 and "_scratch_reverdict.py" in t0)
    # ❗ D59 同族的第四条：第 5 节的判词是**运行时**生成的冻结文本（报告只转印、不重算），
    #    裁决逻辑改过三代 ⇒ 落盘件不记录版本时，读者无法判断这些判词该不该信。
    check("R1p-m 落盘件**没有**裁决规则版本（D59 之前的运行）⇒ 报告必须先警"
          "「判词可能由已被修正的规则生成」",
          "没有记录裁决规则版本" in t0, "先警已印出" if "没有记录裁决规则版本" in t0 else "缺失")
    _dv = dict(_mk_payload())
    _dv["verdict_logic"] = "D59：两根带子各判各的；`ΔA` 在带内不得借 `ΔB` 的带子定论"
    tm = R.build(_write(Path(td0), _dv, "vlogic.json"))
    check("R1p-n 有裁决规则版本 ⇒ 必须印出来，且**不得**再印「没有记录裁决规则版本」",
          "没有记录裁决规则版本" not in tm and "两根带子各判各的" in tm)
    # ❗ D60：判词是运行时冻结产物，规则已改过三代（D55 洗白 → D59 各判各的 → D60 差的带宽）。
    #    光靠「自报版本号」不够 —— 报告必须**自己用当前规则重算一遍**并与转印的判词比对：
    #    一致 ⇒ 说明转印可信；不一致 ⇒ 必须明说「以复核为准」。
    #    R1p-o 用**故意过时的转印判词**（`_mk_payload` 里的手写字符串）触发不一致分支。
    check("R1p-o 转印判词与当前规则不一致 ⇒ 必须点出是哪些臂，并声明以复核文本为准",
          "不一致的臂" in tm and "以本节的复核文本为准" in tm,
          "不一致分支已印出" if "不一致的臂" in tm else "缺失（旧判词被当成当前结论了）")
    # R1p-p：把转印判词换成**当前规则真的会生成的**字符串 ⇒ 必须打 ✅ 一致
    import stage9_loop as _L  # noqa: PLC0415  （只为在自测里造出"当前规则"的判词）
    _hp = _mk_payload()
    _fresh_rows = _L.compare_arms(R._norm_histories(_hp["histories"]), _hp["noise"])
    _hp["compare"] = [{**{k: v for k, v in r.items() if k != "verdict"},
                       "verdict": r["verdict"]} for r in _fresh_rows]
    _hp["verdict_logic"] = _L.VERDICT_LOGIC
    tp2 = R.build(_write(Path(td0), _hp, "freshmatch.json"))
    check("R1p-p 转印判词与当前规则逐字一致 ⇒ 必须打 ✅（否则这条复核只会制造噪音）",
          "✅ 与上面**转印**的判词逐字一致" in tp2 and "不一致的臂" not in tp2)
    # R1p-q：复核本身失败时**必须说出来**，不得静默降级（例如 `histories` 被写坏）
    tq = R.build(_write(Path(td0), _mk_payload(histories={"grid": {"best_J": "not-a-number"}}),
                        "badhist.json"))
    check("R1p-q 离线复核失败 ⇒ 必须明说「未经复核」，不得静默跳过",
          "离线复核失败" in tq and "未经复核" in tq)
    # R1p-r：D60 同族第五处 —— 推荐点本身是极值统计量（选择偏差），报告必须点出来，
    #        并给出「种子平均」这条出路；否则读者会把「CRN 单点最小」当成「真的更好」。
    check("R1p-r 必须点出推荐点的选择偏差（*winner's curse*）并给出种子平均的做法",
          "选择偏差" in tm and "_scratch_mean_A_rank.py" in tm)
    # R1p-r2（D62 改）：原先守的是「必须自认**没算过**本 payload 的种子均值」。D62 把正式
    #          `n_fim = 12` 依据件的种子均值算出来了 ⇒ 现在要守的是**两条边界同时在场**：
    #          ① 举例（`n_fim = 1` 那次）不能被当成结论；② **本依据件的实测**必须明确报出来，
    #          并附带「换一份 payload 则必须另算」—— 否则又会退化成「把某一次的均值当通用结论」。
    check("R1p-r2 必须同时给出「本依据件的种子均值实测」（D62）与「换 payload 须另算」的边界",
          "D62 实测" in tm and "换一份 payload 则必须另算" in tm,
          "两条都在" if ("D62 实测" in tm and "换一份 payload 则必须另算" in tm) else "缺失其一")
    # ❗ D61：带宽既然按**差**的噪声带算（D60），就必须拿它量**可行集内部**：若与最优
    #    不可分辨的设计不止一个，那么「推荐点」只是可行带内的一个点 ⇒ 报告必须把
    #    「身份是否唯一」讲出来，否则读者会把 CRN 口径的最小值当成唯一最优。
    _sp = _mk_payload()
    _sp["cache"] = dict(_sp["cache"])
    # `sd_A = 0.010` ⇒ 判据带 `2·√2·sd_A = 0.028284`：C 与最优不可分辨（ΔA = 0.01）、D 显著更差
    _sp["cache"]["C"] = {"name": "C", "A": 0.31, "B": 7.1, "J": 1.1, "feasible": True, "gates": [],
                         "omission": 0.11, "omission_band": [0.05, 0.2], "cond": 1.0e5, "n_bad": 0,
                         "n_fim": 2}
    _sp["cache"]["D"] = {"name": "D", "A": 0.50, "B": 6.9, "J": 1.5, "feasible": True, "gates": [],
                         "omission": 0.12, "omission_band": [0.05, 0.2], "cond": 1.0e5, "n_bad": 0,
                         "n_fim": 2}
    ts_ = R.build(_write(Path(td0), _sp, "spread.json"))
    check("R1p-s 可行集有多个设计时必须报「身份是否唯一」并给出**不可分辨的个数**"
          "（0.30/0.31/0.50、带 0.0283 ⇒ 2 与最优不可分辨）",
          "身份是否唯一" in ts_ and "**2 / 3**" in ts_,
          "已印出 2 / 3" if "**2 / 3**" in ts_ else "缺失或个数不对")
    check("R1p-s2 该段必须明说「不得」写成「唯一最优」，并给出 `n_fim` 一换推荐点就变的实测（D61）",
          "唯一最优" in ts_ and "不得" in ts_ and "两个不同设计" in ts_)
    check("R1p-s3 可行集只有一个设计时不得硬报唯一性（改为印「只有一个」，且不出现不可分辨计数）",
          "可行集只有" in tm and "身份是否唯一" in tm and "2 / 3" not in tm)
    # ❗ R1p-r3：种子平均探针的**配对**口径与循环判据不是同一个口径（探针把所有设计放在同一条
    #    随机流上 ⇒ 正相关 ⇒ 配对 SE 偏小），报告必须把这条差别讲出来，否则读者会把探针的
    #    t 值当成第 5 节的判词。实测 ρ = +0.49…+0.85（`_scratch_pair_corr.py`）。
    check("R1p-r3 必须写明探针「共用随机流」的配对口径 ≠ 循环的 `2·√2·sd` 判据带"
          "（并给出 `cell_seed` 这一差别）",
          "共用同一条随机流" in tm and "cell_seed" in tm and "不可混用" in tm)
    # ❗ R1p-t（D62）：依据件从 `n_fim = 1` 换到正式 `n_fim = 12` 后，报告里两处旧说法**变成了
    #    假话**：① §3 说「须在正式 `n_fim` 下重测这一节」—— D61 已经测了，结论是**结构性**；
    #    ② §8 说「病态比例是本次 `n_fim` 的产物」—— D61 实测两档逐设计相同，正好相反。
    #    守的是：这两句话不得再出现，而「结构性质」这个正确说法必须在场。
    check("R1p-t 不得再声称「须在正式 `n_fim` 下重测这一节」或「病态比例是本次 `n_fim` 的产物」"
          "（D61 已证伪；须改说「结构性质」）",
          "须在正式 `n_fim` 下重测这一节" not in t0
          and "是**本次 `n_fim` 的产物**，不是设计空间的固有属性" not in t0
          and "结构性质" in t0)
    # ❗ R1p-u（D64）：`2·√2·sd` 里的 `√2` 能取常数，前提是**两条臂的 σ 同量级**。上一轮只在
    #    `n_fim = 1` 上验过 3 个设计（1.18 倍）；D64 用同一批 32 种子读数在正式 `n_fim = 12` 上
    #    取了 7 个设计（0.0068–0.0085、1.24 倍）⇒ 报告必须给出这条证据，否则「√2」是个裸假设。
    check("R1p-u 必须给出「同方差在正式 `n_fim` 下也成立」的实测支持"
          "（`n_fim = 12` 的 7 个设计 sd 0.0068–0.0085、1.24 倍；`n_fim = 1` 档 1.18 倍）",
          "同方差" in t0 and "1.24" in t0 and "0.0068" in t0 and "1.18" in t0)

print()
print("=" * 72)
print("R2 `_f` / `_dominates` 单元判据")
print("=" * 72)
check("R2a `_f(inf) == —`", R._f(float("inf")) == "—")
check("R2b `_f(nan) == —`", R._f(float("nan")) == "—")
check("R2c `_f(None) == —`", R._f(None) == "—")
check("R2d `_f(1.23456, 2) == 1.23`", R._f(1.23456, 2) == "1.23")
check("R2e `_dominates` 正例", R._dominates({"A": 0.3, "B": 8.0}, {"A": 0.4, "B": 7.0}))
check("R2f `_dominates` 反例", not R._dominates({"A": 0.4, "B": 7.0}, {"A": 0.3, "B": 8.0}))
check("R2g `_dominates` 相等也算支配（容差内）",
      R._dominates({"A": 0.3, "B": 7.0}, {"A": 0.3, "B": 7.0}))
check("R2h `_dominates` 权衡不算支配",
      not R._dominates({"A": 0.3, "B": 6.0}, {"A": 0.4, "B": 7.0}))
# ❗ 报告必须**可复现**：同一个 payload 无论用相对路径还是绝对路径调用，生成的文件都要逐字相同。
#    否则「交付件 == 现生成结果」（R1l）会因为调用方式不同而红 —— 这正是它第一次跑出来的样子。
_root = _HERE.parents[1]
check("R2i payload 路径渲染必须与调用方式无关（仓库内 ⇒ 相对仓库根的 `posix` 形式）",
      R._canonical(_root / "1_Code/AutoRA_SPE/x.json") == "1_Code/AutoRA_SPE/x.json",
      R._canonical(_root / "1_Code/AutoRA_SPE/x.json"))
# ❗ 两个数值闸门是**两段文本**（`cond=… > 1e+10（病态，相关不可信）` 与 `n_bad=… > 0（有不可识别方向）`）。
#    `n_fim = 1` 的 174 个候选里两者恰好重合 ⇒ 只认 `cond` 那一段也能全绿，漏判看不出来。
#    这条判据专门造一个**只被 `n_bad` 否决**的设计，把漏判钉死。
_comp = R._composition({
    "only_n_bad": {"name": "only_n_bad", "A": 0.5, "B": 5.0, "J": 3.0, "feasible": False,
                   "gates": ["n_bad=1 > 0（有不可识别方向）"], "omission": 0.10,
                   "cond": 1.0e4, "n_bad": 1, "n_fim": 1},
    "ok": {"name": "ok", "A": 0.3, "B": 7.0, "J": 1.0, "feasible": True, "gates": [],
           "omission": 0.10, "cond": 1.0e5, "n_bad": 0, "n_fim": 1},
})
check("R2j 只被 `n_bad > 0`（有不可识别方向）否决的设计，必须算进「数值病态」而不是算成"
      "「只被遗漏率带否决」或「其它闸门」",
      _comp["ill_cond"] == 1 and _comp["band_only"] == 0 and _comp["other"] == 0
      and _comp["feasible"] == 1 and _comp["n"] == 2, str(_comp))
_c2 = R._composition({
    "g": {"name": "g", "A": 0.5, "B": 5.0, "J": 3.0, "feasible": False,
          "gates": ["cond=2.0e+15 > 1e+10（病态，相关不可信）"], "omission": 0.10,
          "cond": 2.0e15, "n_bad": 0, "n_fim": 1}})
check("R2j-2 只被 `cond` 那一段否决的设计仍算「数值病态」（反向对照，防止把上面那条改成"
      "只认 `n_bad`）", _c2["ill_cond"] == 1 and _c2["other"] == 0, str(_c2))

print()
print("=" * 72)
print("R3 合成 payload：作用域不全 ⇒ 必须自我告警")
print("=" * 72)
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    p = _write(tmp, _mk_payload(front_scope={"n_candidates": 174,
                                             "n_cached_before_full_eval": 7,
                                             "n_evaluated": 12, "n_front": 1}), "partial.json")
    t = R.build(p)
    check("R3a 作用域不全 ⇒ 打 ⚠️ 且说明「只覆盖了一部分候选空间」",
          "只覆盖了一部分候选空间" in t)
    check("R3b 作用域不全 ⇒ **不得**打 ✅", "✅ `n_evaluated == n_candidates`" not in t)
    check("R3c `d54` 计数必须标注「不是全空间真值」", "不是全空间真值" in t)
    check("R3d 表格单元里不得出现 inf/nan", not _cell_inf(t))

    print()
    print("=" * 72)
    print("R4 合成 payload：`A_best = inf` 的臂")
    print("=" * 72)
    p2 = _write(tmp, _mk_payload(), "nopt.json")
    t2 = R.build(p2)
    check("R4a 三分支裁决原样带出", "本预算下 (A,B) 上最好。" in t2)
    check("R4b 旧版措辞告警会出现（因为它含 inf）",
          ("inf" in t2) and ("没有可行点" in t2))
    check("R4c 表格单元仍一律 `—`", not _cell_inf(t2),
          f"命中 {_cell_inf(t2)}" if _cell_inf(t2) else "")
    line = [l for l in t2.splitlines() if l.startswith("| `random`")][0]
    check("R4d `inf` 臂的 (A) 单元印 `—`", "—" in line and "inf" not in line, line)

    # 全臂无可行点 ⇒ 不得出现「最好」字样（报告只复述 verdict，这里断言复述不被篡改）
    p3 = _write(tmp, _mk_payload(
        compare=[dict(r, A_best=float("inf"), B_at_A_best=float("nan"), n_feasible=0,
                      verdict="本预算下**没有任何一条臂**在可行集内取到设计 ⇒ **无对照、无排序证据**。")
                 for r in _mk_payload()["compare"]]), "none.json")
    t3 = R.build(p3)
    check("R4e 全臂无可行点 ⇒ 报告须带出「没有任何一条臂」", "没有任何一条臂" in t3)
    check("R4f 全臂无可行点 ⇒ 四臂表(第5节)里不得出现「上最好」",
          not any("上最好" in l for l in t3.splitlines() if l.startswith("| `")))

    check("R4g 同一 payload 两次生成完全相同（确定性）", R.build(p2) == t2)

    print()
    print("=" * 72)
    print("R5 CLI 端到端（写文件 + 退出码）")
    print("=" * 72)
    out = tmp / "out.md"
    r = subprocess.run([sys.executable, str(_HERE / "stage9_report.py"), str(p2), str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("R5a CLI 退出码 0", r.returncode == 0, (r.stderr or "").strip()[-200:])
    check("R5b CLI 写出了文件且内容 == build() 结果",
          out.is_file() and out.read_text(encoding="utf-8") == R.build(p2))
    r2 = subprocess.run([sys.executable, str(_HERE / "stage9_report.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("R5c 无参数 ⇒ 退出码 2 并打印用法", r2.returncode == 2 and "用法" in r2.stdout)

n_bad = sum(1 for _, ok, _ in _RESULTS if not ok)
print()
print("=" * 72)
print(f"共 {len(_RESULTS)} 项判据，未通过 {n_bad} 项。")
for lab, ok, det in _RESULTS:
    if not ok:
        print(f"  ❌ {lab}" + (f" —— {det}" if det else ""))
print("=" * 72)
raise SystemExit(1 if n_bad else 0)
