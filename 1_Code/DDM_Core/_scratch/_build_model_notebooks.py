"""生成三个模型的 .ipynb（M-T1 / M-T2 / M-T3）。

三个 notebook 结构完全一致，只有「模型是什么」的文字与生成参数不同——这样三个
文件对照着看，就能看出差异只在漂移轨迹那一处。

用法：python -X utf8 1_Code/DDM_Core/_scratch/_build_model_notebooks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
OUT_DIR = ROOT / "1_Code" / "Python_for_Generate"

SPECS = {
    "M-T1": {
        "file": "M-T1_两阶段阶跃_数据生成与可视化.ipynb",
        "title": "M-T1｜两阶段阶跃模型：数据生成与可视化",
        "what": (
            "刺激呈现期内漂移**恒为** `d_stim`；刺激结束（掩蔽）后降为 `ρ·d_stim`。\n\n"
            "$$\n d(t)=\\begin{cases} d_{\\text{stim}}, & 0 \\le t \\le T \\\\ \\rho\\,d_{\\text{stim}}, & t > T\\end{cases}\n$$\n\n"
            "`ρ ∈ [0,3]`：`ρ=0` 掩蔽后停止积累、`ρ=1` 掩蔽无影响（退化为 M-T3）、`ρ>1` 掩蔽后加速。"
        ),
        "gen": "G.generate('M-T1', OUT, n_subjects_per_group=4, rho=0.8, drift_sd=0.25, seed=SEED)",
        "why": "这一条是**主模型**：它把「掩蔽有没有打断证据积累」变成一个可估的参数 ρ。",
    },
    "M-T2": {
        "file": "M-T2_两阶段斜坡_数据生成与可视化.ipynb",
        "title": "M-T2｜两阶段斜坡模型：数据生成与可视化",
        "what": (
            "刺激期内漂移**逐步爬升**，不是阶跃：\n\n"
            "$$\n d(t)=d_{\\text{stim}}\\left(1-e^{-t/\\tau_T}\\right),\\quad 0 \\le t \\le T\n$$\n\n"
            "掩蔽时刻取当时的值并乘 ρ：`ρ·d_stim·(1 − e^{−T/τ_T})`。`τ_T → 0` 时 M-T2 ≡ M-T1。\n\n"
            "⚠️ 在 M-T2 里，**T 的效应来自斜坡本身**（T 越长爬得越久），所以生成时把映射层的 "
            "`beta_T` 置 0，避免与斜坡重复计数（`ramp_beta_t='zero'`）。"
        ),
        "gen": "G.generate('M-T2', OUT, n_subjects_per_group=4, rho=0.8, tau_ramp=0.08, ramp_beta_t='zero', drift_sd=0.25, seed=SEED)",
        "why": "这一条是**竞争解释**：如果 T 的效应全部来自「漂移要时间才升到满」，那么 ρ 就不再需要——用它可以解释「掩蔽效应」的另一种来源。",
    },
    "M-T3": {
        "file": "M-T3_单阶段_数据生成与可视化.ipynb",
        "title": "M-T3｜单阶段模型（掩蔽无影响）：数据生成与可视化",
        "what": (
            "M-T1 在 `ρ = 1` 处的**严格嵌套特例**：漂移在整个试次内恒定，掩蔽不改变积累。\n\n"
            "$$\n d(t)=d_{\\text{stim}},\\quad t \\ge 0\n$$\n\n"
            "它在理论上的意义是**零假设**：如果真实数据支持 M-T3，说明「掩蔽后还能继续积累」，"
            "那么 ρ 就不该出现在模型里。"
        ),
        "gen": "G.generate('M-T3', OUT, n_subjects_per_group=4, drift_sd=0.25, seed=SEED)",
        "why": "这一条是**零假设模型**：它几乎总能拟合得比 M-T1 好一点点（少一个参数），所以判据必须是 ΔELPD / BIC 而不是「谁拟合得更好」。",
    },
}


def md(text: str) -> str:
    return text.strip("\n")


SETUP = """
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import Image, display

