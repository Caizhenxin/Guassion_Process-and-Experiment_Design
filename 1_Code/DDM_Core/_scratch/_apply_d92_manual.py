# -*- coding: utf-8 -*-
"""D92 手册 v2.6 → v2.7：自测改路径无关的 run_selftest.bat、补 §7.w、版本串同步。

幂等；逐处断言命中 1 次。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md"
src = F.read_text(encoding="utf-8")
assert "v2.7（2026-10-18" not in src, "已打过 v2.7 补丁"

OLD_VER = ("> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.7）\n"
           "> 版本：v2.6（2026-10-18，v2.6 补「指导语一闪而过」症状与 v4.7 松键门槛；")
NEW_VER = ("> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.8）\n"
           "> 版本：v2.7（2026-10-18，v2.7 把六条自测改成路径无关的 `test\\run_selftest.bat`、补 §7.w「把整个文件夹拷到实验室机」并对应程序 v4.8；"
           "v2.6 补「指导语一闪而过」症状与 v4.7 松键门槛；")

OLD_SETUP = ("```matlab\n"
             "cd 'D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'\n"
             "setup_paths\n"
             "```")
NEW_SETUP = ("```matlab\n"
             "% 路径换成你这台机器上 exp_matlab 的实际位置（本行只是示例；实验室机不一样）\n"
             "cd 'D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'\n"
             "setup_paths\n"
             "```")

OLD_SELFTEST_HEAD = """在第一个「未响应」试次崩掉，见 6.6）。所以开机前先跑这六条，在 **Windows 命令行**里执行
（约 35 s，不需要被试在场）：

```bat
matlab -batch "cd('D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_ask_info"
matlab -batch "cd('D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_input_validation"
matlab -batch "cd('D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum"
matlab -batch "cd('D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'); addpath('test'); runbatch_full_session(1, 99)"
python -X utf8 D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab\\test\\check_full_session.py
python -X utf8 D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```

| 命令 | 看到什么算通过 |
|---|---|
| `check_ask_info` | 末行 `通过 40 / 未通过 0` |
| `check_input_validation` | 末行 `结果：51 通过 / 0 失败` |
| `check_data_accum` | 末行 `通过 33 / 未通过 0` |
| `runbatch_full_session(1, 99)` | 末行 `SUMMARY pass=27 fail=0`（**整场冒烟**：用 24 个假 PTB 桩在无屏幕环境真的跑完 576 试次，约 3 秒） |
| `check_full_session.py` | 末行 `== 通过 23 / 未通过 0 ==` |
| `check_manual_d4.py` | 末行 `共 40 项：通过 40 / 未通过 0` |
"""
NEW_SELFTEST_HEAD = """在第一个「未响应」试次崩掉，见 6.6）。所以开机前先跑这六条，不需要被试在场（约 50 s）。

**做法（v2.7 起，路径无关）**：在 `exp_matlab` 文件夹里双击

```bat
test\\run_selftest.bat
```

它会自己切到程序目录（用 `%~dp0..`），把六条依次跑完，最后一行明确告诉你
`all six commands returned 0`（六条都返回 0）还是 `SOME STEP RETURNED NON-ZERO`（后者**不要开始采集**）。
**整个 `exp_matlab` 文件夹拷到实验室机也不用改任何路径**——这正是 v2.7 要解决的问题。

<details><summary>要一条一条手动跑，或想看清每条在测什么（都在 exp_matlab 目录下执行）</summary>

