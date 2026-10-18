# -*- coding: utf-8 -*-
"""D92 落纸：主计划（决策/进度/变更日志/产出文件）+ README §8.63 / §9-76 +
Stage1 §6 命令块 + Stage7（手册版本行、工具链）+ PTB 说明（版本串、文件表）。

幂等；逐处断言命中 1 次。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
README = ROOT / "1_Code/DDM_Core/README.md"
STAGE1 = ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md"
STAGE7 = ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md"
PTB = ROOT / "1_Code/Experiment/exp_matlab/PTB免费版配置说明.md"


def patch(path, pairs, tag):
    src = path.read_text(encoding="utf-8")
    for old, new in pairs:
        n = src.count(old)
        assert n == 1, f"{tag} / {path.name}: 命中 {n} 次 → {old[:50]!r}"
        src = src.replace(old, new)
    path.write_text(src, encoding="utf-8", newline="\n")
    print(f"{tag}: {path.name} {len(src.splitlines())} 行")


# ---------------- 主计划 ----------------
D92_ROW = (
    "| **D92** | 2026-10-18 | ✅ **路径可移植：主程序按「本文件所在目录」解析掩蔽纹理；六条自测收成一个路径无关的 .bat**。"
    "① 用户问：实验室路径与本机不同、他习惯把 `exp_matlab` 整个文件夹拷过去，能否改成相对路径；"
    "② 查明旧版用裸文件名 `imread('self10-1.png')`（解析依据 = **当前目录**），而手册要求把当前目录设成本轮数据文件夹 ⇒ "
    "照手册做会在掩蔽预加载处报「文件不存在」（两者从一开始就冲突）；"
    "③ 修法（v4.8，1484 行）：`progDir = fileparts(mfilename('fullpath'))`、10 张 PNG 一律 `fullfile(progDir, …)`、"
    "启动即自检 10 张 PNG 缺哪张一次列全，并打印 `[路径] 程序目录/输出目录`；**数据仍写当前目录**（不改变「数据存本轮文件夹」的用法）；"
    "④ 新增 `test/check_portability.m`（**6/6**）：造临时目录冒充实验室机、`run_full_session(…, false)` 整场跑通，"
    "验「产物落在运行目录、程序目录无残留、启动回显两个路径」；若有人把纹理改回裸文件名，此测试必红；"
    "⑤ 新增 `test/run_selftest.bat`（八条命令一次跑完，`%~dp0..` 定位、**无任何绝对路径**）；"
    "⑥ 手册升 **v2.7**（§3.2 改双击 .bat、新增 §7.w「把整个文件夹拷到实验室机」） | "
    "`Exp_Design_Formal.m`（v4.7 → **v4.8**，1484 行）+ `test/run_full_session.m`（新增第 4 参数 `runInProgramDir`）+ "
    "`test/check_portability.m`（**新建**，6/6）+ `test/run_selftest.bat`（**新建**）+ "
    "`test/check_full_session.py`（29 → **32**，+A14/B30）+ 手册 v2.7（422 行、docx 18331 B） | "
    "用户侧：把 `exp_matlab` 拷到实验室机 → 双击 `test\\run_selftest.bat` → 六条全过再跑第一名真被试 Pilot（N≈8） |"
)
PROGRESS_ROW = (
    "| 2026-10-18 | **6（Pilot 前 · 路径可移植）** | 主程序掩蔽纹理改按程序目录解析（v4.8）、启动即自检 10 张 PNG 并打印两个路径；"
    "自测收成 `test\\run_selftest.bat`（无绝对路径）；新增 `check_portability.m` **6/6**；"
    "手册升 v2.7 ⇒ 整个 `exp_matlab` 文件夹可拷到任意机器 | "
    "`Exp_Design_Formal.m`（1484 行）、`test/check_portability.m`、`test/run_selftest.bat`、手册 v2.7 | "
    "用户侧：拷文件夹 → 双击 `run_selftest.bat` → 第一名真被试 Pilot |"
)
CHANGELOG_ROW = (
    "| 2026-10-18 | **新增 D92（路径可移植）**：程序 v4.8（`progDir` + 10 张 PNG 启动自检 + 打印程序/输出目录，数据仍写当前目录）；"
    "`test/run_full_session.m` 新增第 4 参数 `runInProgramDir`；`test/check_portability.m`（**新建**，6/6）；"
    "`test/run_selftest.bat`（**新建**，无绝对路径）；`check_full_session.py` **32/32**（+A14/B30）；"
    "手册 v2.7（422 行 / docx 18331 B，§3.2 改 .bat + §7.w）；README §8.63 + §9 第 76 项 |"
)
D92_FILES = (
    "| `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.7 → **v4.8**，1484 行）+ "
    "`test/run_full_session.m`（第 4 参数 `runInProgramDir`）+ `test/check_portability.m`（**新建**，6/6）+ "
    "`test/run_selftest.bat`（**新建**，八条一次跑完）+ `test/check_full_session.py`（**32/32**）+ "
    "主试手册 v2.7（422 行 / docx 18331 B）+ `_scratch/_apply_d92_paths.py` / `_apply_d92_driver.py` / "
    "`_apply_d92_checks.py` / `_apply_d92_manual.py` |"
)

plan_src = PLAN.read_text(encoding="utf-8")
lines = plan_src.split("\n")


def insert_after(pred, new_lines, tag):
    hits = [i for i, ln in enumerate(lines) if pred(ln)]
    assert len(hits) == 1, f"{tag}: 命中 {len(hits)} 次"
    i = hits[0]
    lines[i + 1 : i + 1] = new_lines


insert_after(lambda ln: ln.startswith("| **D91** | 2026-10-18 |"), [D92_ROW], "主计划 D92 决策行")
insert_after(lambda ln: "**6（Pilot 前）**" in ln and ln.startswith("| 2026-10-18 |"),
             [PROGRESS_ROW], "主计划 进度行")
insert_after(lambda ln: ln.startswith("| 2026-10-18 | **新增 D91"),
             [CHANGELOG_ROW], "主计划 变更日志")
lines.append(D92_FILES)
PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(f"主计划: {len(lines)} 行")

# ---------------- README ----------------
R863 = """### 8.63 路径写在哪：程序资源跟程序目录、数据跟当前目录（2026-10-18，D92）

