"""给 `1_Code/DDM_Core/README.md` 的 §9 表追加第 33 项（决策 D52）。

为什么写脚本而不是用 `edit`：§9 的表格行是**数千字符的单行**，`edit` 必须一字不差地
匹配行尾；这里按"行首前缀"定位再插入，不依赖行尾形状。同时：
* 断言 §9 表里不存在 `| 33 |`（幂等守卫）；
* 断言新行与表头一样是 3 列（4 个竖线）；
* 断言插入后 32 与 33 相邻（没有空行）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

README = Path(__file__).resolve().parents[1] / "README.md"

ROW = (
    "| 33 | ✅ **LOO 可用性必须同时看 `p_loo`（D52，§8.28）** | "
    "`max k` **单独没有分辨力**：4 人 analytic 干跑的 M-T1 给出 "
    "`max k = 0.000`、`n_failed = 0`、`越界 0/4`，按当时判据与 "
    "`Stage8_建模与验证方案.md` §8 的事前登记规则（三档**全部以 `max k` 为键**）"
    "会被判成**可用**；而同一行的 `p_loo = 2816.26` 对 **`n_obs = 4`** "
    "⇒ **有效参数数是观测数的 704 倍**，结构性崩坏。"
    "**为什么是 4 不是 756**：`hier.loo_matrix` 返回 `(S, N)`（每个抽取 × 每个被试的边际对数似然），"
    "`loo.psis_loo` 的 `n_obs = N` 是列数 ⇒ 本项目 LOO 单位 = **被试**"
    "（`hier.loo_bruteforce` 的 docstring 亦写明）。"
    "**为什么 `k_max = 0.000` 不是健康证明**：同一个 0.000 在健康矩阵上也会出现"
    "（实测 `rng.normal(-3.0, 0.3, size=(30, 3))` 的另一抽样：`p_loo = 0.222`、`max k = 0.000`）"
    "⇒ 0 既可能是「权重近似均匀」也可能是「权重彻底退化」，**无法分辨**。"
    "**健康区间 `[0, n_obs]`**：`p_loo < 0` 意味着留一比拟合内还准（不可能；N=2 干跑实测 −706.37 / −2900.54），"
    "`p_loo > n_obs` 意味着惩罚超过全部信息量。"
    "❗ **这个洞是 N=4 才暴露的**：N=2 时 `n_failed = 2 = n_obs`，被旧判据拦住了。"
    "**修法**：`stage8_run.py::render_group` 改为收集理由清单"
    "（`max k` 非有限 / `n_failed ≥ n_obs` / `p_loo ∉ [0, n_obs]`）任一条成立即判"
    "「⛔ 本组 LOO 无效」，并在报告行**强制**打印 `p_loo` 与 **`p_loo`/`n_obs` 这个比值**"
    "（它是唯一能分辨的那个数）。"
    "**校验**：`_scratch/check_stage8_run.py` **18/18、exit 0**（原 15 项），"
    "新增 A7c（`k_max = 0` + `n_failed = 0` + `p_loo/n_obs = 704` ⇒ 必须报「LOO 无效」）、"
    "A7d（负 `p_loo` ⇒ 必须报）、A7e（反向对照：健康 `p_loo` 不得被误伤，仍给「可报 ΔELPD」）；"
    "日志 `_scratch/check_stage8_run_d52_u8.txt`。"
    "**遗传自**：第 7 / 27 / 32 项（`max k` 会爆表；`nan` 不是最差挡位；一个计数器不够），"
    "以及 `Stage8_建模与验证方案.md` §11 新增的第 9 条已知限制 |"
)


def main() -> int:
    text = README.read_text(encoding="utf-8")
    lines = text.split("\n")
    if any(line.startswith("| 33 |") for line in lines):
        print("❌ 幂等守卫：已存在 `| 33 |` 行，拒绝写回")
        return 2
    # ❗ 必须把锚点限定在 §9 之内：`| 32 |` 在别处也会出现（实测 L626 是一张
    #    数据表的第 32 行）⇒ 只按行首前缀会命中两次（这条守卫第一次跑就抓到了）。
    i9 = [i for i, line in enumerate(lines) if line.startswith("## 9. ")]
    if len(i9) != 1:
        print(f"❌ `## 9. ` 标题命中 {len(i9)} 次（期望 1）")
        return 2
    anchor = [i for i, line in enumerate(lines)
              if i > i9[0] and line.startswith("| 32 |")]
    if len(anchor) != 1:
        print(f"❌ §9 内锚点行 `| 32 |` 命中 {len(anchor)} 次（期望 1）")
        return 2
    i32 = anchor[0]
    if lines[i32].count("|") - lines[i32].count("\\|") != 4:
        print(f"❌ 锚点行不是 3 列：竖线数 {lines[i32].count('|')}")
        return 2
    if ROW.count("|") - ROW.count("\\|") != 4:
        print(f"❌ 新行不是 3 列：竖线数 {ROW.count('|')}")
        return 2
    if lines[i32 + 1].strip() != "":
        print(f"⚠️ 第 32 项之后不是空行（是 {lines[i32 + 1][:40]!r}）—— 仍继续")
    lines.insert(i32 + 1, ROW)
    # ❗ 插入后索引关系：`lines[i32]` 仍是第 32 项（它没有移动），
    #    `lines[i32 + 1]` 才是新的第 33 项；原来在 i32+1 的那一行（这里是空行）
    #    被挤到 i32+2。第一版断言写成查 `lines[i32 + 2].startswith("| 32 |")`
    #    ⇒ 永远失败（那里是空行），且**在写回之前就退出**（fail-safe）。
    if lines[i32 + 1] != ROW or not lines[i32].startswith("| 32 |"):
        print("❌ 插入位置自检失败")
        return 2
    README.write_text("\n".join(lines), encoding="utf-8", newline="")
    print(f"✅ 已插入第 33 项：{README}（{len(text.splitlines())} → {len(lines)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
