# -*- coding: utf-8 -*-
"""_patch_manual_v22.py —— 手册 v2.1 → v2.2（D78：第四条自测 + §6.6 已知崩溃症状）

幂等：锚点唯一性断言；已打过则跳过。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M = ROOT / "1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md"

PAIRS = [
    ("### 3.2 本机自测三条（换电脑 / 改过程序 / 换了手册之后必做）",
     "### 3.2 本机自测四条（换电脑 / 改过程序 / 换了手册之后必做）"),
    ("""程序、校验函数和本手册是**三个独立文件**，任何一方改了而另一方没跟上，症状就是主试被弹窗拒绝
（2026-10-18 就发生过：手册还是旧版，按它填「组别 7」直接被拒绝）。所以开机前先跑这三条，
在 **Windows 命令行**里执行（约 20 s，不需要被试在场）：""",
     """程序、累积/保存函数和本手册是**几个独立文件**，任何一方改了而另一方没跟上，症状就是主试被弹窗拒绝
或跑到一半崩掉（2026-10-18 就发生过两次：手册还是旧版，按它填「组别 7」被拒；以及 V4.3 的数据表
在第一个「未响应」试次崩掉，见 6.6）。所以开机前先跑这四条，在 **Windows 命令行**里执行
（约 25 s，不需要被试在场）："""),
    ("""python -X utf8 D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```""",
     """matlab -batch "cd('D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab'); addpath('test'); check_data_accum"
python -X utf8 D:\\GitHub_programe\\GitHub\\Guassion-Process-Experiment-Design\\1_Code\\Experiment\\exp_matlab\\test\\check_manual_d4.py
```"""),
    ("""| `check_manual_d4.py` | 末行 `共 40 项：通过 40 / 未通过 0` |

三条全过才动机器。任一条 ❌ ⇒ 把整屏输出**截屏发给实验负责人**，不要自己修、也不要跳过。""",
     """| `check_data_accum` | 末行 `通过 24 / 未通过 0` |
| `check_manual_d4.py` | 末行 `共 40 项：通过 40 / 未通过 0` |

四条全过才动机器。任一条 ❌ ⇒ 把整屏输出**截屏发给实验负责人**，不要自己修、也不要跳过。

> `check_manual_d4.py` 守的是「程序常量 / 本手册 / Word 版 / 自测**四者口径一致**」；
> 改了 4 组以外的东西（例如新增输出列）必须手工更新它，否则它会静默放行。"""),
    ("""### 6.5 被试中途不适 / 明确要求停止""",
     """### 6.6 跑到某一试次突然崩，报「赋值右侧的值的宽度错误」

- 症状（v4.3 及更早）：先刷出若干条「警告: 赋值时将各行添加到了表格中，但并未对表格中所有现有的变量赋值」，
  随后 `错误使用 Exp_Design_Formal / 赋值右侧的值的宽度错误。赋值需要宽度为 1 的值。`
- 这是**已知缺陷，v4.4 已修**（D78）：旧版用 `table()` 逐行累积，第一行按键 `f`（1 字符）把该列宽度锁死，
  第一个**未响应**试次要写 `NA`（2 字符）就崩。所以它**只在被试第一次超时的时候**才出现。
- 现场处理：本次作废（数据只在正常结束才写 CSV），升级到 v4.4 后同编号重跑。
- 怎么确认你跑的是新版：执行 5.1 前输入 `type Exp_Design_Formal.m | findstr "v4.4"`，应打印 v4.4 段头注。

### 6.5 被试中途不适 / 明确要求停止"""),
]

t = M.read_text(encoding="utf-8")
for old, new in PAIRS:
    if new in t:
        print("[跳过] " + new.splitlines()[0][:50])
        continue
    if t.count(old) != 1:
        raise SystemExit(f"❌ 锚点命中 {t.count(old)} 次：{old.splitlines()[0][:60]}")
    t = t.replace(old, new)
    print("[替换] " + old.splitlines()[0][:50])

t = t.replace("> 版本：v2.1（2026-10-18，随 D4 设计定稿 + 程序 v4.2 组别加固重写；v2.1 补第 3.2 节「本机自测三条」。上一版 v1.2 还是旧的「9 条件」设计）",
              "> 版本：v2.2（2026-10-18，随 D4 设计定稿 + 程序 v4.2 组别加固重写；v2.1 补第 3.2 节自测；v2.2 增至四条自测并补 6.6 已知崩溃症状。上一版 v1.2 还是旧的「9 条件」设计）")
t = t.replace("> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.3）",
              "> 适用程序：`1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4.4）")

M.write_text(t, encoding="utf-8", newline="\n")
print(f"written {M.name}: {t.count(chr(10)) + 1} 行")
