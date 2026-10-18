# -*- coding: utf-8 -*-
"""把 v4.2 新增的"填写→确认"双层 while 块按层重排缩进（纯排版，不改语义）。

只处理 `Exp_Design_Formal.m` 中从外层 `while true   % ★ v4.2 外层` 到其匹配 `end`
（紧接 `%% 屏幕窗口` 之前）的这一段：整体 +4 空格，使内层循环缩进到 4、体到 8。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
f = ROOT / "1_Code/Experiment/exp_matlab/Exp_Design_Formal.m"
lines = f.read_text(encoding="utf-8").split("\n")

start = None
for i, ln in enumerate(lines):
    if ln.lstrip().startswith("while true   % ★ v4.2 外层"):
        start = i
        break
assert start is not None, "找不到外层 while"

# 结尾：下一个 `%% 屏幕窗口`
stop = None
for j in range(start + 1, len(lines)):
    if lines[j].startswith("%% 屏幕窗口"):
        stop = j
        break
assert stop is not None, "找不到 %% 屏幕窗口"

# 去掉 stop 之前那个空行
end_idx = stop - 1
while end_idx > start and lines[end_idx].strip() == "":
    end_idx -= 1

# 幂等：若首行已缩进 4 空格则视为已重排
if lines[start].startswith("    while true"):
    print("[跳过] 已重排过缩进")
    sys.exit(0)

for k in range(start, end_idx + 1):
    if lines[k].strip() == "":
        continue
    lines[k] = "    " + lines[k]

f.write_text("\n".join(lines), encoding="utf-8", newline="\n")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(f"已重排 {end_idx - start + 1} 行的缩进（L{start+1}–L{end_idx+1}）")
