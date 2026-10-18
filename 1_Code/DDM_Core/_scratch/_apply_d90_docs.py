# -*- coding: utf-8 -*-
"""D90 落纸：主计划 §2 阶段总览 + D90 决策行 + 进度行 + 变更日志；README §8.61 + §9-74；
主试手册 v2.5 → v2.6（新增 §7.z，程序版本 v4.6 → v4.7，顺手修两处被 \t 吃掉的字符）。

全部 newline="\n" 写回，幂等（已存在则跳过 / 断言命中一次）。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
MANUAL = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "主试培训手册_Exp_Design_Formal.md"

STAGE1_OLD_PREFIX = "| **1** | 程序技术验证与修正 | 你（实机） |"
STAGE1_NEW = (
    "| **1** | 程序技术验证与修正 | 你（实机） | 🟢 完成（**六张表已齐**，2026-10-18） | "
    "✅ D5 试次终止逻辑 + 4 项技术修正 + 追加要求全部落到 `Exp_Design_Formal.m`（现 **v4.7**，1460 行），"
    "产出物 [`Stage1_技术验证记录.md`](Stage1_技术验证记录.md) §6 六张表全填："
    "**6-A** 掩蔽纹理预加载回显（D88）、**6-B/6-C/6-D** 由 v4.6 的 60 Hz 实机 576 试次回填（D87，"
    "同时修掉判据自身两处误判）、**6-E** 由截断场次判（D89，可检验形式是 `dur − RT ≤ 1 帧`）。"
    "⚠ 那场是主试按键试跑，只作「程序能跑通、25 列齐、576 试次结构对」的连通性证据；"
    "**真被试数据从 Stage 6 起算** |"
)

STAGE6_OLD_PREFIX = "| **6** | Pilot 技术试测 | 你 |"
STAGE6_NEW = (
    "| **6** | Pilot 技术试测 | 你 | 🟡 进行中（**只等真被试 N≈8**；方案 + 判据 + 工具链已就绪） | "
    "产出物 [`Stage6_Pilot方案.md`](Stage6_Pilot方案.md)（N=8 推荐 / 每人完整 576 试次 / "
    "9 条事前登记判据 / 六例自测全过）；三条阈值已用 `analyze_rt_baseline.py` 的 **87 份历史真人数据**锚定"
    "（D85）。⚠ 2026-10-18 那场判为**主试按键试跑**（RT 中位 0.069 s、过快 56.2%、四条 T 档正确率都贴 0.5），"
    "**不计入 N=8** |"
)

D90_ROW = (
    "| **D90** | 2026-10-18 | ✅ **块首指导语被上一屏的空格穿透：8 处空格等待缺「松键门槛」，程序升 v4.7**。"
    "① 用户实机报告：第一次出现的块首 C6 指导语「好像没按空格就进入正式实验了」。"
    "② 根因（逻辑错误，与 D83 同族：时间边界只判**电平**、不判**沿**）：8 处「按空格继续」"
    "（`:418` / `:460` / `:495` / `:825` / `:880` / `:1157` / `:1178` / `:1203` 的 flag 行与紧随的 `while`）"
    "全部用 `KbCheck` 忙等「此刻空格是否按着」；练习结束休息屏与块首 C6 屏之间只隔一次 `Screen('Flip')` "
    "与建表（几十毫秒），上一屏确认用的空格按住 ≥50 ms 就够穿透。"
    "③ 修法：新增局部函数 `waitForSpaceRelease()`（最多等 5 s 见到「所有键松开」，`WaitSecs(0.005)` + "
    "`checkEscape()`），在每个 flag 行后、`while` 之前调用一次（8 处）；头注加 v4.7 段。"
    "④ 验证：`runbatch_full_session(2, 99)` / `(1, 99)` 均 **27/27**；`check_full_session.py` 29 → **30 项**"
    "（新增 A13：函数存在 + 调用恰 8 次 + v4.7 段头注在）；`checkcode` 仍 8 条旧类型告警、无语法错。"
    "⑤ 边界：只改等待方式，不动试次时序与数据列；v4.6 及更早场次里「某组首个试次 timeout/premature_press」"
    "可能由此产生，分析时作备注即可，不必作废整场 | "
    "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.6 → **v4.7**，1460 行） + "
    "`1_Code/Experiment/exp_matlab/test/check_full_session.py`（+A13，29 → **30 项**） | "
    "用户侧用 v4.7 在实验室机跑第一名**真被试** Pilot |"
)

PROGRESS_ROW = (
    "| 2026-10-18 | **1 → 6**（Stage 1 收口 + D90 空格穿透） | "
    "6-A 回填（D88）、6-E 判完并工具化（D89）⇒ Stage 1 六张表齐、阶段总览置 🟢；"
    "随后用户报告块首指导语一闪而过 ⇒ 定位到 8 处 `KbCheck` 忙等缺「松键门槛」，"
    "程序升 **v4.7**；两组无屏幕冒烟仍 27/27、`check_full_session.py` 29 → 30 项 | "
    "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.6 → **v4.7**，1460 行） + "
    "`1_Code/Experiment/exp_matlab/test/check_full_session.py`（+A13，**30 项**） | "
    "用 v4.7 在实验室机跑第一名**真被试** Pilot（N≈8 的第 1 人） |"
)

CHANGELOG_ROW = (
    "| 2026-10-18 | 新增 **D90**（块首指导语被上一屏空格穿透：8 处空格等待加「先等松键」门槛，"
    "程序升 **v4.7**）；§2 阶段总览把 **Stage 1 置 🟢 完成**、Stage 6 改「只等真被试」；"
    "主试手册升 v2.6（新增 §7.z） |"
)

README_SECTION = """### 8.61 等待「按空格」不能只看电平（2026-10-18，D90）

