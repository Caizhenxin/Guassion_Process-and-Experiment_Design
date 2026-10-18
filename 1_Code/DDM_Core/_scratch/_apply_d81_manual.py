# -*- coding: utf-8 -*-
"""D81 落纸（手册侧）：升 v2.4——把「刷新率 ≥ 60 Hz」这条模糊红线改成硬前提 60.004 Hz。

为什么必须改：第 101 行原写「刷新率 ≥ 60 Hz」，等于允许在 120/144/165 Hz 的屏上采集。
2026-10-18 本机（165 Hz）那场就因此出现 44/576 行刺激多停 2–25 帧——帧长从 16.67 ms
掉到 6.06 ms，MATLAB 每帧预算不够就会漏 vsync。而 T 的四个档位（2/5/9/15 帧）本来就是
按 60.004 Hz 设计的，换屏即变帧数。

同时修掉头注的版本漂移：第 3 行还写「v4.4」，程序实际已是 v4.5。

幂等：断言每处命中恰好 1 次；newline="\\n" 写回。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANUAL = REPO / "1_Code" / "Experiment" / "exp_matlab" / "主试培训手册_Exp_Design_Formal.md"

EDITS: list[tuple[str, str, str]] = [
    (
        "头注程序版本 v4.4 → v4.5",
        "Exp_Design_Formal.m`（v4.4）",
        "Exp_Design_Formal.m`（v4.5）",
    ),
    (
        "版本行 v2.3 → v2.4",
        "> 版本：v2.3（2026-10-18，随 D4 设计定稿 + 程序 v4.5；",
        "> 版本：v2.4（2026-10-18，随 D4 设计定稿 + 程序 v4.5；",
    ),
    (
        "版本行补 v2.4 变更说明",
        "v2.3 增至六条并加「整场冒烟」，对应程序 v4.5。上一版 v1.2 还是旧的「9 条件」设计）",
        "v2.3 增至六条并加「整场冒烟」，对应程序 v4.5；v2.4 把刷新率从「≥ 60 Hz」收紧为"
        "**必须 60.004 Hz**、并补 §7 的「高刷屏症状」与 §8 的 Word 版生成办法。上一版 v1.2 还是旧的「9 条件」设计）",
    ),
    (
        "准备清单：刷新率红线收紧",
        "- [ ] 显示器参数与程序标定一致（刷新率 ≥ 60 Hz、分辨率不更改；程序按 60 Hz 帧量化 T/W）",
        "- [ ] **显示器必须是实验室那块 60.004 Hz 的屏**（`设置 → 系统 → 显示 → 高级显示 → 刷新率` 选 60 Hz）。\n"
        "      ⚠️ **不要用笔记本内屏、也不要选 120/144/165 Hz**：帧长会从 16.67 ms 掉到 6.06 ms，\n"
        "      刺激每漏一次 vsync 就多停 1 帧，T 的帧数也不再是设计里的 2/5/9/15。\n"
        "      判断办法：程序启动会打印帧量化对照表，`stimulus_frames` 必须是 2/5/9/15，否则立即停止采集。",
    ),
]

SYMPTOM = """
### 7.x 高刷新率屏的症状（v2.4 新增，2026-10-18）

在 165 Hz 的屏上跑一场，事后用 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py` 检查会看到：

- 反推 FlipIntv ≈ **6.06 ms**（165 Hz）而不是 16.67 ms；
- `stimulus_frames` 变成 **5 / 14 / 25 / 41**（按毫秒取整），不再是 2 / 5 / 9 / 15；
- 一部分试次的 `stimulus_dur_actual − T` 超出 +1 帧（本机实测 44/576 行多停 2–25 帧 = 12–152 ms）。

**这不是程序坏了，是这块屏不在设计口径里**。检查器会自动打印「证据降级」，此时
这份数据只能证明「程序能跑通、能写出 25 列」，**不能**用来回填技术验证记录 §6 的表。
"""


def main() -> int:
    src = MANUAL.read_text(encoding="utf-8")
    for name, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            print(f"❌ [{name}] 命中 {n} 次（要求 1 次），中止")
            return 1
        src = src.replace(old, new)
        print(f"✅ [{name}]")

    # 症状段插到「## 8」之前（若无则插到文件末尾）
    anchor = "\n## 8"
    if SYMPTOM.strip() in src:
        print("⏭  [症状段] 已存在")
    elif src.count(anchor) == 1:
        src = src.replace(anchor, SYMPTOM + anchor)
        print("✅ [症状段]")
    else:
        src = src.rstrip("\n") + "\n" + SYMPTOM
        print("✅ [症状段] 追加到末尾")

    MANUAL.write_text(src, encoding="utf-8", newline="\n")
    print(f"\n已写回（{len(src.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
