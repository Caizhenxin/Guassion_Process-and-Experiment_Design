"""把 `Exp_Design_Formal.m`（v4.1，25 列）的输出读成 Stage 8 模型能吃的试次表。

为什么需要这一层
================
实验程序存的是**按键与标签**（`Shape`/`Label`/`CorrectKey`/`Response`），
而 DDM 模型要的是**因子与响应侧**（`is_self`/`is_match`/`side`/`omission`）。
这两套坐标之间的映射**不是显然的**，而且错了不会报错——只会把
"Match/Nonmatch"这个因子悄悄反过来，让整条 Stage 8 的比较建在错的签上。

本模块把这份映射写成代码，并且**用两条互相独立的路径推导同一个量**，
要求它们一致才放行：

1. `CorrectKey == matchKey(subjectID)`   （配对规则 + 被试的匹配键循环）
2. `Shape` 的形状-标签组合               （`getPairingRules` 给出的双射）

映射（完整推导见 `1_Code/DDM_Core/README.md` §8.24）
====================================================
* `is_self`  = (`Label == 'self'`)                     —— 标签就是"问的是谁"
* `matchKey` = `{'f','j','j','f'}[(subjectID - 1) % 4]` —— 程序 `getMatchKey`
* `is_match` = (`CorrectKey == matchKey`)              —— 正确答案是匹配键 = 匹配条件
* `side`     = (`Response   == matchKey`)              —— 被试按了匹配键 = 模型的上边界
* `omission` = (`Response == 'NA'`)
* `rt`       = `RT`（秒；未响应为 NaN）

由此必然有 ``Correct == 1`` ⟺ ``side == is_match``（已响应的试次上），
这就是本模块最强的一条自检。

用法
====
    python read_formal_data.py <数据文件或目录...>        # 打印校验报告
    python read_formal_data.py <文件> --dump 20           # 另打印前 20 行试次表
"""

from __future__ import annotations

import sys
from collections import Counter
import csv
from pathlib import Path

import numpy as np

#: v4.1 的 25 列表头，顺序必须与 `Exp_Design_Formal.m` 的 `fprintf` 一致
HEADER25 = (
    "groupID", "subjectID", "gender", "age", "handedness", "stage", "trialID",
    "P", "T", "W", "Shape", "Label", "CorrectKey", "Response", "RT", "Correct",
    "block", "premature_press", "timeout", "responded_by_deadline",
    "stimulus_onset_actual", "stimulus_offset_actual", "mask_onset_actual",
    "stimulus_dur_actual", "stimulus_frames",
)

#: 程序 `getMatchKey` 的循环模式：`{'f','j','j','f'}`，按 `(subjectID-1) % 4` 取
MATCH_KEYS = ("f", "j", "j", "f")

#: 程序 `getPairingRules`：`Shape → {Label → 正确键}`，按 `subjectID % 4` 取。
#: 用于**第二条独立路径**推导 `is_match`（与 `CorrectKey == matchKey` 交叉验证）。
PAIRING_RULES = (
    {"square": {"self": "f", "stranger": "j"}, "circle": {"self": "j", "stranger": "f"}},
    {"square": {"self": "j", "stranger": "f"}, "circle": {"self": "f", "stranger": "j"}},
    {"square": {"self": "j", "stranger": "f"}, "circle": {"self": "f", "stranger": "j"}},
    {"square": {"self": "f", "stranger": "j"}, "circle": {"self": "j", "stranger": "f"}},
)

#: D4 定稿设计的 T / W 档位（秒）
T_LEVELS = (0.033330, 0.083330, 0.149990, 0.249980)
W_LEVELS = (0.799980, 1.199900, 1.799900)

MISSING = {"", "na", "nan", "n/a"}


def match_key(subject_id: int) -> str:
    """程序 `getMatchKey` 的 Python 版：返回该被试的"匹配键"。"""
    subject_id = int(subject_id)
    if subject_id <= 0:
        raise ValueError(f"subjectID 必须是正整数，收到 {subject_id}")
    return MATCH_KEYS[(subject_id - 1) % 4]


def pairing_rule(subject_id: int) -> dict:
    """程序 `getPairingRules` 的 Python 版：返回 `Shape → {Label → 正确键}`。"""
    return PAIRING_RULES[int(subject_id) % 4]