**问题**：8 处「按空格继续」都用 `KbCheck` 忙等「此刻空格是否按着」，没有按下沿 / 松开沿的概念。上一屏确认用的空格若还按着（**≥50 ms 就够**），下一屏的 `while` 立刻被这个残留按下穿透——用户实机看到的症状是块首 C6 指导语一闪而过，被试还没读到「本组反应窗口：800 毫秒」就进了正式试次，那一个试次通常白丢。

**为什么两屏会挨得这么近**：练习结束休息屏（「已完成练习，休息后按空格键进入正式实验」）与块首 C6 屏之间只隔一次 `Screen('Flip')` 与一张 trial 表的生成（几十毫秒），没有任何「必须松手」的阻断。

**修法**：新增局部函数 `waitForSpaceRelease()`——最多等 5 s 见到「所有键都松开」（`WaitSecs(0.005)` 轮询 + `checkEscape()`，超时即返回，防键卡死时死结），在每个 `waitForSpace = true;` / `waitingForSpace = true;` 之后、进入 `while` 之前调用一次，共 **8 处**；程序升 **v4.7**。它只改「这次按键算不算数」，不动试次时序与数据列。

**牙齿**：`test/check_full_session.py` 加 **A13**（`waitForSpaceRelease` 函数存在 + 调用恰 8 次 + 头注 v4.7 段在），**29 → 30 项**；两组无屏幕冒烟仍 27/27（桩的 `KbCheck` 本来就是「每 550 ms 里按 50 ms」，先等松再等按能走通）。

**边界**：v4.6 及更早跑出的场次里，凡「某组第一个试次 `timeout` / `premature_press=1`」都可能由这条造成；不必作废整场，但分析时要作备注（该组的窗口数可能没被被试读到）。

**教训**：这是 D83 的同族缺陷——**时间边界只判「电平」不判「沿」**。凡「等一个动作」，都要问清是在等状态还是在等事件；等状态就会把上一次的残留当成这一次的意图。

"""

README_ITEM74 = (
    "| 74 | ✅ **块首指导语被上一屏的空格穿透（D90，§8.61）** | "
    "8 处 `KbCheck` 忙等只判「此刻是否按着」，上一屏确认的空格按住 ≥50 ms 就穿透 ⇒ 指导语一闪而过；"
    "新增 `waitForSpaceRelease()`（先等全松，最多 5 s）接入 8 处，程序 **v4.7**；"
    "`check_full_session.py` 加 A13 后 **30/30** | "
    "`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.7，1460 行）、"
    "`1_Code/Experiment/exp_matlab/test/check_full_session.py`（30 项） |\n"
)

MANUAL_SECTION = """### 7.z 「块首指导语一闪而过、没按空格就进了正式实验」（v2.6 新增，2026-10-18）

- **现象**：每组开始前那张「本组反应窗口：800 毫秒 / 准备好后按空格键开始本组」的指导语只闪一下，被试还没读完就进了第一个试次；被试因此不知道本组窗口是多少，那一个试次通常白丢。
- **成因**（v4.6 及更早）：相邻两处「按空格继续」都用 `KbCheck` 忙等「此刻空格是否按着」，没有「按下沿」的概念。上一屏（练习结束休息屏）确认用的空格若还按着，下一屏的循环立刻被穿透——两屏之间只隔一次 `Screen('Flip')` 与几十毫秒建表时间，**按住 50 ms 就够**。
- **v4.7 已修**：新增 `waitForSpaceRelease()`，8 处空格等待之前都先等一次「所有键都松开」（最多等 5 s，防键卡死）再等新的按下。
- **怎么确认跑的是 v4.7**：`type Exp_Design_Formal.m | findstr "v4.7"`，应打印 ★★ v4.7 本次修正 段头注。
- **已生成的数据怎么办**：v4.6 及更早的场次里，若某组的第一个试次是 `timeout` 或 `premature_press=1`，可能就是这条造成的。不用作废整场，但在分析里备注「该组首个试次的反应窗口可能未被读到」；v4.7 起不再出现。

