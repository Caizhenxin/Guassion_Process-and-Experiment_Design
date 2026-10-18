# -*- coding: utf-8 -*-
"""D92：程序路径可移植（掩蔽纹理按 .m 所在目录解析，数据仍写当前目录）+ 启动自检。

幂等；逐处断言命中 1 次。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROG = ROOT / "1_Code/Experiment/exp_matlab/Exp_Design_Formal.m"

HEADER = [
    "% ★★ v4.8 本次修正（2026-10-18，路径可移植性；D92）★★",
    "%   (#1) 掩蔽纹理用裸文件名 imread('self10-1.png') ⇒ 解析依据是【当前目录】。而手册第 7 节",
    "%        要求把当前目录设成本轮数据文件夹，两者冲突：照着手册做，预加载就会报”文件不存在”。",
    "%        用户的实际习惯是把 exp_matlab 整个文件夹拷到实验室机器，路径与本机不同。",
    "%        修法：progDir = fileparts(mfilename('fullpath'))，10 张掩蔽纹理一律用",
    "%        fullfile(progDir, ...) 解析；数据仍写【当前目录】（不改变”数据存本轮文件夹”的用法）。",
    "%   (#2) 启动时打印【程序目录】与【输出目录】，并自检 10 张 PNG 是否齐全，",
    "%        缺哪张一次性报出（旧版要等到掩蔽预加载才报，且只说第一个）。",
    "%",
    "",
]

BLOCK = [
    "% 路径锚定（★ v4.8 / D92）：程序资源跟着【本文件所在目录】走，数据仍写【当前目录】",
    "progDir = fileparts(mfilename('fullpath'));",
    "if isempty(progDir), progDir = pwd; end",
    "dataDir = pwd;",
    "maskFiles = {'self10-1.png', 'self10-2.png', 'self10-3.png', 'self10-4.png', 'self10-5.png', ...",
    "             'stranger10-1.png', 'stranger10-2.png', 'stranger10-3.png', 'stranger10-4.png', 'stranger10-5.png'};",
    "missingMask = maskFiles(~cellfun(@(f) exist(fullfile(progDir, f), 'file') == 2, maskFiles));",
    "assert(isempty(missingMask), 'Exp_Design_Formal:maskMissing', ...",
    "    '掩蔽纹理缺失（程序目录 = %s）：%s', progDir, strjoin(missingMask, ', '));",
    "fprintf('[路径] 程序目录（掩蔽纹理） = %s\\n', progDir);",
    "fprintf('[路径] 输出目录（CSV/txt） = %s\\n', dataDir);",
    "",
]

OLD_SELF = ("selfMaskImages = {'self10-1.png', 'self10-2.png', 'self10-3.png', "
            "'self10-4.png', 'self10-5.png'};")
OLD_STR = ("strangerMaskImages = {'stranger10-1.png', 'stranger10-2.png', 'stranger10-3.png', "
           "'stranger10-4.png', 'stranger10-5.png'};")
NEW_LISTS = [
    "selfMaskImages     = cellfun(@(f) fullfile(progDir, f), maskFiles(1:5),  'UniformOutput', false);",
    "strangerMaskImages = cellfun(@(f) fullfile(progDir, f), maskFiles(6:10), 'UniformOutput', false);",
]

src = PROG.read_text(encoding="utf-8")
assert "v4.8 本次修正" not in src, "已打过 v4.8 补丁"
lines = src.split("\n")


def idx(pred, tag):
    hits = [i for i, ln in enumerate(lines) if pred(ln)]
    assert len(hits) == 1, f"{tag}: 命中 {len(hits)} 次"
    return hits[0]


# 1) 头注：插在 %% 被试基础信息 之前
i = idx(lambda ln: ln.startswith("%% 被试基础信息"), "v4.8 头注锚点")
lines = lines[:i] + HEADER + lines[i:]

# 2) 路径块：插在 data = exp_new_data(25); 之后
i = idx(lambda ln: ln.startswith("data = exp_new_data(25);"), "路径块锚点")
lines = lines[: i + 1] + [""] + BLOCK + lines[i + 1 :]

# 3) 掩蔽纹理列表改为 fullfile
i = idx(lambda ln: ln.startswith("selfMaskImages = {"), "selfMaskImages")
assert lines[i] == OLD_SELF, f"selfMaskImages 原文不符：{lines[i]!r}"
j = idx(lambda ln: ln.startswith("strangerMaskImages = {"), "strangerMaskImages")
assert lines[j] == OLD_STR, f"strangerMaskImages 原文不符：{lines[j]!r}"
assert j == i + 1, f"两行不相邻：{i} / {j}"
lines = lines[:i] + NEW_LISTS + lines[j + 1 :]

PROG.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(f"v4.8 补丁完成：{PROG.name} {len(lines)} 行")
