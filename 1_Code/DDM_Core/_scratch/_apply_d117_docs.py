"""D117 落纸：8 支 SPE 候选机制比较（主计划 + README + 3_Figures 索引 + 模型章 §3.14 + 数据字典 §7）。

所有插入都从锚点行动态取列数（这个项目里手写列数已经错过 5 次）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
FIGREADME = ROOT / "3_Figures" / "README.md"
MODEL = ROOT / "5_Reference" / "03_论文写作" / "论文_模型章_模板.md"
GENREADME = ROOT / "2_Data" / "Generate_Data" / "README.md"

DECISION = (
    "| **D117** | 2026-10-25 | **SPE 的函数形式穷举：8 支候选在同一模拟器上比较，推荐「速率 + 漂移」混合，"
    "而不是继续在 λ 天花板族上加工**。新建 `1_Code/Experiment/spe_families.py`（387 行）：同一 Euler 模拟器、"
    "同一群被试、同一噪声流（共同随机数），只换自我优势的**作用通道 / 链接函数**，比较 8 支：`const`（现行加法常数）、"
    "`ceiling`（λ 天花板）、`selfsat`（自我单独饱和）、`power`（幂律衰减）、`ratio`（旧项目乘性口径）、"
    "`gate`（加工速率通道）、`gate_drift`（速率 + 漂移混合）、`noise`（噪声通道）。读数（P = 0 / 8 / 32 / 120 的 "
    "SPE_RT（ms）与 P=0 的 SPE_ACC）：`const` 22.4/22.3/29.9/31.3、+6.4 pp；`ceiling` 22.4/19.3/19.2/13.9、+6.4 pp；"
    "`selfsat` 22.4/13.0/6.1/0.05、+6.4 pp；`power` 22.4/15.2/12.5/7.6、+6.4 pp；`ratio` 18.4/20.0/34.3/42.1、+5.7 pp；"
    "`gate` 64.3/62.6/47.3/31.9、≈0 pp；**`gate_drift` 50.2/50.5/36.4/23.3、+3.2 pp**；`noise` −61.3/−51.4/−45.3/−43.0、"
    "+4.2 pp。三条结论：① **换「练习链接函数」（λ / 幂律 / 自我饱和）不改变 P=0 的 SPE**——四支在 P=0 完全同值"
    "（22.4 ms、+6.4 pp），它们只决定走向，所以对「让 SPE 在图上更显眼」零收益；② **换通道才改变可见度**：`gate` 的 "
    "RT 可见度 0.187 ≈ 2.4× 现行 0.077，但正确率差 ≈ 0；`noise` 与 `boundary` 符号相反（更准但更慢），"
    "不能解释 SPE 的「更快」；③ **`gate_drift` 是唯一同时满足三件事的支**：RT 差 50 ms（可见度 0.155，约 2× 现行）、"
    "正确率差 +3.2 pp、且 ms 差随练习**自动**从 50 缩到 23（因为分母 RT 变快），**不需要 λ**。可辨识性"
    "（`SE = SD_between / dSPE/dθ / √40`，SD_between = 17 ms）：`gate` 0.007、`gate_drift` 0.008、`ratio` 0.025、"
    "`power` 0.107、`ceiling` 0.158、`selfsat` 4.28（基本不可估）。**处置**：主模型（Stage 8 拟合口径）**不改**——"
    "`gate_drift` 的速率比 `r_S` 尚未进似然，改它会推翻已跑通的层级拟合与全部设计论证；把本图作为"
    "「模型扩展的候选集 + 判别依据」写进论文方法章与讨论章，并在结果章强制报 **ΔRT 的分位斜率**（`spe_locus` 的判别规则），"
    "因为 `gate` 与 `ceiling` 在「中位差」上无法区分、在「分位斜率」上可以。 |"
)

DECISION_REASON = (
    " 用户 2026-10-25「λ 天花板族我给的只是可能性和参考，有没有其他更合适的函数引入能提升 SPE，可以探索一下」"
    "⇒ 把「练习 × 自我」的候选集穷举一遍，回答「哪种形式能让 SPE 更可见 / 更能解释收缩」 |"
)

DECISION_ARTIFACT = (
    " `1_Code/Experiment/spe_families.py`（**新建**）+ `3_Figures/_compare/fig11_spe_families.png` + "
    "`2_Data/Generate_Data/_families/{families,families_sensitivity,trials_families}.csv` + "
    "`families_meta.json` + 模型章 **§3.14** + `2_Data/Generate_Data/README.md` **§7** |"
)

PROGRESS = (
    "| 2026-10-25 | **15（SPE 机制候选集 → D117）** | **把「换函数」的收益说清楚了**：λ / 幂律 / 自我饱和三支在 P=0 "
    "与现行加法常数**完全同值**（22.4 ms、+6.4 pp），只改变随练习的走向；真正改变可见度的是**通道**——"
    "`gate`（速率）把 RT 差抬到 64 ms（可见度 2.4×）但没有正确率差，`noise`/`boundary` 方向反了，"
    "`gate_drift`（速率 ×1.06 + 漂移 +0.15）同时给出 50 ms、+3.2 pp，且随练习自动收缩到 23 ms。"
    "主模型不改，图与方法章 / 讨论章口径已落纸。 | 用户 2026-10-25 提出探索其他函数形式 | "
    "`1_Code/Experiment/spe_families.py` + `3_Figures/_compare/fig11_spe_families.png` + 模型章 §3.14 |"
)

CHANGELOG = (
    "| 2026-10-25 | **新增 D117（8 支 SPE 候选机制比较）**：`spe_families.py` 统一模拟器 + 共同随机数，"
    "8 支候选 × 4 档练习；结论：链函数不改 P=0、通道才改可见度；推荐 `gate_drift`，主模型不改；"
    "模型章 §3.14 + Generate_Data README §7。 |"
)

EVIDENCE = (
    "| `1_Code/Experiment/spe_families.py` + `3_Figures/_compare/fig11_spe_families.png` + "
    "`2_Data/Generate_Data/_families/families.csv` | D117：8 支候选（`const`/`ceiling`/`selfsat`/`power`/`ratio`/"
    "`gate`/`gate_drift`/`noise`）× P=0/8/32/120；`gate_drift` 50.2→23.3 ms 且 +3.2 pp |"
)

README_ROW = (
    "| 98 | ✅ **SPE 的 8 支候选机制（D117）** | `1_Code/Experiment/spe_families.py`：同一模拟器 + 共同随机数，"
    "只换作用通道 / 链接函数。结论：λ / 幂律 / 自我饱和在 P=0 与现行加法常数**完全同值**（22.4 ms、+6.4 pp）⇒ "
    "换链接函数不提升可见度；`gate` 64 ms 但 Δacc≈0；`noise`/`boundary` 方向相反；"
    "**`gate_drift` 50 ms + 3.2 pp 且随练习自动收缩**。图 `3_Figures/_compare/fig11_spe_families.png` |"
)

FIG_ROW = (
    "| `_compare/` | `fig11_spe_families` SPE 的 8 支候选机制（三联） | "
    "`python 1_Code/Experiment/spe_families.py` | `2_Data/Generate_Data/_families/families.csv` |"
)

MODEL_SEC = """
---