| 命令 | 看到什么算通过 |
|---|---|
| `matlab -batch "addpath('test'); check_ask_info"` | 末行 `通过 40 / 未通过 0` |
| `matlab -batch "addpath('test'); check_input_validation"` | 末行 `结果：51 通过 / 0 失败` |
| `matlab -batch "addpath('test'); check_data_accum"` | 末行 `通过 33 / 未通过 0` |
| `matlab -batch "addpath('test'); runbatch_full_session(1, 99)"` | 末行 `SUMMARY pass=27 fail=0`（**整场冒烟**：24 个假 PTB 桩、无屏幕真跑 576 试次，约 3 秒） |
| `python -X utf8 test\\check_full_session.py` | 末行 `== 通过 32 / 未通过 0 ==` |
| `python -X utf8 test\\check_manual_d4.py` | 末行 `== 共 40 项：通过 40 / 未通过 0 ==` |

MATLAB 与 Python 必须已在 PATH 里。实验室机若提示"不是内部或外部命令"，用 MATLAB 的全路径
（例如 `E:\\matlab2023b\\bin\\matlab.exe -batch "addpath('test'); check_ask_info"`），Python 同理。
</details>
"""

OLD_7Y = '- **怎么确认跑的是 v4.7**：`type Exp_Design_Formal.m | findstr "v4.7"`，应打印 ★★ v4.7 本次修正 段头注。\n- **已生成的数据怎么办**：这 5 行**不改判据去迁就**'
NEW_7Y = '- **怎么确认跑的是 v4.8**：`type Exp_Design_Formal.m | findstr "v4.8"`，应打印 ★★ v4.8 本次修正 段头注。\n- **已生成的数据怎么办**：这 5 行**不改判据去迁就**'

OLD_7Z = '- **怎么确认跑的是 v4.7**：`type Exp_Design_Formal.m | findstr "v4.7"`，应打印 ★★ v4.7 本次修正 段头注。\n- **已生成的数据怎么办**：v4.6 及更早的场次里'
NEW_7Z = '- **怎么确认跑的是 v4.8**：`type Exp_Design_Formal.m | findstr "v4.8"`，应打印 ★★ v4.8 本次修正 段头注。\n- **已生成的数据怎么办**：v4.6 及更早的场次里'

ANCHOR_8 = "## 8. 数据当场核对清单（每名被试结束后 5 分钟内完成）"
NEW_7W = """### 7.w 把整个文件夹拷到实验室机（v2.7 新增，D92）

- **只拷 `exp_matlab` 这一个文件夹**（含 `test\\`、10 张掩蔽 PNG、`setup_paths.m`）到任意位置即可，不必拷整个仓库。
- **程序资源跟着程序目录走**（v4.8 起）：10 张掩蔽纹理按 `fileparts(mfilename('fullpath'))` 解析，
  所以 MATLAB 的当前文件夹**不需要**是程序目录；数据仍然写在**当前文件夹**（照本文第 7 节把当前文件夹设成本轮数据文件夹）。
- 启动会打印两行自检，**每次开机扫一眼**：
  `[路径] 程序目录（掩蔽纹理） = …` 与 `[路径] 输出目录（CSV/txt） = …`。
  若报「掩蔽纹理缺失（程序目录 = …）：xxx.png」，说明 PNG 没拷全（缺哪张会一次列全），当场补上再跑。
- 数据必须落在你设的那个数据文件夹里；如果打印的「输出目录」不是它，说明当前文件夹设错了，**当场停下改好再重跑**。

---

"""


def rep(old, new, tag):
    global src
    n = src.count(old)
    assert n == 1, f"{tag}: 命中 {n} 次"
    src = src.replace(old, new)


rep(OLD_VER, NEW_VER, "版本行")
rep(OLD_SETUP, NEW_SETUP, "§3.1 cd")
rep(OLD_SELFTEST_HEAD, NEW_SELFTEST_HEAD, "§3.2 命令块")
rep(OLD_7Y, NEW_7Y, "§7.y 版本串")
rep(OLD_7Z, NEW_7Z, "§7.z 版本串")
rep(ANCHOR_8, NEW_7W + ANCHOR_8, "§7.w 插入")

F.write_text(src, encoding="utf-8", newline="\n")
print(f"手册 v2.7 完成：{len(src.splitlines())} 行")
