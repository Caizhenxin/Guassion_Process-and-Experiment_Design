"""在 2_Data/Generate_Data/README.md 追加 §6（λ 天花板机制）与 §1 目录口径补注。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Generate_Data\README.md")

SEC1_NOTE = """
> **图与数据分家（2026-10-24）**：本目录现在**只放数据**（`trials_long.csv` / `subjects.csv` / `cells.csv` /
> `meta.json` / `crf_table.csv`）。六张图、跨模型对照图、λ 图一律在 `3_Figures/` 下的同名子目录
> （`3_Figures/M-T1/`、`3_Figures/_compare/`、`3_Figures/_practice/`）。早期合成数据集在
> `_synth_datasets/_SYNTHETIC_*`。
"""

SEC6 = """
## 6. 练习 × SPE：λ 天花板机制（`_practice/` + `3_Figures/_practice/fig9_practice_lambda.png`）

**这一节回答一个模型层面的真问题，不是又一套模拟数据。**

用户从长期练习数据（`SPE_Database/Datasets/11_Practice-Effect`，HuYQ Exp3，7 天训练）提出：
自我相关刺激的练习增益会**饱和**，而他人还在继续涨，于是 SPE 随练习收缩；他给出的写法是
`f_self = 1 − λ(1 − f_other)`。

### 6.1 先说清「为什么不能照搬」

那条公式与 λ 判据（`λ* = (1+α₂)/(1+α₁) = 0.663`，RT 口径 ≈0.475）是在**旧 GP 模型的乘性参数化**下推出的。
本项目是**加法**：`d_self − d_other = β_S + β_SP·f_P`，`f_P = 1 − e^{−P/τ_P}`。换算过来应为

```
v_other(P) = v_other0 + g_P·f_P
v_self(P)  = v_other(P) + Δ_S·[1 − (1−λ)·f_P]
```

- `λ = 1` ⇒ 差距恒定，**严格等价于现行 `β_SP = 0`**；
- `λ = 0` ⇒ 练习把差距完全吃掉（= `β_SP = −β_S`，且 τ 与 `β_P` 共享）；
- 介于两者 ⇒ 差距收敛到 `λ·Δ_S`。

> ⚠️ 别写成 `Δ_S[λ + (1−λ)f_P]`——那会让差距随练习**变大**，方向正好反（第一版就是这么错的，
> 跑出「λ 越小 SPE 越涨」的自相矛盾结果，见 `practice_lambda.py` 里 `drift_pair` 的注释）。

### 6.2 读数（15 人 × 288 试次/格，`dt=1e-4`，P ∈ {0, 8, 32, 120}）

| λ | SPE_RT(P=0) | P=8 | P=32 | P=120 | SPE_ACC（0→120） |
|---|---|---|---|---|---|
| **1**（现行模型） | +20.5 | +25.3 | +31.5 | +27.6 | +0.077 → +0.053 |
| 0.75 | +20.5 | +24.8 | +26.1 | +22.4 | +0.077 → +0.042 |
| 0.5 | +20.5 | +21.4 | +21.4 | +15.1 | +0.077 → +0.029 |
| 0.25 | +20.5 | +20.9 | +15.7 | +7.8 | +0.077 → +0.017 |
| **0**（完全天花板） | +20.5 | +16.6 | +11.4 | **+0.3** | +0.077 → +0.001 |

**结论一（对模型不利，必须写进论文的局限）**：现行模型（`β_SP = 0`，即 λ=1）预测 SPE_RT 随练习
**上升**（+20.5 → +31.5 → +27.6 ms），而 HuYQ 实测是**下降**（LMM −3.30 ms/阶段，SE 0.91，**p=.00029**；
matching-first −3.16、nonmatching-first −3.47，两组斜率差 p=.87）。方向相反 ⇒ 现行模型不能解释长期练习的 SPE 收缩。

**结论二（λ 可辨识性）**：4 档组间剂量点上，(λ, τ_P) 的联合 Fisher 信息给出

| 每组人数 | SE(λ) | SE(τ_P) |
|---|---|---|
| 20 | 0.230 | 35.6 |
| 40 | **0.162** | 25.2 |
| 80 | 0.115 | 17.8 |

即 40 人/组只能把 λ 定到 ±0.16 —— 足以做**方向检验**（λ 是否显著低于 1），不足以区分 0.5 与 0.75。

### 6.3 处置（D115）

1. **不把 λ 加进主模型**：参数分不清，加进去只会得到「区间跨过 λ*」的软结论，还得多重跑一遍全部校验。
2. **写进论文**：作为「模型扩展 + 可检验预测」。方法章给出 λ 族公式与 `β_SP = 0` 的嵌套关系；讨论章说明
   长期练习的 SPE 收缩**要求** λ<1（在 4 档剂量下可检验方向）。
3. **可检验预测**：若真实数据估出 `β_SP` 的区间**不含 0 且为负**，则 λ<1 得到支持；若含 0，则现行模型与
   数据并不矛盾，SPE 收缩只发生在跨 session 尺度（需另一套数据回答）。

### 6.4 产物

| 文件 | 内容 |
|---|---|
| `_practice/practice_lambda.csv` | λ × P 逐格：SPE_RT / SPE_ACC 的均值与 SE、自我/他人的 RT 中位 |
| `_practice/practice_lambda_ident.csv` | SE(λ) / SE(τ_P) / 被试间 SD / Jacobian 条件数 |
| `_practice/practice_lambda_meta.json` | 全部模拟参数（`v_other0=0.80`、`g_P=0.35`、`Δ_S=0.30`、`τ_P=30`、`ρ=0.8`、HuYQ 实测值） |
| `3_Figures/_practice/fig9_practice_lambda.png` | 三联图：① SPE_RT 随 P（按 λ）② SPE_ACC 同族 ③ 与 HuYQ 归一化实测对照 |

重跑：`python 1_Code/Experiment/practice_lambda.py`（约 2 min）
"""


def main() -> int:
    s = P.read_text(encoding="utf-8")
    if "## 6. 练习 × SPE" in s:
        print("[skip] 已有 §6")
        return 0
    anchor = "## 1. 目录内容"
    i = s.index(anchor)
    j = s.index("\n## 2.")
    s = s[:j] + "\n" + SEC1_NOTE + s[j:]
    s = s.rstrip("\n") + "\n" + SEC6
    P.write_text(s, encoding="utf-8", newline="\n")
    print("ok, lines:", len(s.split("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