**问题**：主程序用裸文件名读 10 张掩蔽纹理（`imread('self10-1.png')`），解析依据是**当前目录**；
而手册第 7 节要求「把 MATLAB 当前文件夹设成本轮数据文件夹」。两者从一开始就冲突——照手册做，
掩蔽预加载就会报文件不存在；反过来把当前目录设成程序目录，数据又会落到程序目录里、和代码混在一起。
用户的实际用法是把 `exp_matlab` 整个文件夹拷到实验室机，路径与本机不同，冲突立刻显形。

**修法（v4.8）**：

- `progDir = fileparts(mfilename('fullpath'))`；10 张 PNG 一律 `fullfile(progDir, …)`；
- 启动即自检 10 张 PNG（`assert(isempty(missingMask), …)` 一次列出所有缺失文件），
  并打印 `[路径] 程序目录（掩蔽纹理） = …` 与 `[路径] 输出目录（CSV/txt） = …`；
- **数据仍写当前目录**（`pwd`）：不改变「数据存本轮文件夹」的既有用法，也不动 25 列任何一列。

**牙齿**：

- `test/check_portability.m`（**6/6**）：造一个临时目录冒充实验室机、`cd` 进去、
  `run_full_session(1, 98, outDir, false)`（第 4 参数 `false` = 不 cd 到程序目录，脚本按名调用）
  跑完整场，验：整场无异常、576 行、产物落在**运行目录**、程序目录无残留、启动回显两个路径、
  掩蔽纹理没被拷进工作目录。把纹理改回裸文件名 ⇒ 这条必红（临时目录里没有 PNG）。
- `test/check_full_session.py` **A14**（静态）：`progDir` 三处 `fullfile(progDir, f)`、PNG 自检、
  v4.8 头注、裸文件名列表已消失。
- `test/run_selftest.bat`：八条命令一次跑完，用 `%~dp0..` 定位程序目录，**不含任何绝对路径**。

**边界**：这只解决「程序能不能找到自己的资源」。真实的 10 张 PNG 仍必须随文件夹一起拷；
启动自检只能告诉你缺哪张，不会替你补。

---

"""
R76 = (
    "| 76 | ✅ **路径可移植：程序资源跟程序目录、数据跟当前目录（D92，§8.63）** | "
    "旧版裸文件名 `imread('self10-1.png')` 依赖当前目录，与手册「当前目录 = 数据文件夹」冲突 ⇒ "
    "v4.8 改 `progDir = fileparts(mfilename('fullpath'))` + 10 张 PNG 启动自检 + 打印程序/输出目录；"
    "`test/check_portability.m` **6/6**（临时目录整场跑通、产物落运行目录、程序目录无残留）、"
    "`test/run_selftest.bat`（无绝对路径）、`check_full_session.py` **32/32**、手册 v2.7（§3.2 + §7.w） |\n"
)
patch(README, [
    ("\n## 9. 尚未做", "\n" + R863 + "## 9. 尚未做"),
], "README §8.63")
rd = README.read_text(encoding="utf-8").rstrip("\n")
assert rd.endswith(R76.rstrip("\n")) is False
README.write_text(rd + "\n" + R76.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
print(f"README: {len(README.read_text(encoding='utf-8').splitlines())} 行")

# ---------------- Stage1 §6 命令块 ----------------
OLD_CMDS = """```bat
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info"
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation"
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum"
matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); runbatch_full_session(1, 99)"
python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_full_session.py
```
"""
NEW_CMDS = """**做法（v2.7 / D92 起路径无关）**：在 `1_Code\\Experiment\\exp_matlab` 里双击