## 3.14 自我优势该放在哪一层、用哪种函数（候选集比较）

> 本节回答「`β_S` 加在漂移上是不是最好的写法」。做法：同一模拟器、同一群被试、同一噪声流，只换
> **自我优势的作用通道或练习链接函数**，看两件事——(a) `P=0` 处 SPE 的可见度，(b) SPE 随练习的走向。

### 3.14.1 八支候选的读数

| 代号 | 机制 | SPE_RT（P=0/8/32/120，ms） | SPE_ACC（P=0） |
|---|---|---|---|
| `const` | 加法常数（§3.4 现行） | 22.4 / 22.3 / 29.9 / 31.3 | +6.4 pp |
| `ceiling` | λ 天花板（§3.13） | 22.4 / 19.3 / 19.2 / 13.9 | +6.4 pp |
| `selfsat` | 自我单独饱和 | 22.4 / 13.0 / 6.1 / 0.05 | +6.4 pp |
| `power` | 幂律衰减 | 22.4 / 15.2 / 12.5 / 7.6 | +6.4 pp |
| `ratio` | 乘性比例（旧口径） | 18.4 / 20.0 / 34.3 / 42.1 | +5.7 pp |
| `gate` | 加工速率通道 | 64.3 / 62.6 / 47.3 / 31.9 | ≈0 pp |
| **`gate_drift`** | **速率 + 漂移（推荐）** | **50.2 / 50.5 / 36.4 / 23.3** | **+3.2 pp** |
| `noise` | 噪声通道 | −61.3 / −51.4 / −45.3 / −43.0 | +4.2 pp |