def _f(v: str) -> float:
    """把 MATLAB 写出的数值列转成 float；`NA`/空 ⇒ NaN。"""
    s = v.strip()
    if s.lower() in MISSING:
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _s(v: str) -> str:
    """字符串列：`NA`/空 ⇒ 空串（调用方按空串判未响应）。"""
    s = v.strip()
    return "" if s.lower() in MISSING else s


def _sniff_delimiter(header_line: str) -> str:
    """按首行嗅探分隔符：有制表符 ⇒ txt（逐试次 `fopen` 写出的通道）；
    否则若含逗号 ⇒ `,`（`cell2table` 快照 CSV，用 `csv.reader` 以正确处理引号）。
    """
    if "\t" in header_line:
        return "\t"
    if "," in header_line:
        return ","
    return "\t"


def _split_line(line: str, delim: str) -> list[str]:
    if delim == ",":
        return next(csv.reader([line]))
    return line.split(delim)


def read_rows(path: str | Path) -> tuple[list[dict], str]:
    """读一个数据文件，返回（行 dict 列表、表头来源说明）。

    ⚠️ 必须用 `utf-8-sig`：MATLAB 写出的文件带 UTF-8 BOM，用 `utf-8` 读会让
    第一列名变成 `"\\ufeffgroupID"`，于是**所有列都认不出来**——而如果只按
    位置取值，576 个试次会静默变成 0 行。这个坑在 `analyze_pilot.py` 里真实发生过。
    """
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], "空文件"
    delim = _sniff_delimiter(lines[0])
    head = [h.strip() for h in _split_line(lines[0], delim)]
    n_col = len(head)
    where = "表头匹配 25 列" if tuple(head) == HEADER25 else f"表头 {n_col} 列（非 v4.1）"
    rows = []
    for ln in lines[1:]:
        parts = _split_line(ln, delim)
        if len(parts) != n_col:
            continue
        rows.append(dict(zip(head, parts)))
    return rows, where


def load_file(path: str | Path, stage: str = "formal") -> tuple[dict, dict]:
    """读一个被试文件，返回（原始观测数组、报告 dict）。

    Parameters
    ----------
    stage : str
        只保留该阶段的试次（默认 `"formal"`；练习段的 `P`/试次数都不同，混进来会
        污染单元计数与 `P` 一致性检查）。
    """
    rows, where = read_rows(path)
    rep: dict = {"path": str(path), "header": where, "n_raw": len(rows)}
    if not rows:
        rep["error"] = "没有解析出任何数据行"
        return {}, rep

    keep = [r for r in rows if _s(r.get("stage", "")) == stage]
    rep["n_stage"] = len(keep)
    rep["stages_present"] = sorted({_s(r.get("stage", "")) for r in rows})
    if not keep:
        rep["error"] = f"没有 stage == {stage!r} 的试次"
        return {}, rep

    subs = sorted({int(_f(r["subjectID"])) for r in keep})
    groups = sorted({int(_f(r["groupID"])) for r in keep})
    rep["subjects"] = subs
    rep["groups"] = groups

    rec = {
        "subjectID": int(_f(keep[0]["subjectID"])),
        "groupID": int(_f(keep[0]["groupID"])),
        # 这一行是整份表的关键：匹配键由被试号决定，不是由数据内容决定
        "matchKey": match_key(int(_f(keep[0]["subjectID"]))),
        "P": np.array([_f(r["P"]) for r in keep]),
        "T": np.array([_f(r["T"]) for r in keep]),
        "W": np.array([_f(r["W"]) for r in keep]),
        "Shape": np.array([_s(r["Shape"]) for r in keep], dtype=object),
        "Label": np.array([_s(r["Label"]) for r in keep], dtype=object),
        "CorrectKey": np.array([_s(r["CorrectKey"]) for r in keep], dtype=object),
        "Response": np.array([_s(r["Response"]) for r in keep], dtype=object),
        "RT": np.array([_f(r["RT"]) for r in keep]),
        "Correct": np.array([_f(r["Correct"]) for r in keep]),
        "block": np.array([_f(r["block"]) for r in keep]),
        "premature_press": np.array([_f(r["premature_press"]) for r in keep]),
        "timeout": np.array([_f(r["timeout"]) for r in keep]),
        "responded_by_deadline": np.array([_f(r["responded_by_deadline"]) for r in keep]),
        "stimulus_dur_actual": np.array([_f(r["stimulus_dur_actual"]) for r in keep]),
    }
    return rec, rep


