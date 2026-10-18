# -*- coding: utf-8 -*-
"""_apply_d77.py —— 把「主试侧输入防线」（D77）落进四份文档（幂等）

落点
----
主计划             ：§5 决策 D77 行（5 列）/ §6 进度行（5 列）/ §7 变更日志（2 列）/ §8 文件清单（2 列）
Stage7 采集执行方案：§6.4 新增小节（插在 §7 之前）/ §10 第 7 条 / §11 变更日志 v1.2
README（DDM_Core） ：§8.51 六小节（插在 §9 之前）/ §9 第 61 项

用法
----
    python -X utf8 1_Code/DDM_Core/_scratch/_apply_d77.py            # 只看计划
    python -X utf8 1_Code/DDM_Core/_scratch/_apply_d77.py --apply    # 真写
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # 仓库根（_scratch → DDM_Core → 1_Code → root）
MP = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
S7 = ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md"
RD = ROOT / "1_Code/DDM_Core/README.md"

U = "`1_Code/Experiment/exp_matlab"


def insert_after(text: str, prefix: str, block: str, tag: str) -> tuple[str, str]:
    """在**唯一**一条以 prefix 开头的行后插入 block（幂等：block 首行已在文中则跳过）"""
    first = block.split("\n")[0]
    if first.strip() and first in text:
        return text, f"[跳过] {tag}（已存在）"
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix[:40]!r} 命中 {len(hits)} 行（要求恰好 1 行）")
    i = hits[0]
    lines[i + 1:i + 1] = block.split("\n")
    return "\n".join(lines), f"[插入] {tag}（锚点 L{i + 1}）"


def insert_before(text: str, prefix: str, block: str, tag: str) -> tuple[str, str]:
    """在**唯一**一条以 prefix 开头的行前插入 block（幂等）"""
    first = block.split("\n")[0]
    if first.strip() and first in text:
        return text, f"[跳过] {tag}（已存在）"
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix[:40]!r} 命中 {len(hits)} 行（要求恰好 1 行）")
    i = hits[0]
    lines[i:i] = block.split("\n")
    return "\n".join(lines), f"[插入] {tag}（锚点 L{i + 1}）"


# ---------------------------------------------------------------- 主计划
MP_D77 = (
    "| **D77** | 2026-10-18 | ❗ **用户报的「组别 7 越界」不是程序 bug，而是文档与代码漂移了三周**。"
    "① 现象：主试运行 `Exp_Design_Formal.m`，在「被试组别」填 7 ⇒ `错误使用 Exp_Design_Formal / "
    "D4 只有 4 个 P 组（被试间），groupID=7 越界。` 整场退出。② 根因：程序的 D4 口径（4 组 / 576 试次 / "
    "3 block / 25 列 / 12 单元全部带掩蔽）从 v4 起就是对的，但 "
    f"{U}/主试培训手册_Exp_Design_Formal.md` 的 v1.2（2026-09-28）**整本还是旧的 9 条件设计**"
    "（520 试次、10 block、16 列、「组 7 = 无掩蔽」、组 5 与组 7 的对照）⇒ 主试照手册填 7、程序照 D4 拒绝。"
    "两侧各自「看着都对」，只有对照才看得见。③ 修法三层：(a) **程序 v4.2/v4.3**：把「弹窗 + 五项校验 + "
    "主试确认」的循环抽成 `exp_ask_subject_info.m`（hooks 可注入），组别只接受 1–4，越界/留空/非整数 ⇒ "
    "`warndlg` 列出「4 个 P 组速查」后**重填**（不再 `error` 退出），只有点「取消」才终止；回显 "
    "「groupID ⇒ 本组 P」且确认时输入 `r` 可重填（不必 Ctrl+C 重开）。(b) **手册 v2.0 重写**为 D4 口径"
    "（第 0 节写明「填 7 会被拒绝并要求重填」），Word 版重生成（13627 B）。(c) **三层牙齿**："
    "`test/check_input_validation.m`（**51/51**，函数级：五项校验与 NaN/非整数）、"
    "`test/check_ask_info.m`（**40/40**，路径级：填 7 → 拒 → 改 1 → 通过 / 连续 3 次非法 / `r` 重填 / "
    "取消是唯一终止 / 回显含「本组 P = ?」）、`test/check_manual_d4.py`（**40/40**，跨文件一致性："
    "程序常量 vs 手册 vs Word 版 vs 自测；旧版残留数字 `9 条件`/`520`/`10 个 block`/`16 列` 只允许出现在"
    "含「旧版/旧的/上一版」的句子里）。④ 教训：**单一产物的自测发现不了「文档与代码漂移」**，必须有一条"
    "把两者放一起比的判据；同理，凡「用户输入 → 硬 error」的路径都必须有**非屏幕**自测（hooks 注入），"
    "否则只能等人踩。 | "
    f"{U}/Exp_Design_Formal.m`（1321 行）+ `exp_check_subject_info.m`（101 行）+ "
    f"{U}/exp_ask_subject_info.m`（**新建**）+ `主试培训手册_Exp_Design_Formal.md`（v2.0，328 行）+ "
    f"{U}/test/check_ask_info.m`（**新建**，40/40）+ `test/check_manual_d4.py`（**新建**，40/40）；"
    "日志 `test/_check_input_validation.txt`（51/51）、`test/_check_ask_info.txt`（40/40）、"
    "`test/_check_manual_d4.txt`（40/40） | "
    "采集前把三条自测命令写进现场清单；任一不通过就**不得**开始正式采集。下一步仍是用户侧 "
    "Stage 1 实机验收 / Stage 6 Pilot / Stage 7 正式采集 / 定稿签批 |"
)

MP_PROG = (
    "| 2026-10-18 | **1/7**（主试侧输入防线 → D77） | "
    "**修掉「按旧手册填组别 7 就整场报错退出」**：根因是主试手册仍为旧的 9 条件设计（程序早已 D4）。"
    "程序 v4.2/v4.3 把弹窗循环抽成 `exp_ask_subject_info.m`（越界 ⇒ 弹说明重填、只有取消才终止、"
    "回显 groupID ⇒ P、可输入 `r` 重填），手册重写为 D4 口径并重生成 Word 版，再立三层牙齿"
    "（函数级 51/51、路径级 40/40、跨文件一致性 40/40）。 | 见 D77 决策行 | "
    "用户侧 Stage 1 实机验收（先跑三条自测）/ Stage 6 Pilot / Stage 7 正式采集 / 定稿签批 |"
)

MP_LOG = (
    "| 2026-10-18 | **新增 D77：主试侧输入防线 —— 组别越界不再 error 退出，手册与程序口径对齐**。"
    "① 触发 = 用户实跑报 `groupID=7 越界`；② 根因 = 手册 v1.2 仍是旧 9 条件设计（520 试次 / 10 block / "
    "16 列 / 组 7 无掩蔽），而程序早已 D4（576 试次 / 3 block / 25 列 / 4 组）；③ 修法 = "
    "`exp_ask_subject_info.m`（hooks 可注入，非法即重填）+ 手册 v2.0 + Word 重生成；④ 牙齿 = "
    "`test/check_input_validation.m` 51/51、`test/check_ask_info.m` 40/40、"
    "`test/check_manual_d4.py` 40/40（含「旧版残留数字必须以旧版口吻出现」的守卫）；⑤ 落点 = "
    "`5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md` §6.4 / §10 第 7 条 / §11 v1.2 + "
    "`1_Code/DDM_Core/README.md` §8.51 与 §9 第 61 项 |"
)

MP_FILE = (
    f"| {U}/{{exp_ask_subject_info.m（**新建**）、test/check_ask_info.m（**新建**）、"
    "test/check_manual_d4.py（**新建**）}}` + `主试培训手册_Exp_Design_Formal.md`（v2.0，**328 行**）+ "
    "`test/_check_ask_info.txt`（40/40）、`test/_check_manual_d4.txt`（40/40） | "
    "**D77 的一手证据（主试侧输入防线）**。三层各自独立：函数级 51/51 钉住「五项校验 + 越界文案」；"
    "路径级 40/40 钉住真实路径——把假 `inputdlg/warndlg/input` 注入 hooks，于是「先填 7 被拒、弹说明、"
    "改填 1 通过」在命令行跑得出来（无需屏幕/无需人在旁边）；跨文件一致性 40/40 钉住「程序常量 / 手册 / "
    "Word 版 / 自测」四者不漂移，并把旧版残留数字（`9 条件`/`520`/`10 个 block`/`16 列`）限制在"
    "「旧版」语境里（**D77**，2026-10-18） |"
)

# ---------------------------------------------------------------- Stage 7
S7_64 = """### 6.4 主试侧输入防线（D77，2026-10-18）

