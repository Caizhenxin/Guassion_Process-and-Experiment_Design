# -*- coding: utf-8 -*-
"""_apply_d77b.py —— 给 Stage 1 技术验证记录补两处（D77，幂等）

1) §6 开头新增「★ 0. 程序自测（跑实验之前先做）」：三条命令 + 判读；
2) §7 新增第 6 条：程序/手册的"版本一致性"是新增缺口，并说明由哪三条自测守住。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D1 = ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md"

BLOCK6 = """### ★ 0. 程序自测（跑实验之前先做，约 20 s）

2026-10-18 主试在实验机填「组别 7」直接报错退出（D77），根因是**培训手册还是旧的 9 条件设计**、
而程序早已 D4。这类"文档与代码漂移"不会自己报错，只能靠对照。**跑实验之前先在实验机执行这三条**：

```bat
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info"
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation"
python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```

| 命令 | 期望末行 | 它守住什么 |
|---|---|---|
| `check_ask_info` | `通过 40 / 未通过 0` | 弹窗路径：填 7 ⇒ 弹「4 个 P 组速查」并**重填**；填 1 ⇒ 回显「本组 P = 0」；只有点取消才终止 |
| `check_input_validation` | `结果：51 通过 / 0 失败` | 五项校验的文案与边界（空/NaN/非整数/越界） |
| `check_manual_d4.py` | `共 40 项：通过 40 / 未通过 0` | 程序常量 / 手册 / Word 版 / 自测**四者口径一致**（4 组、576 试次、3 block、25 列） |

三条全过才动机器。任一条 ❌ ⇒ 程序、校验或手册之一被改过且没同步，**不得**开始正式采集
（`check_manual_d4.py` 会把不一致项逐条打出来，例如手册里还写着旧版的 520 试次／16 列）。

另：程序现在**不会再因组别填错而退出**。填错（越界/留空/非整数）会弹一个说明窗口，列出
「组1 P0 ｜ 组2 P8 ｜ 组3 P32 ｜ 组4 P120」，关掉后自动回到「实验信息」窗重填；填完还会回显
「groupID ⇒ 本组 P」让你核对，输错就输入 `r` 回车重来，不必 Ctrl+C 重开。

"""

BLOCK7 = """6. **程序/手册的版本一致性**（D77 新增）：程序改了设计而手册没同步，症状是主试被弹窗拒绝或按旧口径操作——**代码侧任何回归测试都发现不了**。已由 `1_Code/Experiment/exp_matlab/test/check_manual_d4.py`（40/40，程序常量 vs 手册 vs Word 版 vs 自测）守住，但它只覆盖写死的几项（4 组 / 576 试次 / 3 block / 25 列 / 四档 T / 三档 W）；**新增输出列或改组数时必须手工改该检查器**，否则它会静默放行。
"""


def insert_before(text: str, prefix: str, block: str, tag: str) -> tuple[str, str]:
    first = block.split("\n")[0]
    if first in text:
        return text, f"[跳过] {tag}（已存在）"
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix!r} 命中 {len(hits)} 行")
    i = hits[0]
    lines[i:i] = block.split("\n")
    return "\n".join(lines), f"[插入] {tag}（锚点 L{i + 1}）"


def insert_after(text: str, prefix: str, block: str, tag: str) -> tuple[str, str]:
    first = block.split("\n")[0]
    if first in text:
        return text, f"[跳过] {tag}（已存在）"
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix!r} 命中 {len(hits)} 行")
    i = hits[0]
    lines[i + 1:i + 1] = block.split("\n")
    return "\n".join(lines), f"[插入] {tag}（锚点 L{i + 1}）"


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    t = D1.read_text(encoding="utf-8")
    t, m1 = insert_before(t, "### 6-A 掩蔽纹理预加载", BLOCK6, "Stage1 §6 的第 0 步")
    t, m2 = insert_after(t, "5. **实机证据空缺**", BLOCK7, "Stage1 §7 第 6 条")
    print(f"{D1.name} {m1}")
    print(f"{D1.name} {m2}")
    if apply:
        D1.write_text(t, encoding="utf-8", newline="\n")
        print("✅ 已写入")
    else:
        print("（未写入；加 --apply 生效）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