"""


def replace_line_with_prefix(text, prefix, new_line):
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, "锚点 %r 命中 %d 次" % (prefix, len(hits))
    lines[hits[0]] = new_line
    return "\n".join(lines)


def insert_after_line_with_prefix(text, prefix, new_line):
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) >= 1, "锚点 %r 未命中" % prefix
    lines.insert(hits[-1] + 1, new_line)
    return "\n".join(lines)


def main():
    # ---------------- 主计划 ----------------
    plan = PLAN.read_text(encoding="utf-8")
    n0 = len(plan.split("\n"))
    plan = replace_line_with_prefix(plan, STAGE1_OLD_PREFIX, STAGE1_NEW)
    plan = replace_line_with_prefix(plan, STAGE6_OLD_PREFIX, STAGE6_NEW)
    if "| **D90** |" not in plan:
        plan = insert_after_line_with_prefix(plan, "| **D89** |", D90_ROW)
    if "D90 空格穿透" not in plan:
        # 进度表：插在 `## 7. 变更日志` 之前最后一行 2026 行之后
        lines = plan.split("\n")
        h = next(i for i, ln in enumerate(lines) if ln.startswith("## 7. 变更日志"))
        idx = max(i for i in range(h) if lines[i].startswith("| 2026-"))
        lines.insert(idx + 1, PROGRESS_ROW)
        plan = "\n".join(lines)
    if "新增 **D90**" not in plan:
        lines = plan.split("\n")
        h = next(i for i, ln in enumerate(lines) if ln.startswith("## 7. 变更日志"))
        end = next((i for i in range(h + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        idx = max(i for i in range(h, end) if lines[i].startswith("| 2026-"))
        lines.insert(idx + 1, CHANGELOG_ROW)
        plan = "\n".join(lines)
    PLAN.write_text(plan, encoding="utf-8", newline="\n")
    print("plan: %d → %d 行" % (n0, len(plan.split("\n"))))

    # ---------------- README ----------------
    rd = README.read_text(encoding="utf-8")
    n1 = len(rd.split("\n"))
    if "### 8.61" not in rd:
        lines = rd.split("\n")
        h9 = next(i for i, ln in enumerate(lines) if ln.startswith("## 9."))
        lines[h9:h9] = README_SECTION.rstrip("\n").split("\n") + [""]
        rd = "\n".join(lines)
    if "| 74 |" not in rd:
        lines = rd.split("\n")
        h73 = next(i for i, ln in enumerate(lines) if ln.startswith("| 73 |"))
        lines.insert(h73 + 1, README_ITEM74.rstrip("\n"))
        rd = "\n".join(lines)
    README.write_text(rd, encoding="utf-8", newline="\n")
    print("readme: %d → %d 行" % (n1, len(rd.split("\n"))))

    # ---------------- 手册 ----------------
    man = MANUAL.read_text(encoding="utf-8")
    n2 = len(man.split("\n"))
    assert "（v4.6）" in man
    man = man.replace("（v4.6）", "（v4.7）", 1)
    man = man.replace(
        "> 版本：v2.5（2026-10-18，v2.5 补",
        "> 版本：v2.6（2026-10-18，v2.6 补「指导语一闪而过」症状与 v4.7 松键门槛；v2.5 补",
        1,
    )
    # 两处被 \t 吃掉的字符（v2.5 落纸时的转义残留）
    man = man.replace("\tFloor", "`tFloor`").replace("\type Exp_Design_Formal.m", "`type Exp_Design_Formal.m")
    man = man.replace('findstr "v4.6"', 'findstr "v4.7"').replace(
        "★★ v4.6 本次修正 段头注", "★★ v4.7 本次修正 段头注"
    )
    man = man.replace("**怎么确认跑的是 v4.6**", "**怎么确认跑的是 v4.7**")
    if "### 7.z" not in man:
        lines = man.split("\n")
        h8 = next(i for i, ln in enumerate(lines) if ln.startswith("## 8. 数据当场核对清单"))
        lines[h8:h8] = MANUAL_SECTION.rstrip("\n").split("\n") + [""]
        man = "\n".join(lines)
    MANUAL.write_text(man, encoding="utf-8", newline="\n")
    print("manual: %d → %d 行" % (n2, len(man.split("\n"))))


if __name__ == "__main__":
    main()