def to_trials(rec: dict) -> dict:
    """把观测数组转成 Stage 8 模型需要的试次表。

    返回的 dict 键与 `simulate.build_design` + `simulate.simulate_subject`
    合并后的结果**同构**（`P/T/W/is_self/is_match` + `rt/side/omission`），
    因此可以直接喂给 `likelihood.log_likelihood` 与 `hier.ddm_subject`。
    """
    mk = rec["matchKey"]
    responded = rec["Response"] != ""
    label = rec["Label"]
    # 路径一：配对规则（程序数据里的 CorrectKey）——匹配键就是"匹配"的正确答案
    is_match = (rec["CorrectKey"] == mk).astype(int)
    # ⚠️ dtype 与逐列定义刻意对齐 `likelihood.trials_from_arrays`：
    #    omission 是 int（不是 float）、side 是 int(1=上=Match/0=下)。
    #    自测 `exp_Check/check_read_formal_data.py` 会逐键逐 dtype 断言两者相等，
    #    任何一侧改了定义，这里就会响。
    return {
        "P": rec["P"],
        "T": rec["T"],
        "W": rec["W"],
        "is_self": (label == "self").astype(float),
        "is_match": is_match,
        "rt": np.where(responded, rec["RT"], np.nan),
        "side": (rec["Response"] == mk).astype(int),
        "omission": (~responded).astype(int),
    }


#: 预期性反应的先验下限（秒）。低于它的**已响应**试次按"抢按"剔除，不进似然。
#:
#: 为什么不是可选项
#: ----------------
#: `1_Code/DDM_Core/likelihood.py` 的 `per_trial_loglik` 里有一句
#: ``t = tr["rt"][responded] - t0`` 紧跟 ``if np.any(t <= 0): return None``。
#: 也就是说**一条** `rt ≤ t0` 的已响应试次，会让该被试**整份**对数似然变成
#: `None`（`log_likelihood` 于是返回 `-inf`），拟合直接崩掉或者被优化器
#: 用"把 t0 压到数据最小值以下"的方式绕过 —— 那等于让一条抢按决定
#: 非决策时间的估计。所以必须**先验地**把这类试次摆到明面上。
#:
#: 为什么取 0.15
#: -------------
#: 设计本身就把 `RT < 0.15 s` 当作预期性反应（合成数据生成器
#: `1_Code/DDM_Core/_scratch/make_fake_pilot.py` 的 `--rt-lt-t` 就是按它造的），
#: 而模型的 `t0` 真值在 0.2 s 附近 —— 两者方向一致，0.15 是保守（少剔）的一侧。
RT_FLOOR = 0.15


def fit_ready(tr: dict, rt_floor: float = RT_FLOOR) -> tuple[dict, dict]:
    """剔除"抢按"试次，返回 ``(可进似然的试次表, 剔除报告)``。

    只动**已响应且 `rt < rt_floor`** 的试次；未响应试次原样保留
    （它们走 `survival_series`，不受 `t = rt − t0` 那条约束）。
    """
    rt = np.asarray(tr["rt"], dtype=float)
    responded = ~np.asarray(tr["omission"], dtype=bool)
    keep = ~(responded & (rt < rt_floor))
    if keep.size != rt.size:
        raise ValueError("tr 各列长度不一致")
    out = {}
    for k, v in tr.items():
        a = np.asarray(v)
        out[k] = a[keep] if a.size == keep.size else v
    n_resp = int(responded.sum())
    by_t = []
    for t in np.unique(np.round(np.asarray(tr["T"], dtype=float), 5)):
        sel_t = np.round(np.asarray(tr["T"], dtype=float), 5) == t
        by_t.append({
            "T": float(t),
            "n_kept": int(np.sum(sel_t & keep)),
            "n_dropped": int(np.sum(sel_t & responded & (rt < rt_floor))),
        })
    rep = {
        "n_total": int(keep.size),
        "n_responded": n_resp,
        "n_dropped": int((~keep).sum()),
        "n_kept": int(keep.sum()),
        "rt_floor": float(rt_floor),
        "pct_of_responded": (100.0 * float((~keep).sum()) / n_resp) if n_resp else 0.0,
        "min_rt_kept": float(np.min(rt[keep & responded])) if np.any(keep & responded) else float("nan"),
        "by_T": by_t,
    }
    return out, rep