# --- 找到仓库根（notebook 放在 1_Code/Python_for_Generate/）---
ROOT = Path.cwd()
while not (ROOT / "1_Code").exists():
    ROOT = ROOT.parent
for p in (ROOT / "1_Code" / "DDM_Core", ROOT / "1_Code" / "Experiment"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import gen_model_data as G
import gen_viz as V

MODEL = "__MODEL__"
OUT = G.DEFAULT_OUT / MODEL
SEED = 20261021
print("仓库根：", ROOT)
print("模型：", MODEL, "→", OUT)
print("numpy", np.__version__, "| pandas", pd.__version__)
"""

GEN = """
# 生成（16 名被试 = 每档练习量 4 人；每人 576 试次）
res = __GEN__
meta = res["meta"]
print(json.dumps({k: meta[k] for k in
                  ("model", "label", "rho", "tau_ramp", "drift_sd", "n_subjects",
                   "n_trials_total", "seed", "elapsed_s")}, ensure_ascii=False, indent=2))
print()
print("真值：", json.dumps(meta["truth"], ensure_ascii=False))
if meta.get("truth_note"):
    print("⚠️", meta["truth_note"])
print()
print("产物：")
for p in sorted(OUT.glob("*")):
    if p.is_file():
        print(f"  {p.name:24s} {p.stat().st_size / 1024:8.1f} KB")
"""

DESC = """
df = G.load_trials(OUT)
print(f"逐试次表：{len(df)} 行 × {df.shape[1]} 列；"
      f"被试 {df['subject_id'].nunique()} 名；每人 {df.groupby('subject_id').size().iloc[0]} 试次")
print(f"正确率（已响应）{df.loc[df.omission == 0, 'correct'].mean():.3f}；"
      f"遗漏率 {df.omission.mean():.3f}；"
      f"RT 中位 {df.loc[df.omission == 0, 'rt_ms'].median():.0f} ms")

tab = (df.assign(resp=1 - df.omission)
         .groupby(["P", "T_ms", "is_self"])
         .agg(n=("resp", "size"),
              acc=("correct", lambda s: np.nan),
              om=("omission", "mean"))
         .reset_index())
# 正确率要只看已响应试次
acc = (df[df.omission == 0].groupby(["P", "T_ms", "is_self"])["correct"].mean()
       .rename("acc").reset_index())
tab = tab.drop(columns="acc").merge(acc, on=["P", "T_ms", "is_self"], how="left")
tab["acc"] = tab["acc"].round(3)
tab["om"] = tab["om"].round(3)
piv = tab.pivot_table(index=["P", "T_ms"], columns="is_self", values=["acc", "om"])
piv.columns = [f"{a}_{'自我' if b == 1 else '他人'}" for a, b in piv.columns]
print()
print(piv.round(3).to_string())
"""

FIG1 = """
# 图 1 / 图 2：RT 分布与分位曲线
V.plot_rt_density(df, OUT / "figures" / "fig1_rt_density.png", title=f"{MODEL}（模拟数据，非人类被试）")
V.plot_rt_quantiles(df, OUT / "figures" / "fig2_rt_quantiles.png", title=f"{MODEL}（模拟数据，非人类被试）")
display(Image(filename=str(OUT / "figures" / "fig1_rt_density.png"), width=980))
display(Image(filename=str(OUT / "figures" / "fig2_rt_quantiles.png"), width=980))
"""

FIG3 = """
# 图 3：正确率 / 遗漏率 随 T 与 W——设计的两个操作变量有没有效果
V.plot_accuracy_omission(df, OUT / "figures" / "fig3_accuracy_omission.png",
                         title=f"{MODEL}（模拟数据，非人类被试）")
display(Image(filename=str(OUT / "figures" / "fig3_accuracy_omission.png"), width=980))
"""

FIG4 = """
# 图 4：CRF（条件正确率函数）——按 RT 五分位分箱看正确率
# ⚠️ 分箱必须在 (T × W × 身份) 内部做，否则「长 RT」会与「低漂移条件」混在一起
agg = V.crf_table(df, n_bins=5)
V.plot_crf(df, OUT / "figures" / "fig4_crf.png", title=f"{MODEL}：CRF（条件正确率函数）")
display(Image(filename=str(OUT / "figures" / "fig4_crf.png"), width=760))
print(agg.round(3).to_string(index=False))
"""

FIG5 = """
# 图 5：delta 图——他人 − 自我 在各 RT 分位上的差（每个点一名被试，误差条 = 95% CI）
V.plot_delta(df, OUT / "figures" / "fig5_delta.png", title=f"{MODEL}：delta 图（他人 − 自我）")
display(Image(filename=str(OUT / "figures" / "fig5_delta.png"), width=760))
"""

FIG6 = """
# 图 6：机制图——漂移轨迹（这是三条模型唯一的差别）
V.plot_mechanism(OUT / "figures" / "fig6_mechanism.png", MODEL,
                 rho=meta["rho"], tau_ramp=meta.get("tau_ramp") or 0.08,
                 title=f"{MODEL}：漂移轨迹")
display(Image(filename=str(OUT / "figures" / "fig6_mechanism.png"), width=1040))
"""

CHECK = """
# 自检：这套数据「像不像人、有没有效应方向」
d = df[df.omission == 0]
acc = d.correct.mean()
om = df.omission.mean()
rt_med = d.rt_ms.median()
acc_by_T = d.groupby("T_ms").correct.mean()
self_acc = d[d.is_self == 1].correct.mean()
other_acc = d[d.is_self == 0].correct.mean()

checks = [
    ("正确率在 0.50–0.95", 0.50 <= acc <= 0.95, f"{acc:.3f}"),
    ("遗漏率在 0.02–0.45", 0.02 <= om <= 0.45, f"{om:.3f}"),
    ("RT 中位在 300–1200 ms", 300 <= rt_med <= 1200, f"{rt_med:.0f} ms"),
    ("T 越长越准（末端 > 首端）", acc_by_T.iloc[-1] > acc_by_T.iloc[0],
     f"{acc_by_T.iloc[0]:.3f} → {acc_by_T.iloc[-1]:.3f}"),
    ("自我比他人准", self_acc > other_acc, f"{self_acc:.3f} vs {other_acc:.3f}"),
]
for name, ok, val in checks:
    print(f"{'✅' if ok else '❌'} {name:28s} {val}")
print()
print("全部通过" if all(c[1] for c in checks) else "有项目未通过——先别急着用这套数据")
"""

FILES = """
# 产物清单
print(f"{'文件':34s} {'大小':>10s}")
for p in sorted(OUT.rglob("*")):
    if p.is_file():
        print(f"{str(p.relative_to(OUT)):34s} {p.stat().st_size / 1024:9.1f} KB")
"""


GUIDE = """
## 怎么读这六张图

| 图 | 看什么 | 什么算「不对」 |
|---|---|---|
| 1 RT 分布 | 单峰、右偏、下限由 t0 卡住（≳180 ms） | 双峰 = 混合了两个漂移；左峰贴 0 = 有提前按键没剔除 |
| 2 分位曲线 | 各条件基本平行；T 越长整体略降 | 曲线交叉 = 条件间不只是漂移差（还有边界/起点差） |
| 3 正确率/遗漏率 | T ↑ 正确率 ↑；W ↑ 遗漏率 ↓ | T 的方向相反 = 映射写反了 |
| 4 CRF | 本模拟里**下降**（快试次更准） | 若你希望看到「越慢越准」，需要的是边界波动/注意失效，不是漂移变异 |
| 5 delta 图 | 正 = 他人更慢（自我更快）；看是否随分位放大 | 全 0 = 自我效应没进模型；符号翻转 = 条件编码错了 |
| 6 机制图 | 只有这张图在讲「三条模型差在哪」 | M-T2 的曲线若有折角 = 斜坡实现写错 |

### 一处必须写进方法章的口径差异（D104 纪律）

本模拟的 CRF 是**下降**的：我们只加了「逐试次漂移变异」（低漂移的试次既慢又错）。
真实数据里 CRF 常常是**上升**的，那通常来自**边界波动 / 注意失效 / 非决策时间变异**，
而不是漂移变异。**不要用模拟图去硬凑真实数据的形状**——这条差异本身就是方法章要写明的
模型边界（`Stage9` §13 的三条口径同理）。
"""


def build(model: str) -> Path:
    spec = SPECS[model]
    nb = nbf.v4.new_notebook()
    cells = [
        nbf.v4.new_markdown_cell(md(f"""
# {spec['title']}

> 本 notebook 由 `1_Code/DDM_Core/_scratch/_build_model_notebooks.py` 生成；
> 数据与图都落在 `2_Data/Generate_Data/{model}/`。
> **这是模拟数据，不是人类被试的数据**，只能用于方法/功效论证，不得写进结果章。

## 0. 这个模型在三条模型里的位置
""")),
        nbf.v4.new_markdown_cell(md(spec["what"])),
        nbf.v4.new_markdown_cell(md(f"""
**为什么要有这一条**：{spec['why']}

三条模型是同一条轴上的三种取值：

```
M-T3（ρ=1，无掩蔽效应）  ←——  M-T1（阶跃 + ρ）  ——→  M-T2（斜坡 + ρ，τ_T→0 时退回 M-T1）
```
""")),
        nbf.v4.new_markdown_cell("## 1. 环境"),
        nbf.v4.new_code_cell(SETUP.replace("__MODEL__", model)),
        nbf.v4.new_markdown_cell(md("""
## 2. 生成数据

生成物的含义：

- `trials_long.csv`：逐试次（含真值潜变量 `d_stim`/`a`/`z`/`t0_ms`，用于恢复检验）
- `subjects.csv`：逐被试真值参数
- `cells.csv`：逐单元汇总（正确率 / 遗漏率 / RT 均值与中位）
- `meta.json`：模型、真值、种子、试次数
""")),
        nbf.v4.new_code_cell(GEN.replace("__GEN__", spec["gen"])),
        nbf.v4.new_markdown_cell("## 3. 读回来看一眼"),
        nbf.v4.new_code_cell(DESC),
        nbf.v4.new_markdown_cell(GUIDE),
        nbf.v4.new_markdown_cell("### 图 1–2：RT 分布与分位曲线"),
        nbf.v4.new_code_cell(FIG1),
        nbf.v4.new_markdown_cell("### 图 3：正确率 / 遗漏率"),
        nbf.v4.new_code_cell(FIG3),
        nbf.v4.new_markdown_cell("### 图 4：CRF（条件正确率函数）"),
        nbf.v4.new_code_cell(FIG4),
        nbf.v4.new_markdown_cell("### 图 5：delta 图"),
        nbf.v4.new_code_cell(FIG5),
        nbf.v4.new_markdown_cell("### 图 6：机制图"),
        nbf.v4.new_code_cell(FIG6),
        nbf.v4.new_markdown_cell("## 4. 自检与产物"),
        nbf.v4.new_code_cell(CHECK),
        nbf.v4.new_code_cell(FILES),
    ]
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": sys.version.split()[0]},
        "dsh": {"generated_by": "_build_model_notebooks.py", "model": model},
    }
    path = OUT_DIR / spec["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, str(path))
    return path


def main() -> int:
    for m in SPECS:
        p = build(m)
        print(f"[ok] {p}  ({p.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