2026-10-18 主试在实验机运行 `Exp_Design_Formal.m`，按**旧版培训手册**在「被试组别」填了 7，程序立刻
`错误使用 Exp_Design_Formal / D4 只有 4 个 P 组（被试间），groupID=7 越界。` 并退出。根因不在程序：
D4 只有 4 个 P 组，旧手册（v1.2）整本还是 9 条件设计（520 试次 / 10 block / 16 列 / 「组 7 = 无掩蔽」）。
本轮把这条路径从「报错退出」改成「提示重填」，并补了手册与三层自测：

| 层 | 文件 | 判据 | 自测 |
|---|---|---|---|
| 程序 | `exp_ask_subject_info.m`（新） | 组别只接受 1–4；越界/留空/非整数 ⇒ 弹「4 个 P 组速查」后重填；只有「取消」才终止；回显「groupID ⇒ 本组 P」；确认时可输入 `r` 重填 | `test/check_ask_info.m` **40/40**（含「填 7 → 拒 → 改 1 → 通过」与连续 3 次非法） |
| 校验 | `exp_check_subject_info.m` | 五项（组别/编号/性别/年龄/惯用手）逐项校验，返回逐条中文说明 | `test/check_input_validation.m` **51/51** |
| 文档 | `主试培训手册_Exp_Design_Formal.md`（v2.0）+ `.docx` | 4 组速查、576 试次 / 3 block / 25 列、第 0 节写明「填 7 会被拒绝并要求重填」 | `test/check_manual_d4.py` **40/40**（程序常量 vs 手册 vs Word vs 自测） |