def format_fit_ready(rep: dict) -> str:
    """把 `fit_ready` 的报告压成一行。"""
    bt = "、".join(f"{b['T'] * 1000:.0f}ms {b['n_dropped']}" for b in rep["by_T"])
    return (f"拟合前剔除抢按（rt < {rep['rt_floor'] * 1000:.0f} ms）："
            f"{rep['n_dropped']}/{rep['n_responded']} = "
            f"{rep['pct_of_responded']:.1f}%（按 T 分档 " + bt + "）；"
            f"保留 {rep['n_kept']}/{rep['n_total']} 试次、"
            f"保留试次的最小 RT = {rep['min_rt_kept'] * 1000:.1f} ms")


#: `t0` 距"保留试次最小 RT"的安全余量（秒）。依据见 `t0_upper_bound`。
#:
#: ⚠️ 2026-10-14 起这条余量的**依据换了**：以前它防的是 `wfpt.flux` 的相消地板，
#: 那条已由 `flux` 的镜像级数分支修掉；现在只剩**表示范围**（下溢）一条要求。
T0_SAFE_MARGIN = 0.02
#: 库内 `PARAM_BOUNDS["t0"]` 的上界；这里只作为没有已响应试次时的回退，
#: 刻意不 import `mapping` 以保持本模块零依赖。
_T0_UPPER_LIB = 0.60
_T0_LOWER = 0.05


def t0_upper_bound(tr: dict, margin: float = T0_SAFE_MARGIN) -> float:
    """拟合时 `t0` 的可用上界 = 保留试次的最小 RT − `margin`。

    ❗ 为什么不能只写 `t0 < min(RT)`
    --------------------------------
    `1_Code/DDM_Core/likelihood.py` 的 `per_trial_loglik` 有两道会把**整份**
    数据判成 `None`（`log_likelihood` 于是 −inf）的闸门：

    1. ``t = tr["rt"][responded] - t0`` 后紧跟 ``if np.any(t <= 0): return None``；
    2. ``if not np.all(np.isfinite(f)) or np.any(f <= 0): return None``。

    **闸门 1 是硬的**：``t0 < min(RT)`` 必须严格成立，故 ``margin > 0`` 不可省。

    闸门 2 现在只剩**下溢**一种触发方式。2026-10-14 之前它还有第二种、也是当时
    真正绑定的触发方式：`1_Code/DDM_Core/wfpt.py` 的 `flux` 只有正弦级数一条
    分支，``t`` 小时真值落进相消地板（实测符号随机的 −7.77e−14 / +6.01e−16 /
    −8.23e−15），于是 ``t0 = min(RT) = 0.2370`` 与 ``min(RT) − 0.005 = 0.2320``
    都把整份数据判成 ``None``（`_scratch/_probe_t0_wall.py`、
    `_scratch/_probe_t0_wall2.py`）。**那一类已经修掉**：`flux` 现在按 ``t`` 在
    正弦级数与**镜像级数**之间派发，镜像级数在 ``t → 0`` 时给出正确的（极小的）
    正数 —— `_scratch/check_flux_smallt.py` 的 V3 与闭式吸收概率差 1.3e−15、
    V4 数值积分差 8.8e−16、**V5 测出旧实现在小 ``t`` 侧最差偏 2.2e+34 倍**。

    于是 0.02 s 现在只需覆盖**表示范围**：镜像级数的首个非零项是
    ``d_min·exp(−d_min²/(2t))``，当 ``d_min²/(2t) > 745``（≈ −log 最小次正规数）
    时整条级数下溢为 0，闸门 2 随之触发。阈值 ``t ≈ d_min²/1490``，而
    `1_Code/DDM_Core/mapping.py` 的 ``PARAM_BOUNDS["a_ref"] = (0.30, 5.0)``
    ⇒ ``d_min ≤ a ≲ 5`` ⇒ ``t ≳ 0.017``。取 0.02 即覆盖。

    ⚠️ 但上面的推理**不是**这个数字的担保 —— 担保是拟合时的一道**实测守卫**：
    `1_Code/Experiment/exp_Check/check_read_formal_data.py` 的 A13 拿被试真实的
    数据取 ``t0 = t0_bounds(...)`` 的上界，逐条断言密度有限且为正。凡是参数范围
    越过 0.02 的被试，守卫会报出来，而不是静默地把似然变成 −inf。

    **必须把它写进 bounds**：否则优化器（以及它后面的 `numerical_hessian` /
    `opg_information`）会在一段不连续的面上上下坡。
    """
    rt = np.asarray(tr["rt"], dtype=float)
    responded = ~np.asarray(tr["omission"], dtype=bool)
    if not np.any(responded):
        return _T0_UPPER_LIB
    return float(np.nanmin(rt[responded])) - margin


