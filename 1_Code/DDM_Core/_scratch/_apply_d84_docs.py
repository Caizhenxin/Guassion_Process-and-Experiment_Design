# -*- coding: utf-8 -*-
"""D84 落纸：tFloor 契约测试进主计划 / Stage1 / README，并补齐 D80–D84 的变更日志行。

为什么需要补日志行：主计划 §7 变更日志最新只到 D79，D80–D83 的决策与落纸都只在
§5/§6 里，查「这版文档改过什么」时会漏。这次一次性补齐 D80–D84。
"""
import io
import sys

MASTER, STAGE1, README = sys.argv[1], sys.argv[2], sys.argv[3]


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------- 主计划 ----------------
p = MASTER
lines = read(p).split("\n")

D84_ROW = (
    "| **D84** | 2026-10-18 | ✅ **把 v4.6 的修法钉成可执行的 tFloor 契约测试；顺带抓出测试自身的路径顺序坑（桩被 PTB 的 `KbName` 盖住）**。"
    "① 动机：v4.6 的核心修法只体现在一行 `> tFloor` 上——有人为了「修漏答」把它改回 `>=`、或干脆删掉参数，"
    "整场无屏幕冒烟**仍然全绿**（桩的按键时刻与铺助线无关），等于没有牙齿。"
    "② 做法：新建 `1_Code/Experiment/exp_matlab/test/check_kq_floor.m`（203 行），从 `Exp_Design_Formal.m` **原文抽取** "
    "`kqFirstPressUntil` / `kqScan` / `resolveEscKeyCode` 写进临时目录（不复刻逻辑，测的就是将要发布的那份代码），"
    "配受控的 `GetSecs` / `WaitSecs` / `KbQueueCheck`（全局 `KQF_NOW` / `KQF_TS` / `KQF_CODES`）跑十例：C1 早于 tFloor 不返回、"
    "C2 **不传 floor 时必须返回同一键**（反向有牙）、C3 +1 ms 返回、C4 恰等于 tFloor 不返回、C5 恰等于 deadline 返回、"
    "C6 晚于 deadline 不返回、C7 两键取最早、C8 无键则空、C9 Esc 只计数、C10 早键被挡后窗口内后一键仍取到（D83 机制）。"
    "③ 首轮 **5/10**：C2/C3/C5/C7/C10 全红、只有 Esc 绿（C9）以及「不返回」类（C1/C4/C6/C8）绿。"
    "根因不在被测代码：`PsychStartup` 已把 PTB 的 `KbName` 放到 path **最前**，测试却用 `addpath(stubsDir, '-end')` 把桩加在后面 ⇒ "
    "`KbName('f')` 返回 **70**（PTB 口径）而不是桩的 **6**，`f/j` 永远匹配不上；Esc 的 27 两种口径一致才碰巧绿。"
    "④ 修正（D84/路径）：`addpath(stubsDir, '-begin')` 再 `addpath(tmpDir, '-begin')` ⇒ **10/10**。"
    "⑤ 牙齿：结果落盘 `test/_kq_floor_result.txt`（`SUMMARY pass=10 fail=0`），`test/check_full_session.py` 新增 B27–B29"
    "（十条用例齐 / 桩必须压在 PTB 之前 / 日志 pass=10 fail=0）⇒ **26 → 29/29**。"
    "⑥ 边界：这是**开发者回归**，不进现场六条（主试不必每次跑）；它也不测真实键盘延时，只测边界语义。"
    " | `test/check_kq_floor.m`（203 行）、`test/_kq_floor_result.txt`、`check_full_session.py`（29 项） | 无（主试运行手册仍是六条） |"
)

PROGRESS_ROW = (
    "| 2026-10-18 | **6**（v4.6 修法的契约测试 → D84） | **把「onset 之前的键不算反应」从注释变成断言**："
    "`check_kq_floor.m` 从程序原文抽取三个函数、十例全过（10/10），并用 C2 反向证明测试有牙；"
    "顺带抓出测试自身的坑 —— 桩目录必须压在 PTB 之前，否则 `KbName('f')` 拿到 70（首轮 5/10，只有 Esc 绿）；"
    "`check_full_session.py` 由 26 增到 **29/29**。 |"
)