**现场纪律**：正式采集开始前，先在实验机跑这三条（约 20 s）：

```bat
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info"
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation"
python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```

三条全过才动机器；任一条 ❌ ⇒ 说明程序、校验或手册之一被改过且没同步，**不得**开始正式采集。

> 教训（写进本 Stage 的原因）：`check_manual_d4.py` 是**唯一**一条会把「代码」和「文档」放在一起比的判据。
> 只测代码（51/51、40/40）发现不了手册过期；只读手册也发现不了程序已改。这类漂移不会报错，只会让主试
> 在实验机上撞一次。

---

"""

S7_10 = (
    "7. **主试侧输入只在校验层挡住，挡不住「手册与程序不一致」**（D77）：程序现在会提示并重填，但若将来"
    "再改设计（比如 P 组数或试次数），**必须同时**改 `exp_ask_subject_info.m` 的组别表、`主试培训手册`"
    "与 `test/check_manual_d4.py` 的期望值，否则主试看到的仍是旧口径。该检查器只覆盖它写死的几项"
    "（4 组 / 576 试次 / 3 block / 25 列 / 四档 T / 三档 W），**新增字段要手工补进 `COLUMNS25`**。"
)

S7_11 = (
    "| v1.2 | 2026-10-18 | 新增 §6.4（主试侧输入防线，D77）：把「填组别 7 ⇒ 整场报错退出」改成「提示并重填」，"
    "并补三层牙齿（函数级 51/51、路径级 40/40、跨文件一致性 40/40）；新增 §10 第 7 条（手册改动须同步三条自测）。 |"
)

# ---------------------------------------------------------------- README
RD_851 = """### 8.51 主试侧输入防线：组别越界不再 error 退出（2026-10-18，D77）

