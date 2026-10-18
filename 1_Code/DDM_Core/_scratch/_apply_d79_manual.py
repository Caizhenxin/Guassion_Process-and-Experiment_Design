# -*- coding: utf-8 -*-
"""_apply_d79_manual.py —— 主试手册升 v2.3：自测四条 → 六条（加整场冒烟），并同步版本行"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "主试培训手册_Exp_Design_Formal.md"

errors: list[str] = []
n = 0


def rep(old: str, new: str, name: str) -> None:
    global n
    raw = M.read_text(encoding="utf-8")
    if old not in raw:
        if new in raw:
            print(f"[跳过] {name}")
            return
        errors.append(f"{name}: 锚点未命中")
        return
    M.write_text(raw.replace(old, new, 1), encoding="utf-8", newline="\n")
    n += 1
    print(f"[替换] {name}")


REPO = "D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design"
MAT = f"matlab -batch \"cd('{REPO}\\1_Code\\Experiment\\exp_matlab'); addpath('test');"

rep(
    "> 版本：v2.2（2026-10-18，随 D4 设计定稿 + 程序 v4.2 组别加固重写；v2.1 补第 3.2 节自测；v2.2 增至四条自测并补 6.6 已知崩溃症状。上一版 v1.2 还是旧的「9 条件」设计）",
    "> 版本：v2.3（2026-10-18，随 D4 设计定稿 + 程序 v4.5；v2.1 补第 3.2 节自测；v2.2 增至四条并补 6.6 已知崩溃症状；v2.3 增至六条并加「整场冒烟」，对应程序 v4.5。上一版 v1.2 还是旧的「9 条件」设计）",
    "版本行 v2.2→v2.3",
)

rep(
    "- [ ] **本机自测四条全过**（约 25 s；见第 3.2 节）——任一条 ❌ 就不要开始采集",
    "- [ ] **本机自测六条全过**（约 35 s；见第 3.2 节）——任一条 ❌ 就不要开始采集",
    "准备清单 四条→六条",
)

rep(
    "### 3.2 本机自测四条（换电脑 / 改过程序 / 换了手册之后必做）",
    "### 3.2 本机自测六条（换电脑 / 改过程序 / 换了手册之后必做）",
    "3.2 标题",
)

rep(
    "在第一个「未响应」试次崩掉，见 6.6）。所以开机前先跑这四条，在 **Windows 命令行**里执行\n（约 25 s，不需要被试在场）：",
    "在第一个「未响应」试次崩掉，见 6.6）。所以开机前先跑这六条，在 **Windows 命令行**里执行\n（约 35 s，不需要被试在场）：",
    "3.2 引言 四条→六条",
)

rep(
    f"""{MAT} check_data_accum"
python -X utf8 {REPO}\\1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```""",
    f"""{MAT} check_data_accum"
{MAT} runbatch_full_session(1, 99)"
python -X utf8 {REPO}\\1_Code\\Experiment\\exp_matlab\\test\\check_full_session.py
python -X utf8 {REPO}\\1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```""",
    "3.2 命令块 加两条",
)

rep(
    "| `check_data_accum` | 末行 `通过 33 / 未通过 0` |\n| `check_manual_d4.py` | 末行 `共 40 项：通过 40 / 未通过 0` |\n",
    "| `check_data_accum` | 末行 `通过 33 / 未通过 0` |\n"
    "| `runbatch_full_session(1, 99)` | 末行 `SUMMARY pass=27 fail=0`（**整场冒烟**：用 24 个假 PTB 桩在无屏幕环境真的跑完 576 试次，约 3 秒） |\n"
    "| `check_full_session.py` | 末行 `== 通过 23 / 未通过 0 ==` |\n"
    "| `check_manual_d4.py` | 末行 `共 40 项：通过 40 / 未通过 0` |\n",
    "3.2 表格 加两行",
)

rep(
    "四条全过才动机器。任一条 ❌ ⇒ 把整屏输出**截屏发给实验负责人**，不要自己修、也不要跳过。",
    "六条全过才动机器。任一条 ❌ ⇒ 把整屏输出**截屏发给实验负责人**，不要自己修、也不要跳过。\n"
    "\n"
    "> 冒烟那两条会往 `test\\_full_session_out\\` 里写两份**假数据**（组 1 / 组 2 的 99 号「被试」）。\n"
    "> 看完即可删，**不要**把它们当成真实数据、也不要和真实数据放同一目录。",
    "3.2 四条全过→六条",
)

if errors:
    print("\n=== 失败 ===")
    for e in errors:
        print("  ✗", e)
    sys.exit(1)
print(f"\n手册共替换 {n} 处")