def t0_bounds(tr: dict, margin: float = T0_SAFE_MARGIN,
              lo: float = _T0_LOWER) -> dict:
    """给出可直接传给 `bounds_override=` 的 ``{"t0": (lo, hi)}``。"""
    hi = min(t0_upper_bound(tr, margin), _T0_UPPER_LIB)
    if hi <= lo:
        raise ValueError(
            f"最小 RT 太低（t0 上界 {hi:.4f} ≤ 下界 {lo:.4f}）："
            f"该被试没有留下可用的已响应试次，不应进入拟合")
    return {"t0": (lo, hi)}


def validate(rec: dict, tr: dict) -> list[str]:
    """对 (观测数组, 试次表) 做一致性与完整性检查，返回"问题"清单（空 = 通过）。"""
    bad: list[str] = []
    n = tr["rt"].size
    if n == 0:
        return ["试次数为 0"]

    # ① 未响应的三列必须同时缺，且 RT 与 omission 不能自相矛盾
    responded = rec["Response"] != ""
    if not np.array_equal(responded, np.isfinite(rec["RT"])):
        k = int(np.sum(responded != np.isfinite(rec["RT"])))
        bad.append(f"`Response` 是否缺 与 `RT` 是否有值 不一致：{k} 行")
    if not np.array_equal(np.isfinite(rec["Correct"]), responded):
        k = int(np.sum(np.isfinite(rec["Correct"]) != responded))
        bad.append(f"`Correct` 是否有值 与 `Response` 是否缺 不一致：{k} 行")
    if not np.array_equal(np.asarray(tr["omission"], dtype=bool), ~responded):
        bad.append("`omission` 与 `Response == 'NA'` 不一致")
    if np.nansum(tr["rt"][~responded]) != 0:
        bad.append("未响应试次的 rt 不是 NaN")

    # ② 匹配键：两条独立路径必须给出同一个 is_match
    rule = pairing_rule(rec["subjectID"])
    is_match_b = np.array(
        [rule.get(sh, {}).get(lb, "?") == rec["matchKey"] for sh, lb in
         zip(rec["Shape"], rec["Label"])], dtype=int)
    if not np.array_equal(is_match_b, tr["is_match"]):
        k = int(np.sum(is_match_b != tr["is_match"]))
        bad.append(
            f"`is_match` 的两条推导路径不一致：{k} 行（"
            f"路径一 `CorrectKey==matchKey`、路径二 `getPairingRules`）——"
            f"被试 {rec['subjectID']} 的配对规则可能与本模块不一致")

    # ③ 程序记的 Correct 必须等于 (side == is_match)
    exp_correct = np.where(responded,
                           (tr["side"] == tr["is_match"]).astype(float), np.nan)
    diff = np.nansum(np.abs(np.nan_to_num(exp_correct) - np.nan_to_num(rec["Correct"])))
    if diff > 0:
        k = int(np.sum(np.nan_to_num(exp_correct) != np.nan_to_num(rec["Correct"])))
        bad.append(f"`Correct` 与 `side == is_match` 不一致：{k} 行（满映射推导有误）")

    # ④ 因子结构：设计 = 3 block（每 block 一个 W）× 4 T × 4 类 × 12 次 = 576
    #    ⇒ (T,W) 每格 48 次、(T,W,Self,Match) 每格 12 次、(Self,Match) 每格 144 次。
    #    ⚠️ 别把 (T,W) 的 48 当成最细格——W 是按 block 变的，(T,W) 之下还有 4 类。
    t_u = np.unique(np.round(tr["T"], 5))
    w_u = np.unique(np.round(tr["W"], 5))
    if t_u.size != 4:
        bad.append(f"T 只出现 {t_u.size} 档（设计 4 档）：{list(t_u)}")
    if w_u.size != 3:
        bad.append(f"W 只出现 {w_u.size} 档（设计 3 档）：{list(w_u)}")
    t_r = np.round(tr["T"], 5)
    w_r = np.round(tr["W"], 5)
    c4 = Counter(zip(t_r.tolist(), w_r.tolist(),
                     tr["is_self"].astype(int).tolist(),
                     tr["is_match"].astype(int).tolist()))
    n_cell4 = max(1, t_u.size * w_u.size * 2 * 2)
    want4 = n / n_cell4
    off = {k: v for k, v in c4.items() if v != want4}
    if off:
        k0 = min(off, key=lambda k: off[k])
        bad.append(
            f"(T,W,Self,Match) 单元计数不等：{len(c4)}/{n_cell4} 个单元出现，"
            f"应各 {want4:g} 次，但 {len(off)} 个不符"
            f"（最偏：T={k0[0] * 1000:.1f}ms W={k0[1] * 1000:.1f}ms "
            f"Self={k0[2]} Match={k0[3]} 有 {off[k0]} 次）")
    c2 = Counter(zip(t_r.tolist(), w_r.tolist()))
    want2 = n / max(1, t_u.size * w_u.size)
    off2 = {k: v for k, v in c2.items() if v != want2}
    if off2:
        k0 = min(off2, key=lambda k: off2[k])
        bad.append(
            f"(T,W) 单元计数不等：{len(c2)}/{t_u.size * w_u.size} 个单元出现，"
            f"应各 {want2:g} 次，但 {len(off2)} 个不符"
            f"（最偏：T={k0[0] * 1000:.1f}ms W={k0[1] * 1000:.1f}ms 有 {off2[k0]} 次）")

    # ⑤ 被试内一致性
    if np.unique(tr["P"]).size != 1:
        bad.append(f"`P` 在被试内不唯一：{sorted(set(tr['P'].tolist()))}")

    # ⑥ 技术列（Stage 1 的成果）：刺激在 T 结束，**但刺激期内按键会把它提前**
    #    —— 用户 2026 年方案变更：允许被试在刺激呈现期内反应并直接进入下一试次，
    #    程序把 `stimulus_dur_actual` 截到「按键后的下一帧」。
    #    ⚠️ 因此 `|dur − T| < 1 帧` 是错的判据：它会把正常的提前截断误判成缺陷。
    if "stimulus_dur_actual" in rec and np.size(rec["stimulus_dur_actual"]) == n:
        dur = np.asarray(rec["stimulus_dur_actual"], dtype=float)
        frame = 1.0 / 60.0
        early = (responded & np.isfinite(tr["rt"]) & (tr["rt"] < tr["T"]))
        over = dur > tr["T"] + frame + 1e-9
        if np.any(over):
            bad.append(f"`stimulus_dur_actual` 超过 T + 1 帧：{int(np.sum(over))} 行")
        late = ~early & (np.abs(dur - tr["T"]) >= frame + 1e-9)
        if np.any(late):
            bad.append(
                f"未在刺激期内按键、但 |stimulus_dur_actual − T| ≥ 1 帧："
                f"{int(np.sum(late))} 行")
        exp_early = np.minimum(tr["T"],
                               (np.floor(tr["rt"] / frame) + 1.0) * frame)
        wrong_early = early & (np.abs(dur - exp_early) >= frame + 1e-9)
        if np.any(wrong_early):
            bad.append(
                f"刺激期内按键、但 stimulus_dur_actual 不等于「按键后下一帧」："
                f"{int(np.sum(wrong_early))} 行")
    return bad