CHANGELOG_ROWS = [
    "| 2026-10-18 | **新增 D80（W/T 取点答疑）**：设计文档 §3.3（六小节 + 净可按键窗口表 + 截止→漏答经验曲线表，351 行）+ v2.5 变更行；新建 `check_manipulation.py`（183 行）；主计划 D80 + Stage 6「W 操纵检查」交付项；**程序不改**（块序共线作为限制写入 D80）。 |",
    "| 2026-10-18 | **新增 D81（Stage 1 判据回放）**：`check_stage1_acceptance.py` 440 → 516 行（六处隐含 60 Hz 假设 + 环境门 `--expect-hz`）；Stage1 §6 判据文字订正 + 「设备前提」段（463 行）；README §8.54 + §9-64；手册 v2.4（383 行 / docx 16044 B）。 |",
    "| 2026-10-18 | **新增 D82（被试材料）**：`Stage6_被试招募与知情同意包.md`（166 行）+ `check_consent_pack.py`（28/28、自测 5/5）；机构项一律留 `【】` 不代填。 |",
    "| 2026-10-18 | **新增 D83（onset 之前的按键）**：程序 v4.6（`kqFirstPressUntil(deadline, tFloor)`，四个调用点全传 `stimulusFlipTime`）；`check_full_session.py` 26/26；Stage1 §6 回填 6-B/6-C/6-D、README §8.57、手册 v2.5；D83b 修检查器只认制表符（516 → 537 行）、D83c 修 `read_formal_data.py` 同一漂移。 |",
    "| 2026-10-18 | **新增 D84（tFloor 契约测试）**：`test/check_kq_floor.m`（203 行、十例 10/10）+ `_kq_floor_result.txt` + `check_full_session.py` 26 → 29；D84/路径记「桩目录必须压在 PTB 之前，否则 `KbName('f')`=70」。 |",
]

# D84 决策行：插在 D83 行之后
i83 = next(i for i, ln in enumerate(lines) if ln.startswith("| **D83** | 2026-10-18 |"))
assert "D84" not in "\n".join(lines)
lines.insert(i83 + 1, D84_ROW)

# 进度行：插在 D83 进度行之后
ip = next(i for i, ln in enumerate(lines) if ln.startswith("| 2026-10-18 | **6**（实机回放抓缝 → D83）"))
lines.insert(ip + 1, PROGRESS_ROW)

# 变更日志：插在最后一条（D79）之后
il = max(i for i, ln in enumerate(lines) if ln.startswith("| 2026-10-18 | **新增 D79"))
for k, row in enumerate(CHANGELOG_ROWS):
    lines.insert(il + 1 + k, row)

write(p, "\n".join(lines))
print("master: +%d 行" % (1 + 1 + len(CHANGELOG_ROWS)))

# ---------------- Stage1 ----------------
p = STAGE1
s = read(p)
reps = [
    ("| `check_full_session.py` | `== 通过 23 / 未通过 0 ==` |",
     "| `check_full_session.py` | `== 通过 29 / 未通过 0 ==` |"),
    ("产物已回读通过；含 2 条反例自检 |",
     "产物已回读通过；含 2 条反例自检，以及 D84 的 B27–B29（tFloor 契约测试三条牙齿） |"),
    ("六条全过才动机器。任一条 ❌",
     "六条全过才动机器（另有一条**开发者回归** `check_kq_floor` 见下，不进现场纪律）。任一条 ❌"),
    ("由「整场无屏幕冒烟」`runbatch_full_session` 27/27 + `check_full_session.py` 23/23 钉住。",
     "由「整场无屏幕冒烟」`runbatch_full_session` 27/27 + `check_full_session.py` 29/29 钉住。"),
]
for old, new in reps:
    assert s.count(old) == 1, (old[:40], s.count(old))
    s = s.replace(old, new)

