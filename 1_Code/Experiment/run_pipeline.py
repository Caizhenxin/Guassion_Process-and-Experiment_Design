# -*- coding: utf-8 -*-
"""一键跑完整条分析流水线：入库判定 → Pilot 达标 → 层级拟合 → 图 → 结果节骨架。

用法
====
    python -X utf8 run_pipeline.py <数据目录> [--out <输出目录>] \
        [--profile quick|formal] [--expect-n 8] [--skip-stage8] [--resume]

`<数据目录>` 里放 `EXP_data_group<组>_<编号>.csv` + `exp_group<组>_subject<编号>.txt`
（真数据、合成数据都行；合成数据请自带 `synth_truth.json`）。

四个步骤各写一份产物到 `--out`（默认 `<数据目录>/_pipeline`）：

1. `intake_report.md` —— 每一场能不能计入 N（技术层 / 结构层 / 一致层）
2. `stage6_report.md` —— 计入的场次合起来是否达到 Pilot 判据（S6-1…S6-6）
3. `stage8/stage8_group_*.json` + `stage8.log` —— 层级 DDM 拟合与 PSIS-LOO
4. `figures/`（三张图 + `figures_index.md`）

最后写 `pipeline_report.md`（四步的耗时与退出码）与 `results_skeleton.md`
（**结果节骨架**：表格与统计量已由数据填好，论述留 `【待写】` 槽位）。

设计约束
========
* **不复制任何判据**：入库调用 `intake.audit_one`、达标调用 `stage6_report.build`、
  拟合调用 `stage8_run.py`、图调用 `make_figures.py` —— 全部是既有工具，
  本脚本只做编排与汇总（教训见 `2026-10-18_聚合键后写覆盖导致判定器静默挑错文件.md`）。
* 每一步失败**不静默**：写进 `pipeline_report.md` 并以非零码退出，但已完成的
  步骤产物保留（断点续跑用 `--resume`）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import intake as INTAKE                     # noqa: E402
import stage6_report as S6                  # noqa: E402
import stage8_health as H8                  # noqa: E402  # LOO 闸门（D73/D74/D75），不重写判据

PROFILES = {
    # 流程验证用：1 小时量级；**数值不作结论**
    "quick": {"n_em": 3, "n_draws": 12, "n_x": 21, "n_ppc": 1},
    # 正式采集用（Stage8 方案 §5 的配置）；8 人 × 561 试次上 --plan-only 估 4.30 h
    "formal": {"n_em": 12, "n_draws": 50, "n_x": 81, "n_ppc": 10},
}

# 组层可引用的**经验**起始人数（D100）。实测：n=1 人/组时把 `n_em` 提到 6、`n_draws` 提到 25
# 仍然是 `n_flipped` 2/16、`p_loo`÷`n_obs` 5.12、`k_max` 1.213、`max|θ|` 100.8 ⇒ ⛔；
# n=2 人/组（quick，四组）4/4 全红。⇒ 红的原因是**组层样本量**，不是抽样配置。
MIN_N_HIER = 10


def _run(cmd: list[str], log: Path) -> tuple[int, float]:
    t0 = time.time()
    with log.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("$ " + " ".join(cmd) + "\n\n")
        fh.flush()
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                              cwd=str(ROOT))
    return proc.returncode, time.time() - t0


def step_intake(data: Path, out: Path) -> tuple[bool, list[dict], Path]:
    sessions = INTAKE.find_sessions([data])
    rows = []
    for s in sessions:
        rows.append(INTAKE.audit_one(s["gid"], s["sid"], s["csv"], s["txt"],
                                     s.get("shadowed")))
    keep = [r for r in rows if r["verdict"] == "KEEP"]

    L = ["# 入库判定（intake）", "", f"- 数据目录：`{data}`", f"- 场次：{len(rows)}"
         f"（计入 KEEP = **{len(keep)}**）", "", "| 组 | 编号 | 判定 | 正式/练习 | 去重 | 正确率 | timeout | 说明 |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rec = r.get("rec") or {}
        note = "；".join(r.get("reasons") or []) or "—"
        L.append(f"| {r['gid']} | {r['sid']} | {r['verdict']} | "
                 f"{rec.get('n_formal', '?')}/{rec.get('n_practice', '?')} | "
                 f"{rec.get('n_dropped', 0)} | {rec.get('acc_mean', float('nan')):.3f} | "
                 f"{rec.get('timeout_prop', float('nan')):.1%} | {note} |")
    p = out / "intake_report.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    return len(rows) > 0, rows, p


def step_stage6(data: Path, out: Path, expect_n: int | None) -> tuple[bool, Path]:
    sessions = S6.collect(data)
    counts = S6.tally(sessions)
    md, ok = S6.build(sessions, counts, expect_n)
    p = out / "stage6_report.md"
    p.write_text(md + "\n", encoding="utf-8", newline="\n")
    return ok, p


def step_stage8(data: Path, out: Path, profile: str, resume: bool) -> tuple[bool, Path, dict]:
    cfg = PROFILES[profile]
    s8 = out / "stage8"
    cmd = [sys.executable, "-X", "utf8", "-u", str(ROOT / "1_Code" / "DDM_Core" / "stage8_run.py"),
           "--data", str(data), "--out", str(s8),
           "--n-em", str(cfg["n_em"]), "--n-draws", str(cfg["n_draws"]),
           "--n-x", str(cfg["n_x"]), "--n-ppc", str(cfg["n_ppc"]),
           "--hyper-method", "analytic", "--loo-level", "trial"]
    if resume:
        cmd.append("--resume")
    log = out / "stage8.log"
    code, secs = _run(cmd, log)
    return code == 0, log, {"returncode": code, "seconds": secs, "profile": profile, **cfg}


def step_figures(data: Path, out: Path, s8: Path | None = None) -> tuple[bool, Path, dict]:
    s8 = s8 or (out / "stage8")
    truth = None
    for cand in (data / "synth_truth.json", data / "_synth_truth.json"):
        if cand.is_file():
            truth = cand
            break
    cmd = [sys.executable, "-X", "utf8", "-u", str(HERE / "make_figures.py"),
           str(s8), "--data", str(data), "--out", str(out / "figures")]
    if truth:
        cmd += ["--truth", str(truth)]
    log = out / "figures.log"
    code, secs = _run(cmd, log)
    return code == 0, out / "figures" / "figures_index.md", {"returncode": code,
                                                            "seconds": secs,
                                                            "truth": str(truth) if truth else None}


def resolve_stage8(out: Path, data: Path) -> Path:
    """stage8 产物目录：优先 `<out>/stage8`，回退到 `<data>/stage8`。

    扫描脚本（`scan_min_n.py`）把产物写在 `<scan>/n<N>/stage8` 下，数据在同层
    `data/`；若只认 `<out>/stage8`，`--reuse-stage8` 会误判「没有可复用 JSON」
    而重跑 2.5 h 的拟合（2026-10-21 实跑踩过）。这里与 `manuscript.py` 保持同一
    口径，回退时也先确认目录里真有 `stage8_group_*.json`。
    """
    cand = out / "stage8"
    if sorted(cand.glob("stage8_group_*.json")):
        return cand
    for alt in (data / "stage8", data.parent / "stage8"):
        if sorted(alt.glob("stage8_group_*.json")):
            print(f"[info] stage8 产物回退到：{alt}")
            return alt
    return cand


def load_groups(s8: Path) -> dict[int, dict]:
    out = {}
    for p in sorted(s8.glob("stage8_group_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[int(d.get("tag", p.stem.split("_")[-1]))] = d
    return out


def PAIRED_SE(a: dict, b: dict) -> float:
    """Δelpd 的配对标准误（PSIS-LOO 的 `se_diff` 口径）。

    两个模型在同一批观测上做 LOO，逐观测贡献 `elpd_i` 之差才是正确口径：
    `SE = √n · sd(elpd_i^A − elpd_i^B)`。把两个 SE 平方相加等于把同一批
    数据的共同变异算了两遍，实测会放大一个量级以上。
    """
    import numpy as np

    ea, eb = a.get("elpd_i"), b.get("elpd_i")
    if ea is None or eb is None or len(ea) != len(eb) or not ea:
        return float("nan")
    d = np.asarray(ea, dtype=float) - np.asarray(eb, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 2:
        return float("nan")
    return float(np.sqrt(d.size) * np.std(d, ddof=1))


def assess_health(s8dir: Path) -> dict[int, dict]:
    """对每个 `stage8_group_<组>.json` 复用 `stage8_health.assess_group` 取判词。

    判据（D73/D74/D75）只写在 `stage8_health.py` 一处；这里不重写，
    否则会重演「同一动作被复制成多个工具、各带一半判据」的老毛病（D94）。
    """
    health: dict[int, dict] = {}
    for p in sorted(s8dir.glob("stage8_group_*.json")):
        try:
            gid = int(p.stem.rsplit("_", 1)[-1])
        except ValueError:
            continue
        try:
            health[gid] = H8.assess_group(p)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"[warn] {p.name} 判词失败：{exc}", file=sys.stderr)
    return health


def build_blocks(rows: list[dict], groups: dict, truth: dict | None,
                 health: dict[int, dict] | None = None) -> dict[str, list[str]]:
    """表与横幅的**唯一**渲染处：结果节骨架与论文草稿都从这里取块。

    两处各自渲染必然在改动时分叉（D98 配对 SE、D99 闸门都是这么漏的），所以只留这一个出口。
    """
    from mapping import PARAM_BOUNDS, WITHIN_FREE_LIN
    from twophase import MASK_RHO_BOUNDS
    from likelihood import _from_x
    import numpy as np

    bounds = dict(PARAM_BOUNDS)
    bounds["rho"] = MASK_RHO_BOUNDS
    names = list(WITHIN_FREE_LIN) + ["rho"]
    blocks: dict[str, list[str]] = {}

    tbl = ["| 组 | 编号 | 判定 | 正式试次 | 练习试次 | 正确率 | timeout |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        rec = r.get("rec") or {}
        tbl.append(f"| {r['gid']} | {r['sid']} | {r['verdict']} | {rec.get('n_formal', '?')} | "
                   f"{rec.get('n_practice', '?')} | {rec.get('acc_mean', float('nan')):.3f} | "
                   f"{rec.get('timeout_prop', float('nan')):.1%} |")
    blocks["intake_table"] = tbl

    if not groups:
        return blocks

    health = health or {}
    n_bad = sum(1 for h in health.values() if h.get("status") == H8.BAD)
    m: list[str] = []
    if n_bad:
        m += [f"> ⛔ **本段数值不可引用**：{n_bad}/{len(health)} 组未过 LOO 健康闸门"
              "（D73 口径 / D74 超参数 Hessian 正定 / `p_loo` ∈ [0, `n_obs`] / "
              "`n_draws` ≥ 25）。Δelpd 只能当流程验证，不得写成模型比较证据。", ""]
    nmin = min((int((h.get("modes", {}).get("M-T1") or {}).get("n_subjects") or 0)
                for h in health.values()), default=0)
    if 0 < nmin < MIN_N_HIER:
        m += [f"> ⚠️ **组层样本量不足**：最少 {nmin} 人/组 < {MIN_N_HIER}（D100）。"
              "实测：n=1 人/组时即使把 `n_em` 提到 6、`n_draws` 提到 25，仍是 "
              "`n_flipped` 2/16、`p_loo`÷`n_obs` 5.12、`k_max` 1.213、`max_abs_theta` 100.8；"
              "n=2 人/组（quick，四组）4/4 组红。⇒ 红的是**组层样本量**，不是抽样配置："
              "加 `n_em`／`n_draws` 救不回来，只有加人或加试次。", ""]
    m += ["| 组 | elpd(M-T1) | elpd(M-T3) | Δelpd（正 = 支持两阶段） | SE（配对） "
          "| `p_loo`÷`n_obs` | `n_flipped` | k 诊断 | 判定 | 原因 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for g in sorted(groups):
        res = groups[g].get("results") or {}
        a = (res.get("M-T1") or {}).get("loo") or {}
        b = (res.get("M-T3") or {}).get("loo") or {}
        ea, eb = a.get("elpd_loo"), b.get("elpd_loo")
        d = (ea - eb) if (ea is not None and eb is not None) else float("nan")
        # Δ 的 SE 必须是**配对**口径（逐观测贡献之差的 SD × √n）；
        # 把两个 SE 平方相加会把同一批数据的共同变异算两遍（实测放大 ~35 倍）。
        se = PAIRED_SE(a, b)
        h = health.get(g) or {}
        mt1 = (h.get("modes") or {}).get("M-T1") or {}
        ratio = mt1.get("p_loo_ratio")
        nflip = f"{mt1.get('n_flipped', '?')}/{mt1.get('n_eig', '?')}"
        why = "；".join(mt1.get("reasons") or []) or "—"
        verdict = {"OK": "✅ 可引用", "WARN": "⚠️ 仅提示",
                   "BAD": "⛔ 不可引用"}.get(h.get("status"), "—")
        kd = "是" if a.get("k_diag_ok") else "否（抽样 < 25）"
        m.append(f"| {g} | {ea:.1f} | {eb:.1f} | {d:+.1f} | {se:.1f} | "
                 f"{('%.3f' % ratio) if ratio is not None else '—'} | {nflip} | "
                 f"{kd} | {verdict} | {why} |")
    blocks["model_block"] = m

    p: list[str] = ["| 组 | " + " | ".join(names) + " |",
                    "|---" * (len(names) + 1) + "|"]
    for g in sorted(groups):
        res = (groups[g].get("results") or {}).get("M-T1") or {}
        mu = np.asarray((res.get("fit") or {}).get("mu") or [], dtype=float)
        cells = []
        for j, nm in enumerate(names):
            if j >= mu.size:
                cells.append("—")
                continue
            lo, hi = bounds[nm]
            v = float(_from_x(np.array([mu[j]]), np.array([lo]), np.array([hi]))[0])
            cells.append(f"{v:.3f}")
        p.append(f"| {g} | " + " | ".join(cells) + " |")
    if truth:
        p += ["", "真值（合成数据）：" + "、".join(
            f"`{n}`={truth.get(n)}" for n in names if truth.get(n) is not None)]
    blocks["param_block"] = p
    return blocks


def write_results_skeleton(data: Path, out: Path, rows: list[dict], groups: dict,
                           truth: dict | None, health: dict[int, dict] | None = None) -> Path:
    b = build_blocks(rows, groups, truth, health)
    L = ["# 结果节骨架（半自动）", "",
         "> 表格与统计量由 `run_pipeline.py` 从数据直接生成；`【待写】` 处需要人写论述。",
         "> 若数据是合成的（目录里有 `synth_truth.json`），**本文件不得进入论文**。", ""]
    L += ["## 1. 被试与场次", ""] + b["intake_table"]
    L += ["", "【待写】纳入 N、剔除理由、各组人数是否平衡。", ""]
    if groups:
        L += ["## 2. 模型比较（PSIS-LOO，试次层）", ""] + b["model_block"]
        L += ["", "【待写】Δelpd 的解读与「M-T1 是否被支持」的结论；判定为「不可引用」的组"
                  "一律不得进入结论，只能写进流程验证记录。", ""]
        L += ["## 3. 组层参数（M-T1）", ""] + b["param_block"]
        L += ["", "【待写】参数估计与理论预期的对照；组间差异（P 效应）是否与假设一致。", ""]
    L += ["## 4. 图", "",
          "- `figures/fig1_behavior_by_P.png` —— 行为随 P 的变化（不依赖模型）",
          "- `figures/fig2_param_recovery.png` —— 组层参数与被试层散点",
          "- `figures/fig3_model_comparison.png` —— M-T1 vs M-T3 的 Δelpd", "",
          "【待写】每张图的图注与正文引用。", ""]
    p = out / "results_skeleton.md"
    p.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return p





def main() -> int:
    ap = argparse.ArgumentParser(description="一键跑完 Stage 1→8 的分析流水线")
    ap.add_argument("data")
    ap.add_argument("--out", default=None, help="输出目录（默认 <数据目录>/_pipeline）")
    ap.add_argument("--profile", choices=tuple(PROFILES), default="quick")
    ap.add_argument("--expect-n", type=int, default=8)
    ap.add_argument("--skip-stage8", action="store_true", help="只跑到 Stage 6（不拟合、不出图）")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--reuse-stage8", action="store_true",
                    help="已有 <out>/stage8/stage8_group_*.json 时跳过拟合，只重出图与结果节")
    args = ap.parse_args()

    data = Path(args.data).resolve()
    if not data.is_dir():
        print(f"[FAIL] 不是目录：{data}", file=sys.stderr)
        return 2
    out = Path(args.out).resolve() if args.out else (data / "_pipeline")
    out.mkdir(parents=True, exist_ok=True)

    t_all = time.time()
    steps: list[dict] = []

    ok, rows, p = step_intake(data, out)
    n_keep = sum(1 for r in rows if r["verdict"] == "KEEP")
    steps.append({"name": "1 入库判定", "ok": ok, "detail": f"{len(rows)} 场、KEEP {n_keep}",
                  "product": str(p)})
    print(f"[1/5] 入库判定：{len(rows)} 场、KEEP {n_keep} -> {p}")

    ok6, p6 = step_stage6(data, out, args.expect_n)
    steps.append({"name": "2 Pilot 达标", "ok": ok6, "detail": "见报告", "product": str(p6)})
    print(f"[2/5] Pilot 达标：{'通过' if ok6 else '未通过'} -> {p6}")

    groups: dict = {}
    truth = None
    s8dir = resolve_stage8(out, data)
    cached = sorted(s8dir.glob("stage8_group_*.json"))
    if args.skip_stage8:
        steps.append({"name": "3 层级拟合", "ok": True, "detail": "按 --skip-stage8 跳过",
                      "product": "—"})
        print("[3/5] 层级拟合：跳过")
    elif args.reuse_stage8 and cached:
        steps.append({"name": "3 层级拟合", "ok": True,
                      "detail": f"复用已有 {len(cached)} 组 JSON（--reuse-stage8）",
                      "product": str(s8dir)})
        print(f"[3/5] 层级拟合：复用已有 {len(cached)} 组 JSON -> {s8dir}")
    else:
        if args.reuse_stage8 and not cached:
            print("[warn] --reuse-stage8 但没有可复用的 JSON，改为重新拟合", file=sys.stderr)
        ok8, log, meta = step_stage8(data, out, args.profile, args.resume)
        steps.append({"name": "3 层级拟合", "ok": ok8,
                      "detail": f"{args.profile} 配置、{meta['seconds'] / 60:.1f} min",
                      "product": str(log)})
        print(f"[3/5] 层级拟合：{'完成' if ok8 else '失败'}（{meta['seconds'] / 60:.1f} min）-> {log}")

    health: dict[int, dict] = {}
    if not args.skip_stage8:
        health = assess_health(s8dir)
    if health:
        n_bad = sum(1 for h in health.values() if h.get("status") == H8.BAD)
        okh = n_bad == 0
        detail = f"可引用 {len(health) - n_bad}/{len(health)} 组"
        if n_bad:
            detail += f"、{n_bad} 组不可引用（判据 D73/D74/D75）"
        steps.append({"name": "3.5 LOO 健康", "ok": okh, "detail": detail,
                      "product": str(out / "results_skeleton.md")})
        print(f"[3.5/5] LOO 健康：{detail}")

    if not args.skip_stage8:
        okf, pidx, metaf = step_figures(data, out, s8dir)
        steps.append({"name": "4 图", "ok": okf,
                      "detail": f"{metaf['seconds']:.0f} s" + ("、含真值线" if metaf["truth"] else ""),
                      "product": str(pidx)})
        print(f"[4/5] 图：{'完成' if okf else '失败'} -> {pidx}")
        groups = load_groups(s8dir)
        if metaf["truth"]:
            t = json.loads(Path(metaf["truth"]).read_text(encoding="utf-8"))
            gt = t.get("group_truth") or {}
            truth = next(iter(gt.values()), None)

    skel = write_results_skeleton(data, out, rows, groups, truth, health)

    # 第 5 步：把同一批块填进论文模板（结果章 + 模型章；模板与填法见 manuscript.py）
    draft: Path | None = None
    model_draft: Path | None = None
    if not args.skip_stage8:
        try:
            import manuscript as MS
            draft = MS.write_draft(data, out, rows, groups, truth, health)
            n_pend = draft.read_text(encoding="utf-8").count("【待写】")
            steps.append({"name": "5 论文草稿", "ok": True,
                          "detail": f"{draft.stat().st_size} B、待写处 {n_pend}",
                          "product": str(draft)})
            print(f"[5/5] 论文结果章草稿：{draft}（待写处 {n_pend}）")
        except (KeyError, FileNotFoundError, ValueError) as exc:
            steps.append({"name": "5 论文草稿", "ok": False, "detail": str(exc), "product": "—"})
            print(f"[5/5] 论文结果章草稿：失败（{exc}）", file=sys.stderr)
        try:
            import manuscript as MS
            model_draft = MS.write_model_draft(data, out, rows, groups, truth, health)
            mtxt = model_draft.read_text(encoding="utf-8")
            n_todo = mtxt.count("【待数据：")
            steps.append({"name": "5b 模型章草稿", "ok": True,
                          "detail": f"{model_draft.stat().st_size} B、待数据处 {n_todo}",
                          "product": str(model_draft)})
            print(f"[5/5] 论文模型章草稿：{model_draft}（待数据处 {n_todo}）")
        except (KeyError, FileNotFoundError, ValueError) as exc:
            steps.append({"name": "5b 模型章草稿", "ok": False, "detail": str(exc), "product": "—"})
            print(f"[5/5] 论文模型章草稿：失败（{exc}）", file=sys.stderr)

    total = time.time() - t_all
    L = ["# 流水线报告", "", f"- 数据目录：`{data}`", f"- 输出目录：`{out}`",
         f"- 配置：`{args.profile}`（quick 仅供流程验证，数值不作结论）",
         f"- 总耗时：{total / 60:.1f} min", "",
         "| 步骤 | 结果 | 详情 | 产物 |", "|---|---|---|---|"]
    for s in steps:
        L.append(f"| {s['name']} | {'✅' if s['ok'] else '❌'} | {s['detail']} | `{s['product']}` |")
    L += ["", f"- 结果节骨架：`{skel}`", "",
          f"- 论文结果章草稿：`{draft}`" if draft else "- 论文结果章草稿：（跳过）", "",
          "> 若数据目录含 `synth_truth.json`，则本次全部产物来自**合成数据**，"
          "只能证明流水线可跑通，不得进入论文结果。", ""]
    rp = out / "pipeline_report.md"
    rp.write_text("\n".join(L), encoding="utf-8", newline="\n")

    failed = [s["name"] for s in steps if not s["ok"]]
    print(f"\n[总] {total / 60:.1f} min -> {rp}")
    if failed:
        print(f"[警告] 未通过的步骤：{'、'.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
