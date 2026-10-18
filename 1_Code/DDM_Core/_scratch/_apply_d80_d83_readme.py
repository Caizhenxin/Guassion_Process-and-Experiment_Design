#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_apply_d80_d83_readme.py —— README 补齐 D80 / D82 / D83 三节（§8.55–§8.57）与 §9 第 64–67 项。

起因（D83 收尾核对）：README 的决策索引停在 §9 第 63 项（D79）、
§8.5x 停在 §8.54（D81）—— D80（W 取点的时间账）与 D82（知情同意包）从未进 README，
D83 也只进了主计划/Stage1/手册。这是**索引漂移**，与本轮修的"表头 1 列"是同一类问题：
文档索引不跟上，下一个人就找不到依据。

幂等：已存在 `### 8.55 ` 或 `| 67 |` 时跳过。
"""
from __future__ import annotations

import sys
from pathlib import Path

README = Path(
    r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\README.md"
)

NEW_SECTIONS = """### 8.55 W 的三档取点：用时间账 + 经验曲线关掉「W 不够短」（2026-10-18，D80）

**问题**：主试实机跑通后担心 `W = 800 / 1200 / 1800 ms` 「没有过短的档 ⇒ 不构成速度—准确性权衡，
也就影响不了被试策略」。这个疑问如果不能被文字关掉，Stage 6 Pilot 就没法签批。

**三笔账**（`5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md` §3.3）：

1. **W 自刺激 onset 起算**（`Exp_Design_Formal.m:978-981` 的注释、`:1035` 与 `:1051` 的截止判据），
   而刺激本身占 T、掩蔽又占 200 ms ⇒ 真正能按键的时间是 **W − T − 200**：
   `W = 800` 档在 12 个 (`W`, `T`) 格里只剩 **350–567 ms**（T = 250 ms 那格只有 350 ms）。
2. **旧 88 个 CSV 的实测曲线**（按「截止 − onset」重排漏答率）：330 → **71.6%**、630 → 54.0%、
   680 → 39.2%、830 → 15.2%、1200 → 11.0%、2000 → **5.2%** ⇒ D4 三档落点 **28–34% / 11% / 5–11%**，
   跨度约 25 个百分点，「有没有压力」是**能被数据回答的**，不必靠直觉。
3. **不加 600 档的理由**：设计约束 C1（`W > T + 200`）与 C3（`W − T − 200 ≥ 300 ms`）在 600 上
   会破（T = 250 格只剩 150 ms，48 个试次作废），而省下的只是约 2 分钟。

**两条保留限制**（已写进文档，不许含糊）：`a` 在整个 `W ∈ [0.8, 1.8]` 上只从 1.924 变到 2.057（**6.7%**），
所以只能报**方向与相对次序**、不能报绝对量级；块序固定（800 → 1200 → 1800，`Exp_Design_Formal.m:833-836`）
与 block 完全共线，这项限制由论文方法节承担。

**顺带产出**：`1_Code/Experiment/check_manipulation.py`（183 行，零依赖）——按 W 分组报漏答率
（Wilson 95% 区间）、RT p10/p50/p90、「贴边占比」（RT ≥ W − 100 ms）、漏答随 W 的单调性；
判据 `800 档漏答 ≥ 1800 档 + 10 pp` 且单调不升（容差 5 pp）。对冒烟假数据判「未通过」符合预期
（桩的按键剧本按试次号取模、与 W 无关）。

### 8.56 招募与知情同意：把采集前的纸面环节装上判据（2026-10-18，D82）

**问题**：Stage 6/7 有 Pilot 方案、质控 G1–G9、现场纪律，但**没有一份能直接交到被试手里的材料**。
这类材料出错的方式和代码不同：不崩溃，而是数字与设计脱钩（写「9 组」「≥ 60 Hz 都行」）、
占位符被顺手删掉（伦理批号凭空消失）、关键提醒被删（「刺激很短、看不清是正常的」「不要解释假设」）。

**做法**：新建 `5_Reference/08_工作流/Stage6_被试招募与知情同意包.md`（166 行）——招募公告、
可打印知情同意书（目的/流程/刺激/自愿退出/匿名编号/报酬/联系方式）、被试登记表
（编号 `group<1-4>_subject<n>`）、周排期表、开场口述脚本、采集前检查清单。
机构相关项一律留 `【】` 占位，**不由 AI 代填**。

**牙齿**：`1_Code/Experiment/exp_Check/check_consent_pack.py`（零依赖）**28 项判据 28/28**：6 个章节、
9 个与 D4 一致的数字、5 条必须保留的提醒、占位符仍在、7 条旧口径禁词；`--self-test` 5/5
（删提醒 / 改成 9 组 / 抹掉占位符 / 放宽刷新率 各自被拦住）。