anchor = "由「整场无屏幕冒烟」`runbatch_full_session` 27/27 + `check_full_session.py` 29/29 钉住。\n"
add = anchor + """
另（D84）：v4.6 的修法只体现在一行 `> tFloor` 上，改回 `>=` 或删掉参数时**整场冒烟照样全绿**
（桩的按键时刻与铺助线无关）。因此补了一条**契约测试**，它不进现场六条、只在改程序后跑：

```bat
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_kq_floor"
```

期望 `SUMMARY pass=10 fail=0`。它从 `Exp_Design_Formal.m` **原文抽取** `kqFirstPressUntil` / `kqScan` /
`resolveEscKeyCode` 再测（不复刻逻辑），十例覆盖：早于 onset 不返回、不传 floor 时必须返回（反向有牙）、
+1 ms 返回、恰等于 onset 不返回、恰等于 deadline 返回、晚于 deadline 不返回、两键取最早、无键则空、
Esc 只计数、早键被挡后窗口内后一键仍取到。结果同时落盘 `test/_kq_floor_result.txt`，由
`check_full_session.py` 的 B27–B29 复核。**坑**：桩目录必须用 `-begin` 压在 PTB 之前，
否则 `KbName('f')` 返回 70（PTB 口径）而不是桩的 6，`f/j` 永远匹配不上（首轮 5/10、只有 Esc 绿）。
"""
assert s.count(anchor) == 1
s = s.replace(anchor, add)
write(p, s)
print("stage1: 4 处替换 + 1 段新增")

# ---------------- README ----------------
p = README
s = read(p)
old = "静态判据补 A8b/A11/A12 ⇒ `test/check_full_session.py` **26/26**，\n无屏幕冒烟两组仍 **27/27**。"
new = """静态判据补 A8b/A11/A12 ⇒ `test/check_full_session.py` **26/26**，
无屏幕冒烟两组仍 **27/27**。

**牙齿补强（D84）**：`> tFloor` 这一行很容易在「修漏答」时被改回 `>=` 或被删参数，而整场冒烟**照样全绿**
（桩的按键时刻与铺助线无关）。新建 `test/check_kq_floor.m`（203 行）把这层语义钉成十例：
它从程序**原文抽取** `kqFirstPressUntil` / `kqScan` / `resolveEscKeyCode` 再测（不复刻逻辑），
C2 是反向用例（不传 floor 时必须返回同一键 ⇒ 证明测试有牙）。首轮 **5/10**：根因是 `PsychStartup`
已把 PTB 的 `KbName` 放到 path 最前，桩用 `-end` 加在后面 ⇒ `KbName('f')` 返回 **70** 而非 **6**，
`f/j` 永远匹配不上（Esc=27 两种口径一致才绿）；改成 `addpath(stubsDir, '-begin')` 再 `addpath(tmpDir, '-begin')`
⇒ **10/10**。结果落盘 `test/_kq_floor_result.txt`，`check_full_session.py` 加 B27–B29 ⇒ **29/29**。
它是开发者回归，不进现场六条。"""
assert s.count(old) == 1
s = s.replace(old, new)

row68 = "| 68 | ✅ **`onset` 之前的按键：契约测试把修法钉成断言（D84，§8.57）** | `test/check_kq_floor.m`（203 行）从程序原文抽取 `kqFirstPressUntil`/`kqScan` 再测，十例 10/10（含反向用例）；顺带修掉测试自身「桩被 PTB 的 `KbName` 盖住」的坑（`KbName('f')`=70 而非 6，首轮 5/10）；`check_full_session.py` 26 → 29/29。 |\n"
last = next(i for i, ln in enumerate(s.split("\n")) if ln.startswith("| 67 | ✅ **`onset` 之前的按键被当成反应"))
lines = s.split("\n")
lines.insert(last + 1, row68.rstrip("\n"))
write(p, "\n".join(lines))
print("readme: §8.57 补段 + §9-68")
