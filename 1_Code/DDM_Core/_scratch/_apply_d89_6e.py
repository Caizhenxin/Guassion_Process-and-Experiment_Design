# -*- coding: utf-8 -*-
"""D89 落纸：Stage 1 §6-E 回填（含新判据工具）+ 主计划 D89/进度 + README §9-73。"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STAGE1 = ROOT / "5_Reference" / "08_工作流" / "Stage1_技术验证记录.md"
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)


def rep(p, old, new):
    s = read(p)
    if new in s:
        print("SKIP", p.name, old[:24])
        return
    if s.count(old) != 1:
        sys.exit("HIT %d != 1 :: %s" % (s.count(old), old[:50]))
    write(p, s.replace(old, new))
    print("OK", p.name, old[:30])


# ---------- Stage 1：新增 6-E 小节（插在 6-D 表之后、"---" 之前） ----------
SEC_E = """### 6-E 刺激内与刺激后按键的延时可比性

**口径**：`RT` 取自 `KbQueue` 的硬件时间戳，与「程序什么时候把键取走」无关；但**刺激被敲掉的时间**
（`stimulus_dur_actual`）就是「程序发现这个键」的时刻。所以可比性唯一可检验的形式是：

```
刺激内按键：0 ≤ stimulus_dur_actual − RT ≤ 1 帧        （发现延时不超过一次 vsync 等待）
刺激后按键：dur ≈ T，RT 可远大于 T                    （两者解耦，RT 不被掩蔽期"不读队列"污染）
```

工具：`1_Code/Experiment/exp_Check/check_6e_latency.py`（零依赖、只读；`--self-test` 3/3：
干净场通过、把延时改成 2.5 帧必须判红、只有刺激后按键时必须判"不可判"）。

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| 刺激内按键的检测延时 `stimulus_dur_actual − RT` | ≤ 1 帧（16.7 ms） | ✅ **235 例：1.6–16.6 ms**（v4.6 那场，组 2，576 试次；另一场截断的第 2 组 4 例：3.1–5.4 ms） |
| 刺激后按键的 `RT` 与 `dur` 解耦 | `dur ≈ T`，`RT` 可远大于 T | ✅ 300 例：落在掩蔽窗内 **225 例**（`RT−T` 2.1–199.0 ms）、掩蔽后 **75 例**（最大 1651 ms） |
| 两种路径用的是同一套取键逻辑 | 同一函数、同一时间戳源 | ✅ v4.6 起两条路径都走 `kqFirstPressUntil(deadline, tFloor)`（`Exp_Design_Formal.m:996` / `:1047`） |

> ⚠ 分析层（不属于本条判据）：这场有 **90 例 `RT < 50 ms`**（预期性/连按）。它们会被 S6-5 的"过快"条
> 与分析阶段的 `RT` 下限处理，不影响「记录延时」这一结论。

"""

rep(STAGE1,
    "| 用十六进制查看器搜不到 `0x00` 字节 | ✅ | ✅ 0 个 |\n",
    "| 用十六进制查看器搜不到 `0x00` 字节 | ✅ | ✅ 0 个 |\n\n" + SEC_E.rstrip("\n") + "\n")

rep(STAGE1,
    "**`6-A` 已回填（D88，2026-10-18 控制台确认）**，只剩 **`6-E`**。",
    "**六张表已齐**：`6-A` 于 D88 回填（控制台确认）、`6-B`–`6-D` 于 D87 按 v4.6 那场回填、`6-E` 于 D89 回填（`check_6e_latency.py` 判）。")

# ---------- 主计划 ----------
D89 = ("| **D89** | 2026-10-18 | ✅ **6-E 从「只能人看」变成「可复算」：检测延时的可检验形式是 `dur − RT ≤ 1 帧`**。"
       "① 背景：`RT` 来自 `KbQueue` 硬件时间戳，与程序何时取键无关；但刺激被敲掉的时刻 = 程序发现按键的时刻 ⇒ "
       "可比性只能落在「刺激内按键的 `stimulus_dur_actual − RT` 是否 ≤ 1 帧」这一条上；"
       "② 工具：新建 `1_Code/Experiment/exp_Check/check_6e_latency.py`（零依赖、只读、嗅探分隔符；"
       "`--self-test` 3/3：干净场通过 / 延时改成 2.5 帧必须判红 / 只有刺激后按键必须判「不可判」）；"
       "③ 实测：v4.6 那场 576 试次里刺激内按键 **235 例，延时 1.6–16.6 ms（≤ 1 帧 = 16.7 ms）**；"
       "刺激后按键 300 例，掩蔽窗内 225 例（`RT−T` 2.1–199.0 ms）、掩蔽后 75 例（最大 1651 ms）⇒ 两者解耦；"
       "④ 用户新交的 `exp_group2_subject99.txt`（**截断 + 重启追加**：80 行、正式 64 行、`trialID` 重复、只有 block 1）"
       "不能用于 6-B/6-C/6-D 的统计，但 6-E 是代码路径属性，照样可判：刺激内 4 例、延时 3.1–5.4 ms；"
       "⑤ 结论：Stage 1 六张表齐，Stage 1 可宣布完成（判据全部机器可复算）| "
       "`1_Code/Experiment/exp_Check/check_6e_latency.py`（**171 行**）、`Stage1_技术验证记录.md` §6-E、主计划 D89、README §9 第 73 项 | "
       "Stage 6 Pilot（N≈8，真被试） |\n")

PROG = ("| 2026-10-18 | **1/7**（6-E 判据工具化 → D89） | **把最后一格人看项变成可复算**：`RT` 是硬件时间戳，可比性只能检验「刺激内按键的 `dur − RT ≤ 1 帧`」；"
        "新工具 `check_6e_latency.py`（自测 3/3）在 v4.6 那场上得 235 例、1.6–16.6 ms ⇒ 6-E 通过；Stage 1 六张表齐 | Stage1 §6-E、主计划 D89 | Stage 6 Pilot（真被试） |\n")

ITEM = ("| 73 | ✅ **6-E 可复算：`dur − RT ≤ 1 帧`（D89）** | `check_6e_latency.py`（自测 3/3）：v4.6 场刺激内按键 235 例、延时 1.6–16.6 ms（≤ 16.7 ms）；"
        "刺激后 300 例与 `dur` 解耦（掩蔽窗内 225、掩蔽后 75）。Stage 1 六张表齐。 |\n")


def insert_after(path, anchor_prefix, text, marker):
    s = read(path)
    if marker in s:
        print("SKIP", path.name, marker[:20])
        return
    lines = s.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    if len(idx) != 1:
        sys.exit("anchor %r not unique: %d" % (anchor_prefix, len(idx)))
    lines.insert(idx[0] + 1, text.rstrip("\n"))
    write(path, "\n".join(lines))
    print("OK", path.name, marker[:20])


insert_after(PLAN, "| **D88** |", D89, "| **D89** |")
insert_after(PLAN, "| 2026-10-18 | **1/7**（6-A 回填 → D88） |", PROG, "（6-E 判据工具化 → D89）")
insert_after(README, "| 72 | ✅ ", ITEM, "| 73 | ✅ ")
print("done")
