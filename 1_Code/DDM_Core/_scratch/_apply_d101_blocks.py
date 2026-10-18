"""D101：把 `write_results_skeleton` 里的表格渲染抽成 `build_blocks`，供 `manuscript.py` 复用。"""

from __future__ import annotations

import sys
from pathlib import Path

RP = Path(__file__).resolve().parents[2] / "Experiment" / "run_pipeline.py"

NEW = '''def build_blocks(rows: list[dict], groups: dict, truth: dict | None,
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
    p.write_text("\\n".join(L), encoding="utf-8", newline="\\n")
    return p
'''


def main() -> int:
    src = RP.read_text(encoding="utf-8")
    lines = src.split("\n")
    start = next(i for i, x in enumerate(lines) if x.startswith("def write_results_skeleton("))
    end = next(i for i, x in enumerate(lines) if x.startswith("def main() -> int:"))
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    out_lines = lines[:start] + NEW.split("\n") + ["", ""] + lines[end:]
    RP.write_text("\n".join(out_lines), encoding="utf-8", newline="\n")
    txt = RP.read_text(encoding="utf-8")
    assert "def build_blocks(" in txt, "build_blocks 未写入"
    assert txt.count("def write_results_skeleton(") == 1
    assert txt.count("def main() -> int:") == 1
    assert "PAIRED_SE(a, b)" in txt
    print(f"[ok] run_pipeline.py 现 {len(txt.splitlines())} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
