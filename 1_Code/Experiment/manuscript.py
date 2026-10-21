"""把结果节骨架的同一批块填进论文结果章模板（D101）。

单一来源原则：表格与横幅一律来自 `run_pipeline.build_blocks`，本模块只做
「模板 → 成品」的替换与几处文字化，**不重写任何判据、不另起一套渲染**。
理由见 README §8.70/§8.71：同一张报告里的同一个量，必须由同一个函数产出。

用法（数据目录里已有 `_pipeline/stage6_report.md` 与拟合结果时）：

    python -X utf8 1_Code/Experiment/manuscript.py 2_Data/Real_Data/<目录> [--out ...]

或由 `run_pipeline.py` 作为第 5 步调用（推荐，避免重复读盘）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEMPLATE = ROOT / "5_Reference" / "03_论文写作" / "论文_结果章_模板.md"
MARK_RE = re.compile(r"\{\{([A-Za-z0-9_*]+)\}\}")


def load_template(path: Path | None = None) -> str:
    p = Path(path) if path else TEMPLATE
    if not p.exists():
        raise FileNotFoundError(f"找不到结果章模板：{p}")
    return p.read_text(encoding="utf-8")


def table_under(text: str, heading_prefix: str) -> list[str]:
    """取某个 `## ` 小节里的第一段连续表格行（表格行以 `|` 开头）。"""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(heading_prefix)), None)
    if start is None:
        return []
    out: list[str] = []
    seen = False
    for l in lines[start + 1:]:
        if l.startswith("## "):
            break
        if l.strip().startswith("|"):
            out.append(l)
            seen = True
        elif seen:
            break
    return out


def render(template: str, blocks: dict[str, list[str]]) -> str:
    """把 `{{name}}` 换成对应行块；模板里有而块里没有的占位必须报错（不许静默留空）。"""
    used = MARK_RE.findall(template)
    missing = sorted({m for m in used if m not in blocks})
    if missing:
        raise KeyError(f"模板占位没有对应数据块：{', '.join(missing)}")
    return MARK_RE.sub(lambda m: "\n".join(blocks[m.group(1)]), template)


def synth_banner(data: Path) -> str:
    p = Path(data) / "synth_truth.json"
    if not p.exists():
        return ""
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        meta = {}
    gen = meta.get("generator", "未知生成器")
    n = len(meta.get("sessions") or []) or meta.get("n_sessions", "?")
    return ("> ⚠️ **本文件由合成数据生成**（`synth_truth.json`，生成器 "
            f"`{gen}`，{n} 场）：只用于验证流程是否跑通，"
            "**任何数字都不得写进论文正文**（主计划 D98/D100）。\n")


def write_draft(data: Path, out: Path, rows: list[dict], groups: dict,
                truth: dict | None, health: dict[int, dict] | None = None) -> Path:
    """生成 `<out>/manuscript_draft.md`；返回路径。"""
    import run_pipeline as RP

    blocks = RP.build_blocks(rows, groups, truth, health)
    s6 = Path(out) / "stage6_report.md"
    if s6.exists():
        blocks["s6_table"] = table_under(s6.read_text(encoding="utf-8"), "## 2.")
    else:
        blocks["s6_table"] = ["（本目录没有 `stage6_report.md`：先跑流水线第 2 步）"]

    text = render(load_template(), blocks)

    banner = synth_banner(data)
    if banner:
        lines = text.split("\n")
        idx = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
        lines.insert(idx, banner)
        text = "\n".join(lines)

    p = Path(out) / "manuscript_draft.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def load_truth(data: Path) -> dict | None:
    """从 `<data>/synth_truth.json` 取组真值（只有合成数据才有；真数据返回 None）。"""
    p = Path(data) / "synth_truth.json"
    if not p.exists():
        return None
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    gt = meta.get("group_truth") or {}
    return next(iter(gt.values()), None)


# --------------------------------------------------------------- 模型章（D112）
MODEL_TEMPLATE = ROOT / "5_Reference" / "03_论文写作" / "论文_模型章_模板.md"
PENDING = "【待数据：{}】"
IGNORE_MARKS = {"双花括号"}       # 文档里演示占位符语法的例子，不做替换

# 填不了的原因（写进【待数据：…】里，让读者一眼知道**缺什么、去哪儿补**）
PENDING_WHY = {
    "bic_mt1": "BIC(M-T1)：stage8 JSON 未落盘 BIC，需用 twophase.bic 重算",
    "bic_mt3": "BIC(M-T3)：同上",
    "delta_bic": "ΔBIC：同上",
    "rho_ci": "ρ 的区间：需拟合时落盘 cov 对角，或做剖面似然",
    "se_elpd": "ELPD 的 SE：loo.psis_loo 本次返回 None",
    "beta_T_ci": "β_T 的区间：需组层 SE（stage8 JSON 未落盘）",
    "beta_P": "β_P：组层回归需要 ≥2 个 P 水平（本次数据只有 1 档）",
    "beta_P_ci": "β_P 的区间：只有 1 档 P 或自举样本不足",
}


def load_model_template(path: Path | None = None) -> str:
    p = Path(path) if path else MODEL_TEMPLATE
    if not p.exists():
        raise FileNotFoundError(f"找不到模型章模板：{p}")
    return p.read_text(encoding="utf-8")


def _stage8_dir(data: Path, out: Path) -> Path:
    """stage8 产物目录：`<out>/stage8` → `<data>/stage8` → `<data>/../stage8`。

    第三种是扫描脚本（`scan_min_n.py`）的布局：`<scan>/n<N>/data` 与
    `<scan>/n<N>/stage8` 平级。找不到就返回 `<out>/stage8`，由调用方报错。
    """
    cand = out / "stage8"
    if sorted(cand.glob("stage8_group_*.json")):
        return cand
    for alt in (data / "stage8", data.parent / "stage8"):
        if sorted(alt.glob("stage8_group_*.json")):
            return alt
    return cand


def _param_names():
    """被试层参数名与界（与 `run_pipeline.build_blocks` 同源：`WITHIN_FREE_LIN` + `rho`）。"""
    from mapping import PARAM_BOUNDS, WITHIN_FREE_LIN
    from twophase import MASK_RHO_BOUNDS

    bounds = dict(PARAM_BOUNDS)
    bounds["rho"] = MASK_RHO_BOUNDS
    return list(WITHIN_FREE_LIN) + ["rho"], bounds


def _natural(vec, names, bounds):
    """把 x 空间的一行参数反变换回自然尺度（与 `build_blocks` 用同一个 `_from_x`）。"""
    from likelihood import _from_x
    import numpy as np

    x = np.asarray(vec, dtype=float)
    out = {}
    for j, nm in enumerate(names):
        if j >= x.size:
            break
        lo, hi = bounds[nm]
        out[nm] = float(_from_x(np.array([x[j]]), np.array([lo]), np.array([hi]))[0])
    return out


def subject_points(groups: dict) -> list[dict]:
    """从 stage8 的逐被试众数里取 (P, d_ref, beta_S, beta_T)，供组间回归与组均值用。"""
    names, bounds = _param_names()
    pts: list[dict] = []
    for g in sorted(groups):
        res = (groups[g].get("results") or {}).get("M-T1") or {}
        modes = (res.get("fit") or {}).get("modes") or []
        for row in modes:
            nat = _natural(row, names, bounds)
            if "d_ref" in nat:
                pts.append({"P": float(g), "d_ref": nat["d_ref"],
                            "beta_S": nat.get("beta_S"), "beta_T": nat.get("beta_T")})
    return pts


def group_between(points: list[dict], truth: dict | None, n_boot: int = 200,
                  seed: int = 20261021) -> dict | None:
    """跨 P 组的组间回归（复用 `recover_group.fit_between`，不另写一套）。

    需要 ≥2 个不同 P 水平、且总被试数 ≥ 4；否则返回 None（模板里留【待数据】）。
    """
    import numpy as np
    from recover_group import fit_between

    if len(points) < 4:
        return None
    levels = sorted({p["P"] for p in points})
    if len(levels) < 2:
        return None
    P = np.array([p["P"] for p in points], dtype=float)
    d = np.array([p["d_ref"] for p in points], dtype=float)
    s = np.array([p["beta_S"] if p["beta_S"] is not None else 0.16 for p in points],
                 dtype=float)
    P_ref = float((truth or {}).get("P_ref", max(levels)))
    init = [(truth or {}).get("d_ref", float(np.median(d))),
            (truth or {}).get("beta_P", 0.35),
            (truth or {}).get("beta_S", float(np.median(s))),
            (truth or {}).get("beta_SP", 0.0),
            (truth or {}).get("tau_P", 30.0)]
    fit, _rms, _wrms = fit_between(P, d, s, P_ref, init)
    out = {"beta_P": float(fit["beta_P"]), "tau_P": float(fit["tau_P"]),
           "d_ref": float(fit["d_ref"]), "n_points": len(points),
           "P_levels": levels, "ci": None}
    # 自举区间：按被试重抽样（同一份数据、同一估计量），只做描述用
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(max(0, int(n_boot))):
        idx = rng.integers(0, len(P), len(P))
        try:
            b, _r, _w = fit_between(P[idx], d[idx], s[idx], P_ref, init)
        except (ValueError, RuntimeError):
            continue
        boots.append(float(b["beta_P"]))
    if len(boots) >= 20:
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out["ci"] = (float(lo), float(hi))
        out["n_boot"] = len(boots)
    return out


def model_values(rows: list[dict], groups: dict, truth: dict | None,
                 health: dict | None = None) -> dict[str, str]:
    """模型章里可以用现有产物直接填的占位符（其余一律留【待数据】并写明原因）。"""
    import numpy as np

    health = health or {}
    vals: dict[str, str] = {}
    ns = [int(((groups[g].get("results") or {}).get("M-T1") or {}).get("n_subjects") or 0)
          for g in sorted(groups)]
    n_keep = sum(1 for r in rows if r.get("verdict") == "KEEP")
    total = sum(ns) or n_keep
    vals["n_groups"] = str(len(groups)) if groups else "4"
    vals["n_subjects_total"] = str(total) if total else PENDING.format("样本量")
    if ns and min(ns) != max(ns):
        vals["n_per_group_range"] = f"{min(ns)}–{max(ns)}"
    elif ns:
        vals["n_per_group_range"] = str(ns[0])
    else:
        vals["n_per_group_range"] = PENDING.format("每组人数")

    # 组层参数：M-T1 的 mu / sigma（反变换到自然尺度）
    names, bounds = _param_names()
    mu_rows, sig_rows, rho_rows = [], [], []
    for g in sorted(groups):
        res = (groups[g].get("results") or {}).get("M-T1") or {}
        fit = res.get("fit") or {}
        mu = fit.get("mu") or []
        sg = fit.get("sigma") or []
        if mu:
            nat = _natural(mu, names, bounds)
            mu_rows.append(nat)
            rho_rows.append(f"{nat.get('rho', float('nan')):.3f}")
        if sg:
            sig_rows.append(dict(zip(names, (float(x) for x in sg))))
    if rho_rows:
        vals["rho_hat"] = "、".join(rho_rows) + ("" if len(groups) > 1 else "")
    if sig_rows:
        keys = ["d_ref", "beta_T", "a_ref", "t0"]
        med = {k: float(np.median([s.get(k, float("nan")) for s in sig_rows])) for k in keys}
        vals["sigma_*"] = "、".join(f"sd({k}) = {v:.3f}" for k, v in med.items())

    # LOO 比较
    e1, e3, ds = [], [], []
    for g in sorted(groups):
        res = groups[g].get("results") or {}
        a = (res.get("M-T1") or {}).get("loo") or {}
        b = (res.get("M-T3") or {}).get("loo") or {}
        if a.get("elpd_loo") is not None:
            e1.append(f"{a['elpd_loo']:.1f}")
        if b.get("elpd_loo") is not None:
            e3.append(f"{b['elpd_loo']:.1f}")
        if a.get("elpd_loo") is not None and b.get("elpd_loo") is not None:
            ds.append(a["elpd_loo"] - b["elpd_loo"])
    if e1:
        vals["elpd_mt1"] = "、".join(e1)
        vals["elpd_mt3"] = "、".join(e3)
        # BIC 三项与 ELPD 的 SE 填不了 ⇒ 进 `missed`，原因写进【待数据：…】

    # 被试层关键参数的组均值（组层 β 的读数）
    pts = subject_points(groups) if groups else []
    bt = [p["beta_T"] for p in pts if p.get("beta_T") is not None]
    if bt:
        vals["beta_T"] = f"{float(np.mean(bt)):.3f}"
    if pts:
        gb = group_between(pts, truth, n_boot=int(model_boot()))
        if gb:
            vals["beta_P"] = f"{gb['beta_P']:.3f}"
            if gb.get("ci"):
                vals["beta_P_ci"] = (f"[{gb['ci'][0]:.3f}, {gb['ci'][1]:.3f}]"
                                     f"（按被试自举 B={gb['n_boot']}）")

    # 健康闸门
    if health:
        import stage8_health as H8
        bad = [g for g in sorted(health) if health[g].get("status") == H8.BAD]
        vals["loo_gate"] = ("通过" if not bad else
                            f"未通过（{len(bad)}/{len(health)} 组不可引用）")
        bits = []
        for g in sorted(health):
            h = health[g]
            mt1 = (h.get("modes") or {}).get("M-T1") or {}
            ratio = mt1.get("p_loo_ratio")
            ratio = f"{ratio:.3g}" if isinstance(ratio, (int, float)) else (ratio or "—")
            bits.append(f"组 {g}：{h.get('status')}"
                        f"（`k_max` = {mt1.get('k_max', '—')}、"
                        f"`p_loo`÷`n_obs` = {ratio}、"
                        f"`n_flipped` = {mt1.get('n_flipped', '—')}/{mt1.get('n_eig', '—')}）")
        # 模板把该占位放在表格单元里 ⇒ 必须是一行，不能塞多行表格
        vals["health_table"] = "；".join(bits)
    return vals


def model_boot() -> int:
    """自举次数（环境变量可覆盖，便于自测把 200 降到 20）。"""
    import os
    try:
        return max(0, int(os.environ.get("MANUSCRIPT_BOOT", "200")))
    except ValueError:
        return 200


def render_model(template: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """替换模型章占位符，返回 `(text, missed)`。

    ⚠️ 模板的 §3.11 是**数值总表**（占位符本身就住在表格单元里），所以整篇都要替换。
    唯一不替换的是文档用来演示"占位符长什么样"的那个例子（`IGNORE_MARKS`）。

    未填的占位符**不静默留白**：替换成 `【待数据：<名称>】` 并记进 `missed`，
    与模型章自身的写法一致（真实数据到手后按清单逐项替换）。
    """
    missed: list[str] = []

    def one(m):
        k = m.group(1)
        if k in IGNORE_MARKS:
            return m.group(0)
        if k in values and values[k]:
            return values[k]
        missed.append(k)
        return PENDING.format(PENDING_WHY.get(k, k))

    return MARK_RE.sub(one, template), sorted(set(missed))


def tidy_preamble(text: str) -> str:
    """把模板自带的「用法说明」改成草稿里不会被误当成正文的样子。

    模板开头的 H1 是文件名（`论文_模型章_模板`），正文里应当是章标题；紧跟的
    `> **用法**` 段是给作者看的手册，不是论文内容 ⇒ 换成一行 `> 模板说明`。
    """
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("# ") and "模板" in ln:
            lines[i] = "# 第三章　计算模型（草稿）"
            break
    for i, ln in enumerate(lines):
        if ln.startswith("> **用法**"):
            lines[i] = "> **模板说明（正式稿删去本段）**"
            break
    return "\n".join(lines)


def write_model_draft(data: Path, out: Path, rows: list[dict], groups: dict,
                      truth: dict | None, health: dict | None = None,
                      template: Path | None = None) -> Path:
    """生成 `<out>/manuscript_model_draft.md`；返回路径。"""
    vals = model_values(rows, groups, truth, health)
    text, missed = render_model(load_model_template(template), vals)
    text = tidy_preamble(text)
    L = ["<!-- 由 manuscript.py --model-chapter 生成，请勿手改；改模板而不是改这里 -->", ""]
    if missed:
        L += [f"> ⚠️ 本稿仍有 {len(missed)} 个占位未填："
              + "、".join(f"`{m}`" for m in missed)
              + "（原因见各处的【待数据】标注）。", ""]
    banner = synth_banner(data)
    if banner:
        L += [banner]
    p = Path(out) / "manuscript_model_draft.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + text, encoding="utf-8", newline="\n")
    return p


def main() -> int:
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import intake as INTAKE
    import run_pipeline as RP

    ap = argparse.ArgumentParser(description="把结果章／模型章模板填成草稿（数据须已跑过流水线）")
    ap.add_argument("data")
    ap.add_argument("--out", default=None, help="默认 <数据目录>/_pipeline")
    ap.add_argument("--template", default=None, help="结果章模板")
    ap.add_argument("--model-template", default=None, help="模型章模板")
    ap.add_argument("--only", choices=("results", "model", "both"), default="both")
    args = ap.parse_args()

    data = Path(args.data).resolve()
    out = Path(args.out).resolve() if args.out else data / "_pipeline"
    sessions = INTAKE.find_sessions([data])
    if not sessions:
        print(f"[错误] 没有找到场次：{data}", file=sys.stderr)
        return 2
    rows = [INTAKE.audit_one(s["gid"], s["sid"], s.get("csv"), s.get("txt"),
                             s.get("shadowed")) for s in sessions]
    s8 = _stage8_dir(Path(data), Path(out))
    groups = RP.load_groups(s8) if s8.exists() else {}
    health = RP.assess_health(s8) if s8.exists() else {}
    truth = load_truth(data)
    global TEMPLATE
    if args.template:
        TEMPLATE = Path(args.template).resolve()
    if args.only in ("results", "both"):
        p = write_draft(data, out, rows, groups, truth, health)
        text = p.read_text(encoding="utf-8")
        n_pending = text.count("【待写】")
        print(f"[manuscript] {p}")
        print(f"[manuscript] 行数 {len(text.splitlines())}、表格块 4、待写处 {n_pending}")
    if args.only in ("model", "both"):
        mp = write_model_draft(data, out, rows, groups, truth, health,
                               Path(args.model_template) if args.model_template else None)
        mt = mp.read_text(encoding="utf-8")
        left = [m for m in MARK_RE.findall(mt) if m not in IGNORE_MARKS]
        print(f"[manuscript] {mp}")
        print(f"[manuscript] 行数 {len(mt.splitlines())}、"
              f"待数据处 {mt.count('【待数据：')}、残留占位 {len(left)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