```bat
test\\run_selftest.bat
```

它用 `%~dp0..` 自己切到程序目录，把下面六条（另加两条开发者回归）依次跑完，末行给出 `all six commands returned 0`
或 `SOME STEP RETURNED NON-ZERO`。**整个 `exp_matlab` 文件夹拷到实验室机也不需要改任何路径。**

<details><summary>一条一条手动跑（都在 exp_matlab 目录下执行）</summary>

```bat
matlab -batch "addpath('test'); check_ask_info"
matlab -batch "addpath('test'); check_input_validation"
matlab -batch "addpath('test'); check_data_accum"
matlab -batch "addpath('test'); runbatch_full_session(1, 99)"
python -X utf8 test\\check_manual_d4.py
python -X utf8 test\\check_full_session.py
```
</details>
"""
patch(STAGE1, [
    (OLD_CMDS, NEW_CMDS),
    ("| `check_full_session.py` | `== 通过 29 / 未通过 0 ==` |",
     "| `check_full_session.py` | `== 通过 32 / 未通过 0 ==` |"),
    ("`runbatch_full_session` 27/27 + `check_full_session.py` 29/29 钉住。",
     "`runbatch_full_session` 27/27 + `check_full_session.py` 32/32（含 D92 的 A14/B30）钉住。"),
], "Stage1 §6")

# ---------------- Stage7 ----------------
patch(STAGE7, [
    ("| 文档 | `主试培训手册_Exp_Design_Formal.md`（v2.6，403 行）+ `.docx`（68121 B）",
     "| 文档 | `主试培训手册_Exp_Design_Formal.md`（v2.7，422 行）+ `.docx`（18331 B）"),
    ("""matlab -batch "cd('<仓库>\\1_Code\\Experiment\\exp_matlab'); addpath('test'); runbatch_full_session(1, 99)"
python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_full_session.py
python -X utf8 1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py""",
     """:: 路径无关做法（v2.7 / D92）：在 exp_matlab 里双击这个文件，八条一次跑完
test\\run_selftest.bat
:: 等价的手动版（都在 exp_matlab 目录下执行）
matlab -batch "addpath('test'); runbatch_full_session(1, 99)"
python -X utf8 test\\check_full_session.py
python -X utf8 test\\check_manual_d4.py"""),
], "Stage7")

# ---------------- PTB 说明 ----------------
ptb = PTB.read_text(encoding="utf-8")
old150 = "| `Exp_Design_Formal.m` | 正式实验程序 **v4.7**"
assert ptb.count(old150) == 1
ptb = ptb.replace(old150, "| `Exp_Design_Formal.m` | 正式实验程序 **v4.8**（掩蔽纹理按程序目录解析、启动自检 10 张 PNG；数据仍写当前目录）")
old152 = "| `主试培训手册_Exp_Design_Formal.md` / `.docx` | 主试培训手册（v2.6，D4 口径；§3.2 六条自测、§6.6「已知崩溃」、§3 刷新率须 60.004 Hz） |"
assert ptb.count(old152) == 1
ptb = ptb.replace(old152, "| `主试培训手册_Exp_Design_Formal.md` / `.docx` | 主试培训手册（**v2.7**，D4 口径；§3.2 自测改双击 `run_selftest.bat`、§7.w 拷文件夹、§6.6「已知崩溃」、§3 刷新率须 60.004 Hz） |")
old160 = "| `test/runbatch_full_session.m` | 整场冒烟命令行入口（写 UTF-8 日志，末行 `SUMMARY pass=27 fail=0`） |"
assert ptb.count(old160) == 1
ptb = ptb.replace(old160, old160 + "\n"
    "| `test/run_selftest.bat` | **八条自测一次跑完**（路径无关：`%~dp0..` 定位程序目录，可随文件夹整体拷走） |\n"
    "| `test/check_portability.m` | 可移植性回归（6/6）：临时目录冒充实验室机跑整场，验纹理解析与数据落点 |")
PTB.write_text(ptb, encoding="utf-8", newline="\n")
print(f"PTB说明: {len(ptb.splitlines())} 行")