1. **问题**：2026-10-18 主试在实验机运行 `Exp_Design_Formal.m`，按旧手册在「被试组别」填 7，程序立刻 `error('D4 只有 4 个 P 组（被试间），groupID=7 越界。')` 退出。**根因不在程序**：D4 只有 4 个 P 组（组1 P0 / 组2 P8 / 组3 P32 / 组4 P120），而 `主试培训手册_Exp_Design_Formal.md` 的 v1.2（2026-09-28）整本还是旧的 9 条件设计（520 试次 / 10 block / 16 列 / 「组 7 = 无掩蔽」/ 组 5 与组 7 的对照）⇒ 主试照手册填，程序照 D4 拒。
2. **为什么三周没人发现**：程序侧有 `check_matlab_columns.py`/`check_matlab_blocks.py` 之类的静态检查，手册侧没有；两边各自「看着都对」。**只测代码不会发现文档过期**。
3. **程序侧修法（v4.2 → v4.3）**：把「弹窗 + 五项校验 + 主试确认」的循环从脚本正文抽成 `1_Code/Experiment/exp_matlab/exp_ask_subject_info.m`：组别只接受 1–4，越界/留空/非整数 ⇒ `warndlg` 列「4 个 P 组速查」后**重填**；编号/性别/年龄/惯用手同样逐项校验；**只有点「取消」才终止**（不把 NaN 带进实验）；填完回显「groupID ⇒ 本组 P」并允许输入 `r` 重填。抽成函数的直接目的：hooks 可注入假的 `inputdlg/warndlg/input`，于是这条路径能在**命令行**跑一遍（脚本因此少约 50 行）。
4. **手册侧修法**：`主试培训手册_Exp_Design_Formal.md` 重写为 **v2.0**（328 行，D4 口径：4 组速查、576 试次 = 12 单元 × 4 类 × 12、3 block × 192、60 s 联结学习、25 列、T/W 以秒计、第 0 节写明「填 7 会被拒绝并要求重填」、FAQ 与检查清单同步），`.docx` 用 `automation/md_to_docx.py` 重生成（13627 B）。
5. **三层牙齿**：① `test/check_input_validation.m` **51/51**（函数级：五项校验、NaN/非整数、组别越界文案）；② `test/check_ask_info.m` **40/40**（路径级，headless：填 7 → 拒 → 改 1 → 通过 / 连续 3 次非法（7、空、0）/ 性别·年龄·惯用手·编号各自非法 / 确认输入 `r` 或 `R` 重填 / **取消是唯一终止** / 回显含「本组 P = 0/8/32/120」）；③ `test/check_manual_d4.py` **40/40**（跨文件一致性：`P_groups`/`T_nominal`/`W_nominal`/`nRep`/block 结构/25 列名 与手册、Word 版、自测四者对齐；旧版残留数字 `9 条件`/`520`/`10 个 block`/`16 列` 只允许出现在含「旧版/旧的/上一版」的行里；`.docx` 不得早于 `.md`）。
6. **现场用法**：正式采集前在实验机跑三条（约 20 s）——`matlab -batch "... check_ask_info"`、`matlab -batch "... check_input_validation"`、`python -X utf8 1_Code/Experiment/exp_matlab/test/check_manual_d4.py`；三条全过才动机器。教训：**「用户输入 → 硬 error」的路径必须有非屏幕自测**，否则只能等人踩；**「代码与文档」必须有一条放一起比的判据**，否则漂移不报错。

"""

RD_61 = (
    "| 61 | ✅ **主试侧输入防线：组别越界不再 error 退出（D77，§8.51）** | 程序 v4.3 把弹窗循环抽成 "
    "`exp_ask_subject_info.m`（hooks 可注入；组别只接受 1–4，越界弹「4 个 P 组速查」后重填；只有取消才终止；"
    "回显 groupID ⇒ P；`r` 可重填），手册重写为 v2.0（D4 口径）+ Word 重生成；三层牙齿 "
    "`check_input_validation` 51/51、`check_ask_info` 40/40、`check_manual_d4.py` 40/40。"
    "根因是手册仍为旧 9 条件设计（程序早已 D4），**代码与文档的漂移不报错** |"
)

PLAN = [
    (MP, "after", "| **D76** | 2026-10-17 |", MP_D77, "主计划 §5 决策 D77 行"),
    (MP, "after", "| 2026-10-17 | **8**（组级健康判据 → D76） |", MP_PROG, "主计划 §6 进度行"),
    (MP, "after", "| 2026-10-17 | **新增 D76：", MP_LOG, "主计划 §7 变更日志"),
    (MP, "after", "| `1_Code/DDM_Core/stage8_health.py`（**新建**，267 行）", MP_FILE, "主计划 §8 文件清单"),
    (S7, "before", "## 7. 现场执行清单", S7_64, "Stage7 §6.4 新小节"),
    (S7, "after", "6. **「待复核」不等于「剔除」", S7_10, "Stage7 §10 第 7 条"),
    (S7, "after", "| v1.1 | 2026-10-17 |", S7_11, "Stage7 §11 变更日志 v1.2"),
    (RD, "before", "## 9. 尚未做", RD_851, "README §8.51"),
    (RD, "after", "| 60 | ✅ **Stage 8 组级健康判据一键报告（D76，§8.50）**", RD_61, "README §9 第 61 项"),
]


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    texts = {p: p.read_text(encoding="utf-8") for p in (MP, S7, RD)}
    for path, mode, anchor, block, tag in PLAN:
        fn = insert_after if mode == "after" else insert_before
        texts[path], msg = fn(texts[path], anchor, block, tag)
        print(f"{path.name:38s} {msg}")
    if apply:
        for path, txt in texts.items():
            path.write_text(txt, encoding="utf-8", newline="\n")
        print("\n✅ 已写入 3 个文件")
    else:
        print("\n（未写入；加 --apply 生效）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
