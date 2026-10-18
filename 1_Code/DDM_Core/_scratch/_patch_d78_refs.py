# -*- coding: utf-8 -*-
"""_patch_d78_refs.py —— 版本引用对齐：Stage 1 行号口径、Stage 7 程序版本、PTB 配置说明两行"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S1 = ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md"
S7 = ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md"
PTB = ROOT / "1_Code/Experiment/exp_matlab/PTB免费版配置说明.md"

msgs: list[str] = []


def replace_once(text, old, new, tag):
    if new in text:
        msgs.append(f"[跳过] {tag}")
        return text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"❌ {tag}：命中 {n} 次")
    msgs.append(f"[替换] {tag}")
    return text.replace(old, new)


def insert_after(text, prefix, block, tag):
    first = block.split("\n")[0]
    if first in text:
        msgs.append(f"[跳过] {tag}")
        return text
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"❌ {tag}：锚点 {prefix!r} 命中 {len(hits)} 行")
    i = hits[0]
    lines[i + 1:i + 1] = block.split("\n")
    msgs.append(f"[插入] {tag}（锚点 L{i + 1}）")
    return "\n".join(lines)


# ---------------- Stage 1：行号口径说明
t = S1.read_text(encoding="utf-8")
t = insert_after(
    t,
    "> 权威性：本文件是 Stage 1 的唯一验证记录。",
    ">\n"
    "> **行号口径（2026-10-18，D78）**：§2–§5 里的 `L…` 是按 **v4（1313 行）** 记的。现行程序是 **v4.4（1357 行）**——v4.2/v4.3 把「弹窗 + 校验 +\n"
    "> 主试确认」抽成 `exp_ask_subject_info.m`，v4.4 把逐试次容器从 `table()` 换成 cell（`exp_new_data.m`/`exp_data_table.m`），行号整体后移 40 余行。\n"
    "> 因此**不要拿本文件的 `L…` 去数现行文件的行**：每处引用都附了原文代码串，用该串搜；行为判据以 `test/check_ask_info`、`test/check_data_accum`、\n"
    "> `test/check_input_validation`、`test/check_manual_d4.py` 四条自测为准（见 §6 第 0 步）。\n",
    "S1 行号口径",
)
S1.write_text(t, encoding="utf-8", newline="\n")

# ---------------- Stage 7：程序版本
t = S7.read_text(encoding="utf-8")
t = replace_once(t, "数据文件由 `Exp_Design_Formal.m`（**v4.1，1325 行**）写出",
                 "数据文件由 `Exp_Design_Formal.m`（**v4.4，1357 行**）写出", "S7 程序版本")
S7.write_text(t, encoding="utf-8", newline="\n")

# ---------------- PTB 配置说明
t = PTB.read_text(encoding="utf-8")
t = replace_once(t, "| `主试培训手册_Exp_Design_Formal.md` / `.docx` | 主试培训手册（v2.1，D4 口径） |",
                 "| `主试培训手册_Exp_Design_Formal.md` / `.docx` | 主试培训手册（v2.2，D4 口径；含 §6.6「已知崩溃：第一个未响应试次」） |",
                 "PTB 手册版本")
t = insert_after(
    t,
    "| `主试培训手册_Exp_Design_Formal.md` / `.docx` |",
    "| `exp_new_data.m` | 逐试次累积容器（**0×25 cell**；不要改回 `table()`，见 D78） |\n"
    "| `exp_data_table.m` | 累积 cell → `table` 的一次性转换（char 列转 `string` 去补齐空格） |\n"
    "| `test/check_data_accum.m` | 无屏幕自测：数据累积与保存（`通过 24 / 未通过 0`） |",
    "PTB 新增三行",
)
t = replace_once(t, "| `Exp_Design_Formal.m` | 正式实验程序（D4：4 个 P 组，全部带掩蔽；组别只接受 1–4） |",
                 "| `Exp_Design_Formal.m` | 正式实验程序 **v4.4**（D4：4 个 P 组，全部带掩蔽；组别只接受 1–4；数据累积用 cell，见 D78） |",
                 "PTB 程序版本")
PTB.write_text(t, encoding="utf-8", newline="\n")

for m in msgs:
    print(m)
print("完成")
