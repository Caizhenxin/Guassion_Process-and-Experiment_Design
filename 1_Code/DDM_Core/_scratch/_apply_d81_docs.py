# -*- coding: utf-8 -*-
"""D81 落纸：主计划决策/进度、Stage1 §6 判据订正 + 设备前提、README §8.54 + §9 第 64 项。

背景：2026-10-18 主试用本机（165 Hz）跑了一场并把产物交回来。用
`1_Code/Experiment/exp_Check/check_stage1_acceptance.py` 回放 Stage 1 的机器判据时，
它把正常数据判成缺陷——六处判据都隐含「显示器是 60 Hz、程序零余量」。修完后
只剩一条真差异（165 Hz 下 44 行刺激多停 2–25 帧），而主试说明实验室机是 60.004 Hz，
本机只是临时环境。于是再加一道「环境门」：数据不是来自实验室那块屏时，明确降级为
连通性证据。

幂等：断言每处命中恰好 1 次；以 newline="\\n" 写回（D79 起 `edit` 工具曾写回 CRLF）。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MASTER = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
STAGE1 = REPO / "5_Reference" / "08_工作流" / "Stage1_技术验证记录.md"
README = REPO / "1_Code" / "DDM_Core" / "README.md"

D81_ROW = (
    "| **D81** | 2026-10-18 | ✅ **用实机产物回放 Stage 1 判据，抓出检查器六处隐含「60 Hz 假设」的误判，并给检查器加了一道环境门**。"
    "① 动机：主试跑通程序后交回 `1_Code/Experiment/exp_matlab/exp_group1_subject1.txt` 与同场 `EXP_data_group1_1.csv`，"
    "`check_stage1_acceptance.py` 报 4 条强制 ❌，字面读是「实机时序不合格」。"
    "② 六处误判（全部是检查器的错，不是数据的错）：`estimate_flip()` 用 `T/frames` 反推（应 `dur/frames`，165 Hz 被算成 171.6 Hz）、"
    "`|dur−T| < 1 帧`（程序口径本允许 +0~1 帧，88% 正常行被判死）、`frames == round(T/flip)`（该列是实际时长帧数）、"
    "掩蔽容差 1e-6（实测差值正好 ±1e-6 秒级浮点尘土，62 行误判）、6-B 最小 T 档写死 `2/60`（165 Hz 下最小档是 5 帧 = 30.3 ms）、"
    "未按 `trialID` 去重（txt 588 行 vs CSV 576 行）。"
    "③ 去重背后的真相：`fopen(...,'a+')` 追加写 + 主试先后跑 3 次、前两次各在第 6 个试次处崩（D78 的「第一个未响应试次崩」）"
    "⇒ `trialID` 1–6 各出现 3 次，CSV 是最后一次的 `cell2table` 快照。"
    "④ 修完后只剩一条真差异：576 行里 74 行时长偏离 —— **30 行**是 v4.4 的抢按把刺激截成 1 帧（v4.5 已修，该次是旧版跑的）、"
    "**44 行**是 165 Hz 下每帧只有 6.06 ms 绘制预算导致的掉帧（+2…+25 帧）。主试确认实验室机是 **60.004 Hz**，本机 165 Hz 只是临时测试环境。"
    "⑤ 于是加**环境门**（`--expect-hz`，默认 60.004）：反推刷新率与实验室口径相差 >1% 时，判定「该数据只作连通性证据，不作 Stage 1 帧量化依据」。"
    "⑥ 牙齿：检查器自测 **6/6** 仍全过；`1_Code/Experiment/exp_Check/check_stage1_acceptance.py` 484 → **516 行**；"
    "Stage1 §6 的 6-C 判据文字同步订正（文档原先写的就是错口径）。"
)

PROGRESS_ROW = (
    "| 2026-10-18 | **6**（Stage 1 判据回放 → D81） | **把「检查器报红」与「数据不合格」分开**："
    "拿主试实机产物（165 Hz 临时环境）回放 6-B/6-C/6-D，查出检查器六处隐含 60 Hz 假设的误判并逐条修正；"
    "同时发现 txt 是追加写、崩溃重跑会留下重复 `trialID`（588 行 vs CSV 576 行），加去重 + 环境门。"
    "结论：**本机数据只作连通性证据**，Stage 1 的三张表要等实验室机（60.004 Hz）那一场。 |"
)

STAGE1_6C_OLD = """```
|stimulus_dur_actual − T| < FlipIntv          （即 < 1 帧）
stimulus_frames == T / FlipIntv              （即 T 的帧数）
stimulus_offset_actual == mask_onset_actual
```

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 < 1 帧 | |
| 全部无刺激期按键试次的 `stimulus_frames` | 分别 = 2 / 5 / 9 / 15 | |
| `max \\|stimulus_dur_actual − T\\| / FlipIntv` | < 1 | |"""

STAGE1_6C_NEW = """> **判据口径（D81 订正）**：程序写进第 25 列的是 `round(stimulus_dur_actual / FlipIntv)`，
> 而实际在屏时长本来就允许比名义 T **多 0~1 帧**（vsync 余量，见 §7 第 2 条）。原先这里写
> `|dur − T| < 1 帧` 是**错的口径**：它把 88% 的正常行判死。正确的三条是