（负号表示自我试次更慢。）

### 3.14.2 三条结论

1. **换练习链接函数没有收益。** `const`、`ceiling`、`selfsat`、`power` 四支在 `P=0` 处**完全同值**
   （22.4 ms、+6.4 pp）——它们只决定「随练习怎么走」。所以「让 SPE 更明显」这件事，λ 家族帮不上忙。
2. **换通道才有量级差别。** `gate` 的 RT 可见度（`|ΔRT|/SD`）0.187 ≈ 2.4× 现行的 0.077，但正确率差 ≈ 0；
   `noise` 与边界型同号相反（更准但更慢），单独都解释不了「更快**且**更准」的 SPE。
3. **`gate_drift` 同时满足三件事**：RT 差 50 ms（2× 现行）、正确率差 +3.2 pp、且毫秒差随练习从 50 自动降到 23
   （因为练习把 RT 分母变小了，固定比例优势的绝对差自然收缩）——**不需要额外的 λ**。

### 3.14.3 为什么主模型仍然写加法漂移

- 速率比 `r_S` 还没有进似然（`stage8` 的 `theta` 没有被 `r` 乘过的项），改主模型会推翻已跑通的层级拟合、
  PSIS-LOO 对照与全部设计论证（D109/D116 的样本量都以当前参数化给出）。
- 两者在**中位差**上几乎不可分，但在 **ΔRT 的分位斜率**上可分：漂移型斜率 23 ms、速率型斜率 ≈6 ms、
  边界型 73 ms、`t0` 型 ≈0（§3.8 的 `spe_locus` 判别规则）。
- 因此论文的写法是：主模型给区间，**结果章强制报 ΔRT 的五分位差**，用斜率去判断是漂移型还是速率型；
  若是速率型，讨论章直接用本节表 `gate_drift` 一支做解释，不必重跑拟合。