**边界**：判据只保证材料**没被改坏**，不能保证伦理合规 —— 批号、报酬、单位信息必须人填。

### 8.57 `onset` 之前的按键：5/576 试次被旧键敲掉刺激、误判为漏答（2026-10-18，D83）

**问题**：60 Hz 实机（59.111 Hz）那一场，6-C 核心项报 **5 行越界**：`stimulus_dur_actual` 只有 0–1 帧
（6–14 ms），且 `premature_press = 1`、`Response = NA`、`timeout = 1`。第一反应「卡顿」是错的 ——
卡顿只会让时长**变长**（上一轮 165 Hz 是 +2…+25 帧），这里是**短到 0–1 帧**。

**根因**：注视期抢按在 `kqCountPresses()`（`Exp_Design_Formal.m:964`）处读完立即 `KbQueueFlush()`，
但该点距真正 onset（`:976` 的 `Screen('Flip')`）隔着一次 **vsync 等待（≤ 1 帧）**。
这条缝隙里按下的第二个键：不会进抢按计数、队列又刚清过 ⇒ 刺激期 `kqFirstPressUntil` 一进循环就取到它，
刺激被立刻敲掉，试次记为漏答。**漏答率是本设计的核心因变量**（W 三档的论证全靠它），0.87% 的系统性高估不能当噪声。

**做法（v4.6）**：`kqFirstPressUntil(deadline, tFloor)` 只接受 `tFloor < 时间戳 ≤ deadline` 的按键，
四个调用点（练习/正式 × 刺激期/反应窗）都传 `stimulusFlipTime`；早于 onset 的键不消费，
留给下一试次开头的 `KbQueueFlush()`。静态判据补 A8b/A11/A12 ⇒ `test/check_full_session.py` **26/26**，
无屏幕冒烟两组仍 **27/27**。

**顺带修的检查器漂移（D83b）**：`check_stage1_acceptance.py` 的 `load_rows()` 写死 `split("\\t")`，
而主试交回的 `EXP_data_group1_1.csv` 是逗号分隔 ⇒ 整行被当成 1 列，打印「表头不是 v4.1 的 25 列（1 列）」。
已改为按首行嗅探分隔符（有制表符 ⇒ txt；否则含逗号 ⇒ `csv.reader`），两通道都能吃。

**边界**：这 5 行**保留为「v4.5 已知缺陷」，不放宽 6-C 判据去迁就既有数据**。要回填 Stage 1 §6，
仍须用 v4.6 在实验室机（60.004 Hz）上复跑一场。

"""

NEW_ITEMS = """| 64 | ✅ **W 的三档取点用时间账 + 经验曲线关掉（D80，§8.55）** | 净可按键时间 = W − T − 200 ⇒ W=800 档只剩 350–567 ms；旧 88 个 CSV 的实测曲线 330 → 71.6%、2000 → 5.2%；不加 600 档因 C1/C3 会破。保留限制：a 只变 6.7%、块序共线。新增 `check_manipulation.py`（183 行）。 |
| 65 | ✅ **检查器里的隐含常量 60 Hz / 1 帧 / 1e-6 秒（D81，§8.54）** | 六处误判逐条改成程序真实口径 + 环境门 `--expect-hz`；440 → 516 行，自测 6/6。 |
| 66 | ✅ **招募与知情同意包 + 28 项判据（D82，§8.56）** | `Stage6_被试招募与知情同意包.md`（166 行）+ `check_consent_pack.py`（28/28、自测 5/5）；机构项留 `【】` 不代填。 |
| 67 | ✅ **`onset` 之前的按键被当成反应（D83，§8.57）** | 5/576 行被旧键敲掉刺激、误判漏答；v4.6 给 `kqFirstPressUntil` 加 `tFloor`，26/26；同时修好检查器只认制表符的漂移（D83b）。 |"""


def main() -> int:
    text = README.read_text(encoding="utf-8")
    changed = False

    if "### 8.55 " in text:
        print("[SKIP] §8.55 已存在")
    else:
        anchor = "## 9. 尚未做"
        assert text.count(anchor) == 1, "§9 锚点不唯一"
        text = text.replace(anchor, NEW_SECTIONS + anchor, 1)
        print("[OK] 已插入 §8.55–§8.57（D80 / D82 / D83）")
        changed = True

    if "| 67 | ✅" in text:
        print("[SKIP] §9 第 67 项已存在")
    else:
        lines = text.rstrip("\n").split("\n")
        assert lines[-1].startswith("| 63 |"), f"§9 末行不是第 63 项：{lines[-1][:40]!r}"
        text = text.rstrip("\n") + "\n" + NEW_ITEMS + "\n"
        print("[OK] §9 已追加第 64–67 项")
        changed = True

    if changed:
        README.write_text(text, encoding="utf-8", newline="\n")
        print(f"     README 行数：{len(text.splitlines())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