```
−0.5 ≤ (stimulus_dur_actual − T) / FlipIntv < 1.5      （下界防刺激被截断，上界 = 1 帧余量 + 半帧容差）
stimulus_frames == round(stimulus_dur_actual / FlipIntv)
stimulus_offset_actual == mask_onset_actual
mask_onset_actual == stimulus_onset_actual + stimulus_dur_actual   （容差 1e-5 秒，秒级浮点尘土是 ±1e-6）
```

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 ≤ 1 帧 | |
| 全部无刺激期按键试次的 `stimulus_frames` | 分别 ≈ 2 / 5 / 9 / 15（±1 帧） | |
| `max (stimulus_dur_actual − T) / FlipIntv` | ∈ [−0.5, +1.5) | |"""

STAGE1_DEVICE = """### 设备前提（D81，**先看这一条**）

6-B/6-C/6-D 的每一条都依赖「这块屏是实验室那块 **60.004 Hz** 的屏」：

- 60.004 Hz ⇒ 帧长 16.6656 ms，T 的四个档位才正好是 **2 / 5 / 9 / 15 帧**（33.33 / 83.33 / 149.99 / 249.98 ms）；
- 换成 120 / 144 / 165 Hz 的屏，程序会按毫秒取整成别的帧数（本机 165 Hz 实测 5 / 14 / 25 / 41 帧），
  而每帧可用的绘制预算也从 16.67 ms 掉到 6.06 ms —— 2026-10-18 本机那一场就有 44/576 行刺激多停了 2–25 帧。

所以：**本机/笔记本上的数据只能证明「程序能跑通、能写出 25 列」**（连通性证据），
要回填下面的表，必须在实验室机上重跑一场。检查器会用 `--expect-hz`（默认 60.004）自动判这一层，
刷新率不符时打印「证据降级」而不是把数据判成缺陷。

### 6-A 掩蔽纹理预加载"""

README_SECTION = """### 8.54 检查器里的隐含常量：60 Hz、1 帧容差、1e-6 秒（2026-10-18，D81）

**问题**：`1_Code/Experiment/exp_Check/check_stage1_acceptance.py` 上线时只用自己造的 60 Hz 合成数据自测过。
拿主试实机产物回放，它报 4 条强制 ❌ —— 逐条核对数值后，**四条全是检查器的错**：

1. **`estimate_flip()` 用错了分子**：`T / stimulus_frames` 反推帧长；但第 25 列写的是
   `round(stimulus_dur_actual / FlipIntv)`（实际时长），165 Hz 被反推成 171.6 Hz（低 4%）。
2. **`|dur − T| < 1 帧` 与程序设计矛盾**：程序本来就允许「实际时长 = 名义 T + 0~1 帧」（vsync 余量），
   1 帧容差把 88% 的正常行判死；正确区间是 `[−0.5, +1.5)` 帧。
3. **`frames == round(T/flip)` 比错基准**：该列是**实际**时长的帧数，应比 `round(dur/flip)`。
4. **掩蔽容差 1e-6 秒过紧**：实测 `mask − onset − dur` 的差值正好是 **±1e-6**（秒级浮点尘土）⇒ 62 行误判。
5. **6-B 把最小 T 档写死成 `2/60`**：高刷屏下最小档是 5 帧 = 30.3 ms，写死会让「明明有刺激期内按键」的数据被判成没记到。
6. **未按 `trialID` 去重**：txt 通道是 `fopen(...,'a+')` 追加写，主试先后跑 3 次、前两次各在第 6 个试次处崩
   （D78 的「第一个未响应试次崩」）⇒ txt 有 588 行而 CSV 只有 576 行（`trialID` 1–6 各出现 3 次）。

**做法**：逐条改成与程序真实口径一致（`dur/frames` 反推、`[−0.5,+1.5)` 帧、`round(dur/flip)`、
1e-5 秒容差、最小 T 档取数据实测值、`dedupe()` 保留最后一次出现并打印丢弃行数），
再加一道**环境门** `--expect-hz`（默认 60.004）：反推刷新率与实验室口径相差 >1% 时打印
「证据降级：该数据只作连通性证据，不作 Stage 1 帧量化依据」。检查器 440 → **516 行**，自测 **6/6** 仍全过。

**修完后的真相**：576 行里 74 行时长偏离 —— **30 行**是 v4.4 的抢按把刺激截成 1 帧
（v4.5 的 `KbQueueFlush()` 已修，该次是旧版跑的）、**44 行**是 **165 Hz** 下每帧只有 6.06 ms 绘制预算导致的掉帧
（+2…+25 帧 = 12–152 ms）。主试确认实验室机是 **60.004 Hz**、本机 165 Hz 只是临时测试，
所以这 44 行**不是设计缺陷**，是临时环境的产物。

**牙齿**：`--self-test` 6/6（干净放行；`--defect-1f` 拦住 6-C；`--defect-mismatch` 与三种变异拦住 6-D/0 口径）。

**边界**：环境门只降级证据等级，不判死数据；反过来，它也不能证明 60 Hz 机上就没问题 ——
要回填 Stage 1 §6 的三张表，仍然必须在实验室机上重跑一场。

"""

