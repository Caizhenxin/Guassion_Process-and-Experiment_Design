# -*- coding: utf-8 -*-
"""修 D100 落纸的两类表结构错误：

1. 单元格里写了 `max|θ|` —— 竖线把列切开了（主计划三处、README 表头与各行）；
   改成代码名 `max_abs_theta`，语义不变且不会被误当分隔符。
2. README §9 是 **3 列**表（`| 编号 | 状态 | 内容 |`），补第三列。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"


def fix_plan() -> None:
    t = PLAN.read_text(encoding="utf-8")
    n = t.count("max|θ|")
    t = t.replace("`max|θ|`", "`max_abs_theta`").replace("max|θ|", "max_abs_theta")
    t = t.replace("`max_abs_theta` **100.782**", "`max_abs_theta` **100.782**")
    PLAN.write_text(t, encoding="utf-8", newline="\n")
    print(f"主计划：替换 {n} 处 `max|θ|`；现 {len(t.split(chr(10))) - 1} 行")


def fix_readme() -> None:
    lines = README.read_text(encoding="utf-8").split("\n")
    out: list[str] = []
    for x in lines:
        if x.startswith("| 配置 | 人/组 |"):
            x = ("| 配置 | 人/组 | `n_em` | `n_draws` | `p_loo`÷`n_obs` | `n_flipped` "
                 "| `k_max` | `max_abs_theta` | 判词 |")
        x = x.replace("max|θ|", "max_abs_theta")
        out.append(x)
    # §9 第 83 项：3 列表，补第三列
    for i, x in enumerate(out):
        if x.startswith("| 83 | ❌ **未做**"):
            out[i] = (x.rstrip().rstrip("|").rstrip()
                      + " | 下一步：先用 4 人/组与 8 人/组合成数据各跑一次 formal，"
                        "把「多少人/组才转绿」画成一条曲线 |")
            break
    else:
        raise AssertionError("没找到 §9 第 83 项")
    README.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"README：现 {len(out) - 1} 行")


if __name__ == "__main__":
    fix_plan()
    fix_readme()