def describe(rec: dict, tr: dict, rep: dict) -> str:
    """把一次加载压成人类可读的报告行。"""
    n = tr["rt"].size
    resp = rec["Response"] != ""
    cells = {}
    for s in (0.0, 1.0):
        for m in (0, 1):
            sel = (tr["is_self"] == s) & (tr["is_match"] == m)
            name = f"{'Self' if s else 'Other'}-{'Match' if m else 'Nonmatch'}"
            cells[name] = (int(sel.sum()), float(np.mean(tr["omission"][sel])) if sel.any() else float("nan"))
    out = [f"被试 {rec['subjectID']}（组 {rec['groupID']}）：{n} 试次、"
           f"matchKey = '{rec['matchKey']}'、P = {int(tr['P'][0])}、"
           f"未响应 {float(np.mean(tr['omission'])) * 100:.1f}%"]
    out.append("    单元 n / 未响应率：" + " ｜ ".join(
        f"{k} {v[0]}/{v[1] * 100:.0f}%" for k, v in cells.items()))
    out.append(f"    RT 中位数（已响应） = {np.nanmedian(tr['rt']) * 1000:.0f} ms、"
               f"RT<T 比例 = {float(np.mean(tr['rt'][resp] < tr['T'][resp])) * 100:.1f}%")
    if any(tr["rt"][resp] < tr["T"][resp]):
        n_early = int(np.sum(tr["rt"][resp] < tr["T"][resp]))
        by_t = []
        for t in np.unique(np.round(tr["T"], 5)):
            sel = resp & (np.round(tr["T"], 5) == t)
            if sel.any():
                by_t.append(f"{t * 1000:.0f}ms {int(np.sum(tr['rt'][sel] < t))}"
                            f"/{int(sel.sum())}")
        out.append(f"    刺激期内按键（会被提前截断）：{n_early}/{int(resp.sum())}"
                   f" 次；按 T 分档 " + "、".join(by_t))
    # 拟合前必须剔除的抢按：这一步不进 `validate`（它是预期的、不是缺陷），
    # 但必须在报告里露出来，否则"算不出似然"会在 Stage 8 里以谜题的形式出现。
    _, rep_fit = fit_ready(tr)
    out.append("    " + format_fit_ready(rep_fit))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in argv[1:] if not a.startswith("--")]
    dump = 0
    for a in argv[1:]:
        if a.startswith("--dump"):
            dump = int(a.split("=", 1)[1]) if "=" in a else 20
    if not args:
        root = Path(__file__).resolve().parent
        files = sorted(root.glob("exp_group*_subject*.txt"))
    else:
        files = []
        for a in args:
            p = Path(a)
            files.extend(sorted(p.glob("exp_group*_subject*.txt")) if p.is_dir() else [p])
    if not files:
        print("❌ 没有找到 exp_group*_subject*.txt")
        return 1

    n_fail = 0
    for f in files:
        rec, rep = load_file(f)
        print("=" * 72)
        print(f"{f.name}：{rep.get('header')}、原始 {rep['n_raw']} 行、"
              f"{rep.get('stages_present')} 段"
              + (f"、取 {rep['n_stage']} 试次" if "n_stage" in rep else ""))
        if not rec:
            print(f"  ❌ {rep.get('error')}")
            n_fail += 1
            continue
        tr = to_trials(rec)
        print(describe(rec, tr, rep))
        bad = validate(rec, tr)
        if bad:
            n_fail += 1
            for b in bad:
                print(f"  ❌ {b}")
        else:
            print("  ✅ 全部一致性判据通过")
        if dump:
            print("    试次表预览：")
            for i in range(min(dump, tr["rt"].size)):
                print(f"      {i:>4}  T={tr['T'][i]:.5f} W={tr['W'][i]:.3f} "
                      f"self={int(tr['is_self'][i])} match={tr['is_match'][i]} "
                      f"side={tr['side'][i]} rt={tr['rt'][i]:.4f} "
                      f"om={int(tr['omission'][i])}")
    print("=" * 72)
    if n_fail:
        print(f"❌ {n_fail}/{len(files)} 个文件未通过")
        return 1
    print(f"✅ {len(files)} 个文件全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