README_ITEM = (
    "| 64 | ✅ **检查器的隐含常量：60 Hz、1 帧容差、1e-6 秒（D81，§8.54）** | "
    "`check_stage1_acceptance.py` 只用自造的 60 Hz 合成数据自测过，换成 165 Hz 实机数据回放就报 4 条 ❌；"
    "逐条核对后**四条全是检查器的错**：`T/frames` 反推帧长（应 `dur/frames`）、`|dur−T|<1 帧`（程序口径本就允许 +0~1 帧）、"
    "`frames==round(T/flip)`（该列是实际时长帧数）、掩蔽容差 1e-6（实测差值正好 ±1e-6）。另加 `trialID` 去重"
    "（txt 追加写 ⇒ 崩溃重跑留下重复行）与 `--expect-hz` 环境门。 |\n"
)


def apply(path: Path, edits: list[tuple[str, str, str]]) -> bool:
    src = path.read_text(encoding="utf-8")
    ok = True
    for name, old, new in edits:
        n = src.count(old)
        if n != 1:
            print(f"❌ {path.name} [{name}] 命中 {n} 次（要求 1 次）")
            ok = False
            continue
        src = src.replace(old, new)
        print(f"✅ {path.name} [{name}]")
    if ok:
        path.write_text(src, encoding="utf-8", newline="\n")
    return ok


def main() -> int:
    r1 = True
    # D81 决策行插在 D80 行之后（保持 D 编号递增）
    m_lines = MASTER.read_text(encoding="utf-8").split("\n")
    d80 = [i for i, ln in enumerate(m_lines) if ln.startswith("| **D80** |")]
    if any(ln.startswith("| **D81** |") for ln in m_lines):
        print("⏭  主计划 [D81 决策行] 已存在")
    elif len(d80) == 1:
        m_lines.insert(d80[0] + 1, D81_ROW)
        MASTER.write_text("\n".join(m_lines), encoding="utf-8", newline="\n")
        print("✅ 主计划 [D81 决策行]")
    else:
        print(f"❌ 主计划 [D81 决策行] D80 行命中 {len(d80)} 次")
        r1 = False
    # 进度行要追加在那一行之后：单独处理
    src = MASTER.read_text(encoding="utf-8")
    lines = src.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| 2026-10-18 | **5 + 1**")]
    if len(idx) == 1 and not any(ln.startswith("| 2026-10-18 | **6**") for ln in lines):
        lines.insert(idx[0] + 1, PROGRESS_ROW)
        MASTER.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print("✅ 主计划 [进度行 D81]")
    elif any(ln.startswith("| 2026-10-18 | **6**") for ln in lines):
        print("⏭  主计划 [进度行 D81] 已存在")

    r2 = apply(STAGE1, [
        ("订正 6-C 判据文字", STAGE1_6C_OLD, STAGE1_6C_NEW),
        ("插入设备前提", "### 6-A 掩蔽纹理预加载", STAGE1_DEVICE),
    ])
    r3 = apply(README, [
        ("插入 §8.54", "## 9. 尚未做", README_SECTION + "## 9. 尚未做"),
        ("追加 §9 第 64 项",
         "| 63 | ✅ **整场无屏幕冒烟：跑完 + 存下 + 数值对得上（D79，§8.53）** | "
         "24 个 PTB 桩 + `test/run_full_session.m` /",
         "| 63 | ✅ **整场无屏幕冒烟：跑完 + 存下 + 数值对得上（D79，§8.53）** | "
         "24 个 PTB 桩 + `test/run_full_session.m` /"),
    ])
    # §9 的 63 行是多行表格行：改为在 README 末尾追加，保持表格完整
    txt = README.read_text(encoding="utf-8")
    if "§8.54" in txt and "| 64 | 检查器的隐含常量" not in txt:
        if not txt.endswith("\n"):
            txt += "\n"
        txt += README_ITEM
        README.write_text(txt, encoding="utf-8", newline="\n")
        print("✅ README [§9 第 64 项]")
    elif "| 64 |" in txt:
        print("⏭  README [§9 第 64 项] 已存在")
    return 0 if (r1 and r2 and r3) else 1


if __name__ == "__main__":
    sys.exit(main())