> 写作纪律：本节是**候选集与判别规则**，不是「我们验证了 `gate_drift`」。真实数据未到之前，
> 任何「速率通道更重要」的表述都必须加「在模拟中」。
"""


def insert_after(lines: list[str], anchor: str, new_line: str) -> int:
    """在包含 anchor 的行之后插入 new_line，并断言列数与锚点行一致。"""
    idx = [i for i, ln in enumerate(lines) if anchor in ln]
    if not idx:
        raise SystemExit(f"[fail] 找不到锚点：{anchor}")
    i = idx[-1]
    want = lines[i].count("|")
    got = new_line.count("|")
    if want != got:
        raise SystemExit(f"[fail] 列数不符：锚点 {want} 个竖线，新行 {got} 个\n{new_line[:120]}")
    lines.insert(i + 1, new_line)
    return i + 1


def main() -> int:
    txt = PLAN.read_text(encoding="utf-8")
    if "**D117**" in txt:
        print("[skip] 主计划已有 D117")
    else:
        lines = txt.split("\n")
        insert_after(lines, "| **D116** |", DECISION.rstrip() + DECISION_REASON + DECISION_ARTIFACT)
        insert_after(lines, "**14（③ 设计空间优化 → D116）**", PROGRESS)
        insert_after(lines, "**新增 D116（③ 成本—精度前沿图）**", CHANGELOG)
        # 证据表追加到末尾（最后一行以 "| `1_Code/Experiment/design_frontier.py`" 起头的行之后）
        insert_after(lines, "`1_Code/Experiment/design_frontier.py` + `3_Figures/_design/fig10_design_frontier.png`",
                     EVIDENCE)
        PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print("[ok] 主计划已插入 D117 四行")

    r = README.read_text(encoding="utf-8")
    if "**SPE 的 8 支候选机制（D117）**" in r:
        print("[skip] README 已有第 98 项")
    else:
        lines = r.split("\n")
        insert_after(lines, "| 97 | ✅ **③ 成本—精度前沿图（D116）**", README_ROW)
        README.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print("[ok] README §9 已加第 98 项")

    f = FIGREADME.read_text(encoding="utf-8")
    if "fig11_spe_families" in f:
        print("[skip] 3_Figures README 已有 fig11")
    else:
        lines = f.split("\n")
        insert_after(lines, "`_design/` | `fig10_design_frontier`", FIG_ROW)
        FIGREADME.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print("[ok] 3_Figures README 已加 fig11 行")

    m = MODEL.read_text(encoding="utf-8")
    if "## 3.14 自我优势该放在哪一层" in m:
        print("[skip] 模型章已有 §3.14")
    else:
        MODEL.write_text(m.rstrip("\n") + "\n" + MODEL_SEC, encoding="utf-8", newline="\n")
        print("[ok] 模型章已加 §3.14")

    g = GENREADME.read_text(encoding="utf-8")
    if "## 7. SPE 的函数形式比较" in g:
        print("[skip] Generate_Data README 已有 §7")
    else:
        sec = """
---

## 7. SPE 的函数形式比较（`_families/`，D117）

`1_Code/Experiment/spe_families.py` 把「自我优势放在哪一层、用哪种函数」当自变量，跑 8 支候选
（同一模拟器、同一群被试、同一噪声流）：

| 文件 | 内容 |
|---|---|
| `families.csv` | 每支 × 每档练习的 SPE_RT / SPE_ACC / 可见度 |
| `families_sensitivity.csv` | 每支关键参数的 `|dSPE/dθ|` 与 `SE@40 人/组` |
| `trials_families.csv` | 试次级原始数据（约 18 万行） |
| `families_meta.json` | 基线参数与随机种子（可复现） |

**读图要点**（图在 `3_Figures/_compare/fig11_spe_families.png`）：

1. 左图看 **RT 侧走向**：`const`/`ratio` 随练习**变大**（与长期练习数据相反），`ceiling`/`power`/`selfsat` 变小，
   `gate`/`gate_drift` 因为分母 RT 变快而**自然**变小，`noise` 全程为负（自我更慢）。
2. 中图看 **正确率侧走向**：`gate` 几乎贴在 0（纯速度机制没有正确率差），`const` 保持在 5–6 pp，
   `selfsat` 会一路跌到 0。
3. 右图看 **P=0 的可见度**：四个「只换链接函数」的支共用一个点（22.4 ms / 6.4 pp）——这是本轮的
   核心结论：**换练习映射不改 P=0，换通道才改**。

⚠️ 这些都是**模拟**（`families_meta.json` 里 `note` 写明），不能当结果章数据用。
"""
        GENREADME.write_text(g.rstrip("\n") + "\n" + sec, encoding="utf-8", newline="\n")
        print("[ok] Generate_Data README 已加 §7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
